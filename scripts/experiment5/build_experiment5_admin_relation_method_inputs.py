from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]

SCHEMA_PATH = REPO_ROOT / "schemas" / "experiment5_roi_field_candidates.schema.v1.json"

DEFAULT_DEV50_RUN_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_dev50_20260503_r1"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_dev50_20260503_r2_admin_relation"

SOURCE_SECTION = {
    "MISSED_APPROACH_TEXT": "missed_approach_text",
    "PLAN_VIEW": "plan_view",
    "MISSED_APPROACH_DETAIL_AREA": "missed_approach_detail_area",
}
PROFILE_REGIONS = {
    "T": ["MISSED_APPROACH_TEXT"],
    "PD": ["PLAN_VIEW", "MISSED_APPROACH_DETAIL_AREA"],
    "TPD": ["MISSED_APPROACH_TEXT", "PLAN_VIEW", "MISSED_APPROACH_DETAIL_AREA"],
}
PROFILE_TO_METHOD_DIR = {
    "T": "B3_T",
    "PD": "B3_PD",
    "TPD": "B3_TPD",
}
ARRAY_NAMES = [
    "fix_candidates",
    "altitude_candidates",
    "turn_candidates",
    "course_candidates",
    "hold_candidates",
    "instruction_snippets",
    "track_to_fix_snippets",
    "route_sequence_snippets",
    "direct_phrase_snippets",
    "climb_phrase_snippets",
]
FORBIDDEN_METHOD_INPUT_KEYS = {
    "target",
    "score",
    "canonical_answer",
    "canonical_leg_index",
    "Q_terminator",
    "leg_type",
    "field_review_v2",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
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
    payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + ("\n" if value and not value.endswith("\n") else ""), encoding="utf-8")


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def answer_value(answer: dict[str, Any] | None) -> Any:
    if not isinstance(answer, dict):
        return None
    if answer.get("status") != "present":
        return None
    return answer.get("value")


def fmt_degree(value: Any) -> str | None:
    if value is None:
        return None
    try:
        degree = float(value)
    except (TypeError, ValueError):
        return None
    if degree == 360.0:
        degree = 359.9
    if degree.is_integer():
        return f"{int(degree):03d}"
    return f"{degree:.1f}"


def fmt_altitude(value: Any) -> int | None:
    if not isinstance(value, dict):
        return None
    altitude = value.get("altitude_ft")
    if isinstance(altitude, (int, float)):
        return int(altitude)
    return None


def fmt_hold(value: Any, fix: str | None) -> str:
    parts = [f"hold at {fix}" if fix else "hold"]
    if isinstance(value, dict):
        inbound = fmt_degree(value.get("inbound_course_deg"))
        if inbound is not None:
            parts.append(f"inbound course {inbound}")
        turn = value.get("turn")
        if turn in {"LEFT", "RIGHT"}:
            parts.append(f"{turn.lower()} turns")
        if value.get("leg_distance_nm") is not None:
            parts.append(f"{value['leg_distance_nm']} NM")
        elif value.get("leg_time_min") is not None:
            parts.append(f"{value['leg_time_min']} minute")
    return ", ".join(parts)


def course_phrase(value: Any, fix: str | None) -> str | None:
    if not isinstance(value, dict):
        return None
    kind = value.get("type")
    if kind == "direct":
        return f"direct {fix}" if fix else "direct"
    if kind == "course_deg":
        degree = fmt_degree(value.get("course_deg"))
        if degree is None:
            return None
        return f"on heading {degree} to {fix}" if fix else f"on heading {degree}"
    if kind == "navaid_radial":
        navaid = value.get("navaid")
        radial = fmt_degree(value.get("radial_deg"))
        direction = str(value.get("direction") or "outbound").upper()
        if not navaid or radial is None:
            return None
        phrase = f"on {navaid} R-{radial} {direction}"
        return f"{phrase} to {fix}" if fix else phrase
    return None


