from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATHS = ROOT / "training" / "group1_sft" / "configs" / "local_paths.local.json"
DEFAULT_SPLIT = (
    ROOT
    / "benchmark_exports"
    / "derived"
    / "v2"
    / "formal300"
    / "split_candidates"
    / "split_50_200_50_seed20260437"
    / "splits_50_200_50_seed20260437.json"
)
D1_EVIDENCE_PROMPT = (
    ROOT
    / "training"
    / "group1_sft"
    / "prompts"
    / "d1_chart_to_evidence_boxes_and_canonical.zh.md"
)
WRAPPER_SCHEMA = (
    ROOT
    / "training"
    / "group1_sft"
    / "manifests"
    / "d1_chart_to_evidence_boxes_and_canonical.schema.json"
)
CANONICAL_SCHEMA = ROOT / "schemas" / "missed_approach_leg.schema.json"

QUESTION_FIELDS = [
    "Q_terminator",
    "Q1_fix_ident",
    "Q2_altitude_constraint",
    "Q3_turn",
    "Q4_course_or_radial",
    "Q5_hold_params",
]
QUESTION_FIELD_ORDER = {field: idx for idx, field in enumerate(QUESTION_FIELDS)}

GENERIC_LABELS = {
    "upper coarse formal annotation: missed-approach text block",
    "coarse plan-view context for missed approach",
    "lower/profile missed-approach detail area snapped to AIP table lines",
    "detected lower detail: climb arrow",
    "detected lower detail: fix symbol",
    "detected lower detail: path segment",
    "平面图复飞相关区域",
}

CORE_REGION_ORDER = {
    "FIX_TEXT": 0,
    "ALTITUDE_TEXT": 1,
    "TRACK_OR_RADIAL_TEXT": 2,
    "RADIAL_TEXT": 3,
    "HEADING_TEXT": 4,
    "NAVAID_TEXT": 5,
    "OUTBOUND_INBOUND_MARK": 6,
    "HOLD_INBOUND_COURSE_TEXT": 7,
    "HOLD_DISTANCE_TEXT": 8,
    "HOLD_TIME_TEXT": 9,
    "HOLD_TURN_DIRECTION_TEXT": 10,
    "FIX_SYMBOL": 11,
    "HOLD_SYMBOL": 12,
    "CLIMB_ARROW": 13,
    "PATH_SEGMENT": 14,
    "MISSED_APPROACH_TEXT": 15,
    "PLAN_VIEW": 16,
    "MISSED_APPROACH_DETAIL_AREA": 17,
}

