#!/usr/bin/env python3
"""Run Experiment 6 V4 tolerant/link extract-then-compare.

This runner uses only candidate_record plus one frozen extractor canonical JSON
output. It does not read labels, targets, scores, OCR, or images.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


FIELD_MAP = {
    "path_terminator": "Q_terminator",
    "fix_ident": "Q1_fix_ident",
    "altitude_constraint": "Q2_altitude_constraint",
    "turn": "Q3_turn",
    "course_or_radial": "Q4_course_or_radial",
    "hold_params": "Q5_hold_params",
}

ALIGN_WEIGHTS = {
    "path_terminator": 1.5,
    "fix_ident": 4.0,
    "altitude_constraint": 2.5,
    "turn": 1.0,
    "course_or_radial": 2.5,
    "hold_params": 2.0,
}

ALIGN_THRESHOLD = 2.0
MAX_ERROR_FIELDS = 5
MISMATCH_THRESHOLD = 4.0
MISMATCH_WEIGHTS = {
    "fix_ident": 4.0,
    "altitude_constraint": 2.0,
    "course_or_radial": 2.0,
    "hold_params": 1.5,
    "turn": 1.0,
    "path_terminator": 0.5,
    "missed_approach.legs.sequence": 2.0,
}


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def stable_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_validation_errors(validation_path: Path) -> List[Any]:
    payload = json.loads(validation_path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if payload.get("valid") is True or payload.get("schema_valid") is True:
            return []
        return payload.get("errors") or payload.get("validation_errors") or [payload]
    return [f"unexpected_validation_payload_type:{type(payload).__name__}"]


def extraction_validation_error(validation_dir: Optional[Path], chart_id: str) -> Optional[str]:
    if validation_dir is None:
        return None
    validation_path = validation_dir / f"{chart_id}.json"
    if not validation_path.exists():
        return f"missing_extraction_validation: {validation_path}"
    errors = load_validation_errors(validation_path)
    if errors:
        return f"schema_invalid_extraction: {errors}"
    return None


def field_status(obj: Any) -> str:
    if isinstance(obj, dict) and "status" in obj:
        return str(obj.get("status") or "unknown")
    if obj is None:
        return "unknown"
    return "present"


def field_value(obj: Any) -> Any:
    if isinstance(obj, dict) and "status" in obj and "value" in obj:
        return obj.get("value")
    return obj


def is_present(obj: Any) -> bool:
    status = field_status(obj)
    return status == "present" and field_value(obj) is not None


def normalize_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().upper()
    return value


def angle_diff(a: float, b: float) -> float:
    return abs((float(a) - float(b) + 180.0) % 360.0 - 180.0)


def numeric_tolerance(context: str, a: float, b: float) -> float:
    context = context.lower()
    if any(token in context for token in ("course", "radial", "heading", "inbound_course")):
        return 2.0
    if "altitude" in context:
        return 50.0
    if "distance" in context or context.endswith("_nm"):
        return 0.1
    if "time" in context or context.endswith("_min"):
        return 0.1
    return 2.0 if max(abs(float(a)), abs(float(b))) <= 360 else 50.0


def numbers_equivalent(a: Any, b: Any, context: str) -> bool:
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return False
    if any(token in context.lower() for token in ("course", "radial", "heading", "inbound_course")):
        return angle_diff(float(a), float(b)) <= numeric_tolerance(context, float(a), float(b))
    return abs(float(a) - float(b)) <= numeric_tolerance(context, float(a), float(b))


def partial_value_compare(candidate_value: Any, extraction_value: Any, context: str) -> Tuple[str, Optional[str]]:
    """Compare values using extraction as evidence.

    Returns (state, detail), where state is match, mismatch, or no_evidence.
    """
    candidate_value = normalize_scalar(candidate_value)
    extraction_value = normalize_scalar(extraction_value)

    if extraction_value is None:
        return "no_evidence", None
    if candidate_value is None:
        return "mismatch", context
    if isinstance(candidate_value, (int, float)) and isinstance(extraction_value, (int, float)):
        return ("match", None) if numbers_equivalent(candidate_value, extraction_value, context) else ("mismatch", context)
    if isinstance(candidate_value, str) or isinstance(extraction_value, str):
        return ("match", None) if candidate_value == extraction_value else ("mismatch", context)
    if isinstance(candidate_value, dict) and isinstance(extraction_value, dict):
        saw_evidence = False
        for key, ext_subvalue in extraction_value.items():
            if ext_subvalue is None:
                continue
            state, detail = partial_value_compare(candidate_value.get(key), ext_subvalue, f"{context}.{key}")
            if state == "mismatch":
                return "mismatch", detail
            if state == "match":
                saw_evidence = True
        return ("match", None) if saw_evidence else ("no_evidence", None)
    if isinstance(candidate_value, list) and isinstance(extraction_value, list):
        if not extraction_value:
            return "no_evidence", None
        if len(candidate_value) != len(extraction_value):
            return "mismatch", context
        for idx, (cand_item, ext_item) in enumerate(zip(candidate_value, extraction_value)):
            state, detail = partial_value_compare(cand_item, ext_item, f"{context}.{idx}")
            if state == "mismatch":
                return "mismatch", detail
        return "match", None
    return ("match", None) if candidate_value == extraction_value else ("mismatch", context)


def compare_course_or_radial(candidate_value: Any, extraction_value: Any) -> Tuple[str, Optional[str]]:
    if not isinstance(extraction_value, dict):
        return partial_value_compare(candidate_value, extraction_value, "course_or_radial")
    if not isinstance(candidate_value, dict):
        return "mismatch", "course_or_radial"

    # If both sides expose navaid/radial, this is the strongest comparison.
    ext_radial = extraction_value.get("radial_deg")
    cand_radial = candidate_value.get("radial_deg")
    if isinstance(ext_radial, (int, float)) and isinstance(cand_radial, (int, float)):
        ext_navaid = normalize_scalar(extraction_value.get("navaid"))
        cand_navaid = normalize_scalar(candidate_value.get("navaid"))
        if ext_navaid and cand_navaid and ext_navaid != cand_navaid:
            return "mismatch", "course_or_radial.navaid"
        if angle_diff(float(cand_radial), float(ext_radial)) <= 2.0:
            return "match", None
        if angle_diff(float(cand_radial), float(ext_radial) + 180.0) <= 2.0:
            return "match", None
        return "mismatch", "course_or_radial.radial_deg"

    # Course-only comparison.
    ext_course = extraction_value.get("course_deg")
    cand_course = candidate_value.get("course_deg")
    if isinstance(ext_course, (int, float)) and isinstance(cand_course, (int, float)):
        return ("match", None) if angle_diff(float(cand_course), float(ext_course)) <= 2.0 else ("mismatch", "course_or_radial.course_deg")

    return partial_value_compare(candidate_value, extraction_value, "course_or_radial")


def compare_field(field_name: str, candidate_obj: Any, extraction_obj: Any) -> Tuple[str, Optional[str]]:
    if not is_present(extraction_obj):
        return "no_evidence", None
    if not is_present(candidate_obj):
        return "mismatch", field_name
    candidate_value = field_value(candidate_obj)
    extraction_value = field_value(extraction_obj)
    if field_name == "course_or_radial":
        return compare_course_or_radial(candidate_value, extraction_value)
    return partial_value_compare(candidate_value, extraction_value, field_name)


def answers_for_leg(canonical_leg: Dict[str, Any]) -> Dict[str, Any]:
    return canonical_leg.get("answers", {}) if isinstance(canonical_leg, dict) else {}


def canonical_field(canonical_leg: Dict[str, Any], field_name: str) -> Any:
    return answers_for_leg(canonical_leg).get(FIELD_MAP[field_name])


def present_evidence_count(leg: Dict[str, Any], extractor_leg: bool) -> int:
    count = 0
    for field_name in FIELD_MAP:
        obj = canonical_field(leg, field_name) if extractor_leg else leg.get(field_name)
        if is_present(obj):
            count += 1
    return count


def alignment_score(candidate_leg: Dict[str, Any], extraction_leg: Dict[str, Any]) -> Tuple[float, int]:
    score = 0.0
    comparable = 0
    if candidate_leg.get("leg_index") == extraction_leg.get("leg_index"):
        score += 0.5
    for field_name, weight in ALIGN_WEIGHTS.items():
        candidate_obj = candidate_leg.get(field_name)
        extraction_obj = canonical_field(extraction_leg, field_name)
        if not is_present(candidate_obj) or not is_present(extraction_obj):
            continue
        comparable += 1
        state, _ = compare_field(field_name, candidate_obj, extraction_obj)
        if state == "match":
            score += weight
    return score, comparable


def align_legs(candidate_legs: List[Dict[str, Any]], extraction_legs: List[Dict[str, Any]]) -> Dict[int, int]:
    pair_scores: List[Tuple[float, int, int, int, bool]] = []
    for ci, candidate_leg in enumerate(candidate_legs):
        for ei, extraction_leg in enumerate(extraction_legs):
            score, comparable = alignment_score(candidate_leg, extraction_leg)
            same_index = candidate_leg.get("leg_index") == extraction_leg.get("leg_index")
            if score >= ALIGN_THRESHOLD or (same_index and comparable > 0):
                pair_scores.append((score, comparable, ci, ei, same_index))
    pair_scores.sort(key=lambda item: (item[0], item[1], item[4]), reverse=True)

    aligned: Dict[int, int] = {}
    used_candidates: set[int] = set()
    used_extractions: set[int] = set()
    for _, _, ci, ei, _ in pair_scores:
        if ci in used_candidates or ei in used_extractions:
            continue
        aligned[ci] = ei
        used_candidates.add(ci)
        used_extractions.add(ei)
    return aligned


def hold_param_error_field(leg_index: int, detail: Optional[str]) -> str:
    if detail and "leg_time_min" in detail:
        return f"missed_approach.legs[{leg_index}].hold_params.value.leg_time_min"
    if detail and "leg_distance_nm" in detail:
        return f"missed_approach.legs[{leg_index}].hold_params.value.leg_distance_nm"
    if detail and "inbound_course_deg" in detail:
        return f"missed_approach.legs[{leg_index}].hold_params.value.inbound_course_deg"
    return f"missed_approach.legs[{leg_index}].hold_params"


def error_field_path(leg_index: int, field_name: str, detail: Optional[str]) -> str:
    if field_name == "hold_params":
        return hold_param_error_field(leg_index, detail)
    return f"missed_approach.legs[{leg_index}].{field_name}"


def mismatch_weight(field_name: str) -> float:
    if field_name == "missed_approach.legs.sequence":
        return MISMATCH_WEIGHTS[field_name]
    return MISMATCH_WEIGHTS.get(field_name, 1.0)


def compare_candidate_to_extraction(candidate: Dict[str, Any], extraction: Dict[str, Any]) -> Dict[str, Any]:
    error_fields: List[str] = []
    weighted_mismatches: List[Tuple[str, float]] = []
    candidate_legs = candidate.get("missed_approach", {}).get("legs", [])
    extraction_legs = extraction.get("missed_approach", {}).get("legs", [])
    aligned = align_legs(candidate_legs, extraction_legs)
    aligned_extraction_indices = set(aligned.values())

    for ci, candidate_leg in enumerate(candidate_legs):
        if ci not in aligned:
            # Missing extractor evidence does not disprove a candidate leg.
            continue
        extraction_leg = extraction_legs[aligned[ci]]
        leg_index = candidate_leg.get("leg_index")
        if not isinstance(leg_index, int):
            continue
        for field_name in FIELD_MAP:
            state, detail = compare_field(field_name, candidate_leg.get(field_name), canonical_field(extraction_leg, field_name))
            if state == "mismatch":
                path = error_field_path(leg_index, field_name, detail)
                error_fields.append(path)
                weighted_mismatches.append((path, mismatch_weight(field_name)))

    # Extra extractor legs are weak evidence for sequence error only if they contain
    # enough present fields to be meaningful.
    for ei, extraction_leg in enumerate(extraction_legs):
        if ei in aligned_extraction_indices:
            continue
        if present_evidence_count(extraction_leg, extractor_leg=True) >= 2:
            error_fields.append("missed_approach.legs.sequence")
            weighted_mismatches.append(("missed_approach.legs.sequence", mismatch_weight("missed_approach.legs.sequence")))
            break

    unique_fields: List[str] = []
    for field in error_fields:
        if field not in unique_fields:
            unique_fields.append(field)
    mismatch_score = sum(weight for _, weight in weighted_mismatches)
    if mismatch_score < MISMATCH_THRESHOLD:
        return {"consistent": True, "error_fields": []}
    return {"consistent": False, "error_fields": unique_fields[:MAX_ERROR_FIELDS]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-jsonl", required=True)
    parser.add_argument("--extraction-dir", required=True)
    parser.add_argument("--out-jsonl", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--extractor-method", default="C4")
    parser.add_argument("--validation-dir", default="")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    cases = list(read_jsonl(Path(args.cases_jsonl)))
    if args.limit:
        cases = cases[: args.limit]

    out = Path(args.out_jsonl)
    out.parent.mkdir(parents=True, exist_ok=True)
    extraction_dir = Path(args.extraction_dir)
    validation_dir = Path(args.validation_dir) if args.validation_dir else None
    started = time.time()
    rows: List[Dict[str, Any]] = []

    for case in cases:
        extraction_path = extraction_dir / f"{case['chart_id']}.json"
        parse_ok = True
        parse_error = None
        parsed_output = None
        extraction_hash = None
        try:
            validation_error = extraction_validation_error(validation_dir, case["chart_id"])
            if validation_error is not None:
                raise ValueError(validation_error)
            extraction = load_json(extraction_path)
            extraction_hash = stable_hash(extraction)
            parsed_output = compare_candidate_to_extraction(case["candidate_record"], extraction)
        except Exception as exc:
            parse_ok = False
            parse_error = f"tolerant_extract_then_compare_error: {type(exc).__name__}: {exc}"
        rows.append(
            {
                "verification_case_id": case["verification_case_id"],
                "chart_id": case["chart_id"],
                "sample_id": case["sample_id"],
                "method": f"V4_tolerant_extract_then_compare_{args.extractor_method}",
                "model": "symbolic_tolerant_comparer",
                "prompt_hash": None,
                "input_hash": stable_hash(
                    {
                        "verification_case_id": case["verification_case_id"],
                        "candidate_record": case["candidate_record"],
                        "extraction_hash": extraction_hash,
                        "policy": "v4_tolerant_compare_policy",
                    }
                ),
                "raw_output": json.dumps(parsed_output, ensure_ascii=False, sort_keys=True) if parsed_output else "",
                "parsed_output": parsed_output,
                "parse_ok": parse_ok,
                "parse_error": parse_error,
                "api_error": None,
                "api_attempts": 0,
                "elapsed_sec": 0,
                "diagnostics": {
                    "extraction_path": str(extraction_path),
                    "extraction_hash": extraction_hash,
                    "compare_policy": "configs/v4_tolerant_compare_policy.md",
                },
            }
        )

    with out.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    summary = {
        "method": f"V4_tolerant_extract_then_compare_{args.extractor_method}",
        "cases_jsonl": args.cases_jsonl,
        "extraction_dir": args.extraction_dir,
        "validation_dir": args.validation_dir or None,
        "out_jsonl": args.out_jsonl,
        "requested_records": len(cases),
        "parse_ok": sum(1 for row in rows if row.get("parse_ok")),
        "parse_fail": sum(1 for row in rows if not row.get("parse_ok")),
        "api_error": 0,
        "elapsed_sec": round(time.time() - started, 3),
        "compare_policy": "configs/v4_tolerant_compare_policy.md",
        "mismatch_threshold": MISMATCH_THRESHOLD,
    }
    summary_path = Path(args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["parse_fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