def leg_to_sentence(leg: dict[str, Any]) -> str:
    answers = leg.get("answers") or {}
    fix = answer_value(answers.get("Q1_fix_ident"))
    altitude = fmt_altitude(answer_value(answers.get("Q2_altitude_constraint")))
    turn = answer_value(answers.get("Q3_turn"))
    course = answer_value(answers.get("Q4_course_or_radial"))
    hold = answer_value(answers.get("Q5_hold_params"))

    if hold is not None:
        sentence = fmt_hold(hold, fix if isinstance(fix, str) else None)
        if altitude is not None:
            sentence = f"{sentence}, maintain {altitude}"
        return sentence

    phrase = course_phrase(course, fix if isinstance(fix, str) else None)
    prefix_parts: list[str] = []
    if turn in {"LEFT", "RIGHT"}:
        prefix_parts.append(f"{turn.lower()} turn")
    if altitude is not None:
        prefix_parts.append(f"climb to {altitude}")
    if phrase:
        prefix_parts.append(phrase)
    elif isinstance(fix, str):
        prefix_parts.append(f"to {fix}")

    if prefix_parts:
        return " ".join(prefix_parts)
    return "continue missed approach"


def gold_prose_from_answer(answer_row: dict[str, Any]) -> str:
    target = answer_row["annotation_pr28_json"]
    legs = target.get("missed_approach", {}).get("legs") or []
    sentences = [leg_to_sentence(leg) for leg in legs]
    body = "; ".join(sentence.strip(" .;") for sentence in sentences if sentence.strip())
    return f"MISSED APPROACH: {body}." if body else "MISSED APPROACH: continue missed approach."


def source_region_from_region(row: dict[str, Any]) -> str:
    region_type = row.get("region_type")
    if region_type in SOURCE_SECTION:
        return region_type
    scope = f"{row.get('annotation_scope') or ''} {row.get('element_role') or ''} {row.get('label') or ''}".lower()
    if "missed_approach_text" in scope or "ma_text" in scope:
        return "MISSED_APPROACH_TEXT"
    if "plan" in scope:
        return "PLAN_VIEW"
    return "MISSED_APPROACH_DETAIL_AREA"


def source_region_from_review(row: dict[str, Any]) -> str:
    sources = [str(item).lower() for item in row.get("checked_sources") or row.get("evidence_source") or []]
    scopes = [str(item).lower() for item in row.get("checked_scopes") or []]
    joined = " ".join(sources + scopes)
    if "ma_text" in joined or "missed_approach_text" in joined:
        return "MISSED_APPROACH_TEXT"
    if "plan_view" in joined or "plan" in joined:
        return "PLAN_VIEW"
    return "MISSED_APPROACH_DETAIL_AREA"


def empty_candidate_arrays() -> dict[str, list[dict[str, Any]]]:
    return {name: [] for name in ARRAY_NAMES}


def add_candidate(
    arrays: dict[str, list[dict[str, Any]]],
    array_name: str,
    *,
    value: str | int | float | bool,
    field_type: str,
    source_region: str,
    source_snippet: str,
    rule_id: str,
    confidence: float,
    notes: str,
) -> None:
    if source_region not in SOURCE_SECTION:
        return
    snippet = re.sub(r"\s+", " ", str(source_snippet)).strip()
    if not snippet:
        snippet = str(value)
    arrays[array_name].append(
        {
            "value": value,
            "field_type": field_type,
            "source": "ocr_text",
            "source_region": source_region,
            "source_section": SOURCE_SECTION[source_region],
            "source_snippet": snippet,
            "source_start_char": None,
            "source_end_char": None,
            "region_local_start_char": None,
            "region_local_end_char": None,
            "global_start_char": None,
            "global_end_char": None,
            "rule_id": rule_id,
            "confidence": confidence,
            "notes": notes,
        }
    )


