from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_pilot10_anthropic import (  # noqa: E402
    DATA_DIR,
    SCHEMA_PATH,
    read_jsonl,
    resolve_package_path,
    score_canonical,
    sha256_file,
    validate_canonical,
    write_json,
)


QUESTION_TO_CANONICAL = {
    "q_terminator": "Q_terminator",
    "q1_fix_ident": "Q1_fix_ident",
    "q2_altitude_constraint": "Q2_altitude_constraint",
    "q3_turn": "Q3_turn",
    "q4_course_or_radial": "Q4_course_or_radial",
    "q5_hold_params": "Q5_hold_params",
}
QA_PROMPT_DIR = ROOT / "prompts" / "path_c_qa_v2"
AGGREGATOR_SPEC = ROOT / "docs" / "group1_c2_qa_aggregator_candidate_v1.md"


def answer(status: str, value: Any = None) -> dict[str, Any]:
    if status != "present":
        value = None
    return {"status": status, "value": value}


def read_answer(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, repr(exc)
    if not isinstance(obj, dict) or "status" not in obj or "value" not in obj:
        return None, "answer_object_missing_status_or_value"
    return obj, None


def missing_answer() -> dict[str, Any]:
    return answer("unknown")


def aggregate_chart(row: dict[str, Any], qa_chart_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    prediction = {
        "chart_id": row["chart_id"],
        "procedure": {
            "airport": row["airport"],
            "approach_ident": row["proc_ident"],
            "chart_name": row["chart_name"],
        },
        "missed_approach": {"leg_count": answer("unknown"), "legs": []},
    }
    diagnostics: dict[str, Any] = {
        "qa_chart_root": str(qa_chart_root),
        "missing_or_invalid": [],
        "policy": {
            "q0_leg_count_controls_followup_leg_count": True,
            "missing_or_invalid_answer_fill": {"status": "unknown", "value": None},
            "semantic_repair": False,
            "target_or_scorer_used": False,
        },
    }

    q0, error = read_answer(qa_chart_root / "q0_leg_count.json")
    if error or q0 is None:
        diagnostics["missing_or_invalid"].append({"path": "q0_leg_count.json", "error": error})
        return prediction, diagnostics

    prediction["missed_approach"]["leg_count"] = q0
    if q0.get("status") != "present" or not isinstance(q0.get("value"), int) or q0["value"] < 1:
        prediction["missed_approach"]["leg_count"] = answer("unknown")
        prediction["missed_approach"]["legs"] = []
        diagnostics["leg_count_not_present"] = q0
        return prediction, diagnostics

    legs = []
    for leg_index in range(1, q0["value"] + 1):
        leg_dir = qa_chart_root / f"leg_{leg_index:03d}"
        answers = {}
        for question_id, canonical_field in QUESTION_TO_CANONICAL.items():
            rel_path = f"leg_{leg_index:03d}/{question_id}.json"
            obj, field_error = read_answer(leg_dir / f"{question_id}.json")
            if field_error or obj is None:
                obj = missing_answer()
                diagnostics["missing_or_invalid"].append({"path": rel_path, "error": field_error or "missing"})
            answers[canonical_field] = obj
        legs.append({"leg_index": leg_index, "answers": answers})

    prediction["missed_approach"]["legs"] = legs
    return prediction, diagnostics


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [item["score"] for item in results if item.get("score")]
    correct = sum(item["correct"] for item in scored)
    total = sum(item["total"] for item in scored)
    return {
        "samples_total": len(results),
        "schema_valid": sum(1 for item in results if item.get("validation_error_count") == 0),
        "samples_scored": len(scored),
        "score": {"correct": correct, "total": total, "accuracy": correct / total if total else None},
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate C2 multi-QA outputs into canonical JSON.")
    parser.add_argument("--qa-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--sample-manifest", type=Path, default=DATA_DIR / "pilot10_manifest.jsonl")
    parser.add_argument("--score", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()

    rows = read_jsonl(args.sample_manifest)[: args.limit]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    output_root = args.output_root

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "method": "C2",
        "parameter_status": "candidate_aggregator_not_formal_frozen",
        "qa_root": str(args.qa_root),
        "schema": {"path": SCHEMA_PATH.relative_to(ROOT).as_posix(), "sha256": sha256_file(SCHEMA_PATH)},
        "qa_prompt_bundle": {
            "path": QA_PROMPT_DIR.relative_to(ROOT).as_posix(),
            "status": "upstream_PR28_candidate_not_formal_frozen",
        },
        "aggregator": {
            "script_path": "scripts/aggregate_c2_qa_candidate.py",
            "script_sha256": sha256_file(Path(__file__)),
            "spec_path": AGGREGATOR_SPEC.relative_to(ROOT).as_posix(),
            "spec_sha256": sha256_file(AGGREGATOR_SPEC),
            "target_used_for_aggregation": False,
            "scorer_used_for_aggregation": False,
        },
    }
    write_json(output_root / "aggregation_manifest.json", manifest)

    results = []
    failures = []
    for row in rows:
        chart_id = row["chart_id"]
        prediction, diagnostics = aggregate_chart(row, args.qa_root / chart_id)
        write_json(output_root / "C2" / "canonical_json" / f"{chart_id}.json", prediction)
        write_json(output_root / "C2" / "aggregation_diagnostics" / f"{chart_id}.json", diagnostics)
        validation_errors = validate_canonical(prediction, validator)
        write_json(output_root / "C2" / "validation" / f"{chart_id}.json", validation_errors)
        item: dict[str, Any] = {
            "method": "C2",
            "sample_id": row["pilot_sample_id"],
            "chart_id": chart_id,
            "validation_error_count": len(validation_errors),
            "validation_errors": validation_errors,
            "score": None,
        }
        if validation_errors:
            failures.append({"chart_id": chart_id, "error": "schema_validation_failed"})
        elif args.score:
            target_path = resolve_package_path(row["canonical_proxy_gt_file"])
            target = json.loads(target_path.read_text(encoding="utf-8"))
            score = score_canonical(prediction, target)
            write_json(output_root / "C2" / "scores" / f"{chart_id}.json", score)
            item["score"] = {key: score[key] for key in ["correct", "total", "accuracy"]}
        results.append(item)

    summary = {"created_at": datetime.now(timezone.utc).isoformat(), "method": "C2", "summary": summarize(results), "failures": failures}
    write_json(output_root / "summary_report.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
