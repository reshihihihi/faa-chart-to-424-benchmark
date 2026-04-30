#!/usr/bin/env python3
"""Structural validator for Experiment 6 verification case JSONL."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List


REQUIRED_TOP = {
    "verification_case_id",
    "chart_id",
    "sample_id",
    "split",
    "image_path",
    "image_sha256",
    "candidate_record",
    "label",
    "construction",
}


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc


def validate_case(case: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    missing = REQUIRED_TOP - set(case)
    extra = set(case) - REQUIRED_TOP
    if missing:
        errors.append(f"missing top-level keys: {sorted(missing)}")
    if extra:
        errors.append(f"unexpected top-level keys: {sorted(extra)}")

    candidate = case.get("candidate_record", {})
    if candidate.get("record_schema_version") != "candidate_424_like_v1":
        errors.append("candidate_record.record_schema_version must be candidate_424_like_v1")
    if candidate.get("chart_id") != case.get("chart_id"):
        errors.append("candidate_record.chart_id must match chart_id")
    ma = candidate.get("missed_approach", {})
    legs = ma.get("legs")
    if not isinstance(legs, list):
        errors.append("candidate_record.missed_approach.legs must be a list")
    elif not isinstance(ma.get("leg_count"), int):
        errors.append("candidate_record.missed_approach.leg_count must be an integer")
    elif ma.get("leg_count") != len(legs):
        errors.append("candidate_record.missed_approach.leg_count must equal len(legs)")

    label = case.get("label", {})
    if not isinstance(label.get("consistent"), bool):
        errors.append("label.consistent must be boolean")
    if not isinstance(label.get("error_fields"), list):
        errors.append("label.error_fields must be list")
    if not isinstance(label.get("counterfactual_type"), str):
        errors.append("label.counterfactual_type must be string")
    if label.get("consistent") is True and label.get("error_fields"):
        errors.append("positive/consistent case must have empty error_fields")
    if label.get("consistent") is False and not label.get("error_fields"):
        errors.append("negative/inconsistent case must have non-empty error_fields")
    if label.get("consistent") is True and label.get("counterfactual_type") != "positive":
        errors.append("consistent case must use counterfactual_type=positive")
    if label.get("consistent") is False and label.get("counterfactual_type") == "positive":
        errors.append("positive counterfactual_type cannot be inconsistent")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-jsonl", required=True)
    parser.add_argument("--report-json", required=True)
    args = parser.parse_args()

    path = Path(args.cases_jsonl)
    errors: List[Dict[str, Any]] = []
    ids = set()
    duplicate_ids = []
    type_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    count = 0

    for case in read_jsonl(path):
        count += 1
        case_id = case.get("verification_case_id")
        if case_id in ids:
            duplicate_ids.append(case_id)
        ids.add(case_id)
        type_counts[case.get("label", {}).get("counterfactual_type", "<missing>")] += 1
        split_counts[case.get("split", "<missing>")] += 1
        case_errors = validate_case(case)
        if case_errors:
            errors.append({"verification_case_id": case_id, "errors": case_errors})

    report = {
        "cases_jsonl": str(path),
        "case_count": count,
        "duplicate_ids": duplicate_ids,
        "type_counts": dict(sorted(type_counts.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "error_count": len(errors) + len(duplicate_ids),
        "errors": errors[:100],
        "status": "pass" if not errors and not duplicate_ids else "fail",
    }
    out = Path(args.report_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
