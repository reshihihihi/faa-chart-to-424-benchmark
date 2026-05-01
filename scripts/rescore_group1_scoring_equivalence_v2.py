from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = (
    REPO_ROOT
    / "benchmark_exports"
    / "derived"
    / "v2"
    / "formal300"
    / "targets"
    / "scoring_equivalence_v2"
)

TARGET_V1 = REPO_ROOT / "benchmark_exports" / "derived" / "v2" / "formal300" / "targets" / "canonical_proxy_gt_combined.json"
TARGET_V2 = ARTIFACT_ROOT / "targets" / "canonical_proxy_gt_chart_display_v2.json"
POLICY_PATH = ARTIFACT_ROOT / "targets" / "comparison_policy_v2.jsonl"
SCHEMA_PATH = REPO_ROOT / "schemas" / "missed_approach_leg.schema.json"
SCORER_PATH = REPO_ROOT / "scripts" / "scorers" / "group1_canonical_field_scorer_v2.py"

RUN_ROOT = REPO_ROOT / "formal_runs" / "group1"
BASE_RUN = RUN_ROOT / "group1_formal_eval_50_200_50_seed20260437_20260430_r1"
C3_RUN = RUN_ROOT / "group1_formal_eval_50_200_50_seed20260437_20260430_r1_C3" / "C3"
C4_RUN = RUN_ROOT / "group1_formal_eval_50_200_50_seed20260437_20260430_r1_C4" / "C4"
DSFT_RUN = (
    RUN_ROOT
    / "group1_formal_eval_50_200_50_seed20260437_20260430_r1_D_SFT"
    / "D_SFT"
    / "predictions"
    / "group1_formal_eval_50_200_50_seed20260437_20260430_r1_D_SFT_D_SFT"
)

OUT_ROOT = (
    REPO_ROOT
    / "formal_runs"
    / "group1"
    / "group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2"
)
OUT_SCORES = OUT_ROOT / "scores"
OUT_REPORTS = OUT_ROOT / "reports"
OUT_MANIFESTS = OUT_ROOT / "manifests"


