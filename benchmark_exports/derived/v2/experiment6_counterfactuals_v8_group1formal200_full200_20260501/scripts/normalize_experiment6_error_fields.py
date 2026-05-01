#!/usr/bin/env python3
"""Normalize Experiment 6 audit-decision error_fields to the allowed vocabulary.

This script is a formatter/post-processing step. It does not change the
consistent boolean and does not inspect labels, targets, scores, or other method
outputs. It only maps over-specific paths such as
missed_approach.legs[3].hold_params.value.inbound_course_deg to the allowed
field missed_approach.legs[3].hold_params.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


BASE_FIELD_NAMES = [
    "path_terminator",
    "fix_ident",
    "altitude_constraint",
    "turn",
    "course_or_radial",
    "hold_params",
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def allowed_error_fields(candidate_record: dict[str, Any]) -> set[str]:
    fields = {"missed_approach.leg_count", "missed_approach.legs.sequence"}
    for leg in candidate_record.get("missed_approach", {}).get("legs", []):
        leg_index = leg.get("leg_index")
        if not isinstance(leg_index, int):
            continue
        fields.update(
            {
                f"missed_approach.legs[{leg_index}].path_terminator",
                f"missed_approach.legs[{leg_index}].fix_ident",
                f"missed_approach.legs[{leg_index}].altitude_constraint",
                f"missed_approach.legs[{leg_index}].turn",
                f"missed_approach.legs[{leg_index}].course_or_radial",
                f"missed_approach.legs[{leg_index}].hold_params",
                f"missed_approach.legs[{leg_index}].hold_params.value.leg_time_min",
            }
        )
    return fields


def normalize_field_path(field: Any) -> str:
    value = str(field).strip()
    if value.startswith("candidate_record."):
        value = value[len("candidate_record.") :]
    value = value.replace(".answers.", ".")

    value = re.sub(r"\.value$", "", value)
    value = re.sub(r"(\.hold_params)\.value\.leg_time_min$", r"\1.value.leg_time_min", value)
    value = re.sub(r"(\.hold_params)\.value\.[^.]+$", r"\1", value)
    for name in BASE_FIELD_NAMES:
        marker = f".{name}."
        if marker in value and not value.endswith(".hold_params.value.leg_time_min"):
            value = value.split(marker, 1)[0] + f".{name}"
            break
    return value


def normalize_fields(fields: Any, allowed: set[str]) -> tuple[list[str], list[dict[str, str]]]:
    if not isinstance(fields, list):
        return [], [{"input": "<non_list>", "output": "<dropped>"}]

    normalized: list[str] = []
    changes: list[dict[str, str]] = []
    for field in fields:
        raw = str(field)
        mapped = normalize_field_path(raw)
        if mapped not in allowed:
            changes.append({"input": raw, "output": mapped, "status": "still_not_allowed"})
        elif mapped != raw:
            changes.append({"input": raw, "output": mapped, "status": "normalized"})
        if mapped not in normalized:
            normalized.append(mapped)
    return normalized, changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-jsonl", required=True, type=Path)
    parser.add_argument("--predictions-jsonl", required=True, type=Path)
    parser.add_argument("--out-jsonl", required=True, type=Path)
    parser.add_argument("--audit-json", required=True, type=Path)
    args = parser.parse_args()

    cases = {row["verification_case_id"]: row for row in read_jsonl(args.cases_jsonl)}
    rows = read_jsonl(args.predictions_jsonl)
    out_rows: list[dict[str, Any]] = []
    all_changes: list[dict[str, Any]] = []
    still_not_allowed: list[dict[str, Any]] = []

    for row in rows:
        case_id = row.get("verification_case_id")
        case = cases.get(case_id)
        out = json.loads(json.dumps(row, ensure_ascii=False))
        pred = out.get("parsed_output")
        if case and isinstance(pred, dict):
            allowed = allowed_error_fields(case["candidate_record"])
            normalized, changes = normalize_fields(pred.get("error_fields"), allowed)
            pred["error_fields"] = normalized
            if changes:
                all_changes.append({"verification_case_id": case_id, "changes": changes})
                for change in changes:
                    if change.get("status") == "still_not_allowed":
                        still_not_allowed.append({"verification_case_id": case_id, **change})
            out["error_field_normalization"] = {
                "policy": "experiment6_allowed_vocabulary_v1",
                "changed": bool(changes),
            }
            out["raw_output_before_error_field_normalization"] = row.get("raw_output")
            out["raw_output"] = json.dumps(pred, ensure_ascii=False, sort_keys=True)
        out_rows.append(out)

    write_jsonl(args.out_jsonl, out_rows)
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(
        json.dumps(
            {
                "input_predictions": str(args.predictions_jsonl),
                "output_predictions": str(args.out_jsonl),
                "cases_jsonl": str(args.cases_jsonl),
                "rows": len(rows),
                "changed_rows": len(all_changes),
                "still_not_allowed_count": len(still_not_allowed),
                "still_not_allowed_examples": still_not_allowed[:50],
                "change_examples": all_changes[:50],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"rows": len(rows), "changed_rows": len(all_changes)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
