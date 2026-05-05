from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


VARIANTS = [
    "V1_ma_text_only",
    "V2_full_minus_ma_prose",
    "V3_plan_view_only",
    "V4_icon_detail_only",
    "V5_plan_detail_no_ma",
]

METHODS = ["B1", "C4", "D_SFT", "D1"]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_scorer(repo_root: Path) -> Any:
    scorer_path = repo_root / "scripts" / "scorers" / "group1_canonical_field_scorer_v2.py"
    spec = importlib.util.spec_from_file_location("group1_canonical_field_scorer_v2", scorer_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import scorer from {scorer_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prediction_dir(output_root: Path, variant: str, method: str) -> Path:
    if method == "B1":
        return output_root / "runs" / "formal_eval200" / variant / "B1" / "canonical_json"
    if method == "C4":
        return output_root / "runs" / "formal_eval200" / variant / "C4" / "canonical_json"
    if method == "D_SFT":
        return (
            output_root
            / "runs"
            / "formal_eval200"
            / variant
            / "D_SFT"
            / "predictions"
            / f"{variant}_D_SFT"
            / "canonical_json"
        )
    if method == "D1":
        return output_root / "runs" / "formal_eval200" / variant / "D1" / "canonical_json"
    raise ValueError(f"Unsupported method: {method}")


def score_one_method_variant(
    *,
    output_root: Path,
    repo_root: Path,
    variant: str,
    method: str,
    chart_ids: list[str],
    target_v2: dict[str, Any],
    validator: Draft202012Validator,
    scorer: Any,
    policies: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    pred_dir = prediction_dir(output_root, variant, method)
    score_dir = output_root / "scores" / "v2" / variant / method
    score_dir.mkdir(parents=True, exist_ok=True)

    correct = 0
    total = 0
    schema_valid = 0
    scored = 0
    prediction_files = 0
    failures: list[dict[str, Any]] = []
    per_sample_rows: list[dict[str, Any]] = []
    category_totals: dict[str, Counter] = defaultdict(Counter)
    policy_totals: dict[str, Counter] = defaultdict(Counter)

    for chart_id in chart_ids:
        pred_path = pred_dir / f"{chart_id}.json"
        row: dict[str, Any] = {
            "variant": variant,
            "method": method,
            "chart_id": chart_id,
            "prediction_path": str(pred_path),
            "prediction_exists": pred_path.exists(),
            "schema_valid": False,
            "scored": False,
            "correct": None,
            "total": None,
            "accuracy": None,
            "failure_stage": None,
            "failure_error": None,
        }

        if not pred_path.exists():
            row["failure_stage"] = "missing_prediction"
            row["failure_error"] = "prediction json does not exist"
            failures.append(row.copy())
            per_sample_rows.append(row)
            continue

        prediction_files += 1
        try:
            pred = read_json(pred_path)
        except Exception as exc:
            row["failure_stage"] = "read_prediction"
            row["failure_error"] = str(exc)
            failures.append(row.copy())
            per_sample_rows.append(row)
            continue

        pred_errors = scorer.validate_canonical(pred, validator) if isinstance(pred, dict) else ["prediction is not an object"]
        if pred_errors:
            row["failure_stage"] = "schema_validation"
            row["failure_error"] = "; ".join(pred_errors[:5])
            row["validation_errors"] = pred_errors
            failures.append(row.copy())
            per_sample_rows.append(row)
            write_json(
                score_dir / f"{chart_id}.json",
                {
                    "variant": variant,
                    "method": method,
                    "chart_id": chart_id,
                    "prediction_path": str(pred_path),
                    "prediction_schema_valid": False,
                    "prediction_validation_errors": pred_errors,
                    "score": None,
                    "scoring_mode": "chart_display_aware_v2",
                },
            )
            continue

        schema_valid += 1
        row["schema_valid"] = True

        target = target_v2.get(chart_id)
        if target is None:
            row["failure_stage"] = "missing_target_v2"
            row["failure_error"] = "chart_id not present in v2 target map"
            failures.append(row.copy())
            per_sample_rows.append(row)
            continue

        target_errors = scorer.validate_canonical(target, validator) if isinstance(target, dict) else ["target is not an object"]
        if target_errors:
            row["failure_stage"] = "target_schema_validation"
            row["failure_error"] = "; ".join(target_errors[:5])
            row["target_validation_errors"] = target_errors
            failures.append(row.copy())
            per_sample_rows.append(row)
            continue

        score = scorer.score_canonical(pred, target, chart_id=chart_id, policies=policies)
        scored += 1
        correct += int(score["correct"])
        total += int(score["total"])
        row["scored"] = True
        row["correct"] = score["correct"]
        row["total"] = score["total"]
        row["accuracy"] = score["accuracy"]
        per_sample_rows.append(row)
        write_json(
            score_dir / f"{chart_id}.json",
            {
                "variant": variant,
                "method": method,
                "chart_id": chart_id,
                "prediction_path": str(pred_path),
                "prediction_sha256": sha256(pred_path),
                "prediction_schema_valid": True,
                "score": score,
                "scoring_mode": "chart_display_aware_v2",
            },
        )

        for score_row in score["rows"]:
            category = score_row.get("field_category") or "unknown"
            policy = score_row.get("comparison_policy") or "unknown"
            category_totals[category]["total"] += 1
            category_totals[category]["correct"] += int(bool(score_row.get("correct")))
            policy_totals[policy]["total"] += 1
            policy_totals[policy]["correct"] += int(bool(score_row.get("correct")))

    samples = len(chart_ids)
    summary = {
        "variant": variant,
        "method": method,
        "status": "complete" if scored > 0 else "no_scored_predictions",
        "prediction_dir": str(pred_dir),
        "prediction_dir_exists": pred_dir.exists(),
        "samples": samples,
        "prediction_files": prediction_files,
        "schema_valid": schema_valid,
        "scored": scored,
        "failures": samples - scored,
        "correct": correct,
        "total": total,
        "accuracy": correct / total if total else None,
        "coverage": scored / samples if samples else None,
        "failure_rate": (samples - scored) / samples if samples else None,
        "category_scores": {
            key: {
                "correct": int(value["correct"]),
                "total": int(value["total"]),
                "accuracy": int(value["correct"]) / int(value["total"]) if value["total"] else None,
            }
            for key, value in sorted(category_totals.items())
        },
        "policy_scores": {
            key: {
                "correct": int(value["correct"]),
                "total": int(value["total"]),
                "accuracy": int(value["correct"]) / int(value["total"]) if value["total"] else None,
            }
            for key, value in sorted(policy_totals.items())
        },
        "failures_detail": failures,
    }

    per_sample_path = output_root / "scores" / "v2" / variant / method / "per_sample_scores.csv"
    write_csv(
        per_sample_path,
        per_sample_rows,
        [
            "variant",
            "method",
            "chart_id",
            "prediction_path",
            "prediction_exists",
            "schema_valid",
            "scored",
            "correct",
            "total",
            "accuracy",
            "failure_stage",
            "failure_error",
        ],
    )
    summary["per_sample_scores_csv"] = str(per_sample_path)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Rescore Experiment 4 source-view predictions with Group1 v2 scorer.")
    parser.add_argument("--output-root", type=Path, default=Path(r"formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1"))
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(r"."),
    )
    args = parser.parse_args()

    output_root = args.output_root
    repo_root = args.repo_root
    chart_id_path = output_root / "manifests" / "experiment4_evaluation200_chart_ids.json"
    target_v2_path = (
        repo_root
        / "benchmark_exports"
        / "derived"
        / "v2"
        / "formal300"
        / "targets"
        / "scoring_equivalence_v2"
        / "canonical_proxy_gt_chart_display_v2.json"
    )
    policy_path = (
        repo_root
        / "benchmark_exports"
        / "derived"
        / "v2"
        / "formal300"
        / "targets"
        / "scoring_equivalence_v2"
        / "comparison_policy_v2.jsonl"
    )
    schema_path = repo_root / "schemas" / "missed_approach_leg.schema.json"

    scorer = import_scorer(repo_root)
    chart_ids = read_json(chart_id_path)["chart_ids"]
    target_v2 = read_json(target_v2_path)
    schema = read_json(schema_path)
    validator = Draft202012Validator(schema)
    policies = scorer.load_policy(policy_path)

    summaries = []
    for variant in VARIANTS:
        for method in METHODS:
            summaries.append(
                score_one_method_variant(
                    output_root=output_root,
                    repo_root=repo_root,
                    variant=variant,
                    method=method,
                    chart_ids=chart_ids,
                    target_v2=target_v2,
                    validator=validator,
                    scorer=scorer,
                    policies=policies,
                )
            )

    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scoring_mode": "chart_display_aware_v2",
        "output_root": str(output_root),
        "repo_root": str(repo_root),
        "chart_id_manifest": str(chart_id_path),
        "target_v2_path": str(target_v2_path),
        "policy_path": str(policy_path),
        "schema_path": str(schema_path),
        "summaries": summaries,
    }
    summary_path = output_root / "reports" / "experiment4_v2_scoring_summary.json"
    write_json(summary_path, report)

    table_rows = [
        {
            "variant": item["variant"],
            "method": item["method"],
            "status": item["status"],
            "samples": item["samples"],
            "prediction_files": item["prediction_files"],
            "schema_valid": item["schema_valid"],
            "scored": item["scored"],
            "failures": item["failures"],
            "correct": item["correct"],
            "total": item["total"],
            "accuracy": item["accuracy"],
            "coverage": item["coverage"],
            "failure_rate": item["failure_rate"],
        }
        for item in summaries
    ]
    csv_path = output_root / "reports" / "experiment4_v2_scoring_summary.csv"
    write_csv(
        csv_path,
        table_rows,
        [
            "variant",
            "method",
            "status",
            "samples",
            "prediction_files",
            "schema_valid",
            "scored",
            "failures",
            "correct",
            "total",
            "accuracy",
            "coverage",
            "failure_rate",
        ],
    )
    print(f"Wrote {summary_path}")
    print(f"Wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
