#!/usr/bin/env python3
"""Submit field-review annotations from online Shujuji prelabels.

This mirrors the web UI's field-review flow closely enough for batch work:
for each present PR#28 field, choose the same suggested evidence basket the UI
would prefill, mark selected mappings accepted, reject same-field alternatives,
and save the final annotation through the public service API.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PR28_FIELDS = [
    "Q_terminator",
    "Q1_fix_ident",
    "Q2_altitude_constraint",
    "Q3_turn",
    "Q4_course_or_radial",
    "Q5_hold_params",
]

SUPPORT_REQUIRES_EVIDENCE = {
    "direct_visible",
    "visible_joint",
    "rule_default_completion",
}

DATASET_LABELS = {
    "formal300": "正式集 300 张",
    "practice10": "练习集 10 张",
}


class ApiError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def deep_clone(value: Any) -> Any:
    return copy.deepcopy(value)


def unknown_answer() -> dict[str, Any]:
    return {"status": "unknown", "value": None}


def is_present_answer(answer: dict[str, Any] | None) -> bool:
    return bool(answer and answer.get("status") == "present")


def unique_list(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values or []:
        if not value:
            continue
        item = str(value)
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def support_mode_from_review(raw: dict[str, Any] | None, evidence_ids: list[str] | None = None) -> str:
    evidence_ids = evidence_ids or []
    status = (raw or {}).get("support_mode") or (raw or {}).get("review_status") or "pending"
    if status == "supported_by_chart":
        return "visible_joint" if len(evidence_ids) > 1 else "direct_visible" if evidence_ids else "pending"
    if status == "no_direct_chart_evidence":
        return "insufficient_for_encoding"
    if status == "implicit_or_derived":
        return "rule_default_completion"
    return status


def canonical_leg_index_for_mapping(mapping: dict[str, Any], target: dict[str, Any]) -> int | None:
    if isinstance(mapping.get("canonical_leg_index"), int):
        return mapping["canonical_leg_index"]
    candidate_leg_id = mapping.get("candidate_leg_id") or ""
    for leg in target.get("candidate_legs") or []:
        if leg.get("candidate_leg_id") == candidate_leg_id and isinstance(leg.get("canonical_leg_index"), int):
            return leg["canonical_leg_index"]
    match = re.search(r"__ma(\d+)$", str(candidate_leg_id))
    return int(match.group(1)) if match else None


def field_key(leg_index: int | None, field_name: str) -> str:
    return f"leg{leg_index}.{field_name}" if leg_index and field_name else ""


def field_key_for_mapping(mapping: dict[str, Any], target: dict[str, Any]) -> str:
    return field_key(canonical_leg_index_for_mapping(mapping, target), mapping.get("field_name") or "")


def canonical_field_for_mapping(mapping: dict[str, Any], target: dict[str, Any]) -> dict[str, Any] | None:
    if mapping.get("expected_answer"):
        return mapping["expected_answer"]
    candidate_leg_id = mapping.get("candidate_leg_id") or ""
    for leg in target.get("candidate_legs") or []:
        if leg.get("candidate_leg_id") != candidate_leg_id:
            continue
        for field in leg.get("target_fields") or []:
            if (field.get("field_name") or field.get("name")) == mapping.get("field_name"):
                return field.get("expected_answer")
    return None


def build_field_rows(target: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for leg in target.get("candidate_legs") or []:
        leg_index = leg.get("canonical_leg_index")
        if not isinstance(leg_index, int):
            leg_index = canonical_leg_index_for_mapping({"candidate_leg_id": leg.get("candidate_leg_id")}, target)
        for field in leg.get("target_fields") or []:
            field_name = field.get("field_name") or field.get("name") or ""
            answer = field.get("expected_answer")
            rows.append(
                {
                    "key": field_key(leg_index, field_name),
                    "candidate_leg_id": leg.get("candidate_leg_id") or "",
                    "canonical_leg_index": leg_index,
                    "leg_type": leg.get("leg_type") or "",
                    "field_name": field_name,
                    "expected_value": field.get("expected_value", field.get("value", "")),
                    "expected_answer": answer,
                    "requires_review": is_present_answer(answer),
                    "auto_status": answer.get("status") if answer and answer.get("status") != "present" else None,
                }
            )
    return rows


def normalize_field_reviews(source: Any) -> dict[str, dict[str, Any]]:
    if isinstance(source, list):
        return {item.get("field_key"): item for item in source if isinstance(item, dict) and item.get("field_key")}
    if isinstance(source, dict):
        return deep_clone(source)
    return {}


def normalize_region(region: dict[str, Any], index: int, chart_id: str) -> dict[str, Any]:
    region_id = region.get("region_id") or region.get("final_region_id") or region.get("source_region_id") or f"{chart_id}_auto_{index:03d}"
    reviewed_mappings = region.get("candidate_mappings") or region.get("candidate_mappings_reviewed")
    if reviewed_mappings is None:
        reviewed_mappings = []
        for mapping in region.get("accepted_mappings") or []:
            item = deep_clone(mapping)
            item["human_decision"] = "accepted"
            reviewed_mappings.append(item)
    human_review = region.get("human_review") or {}
    return {
        **deep_clone(region),
        "region_id": region_id,
        "source_region_id": region.get("source_region_id") or region_id,
        "region_type": region.get("region_type") or "",
        "bbox": region.get("bbox") or {"x": 0, "y": 0, "width": 0.1, "height": 0.1},
        "label": region.get("label") or "",
        "ocr_text": region.get("ocr_text") or "",
        "annotation_scope": region.get("annotation_scope") or "",
        "element_role": region.get("element_role") or "",
        "expected_visual_value": region.get("expected_visual_value") or "",
        "step_id": region.get("step_id") or "",
        "parent_step_region_id": region.get("parent_step_region_id") or "",
        "source_candidate_leg_id": region.get("source_candidate_leg_id") or "",
        "source_leg_type": region.get("source_leg_type") or "",
        "source_field_name": region.get("source_field_name") or "",
        "is_formal_annotation_candidate": bool(region.get("is_formal_annotation_candidate")),
        "candidate_mappings": deep_clone(reviewed_mappings),
        "needs_human_decision": region.get("needs_human_decision", True),
        "human_review": {
            "review_action": region.get("review_action") or human_review.get("review_action") or "pending",
            "adjusted_bbox": human_review.get("adjusted_bbox"),
            "final_region_type": human_review.get("final_region_type") or region.get("region_type") or "",
            "notes": region.get("notes") or human_review.get("notes") or "",
        },
    }


def expected_answer_value(row: dict[str, Any]) -> Any:
    answer = row.get("expected_answer") or {}
    return answer.get("value")


def visible_label_text(label: Any) -> str:
    # Labels often look like "ALTITUDE_TEXT: 12000 -> AT_OR_ABOVE 12000 ft".
    # The text after "->" is the target-side interpretation, not independent chart evidence.
    return " ".join(str(part).split("->", 1)[0] for part in str(label or "").split(";"))


def region_text(region: dict[str, Any]) -> str:
    return " ".join(
        [
            str(region.get("region_type") or ""),
            visible_label_text(region.get("label")),
            str(region.get("ocr_text") or ""),
            str(region.get("element_role") or ""),
        ]
    ).upper()


def region_has_token(region: dict[str, Any], token: Any) -> bool:
    wanted = str(token or "").strip().upper()
    if not wanted:
        return False
    return re.search(rf"(^|[^A-Z0-9]){re.escape(wanted)}([^A-Z0-9]|$)", region_text(region)) is not None


def region_has_number(region: dict[str, Any], value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    candidates = unique_list(
        [
            str(round(number)),
            "" if number.is_integer() else f"{number:.1f}".rstrip("0").rstrip("."),
            "" if number.is_integer() else str(int(number // 1)),
            "" if number.is_integer() else str(int(number // 1 + 1)),
        ]
    )
    text = region_text(region)
    return any(re.search(rf"(^|[^0-9]){re.escape(candidate)}([^0-9]|$)", text) for candidate in candidates if candidate)


def is_holding_param_region(region: dict[str, Any]) -> bool:
    region_type = region.get("region_type") or ""
    return region_type in {
        "HOLDING_TIME_TEXT",
        "DME_DISTANCE_TEXT",
        "TRACK_OR_RADIAL_TEXT",
        "RADIAL_TEXT",
        "OUTBOUND_INBOUND_MARK",
    }


def is_coarse_missed_approach_text(region: dict[str, Any]) -> bool:
    return (
        (region.get("region_type") or "") == "MISSED_APPROACH_TEXT"
        and (
            region.get("annotation_scope") == "upper_coarse_formal_annotation"
            or "UPPER COARSE FORMAL ANNOTATION" in region_text(region)
        )
    )


def same_source_leg(row: dict[str, Any], region: dict[str, Any], target: dict[str, Any]) -> bool:
    if region.get("source_candidate_leg_id") and row.get("candidate_leg_id"):
        return region.get("source_candidate_leg_id") == row.get("candidate_leg_id")
    for mapping in region.get("candidate_mappings") or []:
        if canonical_leg_index_for_mapping(mapping, target) == row.get("canonical_leg_index"):
            return True
    return False


def field_evidence_rank(row: dict[str, Any], region: dict[str, Any]) -> int:
    region_type = region.get("region_type") or ""
    value = expected_answer_value(row)
    field_name = row.get("field_name")
    if region_type == "MISSED_APPROACH_TEXT":
        if is_coarse_missed_approach_text(region):
            return 99
        return 60
    if field_name == "Q1_fix_ident":
        if region_type in {"FIX_TEXT", "NAVAID_TEXT"} and region_has_token(region, value):
            return 0
        return 99
    if field_name == "Q2_altitude_constraint":
        if region_type == "ALTITUDE_TEXT" and isinstance(value, dict) and region_has_number(region, value.get("altitude_ft")):
            return 0
        return 99
    if field_name == "Q3_turn":
        if region_type == "TURN_PHRASE" and region_has_token(region, value):
            return 0
        return 99
    if field_name == "Q4_course_or_radial":
        if isinstance(value, dict) and value.get("type") == "navaid_radial":
            if region_type == "NAVAID_TEXT" and region_has_token(region, value.get("navaid") or value.get("navaid_ident")):
                return 0
            if region_type in {"RADIAL_TEXT", "TRACK_OR_RADIAL_TEXT"} and region_has_number(region, value.get("radial_deg") or value.get("course_deg")):
                return 0
            return 99
        if isinstance(value, dict) and value.get("type") == "course_deg" and region_type in {"HEADING_TEXT", "TRACK_OR_RADIAL_TEXT"} and region_has_number(region, value.get("course_deg")):
            return 0
        return 99
    if field_name == "Q5_hold_params":
        if region_type in {"HOLDING_TIME_TEXT", "DME_DISTANCE_TEXT", "TRACK_OR_RADIAL_TEXT", "RADIAL_TEXT", "OUTBOUND_INBOUND_MARK"}:
            return 4
        return 99
    return 50


def candidate_mappings_for_field(row: dict[str, Any], regions: list[dict[str, Any]], target: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for region in regions:
        for mapping in region.get("candidate_mappings") or []:
            if field_key_for_mapping(mapping, target) == row["key"]:
                result.append({"region": region, "mapping": mapping})
    return result


def compatible_evidence_regions_for_field(row: dict[str, Any], regions: list[dict[str, Any]], target: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for region in regions:
        if not same_source_leg(row, region, target):
            continue
        rank = field_evidence_rank(row, region)
        if rank >= 50:
            continue
        if row.get("field_name") == "Q4_course_or_radial":
            value = expected_answer_value(row)
            if not (isinstance(value, dict) and value.get("type") == "navaid_radial"):
                if region.get("region_type") not in {"HEADING_TEXT", "TRACK_OR_RADIAL_TEXT"}:
                    continue
        result.append({"region": region, "rank": rank, "source": "compatible-region"})
    return result


def suggested_evidence_entries_for_field(row: dict[str, Any], regions: list[dict[str, Any]], target: dict[str, Any]) -> list[dict[str, Any]]:
    direct: list[dict[str, Any]] = []
    for item in candidate_mappings_for_field(row, regions, target):
        mapping = item["mapping"]
        if (mapping.get("human_decision") or "pending") in {"rejected", "needs_discussion"}:
            continue
        rank = field_evidence_rank(row, item["region"])
        if rank < 90:
            direct.append({**item, "rank": rank, "source": "candidate-mapping"})
    compatible = compatible_evidence_regions_for_field(row, regions, target)
    by_region: dict[str, dict[str, Any]] = {}
    for item in [*direct, *compatible]:
        region_id = item["region"]["region_id"]
        existing = by_region.get(region_id)
        if not existing or item["rank"] < existing["rank"]:
            by_region[region_id] = item
    decision_rank = {"accepted": 0, "changed": 1, "pending": 2}
    ranked = sorted(
        by_region.values(),
        key=lambda item: (
            item["rank"],
            decision_rank.get((item.get("mapping") or {}).get("human_decision") or "pending", 3),
        ),
    )
    fine = [item for item in ranked if item["rank"] < 50]
    return fine


def evidence_area_key(region: dict[str, Any]) -> str:
    region_type = region.get("region_type") or ""
    scope = region.get("annotation_scope") or ""
    region_id = region.get("region_id") or ""
    if region_type == "MISSED_APPROACH_TEXT":
        return "ma_text"
    if region_type == "PLAN_VIEW":
        return "plan_view"
    if (
        region_type == "MISSED_APPROACH_DETAIL_AREA"
        or "lower_detail" in scope
        or "icon_aligned" in scope
        or "_iconalign_" in region_id
        or "curated_" in str(region.get("element_role") or "")
    ):
        return "lower_detail"
    return evidence_source_for_region(region)


def direct_evidence_ids_for_group(row: dict[str, Any], items: list[dict[str, Any]]) -> list[str]:
    value = expected_answer_value(row)
    field_name = row.get("field_name")

    def matching_ids(predicate: Any) -> list[str]:
        return unique_list([item["region"]["region_id"] for item in items if predicate(item["region"])])

    if field_name == "Q1_fix_ident":
        return matching_ids(lambda region: region.get("region_type") in {"FIX_TEXT", "NAVAID_TEXT"} and region_has_token(region, value))
    if field_name == "Q2_altitude_constraint":
        return matching_ids(lambda region: region.get("region_type") == "ALTITUDE_TEXT" and isinstance(value, dict) and region_has_number(region, value.get("altitude_ft")))
    if field_name == "Q3_turn":
        return matching_ids(lambda region: region.get("region_type") == "TURN_PHRASE" and region_has_token(region, value))
    if field_name == "Q4_course_or_radial" and isinstance(value, dict):
        if value.get("type") == "navaid_radial":
            navaid_ids = matching_ids(lambda region: region.get("region_type") == "NAVAID_TEXT" and region_has_token(region, value.get("navaid") or value.get("navaid_ident")))
            radial_ids = matching_ids(lambda region: region.get("region_type") in {"RADIAL_TEXT", "TRACK_OR_RADIAL_TEXT"} and region_has_number(region, value.get("radial_deg") or value.get("course_deg")))
            return unique_list([*navaid_ids, *radial_ids]) if navaid_ids and radial_ids else []
        if value.get("type") == "course_deg":
            return matching_ids(lambda region: region.get("region_type") in {"HEADING_TEXT", "TRACK_OR_RADIAL_TEXT"} and region_has_number(region, value.get("course_deg")))
    return []


def suggested_evidence_groups_for_field(row: dict[str, Any], regions: list[dict[str, Any]], target: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in suggested_evidence_entries_for_field(row, regions, target):
        grouped.setdefault(evidence_area_key(item["region"]), []).append(item)
    groups: list[dict[str, Any]] = []
    for area_key, items in grouped.items():
        direct_ids = direct_evidence_ids_for_group(row, items)
        if direct_ids:
            groups.append({"area_key": area_key, "items": items, "direct_ids": direct_ids})
    return sorted(
        groups,
        key=lambda group: (
            min(item["rank"] for item in group["items"]),
            len(group["direct_ids"]),
            group["area_key"],
        ),
    )


def suggested_evidence_ids_for_field(
    row: dict[str, Any],
    rows: list[dict[str, Any]],
    regions: list[dict[str, Any]],
    target: dict[str, Any],
) -> list[str]:
    if row.get("field_name") in {"Q_terminator", "Q5_hold_params"}:
        return []
    if row.get("leg_type") == "HM" and row.get("field_name") in {"Q1_fix_ident", "Q2_altitude_constraint"}:
        return []
    groups = suggested_evidence_groups_for_field(row, regions, target)
    if groups:
        return groups[0]["direct_ids"]
    return []


def evidence_source_for_region(region: dict[str, Any] | None) -> str:
    if not region:
        return "other_chart_evidence"
    region_type = region.get("region_type") or ""
    if region.get("evidence_source"):
        return region["evidence_source"]
    if region_type == "MISSED_APPROACH_TEXT":
        return "ma_text"
    if region_type == "PLAN_VIEW":
        return "plan_view"
    if region_type in {"MISSED_APPROACH_DETAIL_AREA", "MISSED_APPROACH_ICON", "MISSED_APPROACH_STEP_BOX", "CLIMB_ARROW"}:
        return "icon_detail"
    if region_type in {"FIX_SYMBOL", "PATH_SEGMENT", "HOLDING_ARC", "HOLDING_PATTERN", "OUTBOUND_INBOUND_MARK"}:
        return "chart_graphic"
    if region_type:
        return "chart_text"
    return "other_chart_evidence"


def sources_for_region_ids(region_ids: list[str], region_by_id: dict[str, dict[str, Any]]) -> list[str]:
    return unique_list([evidence_source_for_region(region_by_id.get(region_id)) for region_id in region_ids])


def mapping_from_field_row(row: dict[str, Any], accepted: bool = True) -> dict[str, Any]:
    return {
        "candidate_leg_id": row.get("candidate_leg_id") or "",
        "canonical_leg_index": row.get("canonical_leg_index"),
        "leg_type": row.get("leg_type") or "",
        "field_name": row.get("field_name"),
        "expected_value": row.get("expected_value"),
        "expected_answer": row.get("expected_answer"),
        "match_basis": "batch field-review queue",
        "confidence": None,
        "human_decision": "accepted" if accepted else "pending",
        "human_notes": "",
    }


def ensure_mapping_for_region(row: dict[str, Any], region: dict[str, Any], target: dict[str, Any], decision: str) -> dict[str, Any]:
    for mapping in region.get("candidate_mappings") or []:
        if field_key_for_mapping(mapping, target) == row["key"]:
            mapping["human_decision"] = decision or mapping.get("human_decision") or "pending"
            return mapping
    mapping = mapping_from_field_row(row, decision == "accepted")
    mapping["human_decision"] = decision
    region.setdefault("candidate_mappings", []).append(mapping)
    return mapping


def apply_evidence_selection_to_mappings(
    row: dict[str, Any],
    required_ids: list[str],
    support_mode: str,
    regions: list[dict[str, Any]],
    target: dict[str, Any],
    reject_unselected: bool = True,
) -> None:
    required_set = set(required_ids)
    for region in regions:
        for mapping in region.get("candidate_mappings") or []:
            if field_key_for_mapping(mapping, target) != row["key"]:
                continue
            if region["region_id"] in required_set:
                mapping["human_decision"] = "accepted"
                if support_mode == "visible_joint":
                    mapping["human_notes"] = "Selected as necessary evidence for multi-evidence support."
                elif support_mode == "rule_default_completion":
                    mapping["human_notes"] = "Selected as premise evidence for rule/default completion."
            elif reject_unselected and (mapping.get("human_decision") or "pending") == "pending":
                mapping["human_decision"] = "rejected"
                mapping["human_notes"] = mapping.get("human_notes") or "Not selected for this field evidence basket."
        if region["region_id"] in required_set:
            ensure_mapping_for_region(row, region, target, "accepted")
            region["human_review"]["review_action"] = "accept"


def recommended_support_mode(
    row: dict[str, Any],
    evidence_ids: list[str],
    region_by_id: dict[str, dict[str, Any]] | None = None,
) -> str:
    if not evidence_ids:
        return ""
    return "direct_visible"


def set_field_review(
    field_reviews: dict[str, dict[str, Any]],
    row: dict[str, Any],
    chart_id: str,
    annotator: str,
    support_mode: str,
    required_ids: list[str],
    checked_scopes: list[str],
    region_by_id: dict[str, dict[str, Any]],
    notes: str = "",
) -> None:
    support_mode = support_mode_from_review({"review_status": support_mode}, required_ids)
    evidence_ids = [] if support_mode == "insufficient_for_encoding" else unique_list(required_ids)
    scopes = checked_scopes or sources_for_region_ids(evidence_ids, region_by_id)
    field_reviews[row["key"]] = {
        "schema": "field_review_v2",
        "field_key": row["key"],
        "chart_id": chart_id,
        "candidate_leg_id": row.get("candidate_leg_id"),
        "canonical_leg_index": row.get("canonical_leg_index"),
        "leg_type": row.get("leg_type"),
        "field_name": row.get("field_name"),
        "canonical_answer": row.get("expected_answer"),
        "review_status": support_mode,
        "support_mode": support_mode,
        "required_evidence_region_ids": evidence_ids,
        "secondary_evidence_region_ids": [],
        "evidence_region_ids": evidence_ids,
        "evidence_source": sources_for_region_ids(evidence_ids, region_by_id) if evidence_ids else [],
        "checked_scopes": scopes,
        "checked_sources": scopes,
        "notes": notes,
        "reviewed_by": annotator,
        "reviewed_at": utc_now() if support_mode != "pending" else "",
    }


def canonical_answer_at(canonical_legs: list[dict[str, Any]], leg_index: int, field_name: str) -> dict[str, Any] | None:
    for leg in canonical_legs:
        if leg.get("leg_index") == leg_index:
            return (leg.get("answers") or {}).get(field_name)
    return None


def build_annotation_canonical_json(
    detail: dict[str, Any],
    rows: list[dict[str, Any]],
    field_reviews: dict[str, dict[str, Any]],
    regions: list[dict[str, Any]],
    target: dict[str, Any],
) -> dict[str, Any]:
    chart_id = detail.get("manifest", {}).get("chart_id", "")
    canonical = detail.get("canonical_gt") or {}
    procedure = canonical.get("procedure") or {
        "airport": chart_id[:4],
        "approach_ident": chart_id.split("_", 1)[1] if "_" in chart_id else "",
        "chart_name": detail.get("manifest", {}).get("procedure_key") or "",
    }
    canonical_legs = (canonical.get("missed_approach") or {}).get("legs") or []
    target_legs = target.get("candidate_legs") or []
    leg_count = len(canonical_legs) or len(target_legs)
    legs: list[dict[str, Any]] = []
    for index in range(1, leg_count + 1):
        answers = {}
        for field_name in PR28_FIELDS:
            canonical_answer = canonical_answer_at(canonical_legs, index, field_name)
            answers[field_name] = deep_clone(canonical_answer) if canonical_answer and not is_present_answer(canonical_answer) else unknown_answer()
        legs.append({"leg_index": index, "answers": answers})

    row_by_key = {row["key"]: row for row in rows}
    for row in rows:
        if not row.get("requires_review") or not row.get("canonical_leg_index"):
            continue
        leg_idx = row["canonical_leg_index"] - 1
        if leg_idx < 0 or leg_idx >= len(legs):
            continue
        review = field_reviews.get(row["key"]) or {}
        support_mode = review.get("support_mode") or review.get("review_status")
        if support_mode in {"direct_visible", "visible_joint", "rule_default_completion"}:
            legs[leg_idx]["answers"][row["field_name"]] = deep_clone(row.get("expected_answer") or unknown_answer())
        elif support_mode in {"insufficient_for_encoding", "no_direct_chart_evidence"}:
            legs[leg_idx]["answers"][row["field_name"]] = {"status": "not_observable", "value": None}
        elif support_mode == "not_applicable":
            legs[leg_idx]["answers"][row["field_name"]] = {"status": "not_applicable", "value": None}

    for region in regions:
        for mapping in region.get("candidate_mappings") or []:
            if mapping.get("human_decision") != "accepted":
                continue
            if mapping.get("field_name") not in PR28_FIELDS:
                continue
            mapped_key = field_key_for_mapping(mapping, target)
            if row_by_key.get(mapped_key, {}).get("requires_review"):
                continue
            leg_index = canonical_leg_index_for_mapping(mapping, target)
            answer = mapping.get("human_answer") or canonical_field_for_mapping(mapping, target)
            if not leg_index or not answer or leg_index - 1 >= len(legs):
                continue
            legs[leg_index - 1]["answers"][mapping["field_name"]] = deep_clone(answer)

    return {
        "chart_id": chart_id,
        "procedure": procedure,
        "missed_approach": {
            "leg_count": {"status": "present", "value": leg_count},
            "legs": legs,
        },
    }


def answer_equal(left: Any, right: Any) -> bool:
    return left == right


def flatten_canonical_answers(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [{"key": "leg_count", "answer": (doc.get("missed_approach") or {}).get("leg_count")}]
    for leg in (doc.get("missed_approach") or {}).get("legs") or []:
        for field_name in PR28_FIELDS:
            rows.append(
                {
                    "key": f"leg{leg.get('leg_index')}.{field_name}",
                    "leg_index": leg.get("leg_index"),
                    "field": field_name,
                    "answer": (leg.get("answers") or {}).get(field_name),
                }
            )
    return rows


def compare_canonical_json(predicted: dict[str, Any], canonical: dict[str, Any] | None) -> dict[str, Any] | None:
    if not canonical:
        return None
    gt_rows = flatten_canonical_answers(canonical)
    pred_by_key = {row["key"]: row["answer"] for row in flatten_canonical_answers(predicted)}
    matched = covered = present_total = present_matched = present_covered = auto_status_total = 0
    for row in gt_rows:
        predicted_answer = pred_by_key.get(row["key"]) or unknown_answer()
        is_covered = predicted_answer.get("status") != "unknown" if isinstance(predicted_answer, dict) else predicted_answer is not None
        is_match = answer_equal(predicted_answer, row.get("answer"))
        requires_box_evidence = row["key"] != "leg_count" and row.get("field") != "Q_terminator" and is_present_answer(row.get("answer"))
        auto_status_field = row["key"] != "leg_count" and (row.get("field") == "Q_terminator" or not is_present_answer(row.get("answer")))
        if is_covered:
            covered += 1
        if is_match:
            matched += 1
        if requires_box_evidence:
            present_total += 1
            if is_covered:
                present_covered += 1
            if is_match:
                present_matched += 1
        if auto_status_field:
            auto_status_total += 1
    total = len(gt_rows)
    return {
        "metric_scope": "manual_evidence_alignment_against_cifp424_canonical_not_independent_extraction_accuracy",
        "canonical_answer_source": "CIFP/424 canonical target",
        "total": total,
        "matched": matched,
        "covered": covered,
        "present_total": present_total,
        "present_matched": present_matched,
        "present_covered": present_covered,
        "auto_status_total": auto_status_total,
        "full_alignment_rate": matched / total if total else 0,
        "overall_evidence_coverage": covered / total if total else 0,
        "present_alignment_rate": present_matched / present_total if present_total else 1,
        "present_evidence_coverage": present_covered / present_total if present_total else 1,
    }


def build_annotation_payload(detail: dict[str, Any], annotator: str, mode: str = "final") -> tuple[dict[str, Any], dict[str, Any]]:
    chart_id = detail.get("manifest", {}).get("chart_id", "")
    target = detail.get("target") or {}
    prelabel = detail.get("prelabel") or {}
    regions = [normalize_region(region, index, chart_id) for index, region in enumerate(prelabel.get("regions") or [])]
    rows = build_field_rows(target)
    field_reviews = normalize_field_reviews((detail.get("draft") or detail.get("annotation") or {}).get("field_reviews"))
    region_by_id = {region["region_id"]: region for region in regions}

    stats = Counter()
    for row in rows:
        if not row.get("requires_review"):
            continue
        evidence_ids = suggested_evidence_ids_for_field(row, rows, regions, target)
        support_mode = recommended_support_mode(row, evidence_ids, region_by_id)
        if not evidence_ids:
            support_mode = "pending"
            stats["needs_judgment_no_direct_evidence"] += 1
        else:
            stats[f"support_{support_mode}"] += 1
        ids_used = evidence_ids if support_mode in SUPPORT_REQUIRES_EVIDENCE else []
        apply_evidence_selection_to_mappings(row, ids_used, support_mode, regions, target)
        checked_scopes = sources_for_region_ids(evidence_ids, region_by_id) if evidence_ids else ["ma_text", "plan_view", "icon_detail"]
        notes = "Needs live judgment: no single direct-visible evidence was prefilled." if support_mode == "pending" else ""
        set_field_review(field_reviews, row, chart_id, annotator, support_mode, ids_used, checked_scopes, region_by_id, notes)

    field_review_list = []
    for row in rows:
        if not row.get("requires_review"):
            continue
        review = field_reviews.get(row["key"]) or {}
        field_review_list.append(
            {
                "field_key": row["key"],
                "chart_id": chart_id,
                "candidate_leg_id": row.get("candidate_leg_id"),
                "canonical_leg_index": row.get("canonical_leg_index"),
                "leg_type": row.get("leg_type"),
                "field_name": row.get("field_name"),
                "canonical_answer": row.get("expected_answer"),
                "review_status": review.get("review_status", "pending"),
                "support_mode": review.get("support_mode") or review.get("review_status", "pending"),
                "required_evidence_region_ids": review.get("required_evidence_region_ids") or [],
                "secondary_evidence_region_ids": review.get("secondary_evidence_region_ids") or [],
                "evidence_region_ids": review.get("evidence_region_ids") or [],
                "evidence_source": review.get("evidence_source") or [],
                "checked_scopes": review.get("checked_scopes") or [],
                "checked_sources": review.get("checked_sources") or review.get("checked_scopes") or [],
                "notes": review.get("notes") or "",
                "reviewed_by": review.get("reviewed_by") or annotator,
                "reviewed_at": review.get("reviewed_at") or "",
                "schema": "field_review_v2",
            }
        )

    pending_count = sum(1 for item in field_review_list if item["review_status"] == "pending")
    support_count = Counter(item["support_mode"] for item in field_review_list)
    annotation_pr28_json = build_annotation_canonical_json(detail, rows, field_reviews, regions, target)
    comparison = compare_canonical_json(annotation_pr28_json, detail.get("canonical_gt"))
    payload_regions = []
    for region in regions:
        accepted = [mapping for mapping in region.get("candidate_mappings") or [] if mapping.get("human_decision") == "accepted"]
        rejected = [mapping for mapping in region.get("candidate_mappings") or [] if mapping.get("human_decision") == "rejected"]
        payload_regions.append(
            {
                "final_region_id": region["region_id"],
                "source_region_id": region.get("source_region_id") or region["region_id"],
                "region_type": region.get("region_type"),
                "bbox": region.get("bbox"),
                "label": region.get("label"),
                "ocr_text": region.get("ocr_text"),
                "annotation_scope": region.get("annotation_scope") or "",
                "element_role": region.get("element_role") or "",
                "expected_visual_value": region.get("expected_visual_value") or "",
                "step_id": region.get("step_id") or "",
                "parent_step_region_id": region.get("parent_step_region_id") or "",
                "source_candidate_leg_id": region.get("source_candidate_leg_id") or "",
                "source_leg_type": region.get("source_leg_type") or "",
                "source_field_name": region.get("source_field_name") or "",
                "is_formal_annotation_candidate": bool(region.get("is_formal_annotation_candidate")),
                "accepted_mappings": [
                    {
                        "candidate_leg_id": mapping.get("candidate_leg_id") or "",
                        "canonical_leg_index": canonical_leg_index_for_mapping(mapping, target),
                        "leg_type": mapping.get("leg_type") or "",
                        "field_name": mapping.get("field_name") or "",
                        "final_value": mapping.get("expected_value"),
                        "canonical_answer": mapping.get("human_answer") or canonical_field_for_mapping(mapping, target),
                        "evidence_role": "supports_field",
                        "human_confidence": "medium",
                        "notes": mapping.get("human_notes") or mapping.get("match_basis") or "",
                    }
                    for mapping in accepted
                ],
                "rejected_mappings": [
                    {
                        "candidate_leg_id": mapping.get("candidate_leg_id") or "",
                        "leg_type": mapping.get("leg_type") or "",
                        "field_name": mapping.get("field_name") or "",
                        "reason": mapping.get("human_notes") or "rejected during batch field review",
                    }
                    for mapping in rejected
                ],
                "candidate_mappings_reviewed": region.get("candidate_mappings") or [],
                "review_action": (region.get("human_review") or {}).get("review_action") or "pending",
                "needs_discussion": any(mapping.get("human_decision") == "needs_discussion" for mapping in region.get("candidate_mappings") or []),
                "notes": (region.get("human_review") or {}).get("notes") or "",
            }
        )

    review_status = "draft_saved" if mode == "draft" else "pilot_reviewed"
    payload = {
        "chart_id": chart_id,
        "dataset_key": (detail.get("dataset") or {}).get("key") or "formal300",
        "dataset_label": (detail.get("dataset") or {}).get("label") or DATASET_LABELS.get((detail.get("dataset") or {}).get("key"), ""),
        "image_path": detail.get("manifest", {}).get("image_file") or "",
        "annotator": annotator,
        "review_status": review_status,
        "save_mode": mode,
        "source_prelabel_file": f"prelabels/{chart_id}.json",
        "canonical_targets_file": "targets/canonical_targets.json",
        "canonical_proxy_gt_combined_file": "targets/canonical_proxy_gt_combined.json",
        "canonical_proxy_gt_file": (target.get("canonical_proxy_gt_file") or f"targets/canonical_proxy_gt/{chart_id}.json"),
        "regions": payload_regions,
        "unresolved_targets": [],
        "field_reviews": field_review_list,
        "evidence_provenance": field_review_list,
        "field_review_summary": {
            "schema": "field_review_v2",
            "total_present_fields": len(field_review_list),
            "pending_fields": pending_count,
            "direct_visible": support_count["direct_visible"],
            "visible_joint": support_count["visible_joint"],
            "rule_default_completion": support_count["rule_default_completion"],
            "insufficient_for_encoding": support_count["insufficient_for_encoding"],
            "uncertain_fields": support_count["uncertain"],
        },
        "annotation_pr28_json": annotation_pr28_json,
        "canonical_gt_file": target.get("canonical_proxy_gt_file") or f"targets/canonical_proxy_gt/{chart_id}.json",
        "pr28_comparison_summary": comparison,
        "sample_notes": "Saved by batch prelabel field-review assistant." if mode != "draft" else "Draft saved by batch prelabel field-review assistant.",
    }
    stats["present_fields"] = len(field_review_list)
    stats["accepted_mappings"] = sum(len(region["accepted_mappings"]) for region in payload_regions)
    stats["rejected_mappings"] = sum(len(region["rejected_mappings"]) for region in payload_regions)
    return payload, dict(stats)


class Client:
    def __init__(self, base_url: str, token: str, dataset: str, annotator: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.dataset = dataset
        self.annotator = annotator
        self.timeout = timeout

    def _url(self, path: str, params: dict[str, Any] | None = None) -> str:
        merged = {"dataset": self.dataset, "token": self.token, "annotator": self.annotator}
        if params:
            merged.update({key: value for key, value in params.items() if value is not None})
        return f"{self.base_url}{path}?{urlencode(merged)}"

    def get(self, path: str, **params: Any) -> dict[str, Any]:
        request = Request(self._url(path, params), headers={"Accept": "application/json", "User-Agent": "codex-batch-annotator/1.0"})
        return self._read_json(request)

    def post(self, path: str, payload: dict[str, Any] | None = None, **params: Any) -> dict[str, Any]:
        body = json.dumps(payload or {}).encode("utf-8")
        request = Request(
            self._url(path, params),
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "codex-batch-annotator/1.0",
            },
        )
        return self._read_json(request)

    def _read_json(self, request: Request) -> dict[str, Any]:
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise ApiError(f"HTTP {error.code} {request.full_url}: {body}") from error


def parse_chart_ids(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[\s,]+", value) if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://43.135.12.254")
    parser.add_argument("--token", required=True)
    parser.add_argument("--dataset", default="formal300")
    parser.add_argument("--annotator", required=True)
    parser.add_argument("--chart-ids", default="", help="Comma/space separated chart ids. If omitted, claim from queue.")
    parser.add_argument("--max-count", type=int, default=1)
    parser.add_argument("--submit", action="store_true", help="Actually POST annotations. Default is dry-run.")
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    client = Client(args.base_url, args.token, args.dataset, args.annotator, timeout=args.timeout)
    chart_ids = parse_chart_ids(args.chart_ids)
    processed = []
    aggregate = Counter()
    after_chart_id = ""

    for index in range(args.max_count if not chart_ids else min(args.max_count, len(chart_ids))):
        if chart_ids:
            chart_id = chart_ids[index]
            if args.submit:
                try:
                    client.post(f"/api/claims/{chart_id}")
                except ApiError as error:
                    if "已由" in str(error) or "submitted" in str(error):
                        print(f"skip {chart_id}: {error}", flush=True)
                        aggregate["skipped"] += 1
                        continue
                    raise
            detail = client.get("/api/chart", chart_id=chart_id)
        elif args.submit:
            queued = client.post("/api/queue/next", {"after_chart_id": after_chart_id})
            detail = queued.get("chart")
            chart_id = queued.get("chart_id") or (detail or {}).get("manifest", {}).get("chart_id")
            if not detail or not chart_id:
                break
        else:
            charts = client.get("/api/charts", scope="queue").get("charts") or []
            candidates = [item["chart_id"] for item in charts if item.get("claim_status") in {"unassigned", "claimed", "claimed_by_me"}]
            if index >= len(candidates):
                break
            chart_id = candidates[index]
            detail = client.get("/api/chart", chart_id=chart_id)

        payload, stats = build_annotation_payload(detail, args.annotator, mode="final")
        chart_id = payload["chart_id"]
        if args.submit and payload["field_review_summary"]["pending_fields"]:
            raise RuntimeError(f"{chart_id} still has pending fields")
        if args.submit:
            result = client.post(f"/api/annotations/{chart_id}", payload)
            print(f"submitted {chart_id} annotator={result.get('annotator')} stats={json.dumps(stats, sort_keys=True)}", flush=True)
        else:
            print(f"dry-run {chart_id} stats={json.dumps(stats, sort_keys=True)}", flush=True)
        processed.append(chart_id)
        after_chart_id = chart_id
        aggregate.update(stats)
        if args.sleep:
            time.sleep(args.sleep)

    print(
        json.dumps(
            {
                "annotator": args.annotator,
                "submit": args.submit,
                "processed_count": len(processed),
                "processed": processed,
                "aggregate": dict(aggregate),
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
