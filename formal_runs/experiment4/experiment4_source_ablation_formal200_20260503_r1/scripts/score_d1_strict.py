from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


QUESTION_FIELDS = [
    "Q_terminator",
    "Q1_fix_ident",
    "Q2_altitude_constraint",
    "Q3_turn",
    "Q4_course_or_radial",
    "Q5_hold_params",
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def validate_canonical(obj: dict[str, Any], validator: Draft202012Validator) -> list[str]:
    errors = sorted(validator.iter_errors(obj), key=lambda err: list(err.path))
    messages = []
    for err in errors:
        loc = ".".join(str(p) for p in err.path) or "$"
        messages.append(f"{loc}: {err.message}")
    return messages


def score_answer(pred: Any, target: Any) -> bool:
    return pred == target


def score_canonical(pred: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    rows = []
    total = 0
    correct = 0
    pred_leg_count = pred.get("missed_approach", {}).get("leg_count")
    target_leg_count = target.get("missed_approach", {}).get("leg_count")
    ok = score_answer(pred_leg_count, target_leg_count)
    rows.append({"field": "leg_count", "correct": ok, "pred": pred_leg_count, "target": target_leg_count})
    total += 1
    correct += int(ok)

    pred_legs = {leg.get("leg_index"): leg for leg in pred.get("missed_approach", {}).get("legs", [])}
    for target_leg in target.get("missed_approach", {}).get("legs", []):
        idx = target_leg["leg_index"]
        pred_leg = pred_legs.get(idx, {})
        pred_answers = pred_leg.get("answers", {})
        target_answers = target_leg.get("answers", {})
        for field in QUESTION_FIELDS:
            pred_answer = pred_answers.get(field)
            target_answer = target_answers.get(field)
            ok = score_answer(pred_answer, target_answer)
            rows.append(
                {
                    "field": f"leg_{idx}.{field}",
                    "correct": ok,
                    "pred": pred_answer,
                    "target": target_answer,
                }
            )
            total += 1
            correct += int(ok)
    return {"correct": correct, "total": total, "accuracy": correct / total if total else None, "rows": rows}


def target_path_from_scoring_row(row: dict[str, Any]) -> Path:
    target = row.get("target")
    if isinstance(target, dict) and target.get("path"):
        return Path(target["path"])
    if row.get("target_path"):
        return Path(row["target_path"])
    raise KeyError(f"Missing target path for {row.get('chart_id')}")


def score_variant(*, d1_root: Path, scoring_manifest: Path, schema_path: Path) -> dict[str, Any]:
    schema = read_json(schema_path)
    validator = Draft202012Validator(schema)
    rows = read_jsonl(scoring_manifest)
    canonical_dir = d1_root / "canonical_json"
    scores_dir = d1_root / "strict_scores"
    failures: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    correct = 0
    total = 0
    schema_valid = 0
    scored = 0

    for row in rows:
        chart_id = row["chart_id"]
        pred_path = canonical_dir / f"{chart_id}.json"
        result: dict[str, Any] = {
            "method": "D1",
            "chart_id": chart_id,
            "sample_id": row.get("sample_id"),
            "prediction_path": str(pred_path),
            "schema_valid": False,
            "score": None,
        }
        if not pred_path.exists():
            result["failure"] = "missing_prediction"
            failures.append(result)
            results.append(result)
            continue
        pred = read_json(pred_path)
        errors = validate_canonical(pred, validator)
        if errors:
            result["validation_errors"] = errors
            result["failure"] = "schema_validation"
            failures.append(result)
            results.append(result)
            continue
        schema_valid += 1
        result["schema_valid"] = True
        target = read_json(target_path_from_scoring_row(row))
        score = score_canonical(pred, target)
        write_json(scores_dir / f"{chart_id}.json", score)
        result["score"] = {key: score[key] for key in ["correct", "total", "accuracy"]}
        correct += int(score["correct"])
        total += int(score["total"])
        scored += 1
        results.append(result)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "method_id": "D1",
        "sample_manifest": str(scoring_manifest),
        "canonical_json_dir": str(canonical_dir),
        "samples_total": len(rows),
        "schema_valid": schema_valid,
        "samples_scored": scored,
        "parse_or_schema_failures": len(failures),
        "score": {"correct": correct, "total": total, "accuracy": correct / total if total else None},
        "results": results,
        "failures": failures,
        "note": "D1 strict scoring uses D1 canonical JSON outputs and the original strict Group 1 canonical scorer.",
    }
    write_json(d1_root / "method_summary.json", summary)
    write_json(d1_root / "summary_report.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Score Experiment 4 D1 canonical outputs with strict Group 1 scorer.")
    parser.add_argument("--d1-root", type=Path, required=True)
    parser.add_argument("--scoring-manifest", type=Path, required=True)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(r".\schemas\missed_approach_leg.schema.json"),
    )
    args = parser.parse_args()
    summary = score_variant(d1_root=args.d1_root, scoring_manifest=args.scoring_manifest, schema_path=args.schema)
    print(
        json.dumps(
            {
                "d1_root": str(args.d1_root),
                "samples_total": summary["samples_total"],
                "schema_valid": summary["schema_valid"],
                "samples_scored": summary["samples_scored"],
                "parse_or_schema_failures": summary["parse_or_schema_failures"],
                "accuracy": summary["score"]["accuracy"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