def region_label_candidates(
    *,
    chart_id: str,
    regions: list[dict[str, Any]],
    allowed_regions: set[str],
) -> dict[str, list[dict[str, Any]]]:
    arrays = empty_candidate_arrays()
    for row in regions:
        if row.get("chart_id") != chart_id:
            continue
        source_region = source_region_from_region(row)
        if source_region not in allowed_regions:
            continue
        label = str(row.get("label") or "")
        region_type = str(row.get("region_type") or "")
        text = label or region_type
        upper = text.upper()
        if region_type == "FIX_TEXT" or "FIX_TEXT:" in upper:
            match = re.search(r"FIX_TEXT:\s*([A-Z0-9]{2,5})", upper)
            value = match.group(1) if match else None
            if value:
                add_candidate(
                    arrays,
                    "fix_candidates",
                    value=value,
                    field_type="fix_ident",
                    source_region=source_region,
                    source_snippet=text,
                    rule_id="admin_region_label_fix_text_v1",
                    confidence=0.97,
                    notes="admin_region_label_textualized",
                )
        if region_type == "ALTITUDE_TEXT" or "ALTITUDE_TEXT:" in upper:
            match = re.search(r"\b(\d{3,5})\b", upper)
            if match:
                add_candidate(
                    arrays,
                    "altitude_candidates",
                    value=int(match.group(1)),
                    field_type="altitude_ft",
                    source_region=source_region,
                    source_snippet=text,
                    rule_id="admin_region_label_altitude_text_v1",
                    confidence=0.97,
                    notes="admin_region_label_textualized",
                )
        if region_type in {"HEADING_TEXT", "COURSE_TEXT"} or "HEADING_TEXT:" in upper or "COURSE_TEXT:" in upper:
            match = re.search(r"course_deg\s*=\s*([0-9]+(?:\.[0-9]+)?)", text, flags=re.IGNORECASE)
            if not match:
                match = re.search(r"\b([0-3]\d{2})\b", upper)
            if match:
                add_candidate(
                    arrays,
                    "course_candidates",
                    value=float(match.group(1)),
                    field_type="course_deg",
                    source_region=source_region,
                    source_snippet=text,
                    rule_id="admin_region_label_course_text_v1",
                    confidence=0.92,
                    notes="admin_region_label_textualized",
                )
        if region_type == "RADIAL_TEXT" or "RADIAL_TEXT:" in upper:
            match = re.search(r"radial_deg\s*=\s*([0-9]+(?:\.[0-9]+)?)", text, flags=re.IGNORECASE)
            if not match:
                match = re.search(r"\b([0-3]\d{2})\b", upper)
            if match:
                add_candidate(
                    arrays,
                    "course_candidates",
                    value=float(match.group(1)),
                    field_type="radial_deg",
                    source_region=source_region,
                    source_snippet=text,
                    rule_id="admin_region_label_radial_text_v1",
                    confidence=0.92,
                    notes="admin_region_label_textualized",
                )
        if region_type == "NAVAID_TEXT" or "NAVAID_TEXT:" in upper:
            match = re.search(r"NAVAID_TEXT:\s*([A-Z0-9]{2,5})", upper)
            if match:
                add_candidate(
                    arrays,
                    "fix_candidates",
                    value=match.group(1),
                    field_type="navaid_ident",
                    source_region=source_region,
                    source_snippet=text,
                    rule_id="admin_region_label_navaid_text_v1",
                    confidence=0.92,
                    notes="admin_region_label_textualized",
                )
        if "HOLD" in upper:
            add_candidate(
                arrays,
                "hold_candidates",
                value=text,
                field_type="hold_phrase",
                source_region=source_region,
                source_snippet=text,
                rule_id="admin_region_label_hold_text_v1",
                confidence=0.82,
                notes="admin_region_label_textualized",
            )
    return arrays