def import_scorer():
    spec = importlib.util.spec_from_file_location("group1_scorer_v2", SCORER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import scorer from {SCORER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def method_sources() -> dict[str, list[Path]]:
    c2_sources = [BASE_RUN / "C2"]
    c2_sources.extend(sorted(RUN_ROOT.glob("group1_formal_eval_50_200_50_seed20260437_20260430_r1_C2_chunk_*/*")))
    # Keep only the method directory inside each chunk.
    c2_sources = [p for p in c2_sources if p.name == "C2" and (p / "canonical_json").exists()]
    return {
        "A1": [BASE_RUN / "A1"],
        "A2": [BASE_RUN / "A2"],
        "B1": [BASE_RUN / "B1"],
        "B1_prime": [BASE_RUN / "B1_prime"],
        "B1_prime_link": [BASE_RUN / "B1_prime_link"],
        "C1": [BASE_RUN / "C1"],
        "C2": c2_sources,
        "C3": [C3_RUN],
        "C4": [C4_RUN],
        "D_SFT": [DSFT_RUN],
    }


def read_old_score(score_path: Path) -> dict[str, Any] | None:
    if not score_path.exists():
        return None
    try:
        obj = read_json(score_path)
    except Exception:
        return None
    if "score" in obj and isinstance(obj["score"], dict):
        return obj["score"]
    if {"correct", "total", "accuracy"}.issubset(obj):
        return obj
    return None


def result_by_field(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row.get("field") or row.get("field_path"): row for row in rows}


def rescore_method(
    method: str,
    sources: list[Path],
    *,
    target_v2: dict[str, Any],
    validator: Draft202012Validator,
    scorer: Any,
    policies: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    method_score_dir = OUT_SCORES / method
    method_score_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    duplicate_charts: list[dict[str, str]] = []
    missing_old_score: list[str] = []
    invalid_predictions: list[dict[str, Any]] = []
    per_sample_rows: list[dict[str, Any]] = []
    changed_rows: list[dict[str, Any]] = []
    category_totals: dict[str, Counter] = defaultdict(Counter)
    policy_totals: dict[str, Counter] = defaultdict(Counter)

    old_correct = 0
    old_total = 0
    v2_correct = 0
    v2_total = 0
    prediction_files = 0
    valid_predictions = 0

    for source in sources:
        canonical_dir = source / "canonical_json"
        score_dir = source / "scores"
        if not canonical_dir.exists():
            continue
        for pred_path in sorted(canonical_dir.glob("*.json")):
            chart_id = pred_path.stem
            if chart_id in seen:
                duplicate_charts.append({"chart_id": chart_id, "source": rel(source)})
                continue
            seen.add(chart_id)
            prediction_files += 1
            pred = read_json(pred_path)
            pred_errors = scorer.validate_canonical(pred, validator)
            if pred_errors:
                invalid_predictions.append(
                    {"chart_id": chart_id, "prediction_path": rel(pred_path), "errors": pred_errors}
                )
                continue
            if chart_id not in target_v2:
                invalid_predictions.append(
                    {"chart_id": chart_id, "prediction_path": rel(pred_path), "errors": ["missing target_v2"]}
                )
                continue
            valid_predictions += 1
            score_v2 = scorer.score_canonical(pred, target_v2[chart_id], chart_id=chart_id, policies=policies)
            v2_correct += score_v2["correct"]
            v2_total += score_v2["total"]

            out_score = {
                "method": method,
                "chart_id": chart_id,
                "source_prediction_path": rel(pred_path),
                "scoring_mode": "chart_display_aware_v2",
                "score": score_v2,
            }
            write_json(method_score_dir / f"{chart_id}.json", out_score)

            old_score = read_old_score(score_dir / f"{chart_id}.json")
            if old_score is None:
                missing_old_score.append(chart_id)
                old_chart_correct = None
                old_chart_total = None
                old_chart_accuracy = None
                old_by_field = {}
            else:
                old_chart_correct = old_score.get("correct")
                old_chart_total = old_score.get("total")
                old_chart_accuracy = old_score.get("accuracy")
                old_correct += int(old_chart_correct or 0)
                old_total += int(old_chart_total or 0)
                old_by_field = result_by_field(old_score.get("rows", []))

            for row in score_v2["rows"]:
                category = row.get("field_category") or "unknown"
                policy = row.get("comparison_policy") or "unknown"
                category_totals[category]["total"] += 1
                category_totals[category]["correct"] += int(bool(row.get("correct")))
                policy_totals[policy]["total"] += 1
                policy_totals[policy]["correct"] += int(bool(row.get("correct")))
                old_row = old_by_field.get(row.get("field")) if old_by_field else None
                old_ok = old_row.get("correct") if old_row else None
                if old_ok is not None and old_ok != row.get("correct"):
                    changed_rows.append(
                        {
                            "method": method,
                            "chart_id": chart_id,
                            "field": row.get("field"),
                            "field_path": row.get("field_path"),
                            "comparison_policy": policy,
                            "field_category": category,
                            "old_correct": old_ok,
                            "new_correct": row.get("correct"),
                            "old_target": old_row.get("target"),
                            "new_target": row.get("target"),
                            "pred": row.get("pred"),
                            "detail": row.get("detail"),
                        }
                    )

            per_sample_rows.append(
                {
                    "method": method,
                    "chart_id": chart_id,
                    "source": rel(source),
                    "old_correct": old_chart_correct,
                    "old_total": old_chart_total,
                    "old_accuracy": old_chart_accuracy,
                    "v2_correct": score_v2["correct"],
                    "v2_total": score_v2["total"],
                    "v2_accuracy": score_v2["accuracy"],
                    "delta_correct": (
                        score_v2["correct"] - old_chart_correct if old_chart_correct is not None else None
                    ),
                }
            )

    summary = {
        "method": method,
        "sources": [rel(s) for s in sources],
        "prediction_files": prediction_files,
        "unique_charts": len(seen),
        "schema_valid_predictions": valid_predictions,
        "schema_invalid_predictions": len(invalid_predictions),
        "old_strict_score": {
            "correct": old_correct,
            "total": old_total,
            "accuracy": old_correct / old_total if old_total else None,
        },
        "chart_display_v2_score": {
            "correct": v2_correct,
            "total": v2_total,
            "accuracy": v2_correct / v2_total if v2_total else None,
        },
        "delta_correct": v2_correct - old_correct,
        "delta_accuracy": (v2_correct / v2_total if v2_total else 0)
        - (old_correct / old_total if old_total else 0),
        "missing_old_score_count": len(missing_old_score),
        "missing_old_score": missing_old_score,
        "duplicate_charts": duplicate_charts,
        "invalid_predictions": invalid_predictions,
        "category_scores": {
            key: {
                "correct": val["correct"],
                "total": val["total"],
                "accuracy": val["correct"] / val["total"] if val["total"] else None,
            }
            for key, val in sorted(category_totals.items())
        },
        "policy_scores": {
            key: {
                "correct": val["correct"],
                "total": val["total"],
                "accuracy": val["correct"] / val["total"] if val["total"] else None,
            }
            for key, val in sorted(policy_totals.items())
        },
        "changed_rows_count": len(changed_rows),
    }
    write_json(OUT_REPORTS / f"{method}_summary_v2.json", summary)
    write_jsonl(OUT_REPORTS / f"{method}_per_sample_v2.jsonl", per_sample_rows)
    write_jsonl(OUT_REPORTS / f"{method}_changed_rows_v2.jsonl", changed_rows)
    return summary


def main() -> int:
    OUT_SCORES.mkdir(parents=True, exist_ok=True)
    OUT_REPORTS.mkdir(parents=True, exist_ok=True)
    OUT_MANIFESTS.mkdir(parents=True, exist_ok=True)
    scorer = import_scorer()
    schema = read_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    policies = scorer.load_policy(POLICY_PATH)
    target_v2 = read_json(TARGET_V2)
    sources_by_method = method_sources()

    summaries = []
    for method, sources in sources_by_method.items():
        summaries.append(
            rescore_method(
                method,
                sources,
                target_v2=target_v2,
                validator=validator,
                scorer=scorer,
                policies=policies,
            )
        )

    csv_path = OUT_REPORTS / "old_vs_new_score_delta.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "method",
                "prediction_files",
                "schema_valid_predictions",
                "schema_invalid_predictions",
                "old_correct",
                "old_total",
                "old_accuracy",
                "v2_correct",
                "v2_total",
                "v2_accuracy",
                "delta_correct",
                "delta_accuracy",
                "changed_rows_count",
            ],
        )
        writer.writeheader()
        for s in summaries:
            writer.writerow(
                {
                    "method": s["method"],
                    "prediction_files": s["prediction_files"],
                    "schema_valid_predictions": s["schema_valid_predictions"],
                    "schema_invalid_predictions": s["schema_invalid_predictions"],
                    "old_correct": s["old_strict_score"]["correct"],
                    "old_total": s["old_strict_score"]["total"],
                    "old_accuracy": s["old_strict_score"]["accuracy"],
                    "v2_correct": s["chart_display_v2_score"]["correct"],
                    "v2_total": s["chart_display_v2_score"]["total"],
                    "v2_accuracy": s["chart_display_v2_score"]["accuracy"],
                    "delta_correct": s["delta_correct"],
                    "delta_accuracy": s["delta_accuracy"],
                    "changed_rows_count": s["changed_rows_count"],
                }
            )

    audit = {
        "run_id": "group1_rescore_scoring_equivalence_v2_20260501_r1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_root": rel(OUT_ROOT),
        "target_v1": {"path": rel(TARGET_V1), "sha256": sha256(TARGET_V1)},
        "target_v2": {"path": rel(TARGET_V2), "sha256": sha256(TARGET_V2)},
        "policy_v2": {"path": rel(POLICY_PATH), "sha256": sha256(POLICY_PATH)},
        "schema": {"path": rel(SCHEMA_PATH), "sha256": sha256(SCHEMA_PATH)},
        "scorer_v2": {"path": rel(SCORER_PATH), "sha256": sha256(SCORER_PATH)},
        "method_summaries": summaries,
        "outputs": {
            "old_vs_new_score_delta_csv": rel(csv_path),
        },
    }
    write_json(OUT_REPORTS / "scoring_equivalence_audit.json", audit)
    write_json(OUT_MANIFESTS / "rescore_manifest.json", audit)

    md = [
        "# Group 1 scoring-equivalence v2 rescore audit",
        "",
        f"Run ID: `{audit['run_id']}`",
        "",
        "This audit re-scores existing Group 1 predictions using chart-display-aware target/scoring v2.",
        "It does not rerun OCR, LLM, VLM, or D-SFT inference.",
        "",
        "## Method Summary",
        "",
        "| method | valid | invalid | strict old acc | v2 display-aware acc | delta acc | delta correct | changed rows |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summaries:
        old_acc = s["old_strict_score"]["accuracy"]
        new_acc = s["chart_display_v2_score"]["accuracy"]
        md.append(
            "| {method} | {valid} | {invalid} | {old:.4f} | {new:.4f} | {delta:.4f} | {dc} | {chg} |".format(
                method=s["method"],
                valid=s["schema_valid_predictions"],
                invalid=s["schema_invalid_predictions"],
                old=old_acc if old_acc is not None else 0,
                new=new_acc if new_acc is not None else 0,
                delta=s["delta_accuracy"],
                dc=s["delta_correct"],
                chg=s["changed_rows_count"],
            )
        )
    md.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Positive deltas mainly come from chart-display degree rounding and conservative string/number normalization.",
            "- Invalid predictions remain invalid and are not silently repaired by scoring v2.",
            "- Q_terminator remains strict and is only marked as 424-derived for reporting separation.",
            "",
            "## Files",
            "",
            f"- CSV delta table: `{csv_path}`",
            f"- JSON audit: `{OUT_REPORTS / 'scoring_equivalence_audit.json'}`",
        ]
    )
    (OUT_REPORTS / "scoring_equivalence_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(
        {
            "methods": len(summaries),
            "out_root": rel(OUT_ROOT),
            "delta_csv": rel(csv_path),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
