from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from scorers.group1_canonical_field_scorer import (
    DEFAULT_SCHEMA_PATH,
    load_json,
    score_canonical,
    score_invalid_output,
    validate_canonical,
    write_json,
)


ROOT = Path(__file__).resolve().parents[1]
GROUP1_ROOT = ROOT / "formal_runs" / "group1"
DEFAULT_RUN_ID = "group1_formal_eval_50_200_50_seed20260437_20260430_r1"
DEFAULT_RUN_DIR = GROUP1_ROOT / DEFAULT_RUN_ID
DEFAULT_OUTPUT_DIR = GROUP1_ROOT / f"{DEFAULT_RUN_ID}_scoring_equivalence_v2"
DEFAULT_SCORING_MANIFEST = DEFAULT_RUN_DIR / "scoring_manifest.jsonl"
COMPARISON_POLICY = "narrowed_v2"

ROOT_METHODS = ["A1", "A2", "B1", "B1_prime", "B1_prime_link", "C1"]
ALL_METHODS = ROOT_METHODS + ["C2", "C3", "C4", "D_SFT"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
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


def collect_prediction_dirs(run_id: str, run_dir: Path) -> dict[str, list[Path]]:
    dirs: dict[str, list[Path]] = {}
    for method in ROOT_METHODS:
        dirs[method] = [run_dir / method / "canonical_json"]

    c2_chunk_dirs = sorted(GROUP1_ROOT.glob(f"{run_id}_C2_chunk_*"))
    dirs["C2"] = [run_dir / "C2" / "canonical_json"] + [
        d / "C2" / "canonical_json" for d in c2_chunk_dirs
    ]

    dirs["C3"] = [GROUP1_ROOT / f"{run_id}_C3" / "C3" / "canonical_json"]
    dirs["C4"] = [GROUP1_ROOT / f"{run_id}_C4" / "C4" / "canonical_json"]
    dirs["D_SFT"] = [
        GROUP1_ROOT
        / f"{run_id}_D_SFT"
        / "D_SFT"
        / "predictions"
        / f"{run_id}_D_SFT_D_SFT"
        / "canonical_json"
    ]
    return dirs


def prediction_index(prediction_dirs: list[Path]) -> tuple[dict[str, Path], dict[str, list[str]]]:
    index: dict[str, Path] = {}
    duplicates: dict[str, list[str]] = defaultdict(list)
    for directory in prediction_dirs:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.json")):
            chart_id = path.stem
            if chart_id in index:
                duplicates[chart_id].append(str(path))
                continue
            index[chart_id] = path
    return index, dict(duplicates)


def score_one(
    *,
    prediction_path: Path | None,
    target_path: Path,
    validator: Draft202012Validator,
) -> tuple[dict[str, Any], list[str], bool]:
    target = load_json(target_path)
    target_errors = validate_canonical(target, validator)
    if target_errors:
        raise ValueError(f"target is not schema-valid: {target_path}: {target_errors}")

    if prediction_path is None:
        score = score_invalid_output(
            target,
            failure_type="missing_prediction",
            failure_detail="prediction file missing",
        )
        score["comparison_policy"] = COMPARISON_POLICY
        return score, ["prediction file missing"], False

    prediction = load_json(prediction_path)
    pred_errors = validate_canonical(prediction, validator)
    if pred_errors:
        score = score_invalid_output(
            target,
            failure_type="schema_failure",
            failure_detail=pred_errors,
        )
        score["comparison_policy"] = COMPARISON_POLICY
        return score, pred_errors, False

    return (
        score_canonical(prediction, target, comparison_policy=COMPARISON_POLICY),
        [],
        True,
    )


def summarize_method(
    *,
    method: str,
    manifest_rows: list[dict[str, Any]],
    pred_index: dict[str, Path],
    validator: Draft202012Validator,
    out_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    scores_dir = out_dir / method / "scores"
    validation_dir = out_dir / method / "validation"
    scores_dir.mkdir(parents=True, exist_ok=True)
    validation_dir.mkdir(parents=True, exist_ok=True)

    total_correct = 0
    total_fields = 0
    zero_policy_correct = 0
    zero_policy_fields = 0
    schema_valid = 0
    method_failure_count = 0
    strict_to_v2_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []

    for row in manifest_rows:
        chart_id = row["chart_id"]
        sample_id = row.get("sample_id")
        target_path = ROOT / row["target"]["path"]
        prediction_path = pred_index.get(chart_id)
        score, errors, valid = score_one(
            prediction_path=prediction_path,
            target_path=target_path,
            validator=validator,
        )

        schema_valid += int(valid)
        method_failure_count += int(not valid)
        zero_policy_correct += score["correct"]
        zero_policy_fields += score["total"]
        if valid:
            total_correct += score["correct"]
            total_fields += score["total"]

        for score_row in score.get("rows", []):
            if score_row.get("correct") and not score_row.get("strict_correct", False):
                strict_to_v2_rows.append(
                    {
                        "method": method,
                        "sample_id": sample_id,
                        "chart_id": chart_id,
                        "field": score_row.get("field"),
                        "question_field": score_row.get("question_field"),
                        "match_policy": score_row.get("match_policy"),
                        "pred": score_row.get("pred"),
                        "target": score_row.get("target"),
                    }
                )

        write_json(scores_dir / f"{chart_id}.json", score)
        write_json(
            validation_dir / f"{chart_id}.json",
            {
                "method": method,
                "sample_id": sample_id,
                "chart_id": chart_id,
                "prediction_path": str(prediction_path) if prediction_path else None,
                "schema_valid": valid,
                "validation_errors": errors,
            },
        )
        result_rows.append(
            {
                "method": method,
                "sample_id": sample_id,
                "chart_id": chart_id,
                "prediction_path": str(prediction_path) if prediction_path else None,
                "schema_valid": valid,
                "validation_error_count": len(errors),
                "score": {
                    "correct": score["correct"],
                    "total": score["total"],
                    "accuracy": score["accuracy"],
                },
            }
        )

    summary = {
        "method": method,
        "samples_total": len(manifest_rows),
        "schema_valid": schema_valid,
        "samples_scored": schema_valid,
        "method_failure_count": method_failure_count,
        "score": {
            "correct": total_correct,
            "total": total_fields,
            "accuracy": total_correct / total_fields if total_fields else None,
        },
        "invalid_as_zero_score": {
            "correct": zero_policy_correct,
            "total": zero_policy_fields,
            "accuracy": zero_policy_correct / zero_policy_fields if zero_policy_fields else None,
        },
        "comparison_policy": COMPARISON_POLICY,
        "strict_to_v2_corrected_fields": len(strict_to_v2_rows),
        "results": result_rows,
    }
    write_json(out_dir / method / "method_summary.json", summary)
    return summary, strict_to_v2_rows, result_rows


def write_summary_csv(path: Path, summaries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "method",
        "samples_total",
        "schema_valid",
        "samples_scored",
        "method_failure_count",
        "correct",
        "total",
        "accuracy",
        "strict_to_v2_corrected_fields",
        "invalid_as_zero_correct",
        "invalid_as_zero_total",
        "invalid_as_zero_accuracy",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for summary in summaries:
            writer.writerow(
                {
                    "method": summary["method"],
                    "samples_total": summary["samples_total"],
                    "schema_valid": summary["schema_valid"],
                    "samples_scored": summary["samples_scored"],
                    "method_failure_count": summary["method_failure_count"],
                    "correct": summary["score"]["correct"],
                    "total": summary["score"]["total"],
                    "accuracy": summary["score"]["accuracy"],
                    "strict_to_v2_corrected_fields": summary["strict_to_v2_corrected_fields"],
                    "invalid_as_zero_correct": summary["invalid_as_zero_score"]["correct"],
                    "invalid_as_zero_total": summary["invalid_as_zero_score"]["total"],
                    "invalid_as_zero_accuracy": summary["invalid_as_zero_score"]["accuracy"],
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rescore Group 1 formal200 predictions with narrowed scoring-equivalence v2."
    )
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--scoring-manifest", type=Path, default=DEFAULT_SCORING_MANIFEST)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    schema = load_json(args.schema)
    validator = Draft202012Validator(schema)
    manifest_rows = load_jsonl(args.scoring_manifest)
    prediction_dirs = collect_prediction_dirs(args.run_id, args.run_dir)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_summaries: list[dict[str, Any]] = []
    all_corrected_rows: list[dict[str, Any]] = []
    all_result_rows: list[dict[str, Any]] = []
    duplicate_report: dict[str, Any] = {}

    for method in ALL_METHODS:
        pred_index, duplicates = prediction_index(prediction_dirs[method])
        duplicate_report[method] = {
            "prediction_dirs": [str(path) for path in prediction_dirs[method]],
            "prediction_count": len(pred_index),
            "duplicate_count": len(duplicates),
            "duplicates": duplicates,
        }
        summary, corrected_rows, result_rows = summarize_method(
            method=method,
            manifest_rows=manifest_rows,
            pred_index=pred_index,
            validator=validator,
            out_dir=args.output_dir,
        )
        all_summaries.append(summary)
        all_corrected_rows.extend(corrected_rows)
        all_result_rows.extend(result_rows)

    write_summary_csv(args.output_dir / "combined_summary_table.csv", all_summaries)
    write_json(args.output_dir / "combined_summary_report.json", {"methods": all_summaries})
    write_jsonl(args.output_dir / "strict_to_v2_corrected_fields.jsonl", all_corrected_rows)
    write_json(args.output_dir / "prediction_collection_audit.json", duplicate_report)

    manifest = {
        "run_id": f"{args.run_id}_scoring_equivalence_v2",
        "source_group1_run_id": args.run_id,
        "comparison_policy": COMPARISON_POLICY,
        "policy_scope": {
            "Q1_fix_ident": "status must match; compare present values after normalized display string",
            "Q4_course_or_radial": "status/type/direction strict; compare navaid normalized; compare course_deg/radial_deg by integer chart-display rounding only",
            "Q5_hold_params": "status strict; compare inbound_course_deg by integer chart-display rounding only; turn/time/distance strict",
            "all_other_fields": "strict status/value equality",
        },
        "forbidden_relaxations": [
            "altitude_tolerance",
            "turn_relaxation",
            "holding_time_default",
            "distance_tolerance",
            "reciprocal_course_equivalence",
            "leg_alignment_change",
            "missing_present_status_relaxation",
        ],
        "inputs": {
            "scoring_manifest": str(args.scoring_manifest),
            "schema": str(args.schema),
            "source_run_dir": str(args.run_dir),
        },
        "hashes": {
            "scorer_sha256": sha256_file(ROOT / "scripts" / "scorers" / "group1_canonical_field_scorer.py"),
            "rescore_script_sha256": sha256_file(Path(__file__)),
            "scoring_manifest_sha256": sha256_file(args.scoring_manifest),
            "schema_sha256": sha256_file(args.schema),
        },
    }
    write_json(args.output_dir / "rescore_manifest.json", manifest)

    print(json.dumps({"output_dir": str(args.output_dir), "methods": len(all_summaries)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