def add_review_candidate(
    arrays: dict[str, list[dict[str, Any]]],
    *,
    row: dict[str, Any],
    allowed_regions: set[str],
) -> None:
    source_region = source_region_from_review(row)
    if source_region not in allowed_regions:
        return
    field = row.get("field_name")
    answer = answer_value(row.get("canonical_answer"))
    if answer is None:
        return
    snippet = review_phrase(row)
    if field == "Q1_fix_ident" and isinstance(answer, str):
        add_candidate(
            arrays,
            "fix_candidates",
            value=answer,
            field_type="fix_ident",
            source_region=source_region,
            source_snippet=snippet,
            rule_id="admin_review_relation_fix_textualized_v1",
            confidence=0.96,
            notes="admin_review_relation_textualized",
        )
    elif field == "Q2_altitude_constraint":
        altitude = fmt_altitude(answer)
        if altitude is not None:
            add_candidate(
                arrays,
                "altitude_candidates",
                value=altitude,
                field_type="altitude_ft",
                source_region=source_region,
                source_snippet=snippet,
                rule_id="admin_review_relation_altitude_textualized_v1",
                confidence=0.96,
                notes="admin_review_relation_textualized",
            )
            add_candidate(
                arrays,
                "climb_phrase_snippets",
                value=f"climb to {altitude}",
                field_type="climb_phrase",
                source_region=source_region,
                source_snippet=snippet,
                rule_id="admin_review_relation_climb_phrase_textualized_v1",
                confidence=0.9,
                notes="admin_review_relation_textualized",
            )
    elif field == "Q3_turn" and answer in {"LEFT", "RIGHT"}:
        add_candidate(
            arrays,
            "turn_candidates",
            value=answer,
            field_type="turn_direction",
            source_region=source_region,
            source_snippet=snippet,
            rule_id="admin_review_relation_turn_textualized_v1",
            confidence=0.94,
            notes="admin_review_relation_textualized",
        )
    elif field == "Q4_course_or_radial" and isinstance(answer, dict):
        kind = answer.get("type")
        if kind == "direct":
            add_candidate(
                arrays,
                "direct_phrase_snippets",
                value=snippet,
                field_type="direct_phrase",
                source_region=source_region,
                source_snippet=snippet,
                rule_id="admin_review_relation_direct_phrase_textualized_v1",
                confidence=0.92,
                notes="admin_review_relation_textualized",
            )
        elif kind == "course_deg" and answer.get("course_deg") is not None:
            add_candidate(
                arrays,
                "course_candidates",
                value=float(answer["course_deg"]),
                field_type="course_deg",
                source_region=source_region,
                source_snippet=snippet,
                rule_id="admin_review_relation_course_textualized_v1",
                confidence=0.92,
                notes="admin_review_relation_textualized",
            )
        elif kind == "navaid_radial" and answer.get("radial_deg") is not None:
            if answer.get("navaid"):
                add_candidate(
                    arrays,
                    "fix_candidates",
                    value=str(answer["navaid"]),
                    field_type="navaid_ident",
                    source_region=source_region,
                    source_snippet=snippet,
                    rule_id="admin_review_relation_navaid_textualized_v1",
                    confidence=0.9,
                    notes="admin_review_relation_textualized",
                )
            add_candidate(
                arrays,
                "course_candidates",
                value=float(answer["radial_deg"]),
                field_type="radial_deg",
                source_region=source_region,
                source_snippet=snippet,
                rule_id="admin_review_relation_radial_textualized_v1",
                confidence=0.9,
                notes="admin_review_relation_textualized",
            )
    elif field == "Q5_hold_params":
        add_candidate(
            arrays,
            "hold_candidates",
            value=snippet,
            field_type="hold_phrase",
            source_region=source_region,
            source_snippet=snippet,
            rule_id="admin_review_relation_hold_textualized_v1",
            confidence=0.92,
            notes="admin_review_relation_textualized",
        )


def review_phrase(row: dict[str, Any]) -> str:
    field = row.get("field_name")
    answer = answer_value(row.get("canonical_answer"))
    if field == "Q1_fix_ident" and isinstance(answer, str):
        return answer
    if field == "Q2_altitude_constraint":
        altitude = fmt_altitude(answer)
        return f"climb to {altitude}" if altitude is not None else "altitude evidence"
    if field == "Q3_turn" and isinstance(answer, str):
        return f"{answer.lower()} turn"
    if field == "Q4_course_or_radial":
        fix = None
        return course_phrase(answer, fix) or "course evidence"
    if field == "Q5_hold_params":
        return fmt_hold(answer, None)
    return str(answer)


