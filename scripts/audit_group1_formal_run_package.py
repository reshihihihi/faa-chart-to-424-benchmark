from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
METHODS = ["A1", "A2", "B1", "B1_prime", "B1_prime_link", "C1", "C2", "C3", "C4", "D_SFT"]
FORBIDDEN_INPUT_KEY_FRAGMENTS = ["target", "score", "canonical_proxy_gt", "cifp", "answer_key"]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def repo_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def artifact_exists(value: Any) -> bool | None:
    if not isinstance(value, dict) or not value.get("path"):
        return None
    if value.get("exists") is False:
        return False
    return repo_path(str(value["path"])).exists()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a prepared Group 1 formal run package before inference.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--expected-split-candidate-id", required=True)
    parser.add_argument("--expected-split", default="evaluation")
    parser.add_argument("--expected-sample-count", type=int, default=200)
    args = parser.parse_args()

    run_dir = args.run_dir
    run_plan = read_json(run_dir / "run_plan.json")
    scoring_rows = read_jsonl(run_dir / "scoring_manifest.jsonl")
    scoring_sample_ids = {row["sample_id"] for row in scoring_rows}
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if run_plan.get("split_candidate_id") != args.expected_split_candidate_id:
        errors.append(
            {
                "kind": "split_candidate_id_mismatch",
                "expected": args.expected_split_candidate_id,
                "actual": run_plan.get("split_candidate_id"),
            }
        )
    if run_plan.get("split_filter") != args.expected_split:
        errors.append({"kind": "split_filter_mismatch", "expected": args.expected_split, "actual": run_plan.get("split_filter")})
    if run_plan.get("sample_count") != args.expected_sample_count:
        errors.append({"kind": "sample_count_mismatch", "expected": args.expected_sample_count, "actual": run_plan.get("sample_count")})
    if len(scoring_rows) != args.expected_sample_count:
        errors.append({"kind": "scoring_manifest_count_mismatch", "expected": args.expected_sample_count, "actual": len(scoring_rows)})

    target_missing = []
    for row in scoring_rows:
        target = row.get("target")
        if artifact_exists(target) is not True:
            target_missing.append({"sample_id": row.get("sample_id"), "chart_id": row.get("chart_id"), "target": target})
    if target_missing:
        errors.append({"kind": "missing_scoring_targets", "count": len(target_missing), "sample": target_missing[:20]})

    method_summary: dict[str, Any] = {}
    for method in run_plan.get("methods", METHODS):
        manifest = run_dir / method / "input_manifest.jsonl"
        if not manifest.exists():
            errors.append({"kind": "missing_method_manifest", "method": method, "path": str(manifest)})
            continue
        rows = read_jsonl(manifest)
        sample_ids = {row["sample_id"] for row in rows}
        method_errors = []
        if len(rows) != args.expected_sample_count:
            method_errors.append({"kind": "method_row_count_mismatch", "expected": args.expected_sample_count, "actual": len(rows)})
        if sample_ids != scoring_sample_ids:
            method_errors.append(
                {
                    "kind": "method_sample_set_mismatch",
                    "missing_from_method": sorted(scoring_sample_ids - sample_ids)[:20],
                    "extra_in_method": sorted(sample_ids - scoring_sample_ids)[:20],
                }
            )
        for row in rows:
            for key, value in row.items():
                key_lower = key.lower()
                if any(fragment in key_lower for fragment in FORBIDDEN_INPUT_KEY_FRAGMENTS):
                    method_errors.append(
                        {
                            "kind": "forbidden_input_key",
                            "sample_id": row.get("sample_id"),
                            "chart_id": row.get("chart_id"),
                            "key": key,
                        }
                    )
                if isinstance(value, dict) and "exists" in value and value.get("exists") is False:
                    method_errors.append(
                        {
                            "kind": "missing_input_artifact",
                            "sample_id": row.get("sample_id"),
                            "chart_id": row.get("chart_id"),
                            "key": key,
                            "path": value.get("path"),
                        }
                    )
        method_summary[method] = {
            "rows": len(rows),
            "sample_ids_match_scoring_manifest": sample_ids == scoring_sample_ids,
            "errors": method_errors[:50],
            "error_count": len(method_errors),
        }
        errors.extend({"method": method, **error} for error in method_errors)

    sample_manifest = run_plan.get("sample_manifest") if isinstance(run_plan.get("sample_manifest"), dict) else {}
    sample_manifest_path = sample_manifest.get("path")
    split_distribution = {}
    if sample_manifest_path:
        manifest_rows = read_jsonl(repo_path(sample_manifest_path))
        selected = [row for row in manifest_rows if row.get("dataset_split") == args.expected_split]
        split_distribution = {
            "selected_count": len(selected),
            "procedure_type": dict(Counter(str(row.get("procedure_type")) for row in selected)),
            "sample_source": dict(Counter(str(row.get("sample_source")) for row in selected)),
            "sample_type": dict(Counter(str(row.get("sample_type")) for row in selected)),
            "previous_dataset_split": dict(Counter(str(row.get("previous_dataset_split")) for row in selected)),
        }
        if {row["sample_id"] for row in selected} != scoring_sample_ids:
            errors.append({"kind": "selected_sample_ids_do_not_match_scoring_manifest"})
    else:
        warnings.append({"kind": "sample_manifest_missing_from_run_plan"})

    audit = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "expected_split_candidate_id": args.expected_split_candidate_id,
        "expected_split": args.expected_split,
        "expected_sample_count": args.expected_sample_count,
        "run_plan_status": run_plan.get("status"),
        "formal300_evaluation_ran": run_plan.get("formal300_evaluation_ran"),
        "method_summary": method_summary,
        "scoring_manifest_rows": len(scoring_rows),
        "split_distribution": split_distribution,
        "warnings": warnings,
        "errors": errors[:200],
        "error_count": len(errors),
        "ready_for_user_decision_to_run": len(errors) == 0,
    }
    write_json(run_dir / "reports" / "formal200_manifest_readiness_audit.json", audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