TEXT_REGION_TYPES = {
    "MISSED_APPROACH_TEXT",
    "ALTITUDE_TEXT",
    "FIX_TEXT",
    "NAVAID_TEXT",
    "RADIAL_TEXT",
    "HEADING_TEXT",
    "TRACK_OR_RADIAL_TEXT",
    "HOLD_INBOUND_COURSE_TEXT",
    "HOLD_DISTANCE_TEXT",
    "HOLD_TIME_TEXT",
    "HOLD_TURN_DIRECTION_TEXT",
}
SYMBOL_REGION_TYPES = {
    "FIX_SYMBOL",
    "HOLD_SYMBOL",
    "CLIMB_ARROW",
    "PATH_SEGMENT",
    "OUTBOUND_INBOUND_MARK",
}
COARSE_REGION_TYPES = {
    "MISSED_APPROACH_TEXT",
    "PLAN_VIEW",
    "MISSED_APPROACH_DETAIL_AREA",
}
FINE_REGION_TYPES = set(CORE_REGION_ORDER) - COARSE_REGION_TYPES


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def resolve_path(value: str, *, repo_root: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def normalize_spaces(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def load_paths(paths_file: Path) -> tuple[dict[str, str], Path]:
    config = read_json(paths_file)
    repo_root = resolve_path(config.get("repo_root", str(ROOT)), repo_root=ROOT)
    return config, repo_root


def annotation_records(export: dict[str, Any]) -> list[dict[str, Any]]:
    by_annotator = export["datasets"]["formal300"]["annotations"]["by_annotator"]
    values = by_annotator.values() if isinstance(by_annotator, dict) else by_annotator
    records: list[dict[str, Any]] = []
    for item in values:
        data = item.get("data") if isinstance(item, dict) else None
        if isinstance(data, dict) and data.get("save_mode") == "final":
            records.append(data)
    return records


def bbox_to_array(bbox: Any) -> list[float] | None:
    if not isinstance(bbox, dict):
        return None
    keys = ["x_center", "y_center", "width", "height"]
    if not all(key in bbox for key in keys):
        return None
    values = [round(float(bbox[key]), 4) for key in keys]
    if any(value < 0 or value > 1 for value in values):
        return None
    return values


def region_ids(region: dict[str, Any]) -> list[str]:
    values = [region.get("final_region_id"), region.get("source_region_id")]
    return [str(value) for value in values if value]


def primary_region_id(region: dict[str, Any]) -> str | None:
    ids = region_ids(region)
    return ids[0] if ids else None


def visible_text_from_region(region: dict[str, Any]) -> str | None:
    text = normalize_spaces(region.get("ocr_text"))
    if not text:
        text = normalize_spaces(region.get("label"))
    if not text or text in GENERIC_LABELS:
        return None
    if ":" in text:
        text = text.split(":", 1)[1].strip()
    if "->" in text:
        text = text.split("->", 1)[0].strip()
    text = normalize_spaces(text)
    return text if text and text not in GENERIC_LABELS else None


def compact_binding(mapping: dict[str, Any]) -> dict[str, Any] | None:
    leg_index = mapping.get("canonical_leg_index")
    field_name = mapping.get("field_name")
    if not isinstance(leg_index, int) or field_name not in QUESTION_FIELDS:
        return None
    return {
        "leg_index": leg_index,
        "candidate_leg_id": mapping.get("candidate_leg_id") or None,
        "field_name": field_name,
        "evidence_role": mapping.get("evidence_role") or None,
        "human_confidence": mapping.get("human_confidence") or None,
    }


def candidate_bindings(region: dict[str, Any], *, include_reviewed_candidates: bool = False) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    rows: list[dict[str, Any]] = []
    mappings = list(region.get("accepted_mappings") or [])
    if include_reviewed_candidates:
        mappings.extend(region.get("candidate_mappings_reviewed") or [])
    for mapping in mappings:
        row = compact_binding(mapping)
        if row is None:
            continue
        key = (row["leg_index"], row["candidate_leg_id"], row["field_name"], row["evidence_role"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return sorted(rows, key=lambda item: (item["leg_index"], item["field_name"], item["candidate_leg_id"] or ""))


def review_region_ids(review: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for key in ["required_evidence_region_ids", "secondary_evidence_region_ids", "evidence_region_ids"]:
        for value in review.get(key) or []:
            item = str(value)
            if item and item not in seen:
                seen.add(item)
                rows.append(item)
    return rows


def region_sort_key(region: dict[str, Any]) -> tuple[int, int, float, float, str]:
    bindings = candidate_bindings(region, include_reviewed_candidates=True)
    region_type = str(region.get("region_type") or "OTHER")
    bbox = bbox_to_array(region.get("bbox")) or [1.0, 1.0, 1.0, 1.0]
    has_bindings = 0 if bindings else 1
    region_rank = CORE_REGION_ORDER.get(region_type, 99)
    return (has_bindings, region_rank, bbox[1], bbox[0], primary_region_id(region) or "")


def region_alias_map(annotation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    aliases: dict[str, dict[str, Any]] = {}
    for region in annotation.get("regions") or []:
        for value in region_ids(region):
            aliases[value] = region
    return aliases


def field_names_for_region(
    region: dict[str, Any],
    reviews_by_region: dict[str, set[str]],
) -> list[str]:
    names = {binding["field_name"] for binding in candidate_bindings(region, include_reviewed_candidates=True)}
    source_field = region.get("source_field_name")
    if source_field in QUESTION_FIELDS:
        names.add(str(source_field))
    for rid in region_ids(region):
        names.update(reviews_by_region.get(rid, set()))
    return [name for name in QUESTION_FIELDS if name in names]


def evidence_role_for_region(region_type: str, field_names: list[str]) -> str:
    if region_type == "PLAN_VIEW":
        return "plan_view_context_evidence"
    if region_type in {"MISSED_APPROACH_TEXT", "MISSED_APPROACH_DETAIL_AREA"}:
        return "missed_approach_context_evidence"
    fields = set(field_names)
    if "Q5_hold_params" in fields or region_type.startswith("HOLD_"):
        return "holding_parameter_evidence"
    if "Q2_altitude_constraint" in fields or region_type == "ALTITUDE_TEXT":
        return "altitude_text_evidence"
    if "Q4_course_or_radial" in fields or region_type in {
        "RADIAL_TEXT",
        "TRACK_OR_RADIAL_TEXT",
        "HEADING_TEXT",
        "HOLD_INBOUND_COURSE_TEXT",
    }:
        return "course_or_radial_evidence"
    if "Q1_fix_ident" in fields or region_type in {"FIX_TEXT", "NAVAID_TEXT", "FIX_SYMBOL"}:
        return "fix_or_navaid_evidence"
    if "Q3_turn" in fields or region_type in {"CLIMB_ARROW", "PATH_SEGMENT", "OUTBOUND_INBOUND_MARK"}:
        return "turn_or_path_symbol_evidence"
    if "Q_terminator" in fields:
        return "terminator_context_evidence"
    return "missed_approach_context_evidence"


def collect_reviews_by_region(annotation: dict[str, Any]) -> dict[str, set[str]]:
    by_region: dict[str, set[str]] = defaultdict(set)
    for review in annotation.get("field_reviews") or []:
        field_name = review.get("field_name")
        if field_name not in QUESTION_FIELDS:
            continue
        for rid in review_region_ids(review):
            by_region[str(rid)].add(str(field_name))
    return by_region


def selected_evidence_regions(annotation: dict[str, Any]) -> list[dict[str, Any]]:
    aliases = region_alias_map(annotation)
    selected_ids: set[str] = set()
    for review in annotation.get("field_reviews") or []:
        selected_ids.update(review_region_ids(review))
    for region in annotation.get("regions") or []:
        region_type = str(region.get("region_type") or "")
        candidate_flag = region.get("is_formal_annotation_candidate")
        is_formal_candidate = candidate_flag is True or str(candidate_flag).lower() == "true"
        is_fine_candidate = region_type in FINE_REGION_TYPES and is_formal_candidate
        if candidate_bindings(region, include_reviewed_candidates=True) or is_fine_candidate:
            selected_ids.update(region_ids(region))

    selected: dict[str, dict[str, Any]] = {}
    for rid in selected_ids:
        region = aliases.get(rid)
        if region is None or bbox_to_array(region.get("bbox")) is None:
            continue
        primary = primary_region_id(region)
        if primary:
            selected[primary] = region
    return sorted(selected.values(), key=region_sort_key)


def build_evidence_boxes(
    annotation: dict[str, Any],
    *,
    max_boxes: int,
) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, str]]:
    reviews_by_region = collect_reviews_by_region(annotation)
    regions = selected_evidence_regions(annotation)
    if max_boxes > 0:
        regions = regions[:max_boxes]

    region_id_to_box_id: dict[str, str] = {}
    region_id_to_type: dict[str, str] = {}
    boxes: list[dict[str, Any]] = []
    for idx, region in enumerate(regions, 1):
        rid = primary_region_id(region)
        bbox = bbox_to_array(region.get("bbox"))
        region_type = str(region.get("region_type") or "")
        if rid is None or bbox is None:
            continue
        box_id = f"box_{idx:03d}"
        for alias in region_ids(region):
            region_id_to_box_id[alias] = box_id
            region_id_to_type[alias] = region_type
        field_names = field_names_for_region(region, reviews_by_region)
        boxes.append(
            {
                "box_id": box_id,
                "bbox": bbox,
                "region_type": region_type,
                "visible_text": visible_text_from_region(region),
                "field_names": field_names,
                "evidence_role": evidence_role_for_region(region_type, field_names),
            }
        )
    return boxes, region_id_to_box_id, region_id_to_type


def procedure_metadata(sample: dict[str, Any]) -> dict[str, Any]:
    chart_id = str(sample["chart_id"])
    approach_ident = str(sample.get("proc_ident") or (chart_id.split("_", 1)[1] if "_" in chart_id else chart_id))
    return {
        "airport": str(sample.get("airport") or chart_id[:4]),
        "approach_ident": approach_ident,
        "chart_name": str(sample.get("chart_name") or "UNKNOWN"),
    }


def build_questionnaire(annotation: dict[str, Any]) -> dict[str, Any]:
    by_leg: dict[int, dict[str, Any]] = defaultdict(dict)
    for review in annotation.get("field_reviews") or []:
        idx = review.get("canonical_leg_index")
        field_name = review.get("field_name")
        answer = review.get("canonical_answer")
        if not isinstance(idx, int) or field_name not in QUESTION_FIELDS or not isinstance(answer, dict):
            continue
        by_leg[idx][field_name] = {
            "status": answer.get("status", "unknown"),
            "value": answer.get("value"),
        }

    leg_count = max(by_leg.keys(), default=0)
    legs = []
    for idx in range(1, leg_count + 1):
        row = {"leg_index": idx}
        for field in QUESTION_FIELDS:
            row[field] = by_leg.get(idx, {}).get(field, {"status": "not_applicable", "value": None})
        legs.append(row)
    return {"leg_count": leg_count, "legs": legs}


def build_canonical(sample: dict[str, Any], annotation: dict[str, Any]) -> dict[str, Any]:
    questionnaire = build_questionnaire(annotation)
    return {
        "chart_id": sample["chart_id"],
        "procedure": procedure_metadata(sample),
        "missed_approach": {
            "leg_count": {"status": "present", "value": questionnaire["leg_count"]},
            "legs": [
                {
                    "leg_index": leg["leg_index"],
                    "answers": {field: leg[field] for field in QUESTION_FIELDS},
                }
                for leg in questionnaire["legs"]
            ],
        },
    }


def unique_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        item = str(value)
        if item and item not in seen:
            seen.add(item)
            rows.append(item)
    return rows


def mapping_regions_for_field(
    annotation: dict[str, Any],
    *,
    leg_index: int,
    field_name: str,
) -> list[str]:
    rows: list[str] = []
    for region in annotation.get("regions") or []:
        mappings = list(region.get("accepted_mappings") or [])
        mappings.extend(region.get("candidate_mappings_reviewed") or [])
        for mapping in mappings:
            if mapping.get("canonical_leg_index") == leg_index and mapping.get("field_name") == field_name:
                rid = primary_region_id(region)
                if rid:
                    rows.append(rid)
                break
    return unique_strings(rows)


def answer_path(leg_index: int, field_name: str) -> str:
    return f"missed_approach.legs[{leg_index - 1}].answers.{field_name}"


def classify_support_mode(
    *,
    raw_support_mode: str | None,
    evidence_box_ids: list[str],
    evidence_region_ids: list[str],
    region_id_to_type: dict[str, str],
) -> str:
    if raw_support_mode == "rule_default_completion":
        return "rule_default_not_directly_visible"
    if raw_support_mode == "insufficient_for_encoding":
        return "insufficient_for_encoding"
    if not evidence_box_ids:
        return "not_grounded"

    region_types = [region_id_to_type.get(rid) for rid in evidence_region_ids]
    if raw_support_mode in {"direct_visible", "visible_joint"}:
        if any(region_type in TEXT_REGION_TYPES for region_type in region_types):
            return "direct_visible_text"
        if any(region_type in SYMBOL_REGION_TYPES for region_type in region_types):
            return "direct_visible_symbol"
        if any(region_type in COARSE_REGION_TYPES for region_type in region_types):
            return "direct_visible_region"
        return "direct_visible_region"
    return "inferred_from_visible_evidence"


def evidence_summary_for_answer(
    *,
    field_name: str,
    support_mode: str,
    evidence_box_ids: list[str],
    box_by_id: dict[str, dict[str, Any]],
) -> str:
    if not evidence_box_ids:
        return f"{field_name} has no selected fine evidence box; support_mode={support_mode}."
    parts = []
    for box_id in evidence_box_ids:
        box = box_by_id.get(box_id, {})
        region_type = box.get("region_type") or "UNKNOWN_REGION"
        visible_text = box.get("visible_text")
        if visible_text:
            parts.append(f"{box_id}:{region_type}:{visible_text}")
        else:
            parts.append(f"{box_id}:{region_type}")
    return f"{field_name} is supported by " + "; ".join(parts)


def build_answer_grounding(
    annotation: dict[str, Any],
    *,
    boxes: list[dict[str, Any]],
    region_id_to_box_id: dict[str, str],
    region_id_to_type: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    box_by_id = {box["box_id"]: box for box in boxes}
    reviews = sorted(
        annotation.get("field_reviews") or [],
        key=lambda review: (
            review.get("canonical_leg_index") if isinstance(review.get("canonical_leg_index"), int) else 999,
            QUESTION_FIELD_ORDER.get(str(review.get("field_name")), 999),
            str(review.get("field_key") or ""),
        ),
    )
    for review in reviews:
        leg_index = review.get("canonical_leg_index")
        field_name = review.get("field_name")
        if not isinstance(leg_index, int) or field_name not in QUESTION_FIELDS:
            continue
        source_region_ids = review_region_ids(review)
        mapped_region_ids = mapping_regions_for_field(
            annotation,
            leg_index=leg_index,
            field_name=str(field_name),
        )
        if mapped_region_ids:
            source_region_ids = unique_strings(source_region_ids + mapped_region_ids)
        if not source_region_ids:
            source_region_ids = mapping_regions_for_field(
                annotation,
                leg_index=leg_index,
                field_name=str(field_name),
            )
        evidence_box_ids = unique_strings(
            [region_id_to_box_id[rid] for rid in source_region_ids if rid in region_id_to_box_id]
        )
        raw_support_mode = review.get("support_mode") or review.get("review_status")
        support_mode = classify_support_mode(
            raw_support_mode=str(raw_support_mode) if raw_support_mode else None,
            evidence_box_ids=evidence_box_ids,
            evidence_region_ids=source_region_ids,
            region_id_to_type=region_id_to_type,
        )
        rows.append(
            {
                "leg_index": leg_index,
                "field_name": field_name,
                "answer_path": answer_path(leg_index, str(field_name)),
                "support_mode": support_mode,
                "evidence_box_ids": evidence_box_ids,
                "evidence_summary": evidence_summary_for_answer(
                    field_name=str(field_name),
                    support_mode=support_mode,
                    evidence_box_ids=evidence_box_ids,
                    box_by_id=box_by_id,
                ),
            }
        )
    return rows


def build_joint_output(sample: dict[str, Any], annotation: dict[str, Any], *, max_boxes: int) -> dict[str, Any]:
    boxes, region_id_to_box_id, region_id_to_type = build_evidence_boxes(annotation, max_boxes=max_boxes)
    return {
        "evidence_boxes": boxes,
        "answer_grounding": build_answer_grounding(
            annotation,
            boxes=boxes,
            region_id_to_box_id=region_id_to_box_id,
            region_id_to_type=region_id_to_type,
        ),
        "canonical_prediction": build_canonical(sample, annotation),
    }


def base_row_metadata(
    *,
    split: str,
    sample_id: str,
    sample: dict[str, Any],
    image_path: Path,
    prompt_text: str,
) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "split": split,
        "chart_id": sample["chart_id"],
        "airport": sample.get("airport"),
        "proc_ident": sample.get("proc_ident"),
        "chart_name": sample.get("chart_name"),
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": str(image_path)},
                    {"type": "text", "text": prompt_text},
                ],
            }
        ],
    }


def make_joint_training_row(
    *,
    split: str,
    sample_id: str,
    sample: dict[str, Any],
    annotation: dict[str, Any],
    image_path: Path,
    prompt_text: str,
    max_boxes: int,
) -> dict[str, Any]:
    label = build_joint_output(sample, annotation, max_boxes=max_boxes)
    row = base_row_metadata(
        split=split,
        sample_id=sample_id,
        sample=sample,
        image_path=image_path,
        prompt_text=prompt_text,
    )
    row["messages"].append({"role": "assistant", "content": json.dumps(label, ensure_ascii=False, separators=(",", ":"))})
    row["source_annotation"] = {
        "dataset_key": "formal300",
        "split_candidate_subset": "development",
        "annotation_source": "shujuji_export_final_by_annotator",
        "uses_regions_as_evidence_box_labels": True,
        "uses_reviewed_candidate_mappings_for_fine_box_field_links": True,
        "uses_field_reviews_as_canonical_labels": True,
        "evidence_boxes_exclude_final_answer_values": True,
        "answer_grounding_excludes_final_answer_values": True,
        "backend_region_ids_kept_out_of_assistant_label": True,
        "formal_scoring_uses_canonical_prediction_only": True,
        "chart_id": sample["chart_id"],
    }
    return row


def make_eval_row(*, sample_id: str, sample: dict[str, Any], image_path: Path, prompt_text: str) -> dict[str, Any]:
    row = base_row_metadata(
        split="evaluation",
        sample_id=sample_id,
        sample=sample,
        image_path=image_path,
        prompt_text=prompt_text,
    )
    row["source_split"] = "evaluation"
    row["target_excluded_from_input_manifest"] = True
    return row


def split_train_dev(
    samples: list[dict[str, Any]],
    by_chart: dict[str, dict[str, Any]],
    train_target: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        airport = str(by_chart[sample["chart_id"]].get("airport") or sample["chart_id"][:4])
        groups[airport].append(sample)
    train: list[dict[str, Any]] = []
    dev: list[dict[str, Any]] = []
    for airport in sorted(groups):
        group = groups[airport]
        if len(train) + len(group) <= train_target or not train:
            train.extend(group)
        else:
            dev.extend(group)
    if not dev and len(train) > train_target:
        dev = train[train_target:]
        train = train[:train_target]
    return train, dev


def validation_errors(value: dict[str, Any], validator: Draft202012Validator) -> list[str]:
    errors = sorted(validator.iter_errors(value), key=lambda err: list(err.path))
    return [(".".join(str(part) for part in err.path) or "$") + f": {err.message}" for err in errors]


def assert_no_eval_labels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    violations = []
    forbidden_fragments = [
        "canonical_answer",
        "final_value",
        "target_json",
        "score_file",
        "raw_cifp",
        "raw_424",
        "\"role\": \"assistant\"",
        "\"role\":\"assistant\"",
    ]
    for row in rows:
        if len(row.get("messages") or []) != 1:
            violations.append({"chart_id": row.get("chart_id"), "reason": "eval_row_has_assistant_message"})
        text = json.dumps(row, ensure_ascii=False).lower()
        hits = [fragment for fragment in forbidden_fragments if fragment in text]
        if hits:
            violations.append({"chart_id": row.get("chart_id"), "reason": "forbidden_fragment", "hits": hits})
    return violations


def collect_joint_label_audit(label: dict[str, Any], audit: dict[str, Any], chart_id: str) -> None:
    audit["box_count_by_chart"][chart_id] = len(label["evidence_boxes"])
    box_type_by_id = {box["box_id"]: box["region_type"] for box in label["evidence_boxes"]}
    for box in label["evidence_boxes"]:
        audit["region_type_counts"][box["region_type"]] += 1
        for field_name in box.get("field_names") or []:
            audit["field_binding_counts"][field_name] += 1
    for item in label["answer_grounding"]:
        field_name = item["field_name"]
        support_mode = item["support_mode"]
        audit["grounding_counts"][support_mode] += 1
        audit["grounding_by_field"][field_name][support_mode] += 1
        if field_name == "Q5_hold_params":
            audit["q5_hold_params_grounding_counts"][support_mode] += 1
            evidence_types = sorted({box_type_by_id.get(box_id, "MISSING") for box_id in item["evidence_box_ids"]})
            audit["q5_hold_params_evidence_region_type_counts"][",".join(evidence_types) or "NO_BOX"] += 1
            if set(evidence_types).issubset({"PLAN_VIEW"}) and evidence_types:
                audit["q5_hold_params_needs_fine_box_rows"].append(
                    {
                        "chart_id": chart_id,
                        "leg_index": item["leg_index"],
                        "field_name": field_name,
                        "support_mode": support_mode,
                        "evidence_region_types": evidence_types,
                        "evidence_box_ids": item["evidence_box_ids"],
                    }
                )
        if not item["evidence_box_ids"] and support_mode not in {"insufficient_for_encoding", "not_grounded"}:
            audit["not_grounded_rows"].append(
                {
                    "chart_id": chart_id,
                    "leg_index": item["leg_index"],
                    "field_name": field_name,
                    "support_mode": support_mode,
                    "evidence_box_ids": item["evidence_box_ids"],
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build D1 continued-SFT JSONL with fine evidence boxes, answer grounding, "
            "and an unchanged canonical_prediction for formal scoring."
        )
    )
    parser.add_argument("--export-json", required=True, type=Path, help="Downloaded shujuji annotation export JSON.")
    parser.add_argument("--paths", type=Path, default=DEFAULT_PATHS)
    parser.add_argument("--split-json", type=Path, default=DEFAULT_SPLIT)
    parser.add_argument("--train-target", type=int, default=40)
    parser.add_argument("--max-boxes", type=int, default=24)
    args = parser.parse_args()

    config, repo_root = load_paths(args.paths)
    export = read_json(args.export_json)
    split = read_json(args.split_json)
    formal_manifest = resolve_path(config["formal_manifest"], repo_root=repo_root)
    sample_rows = read_json(formal_manifest)
    by_chart = {row["chart_id"]: row for row in sample_rows}
    annotations = {item["chart_id"]: item for item in annotation_records(export)}
    images_dir = resolve_path(config["formal_images_dir"], repo_root=repo_root)
    joint_prompt_text = D1_EVIDENCE_PROMPT.read_text(encoding="utf-8").strip()
    wrapper_validator = Draft202012Validator(read_json(WRAPPER_SCHEMA))
    canonical_validator = Draft202012Validator(read_json(CANONICAL_SCHEMA))

    dev_split = split["splits"]["development"]
    eval_split = split["splits"]["evaluation"]
    probe_split = split["splits"]["probe"]
    train_samples, dev_samples = split_train_dev(dev_split, by_chart, args.train_target)

    missing_annotations = [sample["chart_id"] for sample in dev_split if sample["chart_id"] not in annotations]
    if missing_annotations:
        raise RuntimeError(f"Missing development annotations for {len(missing_annotations)} charts: {missing_annotations[:10]}")

    def image_for(sample: dict[str, Any]) -> Path:
        return images_dir / by_chart[sample["chart_id"]]["image_file"]

    joint_train_rows: list[dict[str, Any]] = []
    joint_dev_rows: list[dict[str, Any]] = []
    joint_eval_rows: list[dict[str, Any]] = []
    schema_errors: list[dict[str, Any]] = []
    audit: dict[str, Any] = {
        "region_type_counts": Counter(),
        "field_binding_counts": Counter(),
        "grounding_counts": Counter(),
        "grounding_by_field": defaultdict(Counter),
        "q5_hold_params_grounding_counts": Counter(),
        "q5_hold_params_evidence_region_type_counts": Counter(),
        "q5_hold_params_needs_fine_box_rows": [],
        "not_grounded_rows": [],
        "box_count_by_chart": {},
    }

    for split_name, samples, joint_out_rows in [
        ("train", train_samples, joint_train_rows),
        ("dev", dev_samples, joint_dev_rows),
    ]:
        for idx, sample in enumerate(samples, 1):
            chart_id = sample["chart_id"]
            annotation = annotations[chart_id]
            joint_row = make_joint_training_row(
                split=split_name,
                sample_id=f"d1_evidence_boxes_canonical_{split_name}_{idx:04d}",
                sample=by_chart[chart_id],
                annotation=annotation,
                image_path=image_for(sample),
                prompt_text=joint_prompt_text,
                max_boxes=args.max_boxes,
            )
            joint_out_rows.append(joint_row)
            label = json.loads(joint_row["messages"][1]["content"])
            collect_joint_label_audit(label, audit, chart_id)
            for error in validation_errors(label, wrapper_validator):
                schema_errors.append({"chart_id": chart_id, "artifact": "wrapper", "error": error})
            for error in validation_errors(label["canonical_prediction"], canonical_validator):
                schema_errors.append({"chart_id": chart_id, "artifact": "canonical_prediction", "error": error})

    for idx, sample in enumerate(eval_split, 1):
        chart_sample = by_chart[sample["chart_id"]]
        joint_eval_rows.append(
            make_eval_row(
                sample_id=f"d1_evidence_boxes_canonical_eval_{idx:04d}",
                sample=chart_sample,
                image_path=image_for(sample),
                prompt_text=joint_prompt_text,
            )
        )

    eval_violations = assert_no_eval_labels(joint_eval_rows)
    joint_train_path = resolve_path(config["d1_evidence_boxes_train_jsonl"], repo_root=repo_root)
    joint_dev_path = resolve_path(config["d1_evidence_boxes_dev_jsonl"], repo_root=repo_root)
    joint_eval_path = resolve_path(config["d1_evidence_boxes_eval_jsonl"], repo_root=repo_root)
    write_jsonl(joint_train_path, joint_train_rows)
    write_jsonl(joint_dev_path, joint_dev_rows)
    write_jsonl(joint_eval_path, joint_eval_rows)

    reports_dir = resolve_path(config.get("reports_dir", str(joint_train_path.parent)), repo_root=repo_root)
    gap_path = reports_dir / "d1_q5_hold_params_needs_fine_box_review.jsonl"
    write_jsonl(gap_path, audit["q5_hold_params_needs_fine_box_rows"])
    box_counts = list(audit["box_count_by_chart"].values())
    q5_gap_count = len(audit["q5_hold_params_needs_fine_box_rows"])
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "method_id": "D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL",
        "method_version": "D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL-1",
        "continued_from_checkpoint_key": "d1_lora_or_checkpoint_dir",
        "export_json": str(args.export_json),
        "split_json": str(args.split_json),
        "formal_manifest": str(formal_manifest),
        "development_count": len(dev_split),
        "evaluation_count": len(eval_split),
        "probe_count": len(probe_split),
        "train_count": len(joint_train_rows),
        "dev_count": len(joint_dev_rows),
        "max_boxes_per_chart": args.max_boxes,
        "schema_errors": schema_errors,
        "eval_input_violations": eval_violations,
        "box_count": {
            "min": min(box_counts, default=0),
            "max": max(box_counts, default=0),
            "mean": sum(box_counts) / len(box_counts) if box_counts else None,
        },
        "region_type_counts_train_dev": dict(sorted(audit["region_type_counts"].items())),
        "field_binding_counts_train_dev": dict(sorted(audit["field_binding_counts"].items())),
        "grounding_counts_train_dev": dict(sorted(audit["grounding_counts"].items())),
        "grounding_by_field_train_dev": {
            field: dict(sorted(counter.items()))
            for field, counter in sorted(audit["grounding_by_field"].items())
        },
        "q5_hold_params_grounding_counts_train_dev": dict(
            sorted(audit["q5_hold_params_grounding_counts"].items())
        ),
        "q5_hold_params_evidence_region_type_counts_train_dev": dict(
            sorted(audit["q5_hold_params_evidence_region_type_counts"].items())
        ),
        "q5_hold_params_needs_fine_box_count": q5_gap_count,
        "q5_hold_params_needs_fine_box_report": str(gap_path),
        "not_grounded_rows": audit["not_grounded_rows"],
        "outputs": {
            "d1_evidence_boxes_train_jsonl": str(joint_train_path),
            "d1_evidence_boxes_train_rows": len(joint_train_rows),
            "d1_evidence_boxes_dev_jsonl": str(joint_dev_path),
            "d1_evidence_boxes_dev_rows": len(joint_dev_rows),
            "d1_evidence_boxes_eval_jsonl": str(joint_eval_path),
            "d1_evidence_boxes_eval_rows": len(joint_eval_rows),
        },
        "input_boundary": {
            "development_train_dev_use_regions_as_evidence_box_labels": True,
            "development_train_dev_use_reviewed_candidate_mappings_for_fine_box_field_links": True,
            "development_train_dev_use_field_reviews_as_canonical_labels": True,
            "backend_region_ids_are_training_audit_only": True,
            "evaluation_has_assistant_labels": False,
            "evaluation_contains_canonical_answer": False,
            "probe_used": False,
        },
        "formal_scoring_boundary": {
            "raw_model_output": "diagnostic_wrapper_with_evidence_boxes_answer_grounding_and_canonical_prediction",
            "formal_prediction_for_scoring": "canonical_prediction_only",
            "canonical_schema_changed": False,
        },
        "ready": not schema_errors and not eval_violations,
        "ready_for_fine_holding_training_goal": not schema_errors and not eval_violations and q5_gap_count == 0,
        "methodology_warning": (
            "Q5_hold_params is still grounded only to PLAN_VIEW in the current annotation export; "
            "add fine holding-symbol/course/distance/time boxes before treating this as a fine-holding grounding set."
            if q5_gap_count
            else None
        ),
    }
    write_json(reports_dir / "d1_evidence_boxes_canonical_jsonl_build_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
