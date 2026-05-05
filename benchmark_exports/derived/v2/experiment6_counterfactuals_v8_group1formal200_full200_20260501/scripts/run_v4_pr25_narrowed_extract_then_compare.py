#!/usr/bin/env python3
"""Run Experiment 6 Group-1-v2-neutralized extract-then-compare.

This is not intended as a separate paper method. It applies the same
chart-display equivalence introduced for Group 1 scoring-equivalence v2 so
Experiment 6 does not treat harmless display differences as counterfactual
errors.
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


def extraction_validation_error(validation_dir: Optional[Path], chart_id: str) -> Optional[str]:
    if validation_dir is None:
        return None
    validation_path = validation_dir / f"{chart_id}.json"
    if not validation_path.exists():
        return f"missing_extraction_validation: {validation_path}"
    errors = json.loads(validation_path.read_text(encoding="utf-8"))
    if errors:
        return f"schema_invalid_extraction: {errors}"
    return None


def unwrap_field(obj: Any) -> Any:
    if isinstance(obj, dict) and set(obj).issuperset({"status", "value"}):
        return {"status": obj.get("status"), "value": obj.get("value")}
    return obj


def answers_for_leg(canonical: Dict[str, Any], leg_index: int) -> Optional[Dict[str, Any]]:
    for leg in canonical.get("missed_approach", {}).get("legs", []):
        if leg.get("leg_index") == leg_index:
            return leg.get("answers", {})
    return None


def canonical_field(canonical: Dict[str, Any], leg_index: int, field_name: str) -> Any:
    answers = answers_for_leg(canonical, leg_index)
    if answers is None:
        return None
    return unwrap_field(answers.get(FIELD_MAP[field_name]))


def normalize_fix_or_navaid(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip().upper()
    suffixes = [" LOCALIZER", " VORTAC", " VOR/DME", " VOR", " NDB", " LOC", " DME"]
    for suffix in suffixes:
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    text = text.replace("-", "")
    text = " ".join(text.split())
    return text


def round_half_up_degree(value: float) -> int:
    return int(math.floor(float(value) + 0.5)) % 360


def degree_display_equal(a: Any, b: Any) -> bool:
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return a == b
    return round_half_up_degree(float(a)) == round_half_up_degree(float(b))


def scalar_strict_equal(a: Any, b: Any) -> bool:
    return a == b


def status_value_equal(candidate: Any, extraction: Any, context: str) -> bool:
    if isinstance(candidate, dict) and set(candidate).issuperset({"status", "value"}):
        if not isinstance(extraction, dict) or not set(extraction).issuperset({"status", "value"}):
            return False
        if candidate.get("status") != extraction.get("status"):
            return False
        return values_equal(candidate.get("value"), extraction.get("value"), context + ".value")
    return values_equal(candidate, extraction, context)


def values_equal(a: Any, b: Any, context: str = "") -> bool:
    if context.endswith("fix_ident") or context.endswith("navaid") or ".navaid" in context:
        return normalize_fix_or_navaid(a) == normalize_fix_or_navaid(b)
    if context.endswith("course_deg") or context.endswith("radial_deg") or context.endswith("inbound_course_deg"):
        return degree_display_equal(a, b)
    if isinstance(a, dict) and isinstance(b, dict):
        keys = set(a) | set(b)
        return all(values_equal(a.get(k), b.get(k), f"{context}.{k}" if context else str(k)) for k in keys)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(values_equal(x, y, context) for x, y in zip(a, b))
    return scalar_strict_equal(a, b)


def hold_param_error_field(leg_index: int, candidate_value: Any, extraction_value: Any) -> str:
    candidate_inner = candidate_value.get("value") if isinstance(candidate_value, dict) else None
    extraction_inner = extraction_value.get("value") if isinstance(extraction_value, dict) else None
    if isinstance(candidate_inner, dict) and isinstance(extraction_inner, dict):
        for subfield in ["inbound_course_deg", "leg_time_min", "leg_distance_nm", "turn"]:
            if not values_equal(candidate_inner.get(subfield), extraction_inner.get(subfield), f"hold_params.value.{subfield}"):
                if subfield == "leg_time_min":
                    return f"missed_approach.legs[{leg_index}].hold_params.value.leg_time_min"
                if subfield == "inbound_course_deg":
                    return f"missed_approach.legs[{leg_index}].hold_params.value.inbound_course_deg"
                return f"missed_approach.legs[{leg_index}].hold_params"
    return f"missed_approach.legs[{leg_index}].hold_params"


def compare_candidate_to_extraction(candidate: Dict[str, Any], extraction: Dict[str, Any]) -> Dict[str, Any]:
    error_fields: List[str] = []
    candidate_ma = candidate.get("missed_approach", {})
    extraction_ma = extraction.get("missed_approach", {})
    candidate_leg_count = candidate_ma.get("leg_count")
    extraction_leg_count_obj = extraction_ma.get("leg_count")
    extraction_leg_count = extraction_leg_count_obj.get("value") if isinstance(extraction_leg_count_obj, dict) else extraction_leg_count_obj
    if isinstance(extraction_leg_count, int) and candidate_leg_count != extraction_leg_count:
        error_fields.append("missed_approach.leg_count")

    extraction_leg_indices = {leg.get("leg_index") for leg in extraction_ma.get("legs", [])}
    candidate_leg_indices = {leg.get("leg_index") for leg in candidate_ma.get("legs", [])}
    if extraction_leg_indices and extraction_leg_indices != candidate_leg_indices:
        error_fields.append("missed_approach.legs.sequence")

    for leg in candidate_ma.get("legs", []):
        leg_index = leg.get("leg_index")
        if not isinstance(leg_index, int) or leg_index not in extraction_leg_indices:
            continue
        for field_name in FIELD_MAP:
            candidate_value = unwrap_field(leg.get(field_name))
            extraction_value = canonical_field(extraction, leg_index, field_name)
            if extraction_value is None:
                continue
            if not status_value_equal(candidate_value, extraction_value, field_name):
                if field_name == "hold_params":
                    error_fields.append(hold_param_error_field(leg_index, candidate_value, extraction_value))
                else:
                    error_fields.append(f"missed_approach.legs[{leg_index}].{field_name}")

    unique_fields = []
    for field in error_fields:
        if field not in unique_fields:
            unique_fields.append(field)
    return {"consistent": len(unique_fields) == 0, "error_fields": unique_fields[:5]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-jsonl", required=True)
    parser.add_argument("--extraction-dir", required=True)
    parser.add_argument("--out-jsonl", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--extractor-method", default="C4")
    parser.add_argument("--method-name", default="")
    parser.add_argument("--policy-name", default="group1_scoring_equivalence_v2_neutralized")
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
            parse_error = f"pr25_narrowed_extract_then_compare_error: {type(exc).__name__}: {exc}"
        rows.append(
            {
                "verification_case_id": case["verification_case_id"],
                "chart_id": case["chart_id"],
                "sample_id": case["sample_id"],
                "method": args.method_name or f"V3_group1v2_neutralized_extract_then_compare_{args.extractor_method}",
                "model": "symbolic_group1v2_neutralized_comparer",
                "prompt_hash": None,
                "input_hash": stable_hash(
                    {
                        "verification_case_id": case["verification_case_id"],
                        "candidate_record": case["candidate_record"],
                        "extraction_path": str(extraction_path),
                        "extraction_hash": extraction_hash,
                        "policy": args.policy_name,
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
                    "compare_policy": args.policy_name,
                },
            }
        )

    out.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    summary = {
        "method": args.method_name or f"V3_group1v2_neutralized_extract_then_compare_{args.extractor_method}",
        "cases_jsonl": args.cases_jsonl,
        "extraction_dir": args.extraction_dir,
        "validation_dir": args.validation_dir or None,
        "compare_policy": args.policy_name,
        "out_jsonl": args.out_jsonl,
        "requested_records": len(cases),
        "parse_ok": sum(1 for row in rows if row["parse_ok"]),
        "parse_fail": sum(1 for row in rows if not row["parse_ok"]),
        "api_error": 0,
        "elapsed_sec": round(time.time() - started, 3),
    }
    summary_path = Path(args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["parse_fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