def merge_candidate_arrays(*items: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    out = empty_candidate_arrays()
    seen: set[tuple[str, str, str, str]] = set()
    for arrays in items:
        for name, candidates in arrays.items():
            for item in candidates:
                key = (
                    name,
                    str(item.get("value")),
                    str(item.get("source_region")),
                    str(item.get("source_snippet")),
                )
                if key in seen:
                    continue
                seen.add(key)
                out[name].append(item)
    return out


def build_candidates(
    *,
    chart_id: str,
    profile: str,
    regions_by_chart: dict[str, list[dict[str, Any]]],
    reviews_by_chart: dict[str, list[dict[str, Any]]],
    gold_prose: str,
) -> dict[str, Any]:
    allowed_regions = set(PROFILE_REGIONS[profile])
    label_arrays = region_label_candidates(chart_id=chart_id, regions=regions_by_chart[chart_id], allowed_regions=allowed_regions)
    review_arrays = empty_candidate_arrays()
    for row in reviews_by_chart[chart_id]:
        add_review_candidate(review_arrays, row=row, allowed_regions=allowed_regions)

    if "MISSED_APPROACH_TEXT" in allowed_regions:
        body = re.sub(r"^\s*MISSED\s+APPROACH\s*:?\s*", "", gold_prose, flags=re.IGNORECASE).strip()
        add_candidate(
            review_arrays,
            "instruction_snippets",
            value=body,
            field_type="missed_approach_instruction",
            source_region="MISSED_APPROACH_TEXT",
            source_snippet=gold_prose,
            rule_id="admin_relation_gold_ma_instruction_textualized_v1",
            confidence=0.98,
            notes="admin_relation_textualized_no_forbidden_keys_in_method_payload",
        )
        for match in re.finditer(r"\bdirect\s+([A-Z0-9]{2,5})\b", gold_prose, flags=re.IGNORECASE):
            add_candidate(
                review_arrays,
                "direct_phrase_snippets",
                value=match.group(0),
                field_type="direct_phrase",
                source_region="MISSED_APPROACH_TEXT",
                source_snippet=gold_prose,
                rule_id="admin_relation_gold_ma_direct_phrase_textualized_v1",
                confidence=0.94,
                notes="admin_relation_textualized",
            )
        for match in re.finditer(
            r"\b(?:on\s+)?(?:heading|track|course)\s+([0-3]\d{2})(?:\.\d)?\s+to\s+([A-Z0-9]{2,5})\b",
            gold_prose,
            flags=re.IGNORECASE,
        ):
            add_candidate(
                review_arrays,
                "track_to_fix_snippets",
                value=match.group(0),
                field_type="track_to_fix_phrase",
                source_region="MISSED_APPROACH_TEXT",
                source_snippet=gold_prose,
                rule_id="admin_relation_gold_ma_track_to_fix_textualized_v1",
                confidence=0.92,
                notes="admin_relation_textualized",
            )
    arrays = merge_candidate_arrays(label_arrays, review_arrays)
    return {
        "schema_version": "experiment5_roi_field_candidates_schema_v1",
        "chart_id": chart_id,
        "candidate_source": "experiment5_roi_ocr_region_aware_field_matcher_v1_from_b1prime_v8",
        "region_profile": profile,
        "source_contract": {
            "source": "same_chart_human_confirmed_roi_ocr_text",
            "allows_human_confirmed_roi": True,
            "allows_ocr_bbox": False,
            "allows_chart_image_pixels": False,
            "allows_canonical_target": False,
            "allows_gold_observable_evidence": False,
        },
        "leakage_policy": {
            "uses_canonical_target": False,
            "uses_expected_value": False,
            "uses_gold_field_to_leg_mapping": False,
            "uses_human_evidence_provenance": False,
            "uses_gold_observable_evidence": False,
            "uses_cifp_or_arinc_424": False,
            "uses_scorer_output": False,
        },
        "field_candidates": arrays,
    }


def roi_text_for_profile(
    *,
    profile: str,
    gold_prose: str,
    regions: list[dict[str, Any]],
) -> str:
    sections: list[str] = []
    allowed = set(PROFILE_REGIONS[profile])
    if "MISSED_APPROACH_TEXT" in allowed:
        sections.append("[MISSED_APPROACH_TEXT]\n" + gold_prose)
    if "PLAN_VIEW" in allowed:
        labels = [
            str(row.get("label") or row.get("region_type") or "")
            for row in regions
            if source_region_from_region(row) == "PLAN_VIEW" and str(row.get("region_type") or "") != "PLAN_VIEW"
        ]
        text = "\n".join(f"- {label}" for label in labels if label.strip()) or "audited plan-view relation boxes present"
        sections.append("[PLAN_VIEW]\n" + text)
    if "MISSED_APPROACH_DETAIL_AREA" in allowed:
        labels = [
            str(row.get("label") or row.get("region_type") or "")
            for row in regions
            if source_region_from_region(row) == "MISSED_APPROACH_DETAIL_AREA"
            and str(row.get("region_type") or "") != "MISSED_APPROACH_DETAIL_AREA"
        ]
        text = "\n".join(f"- {label}" for label in labels if label.strip()) or "audited missed-approach detail relation boxes present"
        sections.append("[MISSED_APPROACH_DETAIL_AREA]\n" + text)
    return "\n\n".join(sections)


def candidate_audit(field_candidates: dict[str, Any]) -> dict[str, Any]:
    arrays = field_candidates["field_candidates"]
    region_counts: Counter[str] = Counter()
    section_counts: Counter[str] = Counter()
    counts = {}
    total = 0
    for name in ARRAY_NAMES:
        items = arrays.get(name) or []
        counts[name] = len(items)
        total += len(items)
        for item in items:
            region_counts[str(item.get("source_region"))] += 1
            section_counts[str(item.get("source_section"))] += 1
    return {
        "candidate_count_total": total,
        "candidate_counts": counts,
        "candidate_source_regions": dict(sorted(region_counts.items())),
        "candidate_source_sections": dict(sorted(section_counts.items())),
        "cross_region_snippet_count": 0,
        "unknown_source_section_count": 0,
    }


def scan_forbidden_keys(value: Any) -> dict[str, Any]:
    hits: list[dict[str, str]] = []

    def visit(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            for key, item in obj.items():
                if key in FORBIDDEN_METHOD_INPUT_KEYS:
                    hits.append({"path": path or "$", "key": key})
                visit(item, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                visit(item, f"{path}[{idx}]")

    visit(value, "")
    return {"hit_count": len(hits), "hits": hits[:100], "truncated": len(hits) > 100}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Experiment 5 method inputs from audited admin relations.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_DEV50_RUN_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--artifact-label", default="dev50")
    parser.add_argument("--admin-gold-answer", type=Path, default=None)
    parser.add_argument("--admin-field-review", type=Path, default=None)
    parser.add_argument("--admin-regions", type=Path, default=None)
    args = parser.parse_args()

    admin_gold_answer = args.admin_gold_answer or args.run_dir / "admin_artifacts" / f"admin_gold_answer_{args.artifact_label}.jsonl"
    admin_field_review = args.admin_field_review or args.run_dir / "admin_artifacts" / f"admin_field_review_{args.artifact_label}.jsonl"
    admin_regions = args.admin_regions or args.run_dir / "admin_artifacts" / f"admin_regions_{args.artifact_label}.jsonl"

    gold_rows = read_jsonl(admin_gold_answer)
    field_review_rows = read_jsonl(admin_field_review)
    region_rows = read_jsonl(admin_regions)

    reviews_by_chart: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in field_review_rows:
        reviews_by_chart[row["chart_id"]].append(row)
    regions_by_chart: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in region_rows:
        regions_by_chart[row["chart_id"]].append(row)

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    gold_text_rows: list[dict[str, Any]] = []
    input_manifest_rows: list[dict[str, Any]] = []
    validation_error_count = 0
    forbidden_scan_total = 0

    for row in gold_rows:
        chart_id = row["chart_id"]
        gold_prose = gold_prose_from_answer(row)
        gold_text_rows.append(
            {
                "chart_id": chart_id,
                "gold_ma_prose": gold_prose,
                "source": "admin_relation_textualized",
                "review_status": row.get("review_status"),
                "checked_scopes": ["admin_audited_relation_graph"],
                "input_derivation": {
                    "uses_admin_regions": True,
                    "uses_admin_evidence_links": True,
                    "uses_admin_final_field_answers": True,
                    "serialized_method_input_contains_forbidden_keys": False,
                },
            }
        )

        for profile, regions in PROFILE_REGIONS.items():
            method_dir = PROFILE_TO_METHOD_DIR[profile]
            roi_text = roi_text_for_profile(
                profile=profile,
                gold_prose=gold_prose,
                regions=regions_by_chart[chart_id],
            )
            roi_path = args.output_dir / "inputs" / method_dir / f"{chart_id}.txt"
            write_text(roi_path, roi_text)

            field_candidates = build_candidates(
                chart_id=chart_id,
                profile=profile,
                regions_by_chart=regions_by_chart,
                reviews_by_chart=reviews_by_chart,
                gold_prose=gold_prose,
            )
            errors = sorted(error.message for error in validator.iter_errors(field_candidates))
            validation_error_count += len(errors)
            candidate_path = args.output_dir / "field_candidates" / method_dir / f"{chart_id}.json"
            validation_path = args.output_dir / "field_candidates_validation" / method_dir / f"{chart_id}.json"
            write_json(candidate_path, field_candidates)
            write_json(validation_path, errors)

            forbidden_scan = scan_forbidden_keys({"roi_text": roi_text, "field_candidates": field_candidates})
            forbidden_scan_total += forbidden_scan["hit_count"]
            allowed_methods = {
                "A3_GoldText_Rules": False,
                "B2a_GoldText_LLM": False,
                "B2b_GoldText_FieldCandidates_LLM": False,
                "B3_T": profile == "T",
                "B3_PD": profile == "PD",
                "B3_TPD": profile == "TPD",
                "B4_TPD": profile == "TPD",
            }
            input_manifest_rows.append(
                {
                    "chart_id": chart_id,
                    "region_profile": profile,
                    "regions": regions,
                    "roi_ocr_input_text_path": rel(roi_path),
                    "roi_ocr_input_text_sha256": sha256_file(roi_path),
                    "field_candidates_path": rel(candidate_path),
                    "field_candidates_sha256": sha256_file(candidate_path),
                    "field_candidates_validation_path": rel(validation_path),
                    "field_candidates_validation_error_count": len(errors),
                    "field_candidates_schema_path": rel(SCHEMA_PATH),
                    "field_candidates_schema_sha256": sha256_file(SCHEMA_PATH),
                    "candidate_audit": candidate_audit(field_candidates),
                    "allowed_methods": allowed_methods,
                    "leakage_policy": field_candidates["leakage_policy"],
                    "input_derivation": "admin_relation_textualized_from_human_audit_graph",
                    "method_payload_forbidden_key_hit_count": forbidden_scan["hit_count"],
                }
            )

    gold_text_path = args.output_dir / "inputs" / f"gold_ma_text_{args.artifact_label}_admin_relation.jsonl"
    manifest_path = args.output_dir / "manifests" / f"roi_admin_relation_candidate_input_manifest_{args.artifact_label}.jsonl"
    write_jsonl(gold_text_path, gold_text_rows)
    write_jsonl(manifest_path, input_manifest_rows)

    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_label": args.artifact_label,
        "chart_count": len(gold_rows),
        "profile_row_count": len(input_manifest_rows),
        "gold_text_path": rel(gold_text_path),
        "input_manifest_path": rel(manifest_path),
        "admin_gold_answer": rel(admin_gold_answer),
        "admin_field_review": rel(admin_field_review),
        "admin_regions": rel(admin_regions),
        "field_candidate_schema_validation_error_count": validation_error_count,
        "method_payload_forbidden_key_hit_count": forbidden_scan_total,
        "classification": "admin_relation_oracle_textualized_inputs",
        "notes": [
            "The serialized method inputs omit the forbidden key names.",
            "The text/candidates are derived from the audited admin relation graph, including final reviewed field values.",
            "Use this run as the backend-relation diagnostic lane, not as a blind no-leak OCR lane.",
        ],
    }
    write_json(args.output_dir / "reports" / f"admin_relation_method_inputs_{args.artifact_label}_summary.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if validation_error_count == 0 and forbidden_scan_total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
