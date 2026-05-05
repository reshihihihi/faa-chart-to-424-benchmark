#!/usr/bin/env python3
"""Check Experiment 6 packed verifier inputs for answer leakage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


FORBIDDEN_KEY_TOKENS = [
    "label",
    "consistent",
    "error_fields",
    "counterfactual_type",
    "target",
    "canonical_target",
    "canonical_proxy_gt",
    "score",
    "expected",
    "answer_key",
    "evidence_provenance",
    "challenge_tags",
    "raw_cifp",
    "source_target_sha256",
    "mutation_rule",
    "mutation_notes",
]

FORBIDDEN_VALUE_TOKENS = [
    "counterfactual_type",
    "fix_substitution",
    "altitude_perturbation",
    "turn_direction_flip",
    "course_radial_error",
    "holding_parameter_error",
    "implicit_hold_time_omission",
    "path_terminator_substitution",
    "ca_omission",
    "positive candidate",
    "negative candidate",
]


def read_jsonl(path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if line:
                yield line_no, json.loads(line)


def walk(obj: Any, path: str = "$") -> Iterable[Tuple[str, Any]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_path = f"{path}.{key}"
            yield key_path, key
            yield from walk(value, key_path)
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from walk(value, f"{path}[{idx}]")
    else:
        yield path, obj


def check_obj(obj: Dict[str, Any]) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    for path, value in walk(obj):
        if path.endswith("verification_case_id") or path.endswith("chart_id") or path.endswith("sample_id"):
            continue
        if isinstance(value, str):
            lower_value = value.lower()
            if path.split(".")[-1] == value:
                for token in FORBIDDEN_KEY_TOKENS:
                    if token in lower_value:
                        findings.append({"path": path, "kind": "forbidden_key", "token": token})
            else:
                for token in FORBIDDEN_VALUE_TOKENS:
                    if token in lower_value:
                        findings.append({"path": path, "kind": "forbidden_value", "token": token})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-jsonl", required=True)
    parser.add_argument("--report-json", required=True)
    args = parser.parse_args()

    findings: List[Dict[str, Any]] = []
    count = 0
    for line_no, obj in read_jsonl(Path(args.input_jsonl)):
        count += 1
        obj_findings = check_obj(obj)
        if obj_findings:
            findings.append({"line": line_no, "verification_case_id": obj.get("verification_case_id"), "findings": obj_findings})

    report = {
        "input_jsonl": args.input_jsonl,
        "checked_records": count,
        "finding_count": len(findings),
        "findings": findings[:100],
        "status": "pass" if not findings else "fail",
    }
    out = Path(args.report_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
