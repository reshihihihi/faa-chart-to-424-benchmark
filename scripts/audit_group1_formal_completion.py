from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GROUP1_ROOT = ROOT / "formal_runs" / "group1"
EXPECTED_METHODS = [
    "A1",
    "A2",
    "B1",
    "B1_prime",
    "B1_prime_link",
    "C1",
    "C2",
    "C3",
    "C4",
    "D_SFT",
]
SOURCE_METHODS = ["A1", "A2", "B1", "B1_prime", "B1_prime_link", "C1"]


def display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def count_files(path: Path, pattern: str = "*", recursive: bool = False) -> int:
    if not path.exists():
        return 0
    iterator = path.rglob(pattern) if recursive else path.glob(pattern)
    return sum(1 for item in iterator if item.is_file())


def artifact_counts(method_dir: Path) -> dict[str, Any]:
    input_manifest = method_dir / "input_manifest.jsonl"
    return {
        "method_dir": display(method_dir),
        "input_manifest_rows": len(read_jsonl(input_manifest)) if input_manifest.exists() else None,
        "canonical_json_files": count_files(method_dir / "canonical_json", "*.json"),
        "score_files": count_files(method_dir / "scores", "*.json"),
        "validation_files": count_files(method_dir / "validation", "*.json"),
        "raw_response_files": count_files(method_dir / "raw_responses", "*", recursive=True),
        "raw_text_files": count_files(method_dir / "raw_text", "*", recursive=True),
        "qa_json_files": count_files(method_dir / "qa_json", "*", recursive=True),
        "qa_validation_files": count_files(method_dir / "qa_validation", "*", recursive=True),
        "qa_invalid_files": count_files(method_dir / "qa_invalid", "*", recursive=True),
        "qa_error_files": count_files(method_dir / "qa_errors", "*", recursive=True),
    }


def is_failure_result(result: dict[str, Any]) -> bool:
    if result.get("failure"):
        return True
    if result.get("score") is None:
        return True
    validation_error_count = result.get("validation_error_count")
    return validation_error_count not in (None, 0)


def failure_type(result: dict[str, Any]) -> str:
    failure = str(result.get("failure") or "")
    if "InternalServerError" in failure or "502" in failure:
        return "api_failure"
    if "JSONDecodeError" in failure or "parse" in failure.lower():
        return "parse_failure"
    if result.get("validation_error_count") not in (None, 0):
        return "schema_validation_failure"
    if result.get("score") is None:
        return "unscored_result"
    return "unknown_failure"


def method_failure_details(method: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for result in results:
        if not is_failure_result(result):
            continue
        details.append(
            {
                "method": method,
                "sample_id": result.get("sample_id"),
                "chart_id": result.get("chart_id"),
                "failure_type": failure_type(result),
                "failure": result.get("failure"),
                "validation_error_count": result.get("validation_error_count"),
                "validation_errors": result.get("validation_errors"),
                "attempt_count": result.get("attempt_count"),
                "schema_retry_count": result.get("schema_retry_count"),
            }
        )
    return details


def duplicate_values(values: list[Any]) -> list[Any]:
    counts = Counter(value for value in values if value not in (None, ""))
    return sorted([value for value, count in counts.items() if count > 1])


def normalize_summary(
    method: str,
    summary: dict[str, Any],
    summary_path: Path,
    method_dir: Path,
    expected_samples: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    score = summary.get("score") or {}
    results = summary.get("results") or []
    failures = method_failure_details(method, results)
    sample_ids = [result.get("sample_id") for result in results]
    chart_ids = [result.get("chart_id") for result in results]
    duplicate_sample_ids = duplicate_values(sample_ids)
    duplicate_chart_ids = duplicate_values(chart_ids)
    hard_blockers: list[str] = []
    if summary.get("samples_total") != expected_samples:
        hard_blockers.append(f"samples_total_is_{summary.get('samples_total')}_expected_{expected_samples}")
    if duplicate_sample_ids:
        hard_blockers.append("duplicate_sample_ids")
    if duplicate_chart_ids:
        hard_blockers.append("duplicate_chart_ids")
    if score.get("correct") is None or score.get("total") is None:
        hard_blockers.append("missing_score_totals")

    row = {
        "method": method,
        "run_id": method_dir.parent.name,
        "summary_path": display(summary_path),
        "samples_total": summary.get("samples_total"),
        "schema_valid": summary.get("schema_valid"),
        "samples_scored": summary.get("samples_scored"),
        "method_failure_count": len(failures),
        "failure_type_counts": dict(Counter(item["failure_type"] for item in failures)),
        "correct": score.get("correct"),
        "total": score.get("total"),
        "accuracy": score.get("accuracy"),
        "schema_retry_count_total": summary.get("schema_retry_count_total"),
        "qa_calls_total": summary.get("qa_calls_total"),
        "qa_schema_retry_count_total": summary.get("qa_schema_retry_count_total"),
        "json_extraction_policy_counts": summary.get("json_extraction_policy_counts"),
        "parser_repair_count_non_strict_json": summary.get("parser_repair_count_non_strict_json"),
        "artifact_counts": artifact_counts(method_dir),
        "duplicate_sample_ids": duplicate_sample_ids,
        "duplicate_chart_ids": duplicate_chart_ids,
        "hard_blockers": hard_blockers,
        "status": "hard_blocked" if hard_blockers else ("complete_with_method_failures" if failures else "complete"),
    }
    return row, failures, results


def reconstruct_c2_source(source_run_dir: Path) -> dict[str, Any]:
    method_dir = source_run_dir / "C2"
    input_rows = read_jsonl(method_dir / "input_manifest.jsonl")
    chart_to_row = {str(row.get("chart_id")): row for row in input_rows}
    results: list[dict[str, Any]] = []
    correct = 0
    total = 0
    for score_path in sorted((method_dir / "scores").glob("*.json")):
        chart_id = score_path.stem
        score = read_json(score_path)
        validation_path = method_dir / "validation" / f"{chart_id}.json"
        validation_errors = read_json(validation_path) if validation_path.exists() else None
        row = chart_to_row.get(chart_id, {})
        correct += int(score.get("correct", 0))
        total += int(score.get("total", 0))
        results.append(
            {
                "method": "C2",
                "sample_id": row.get("sample_id"),
                "chart_id": chart_id,
                "score": {
                    "correct": score.get("correct"),
                    "total": score.get("total"),
                    "accuracy": score.get("accuracy"),
                },
                "validation_error_count": len(validation_errors) if isinstance(validation_errors, list) else None,
                "validation_errors": validation_errors if isinstance(validation_errors, list) else None,
                "source_slice": "monolithic_partial_before_stop",
            }
        )
    samples = len(results)
    return {
        "slice_id": "source_partial",
        "run_id": source_run_dir.name,
        "method_dir": display(method_dir),
        "source_input_manifest_rows": len(input_rows),
        "samples_total": samples,
        "schema_valid": sum(1 for result in results if result.get("validation_error_count") == 0),
        "samples_scored": samples,
        "correct": correct,
        "total": total,
        "accuracy": (correct / total) if total else None,
        "artifact_counts": artifact_counts(method_dir),
        "results": results,
        "note": "Reconstructed from the interrupted monolithic C2 score files; this slice has no method_summary.json.",
    }


def combine_c2(source_run_dir: Path, group1_root: Path, base_run_id: str, expected_samples: int) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    source = reconstruct_c2_source(source_run_dir)
    chunks: list[dict[str, Any]] = []
    all_results = list(source["results"])
    correct = int(source["correct"])
    total = int(source["total"])
    samples_total = int(source["samples_total"])
    schema_valid = int(source["schema_valid"])
    samples_scored = int(source["samples_scored"])
    qa_calls_total_from_chunk_summaries = 0
    qa_schema_retry_count_total = 0
    hard_blockers: list[str] = []

    chunk_dirs = sorted(
        group1_root.glob(f"{base_run_id}_C2_chunk_*"),
        key=lambda path: int(re.search(r"chunk_(\d+)$", path.name).group(1)) if re.search(r"chunk_(\d+)$", path.name) else 9999,
    )
    if not chunk_dirs:
        hard_blockers.append("missing_c2_chunk_dirs")

    for chunk_dir in chunk_dirs:
        summary_path = chunk_dir / "C2" / "method_summary.json"
        if not summary_path.exists():
            hard_blockers.append(f"missing_c2_chunk_summary:{chunk_dir.name}")
            continue
        summary = read_json(summary_path)
        score = summary.get("score") or {}
        chunk_results = summary.get("results") or []
        chunks.append(
            {
                "chunk_run_id": chunk_dir.name,
                "summary_path": display(summary_path),
                "samples_total": summary.get("samples_total"),
                "schema_valid": summary.get("schema_valid"),
                "samples_scored": summary.get("samples_scored"),
                "correct": score.get("correct"),
                "total": score.get("total"),
                "accuracy": score.get("accuracy"),
                "qa_calls_total": summary.get("qa_calls_total"),
                "qa_schema_retry_count_total": summary.get("qa_schema_retry_count_total"),
                "artifact_counts": artifact_counts(chunk_dir / "C2"),
            }
        )
        all_results.extend(chunk_results)
        samples_total += int(summary.get("samples_total") or 0)
        schema_valid += int(summary.get("schema_valid") or 0)
        samples_scored += int(summary.get("samples_scored") or 0)
        correct += int(score.get("correct") or 0)
        total += int(score.get("total") or 0)
        qa_calls_total_from_chunk_summaries += int(summary.get("qa_calls_total") or 0)
        qa_schema_retry_count_total += int(summary.get("qa_schema_retry_count_total") or 0)

    failures = method_failure_details("C2", all_results)
    duplicate_sample_ids = duplicate_values([result.get("sample_id") for result in all_results])
    duplicate_chart_ids = duplicate_values([result.get("chart_id") for result in all_results])
    if samples_total != expected_samples:
        hard_blockers.append(f"samples_total_is_{samples_total}_expected_{expected_samples}")
    if duplicate_sample_ids:
        hard_blockers.append("duplicate_sample_ids")
    if duplicate_chart_ids:
        hard_blockers.append("duplicate_chart_ids")
    if total == 0:
        hard_blockers.append("missing_score_totals")

    row = {
        "method": "C2",
        "run_id": f"{base_run_id}+C2_chunks",
        "summary_path": None,
        "samples_total": samples_total,
        "schema_valid": schema_valid,
        "samples_scored": samples_scored,
        "method_failure_count": len(failures),
        "failure_type_counts": dict(Counter(item["failure_type"] for item in failures)),
        "correct": correct,
        "total": total,
        "accuracy": (correct / total) if total else None,
        "schema_retry_count_total": None,
        "qa_calls_total": None,
        "qa_schema_retry_count_total": qa_schema_retry_count_total,
        "json_extraction_policy_counts": None,
        "parser_repair_count_non_strict_json": None,
        "artifact_counts": {
            "source_partial": source["artifact_counts"],
            "chunk_count": len(chunks),
            "qa_calls_total_from_chunk_summaries": qa_calls_total_from_chunk_summaries,
            "source_qa_json_files_partial": source["artifact_counts"]["qa_json_files"],
            "source_qa_error_files_partial": source["artifact_counts"]["qa_error_files"],
            "source_qa_invalid_files_partial": source["artifact_counts"]["qa_invalid_files"],
        },
        "c2_source_partial": {key: value for key, value in source.items() if key != "results"},
        "c2_chunks": chunks,
        "duplicate_sample_ids": duplicate_sample_ids,
        "duplicate_chart_ids": duplicate_chart_ids,
        "hard_blockers": hard_blockers,
        "status": "hard_blocked" if hard_blockers else ("complete_with_method_failures" if failures else "complete"),
    }
    return row, failures, all_results


def find_d_sft_summary(group1_root: Path, base_run_id: str) -> Path | None:
    run_dir = group1_root / f"{base_run_id}_D_SFT" / "D_SFT" / "predictions"
    candidates = sorted(run_dir.glob("*/summary_report.json")) if run_dir.exists() else []
    return candidates[-1] if candidates else None


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "method",
        "run_id",
        "status",
        "samples_total",
        "schema_valid",
        "samples_scored",
        "method_failure_count",
        "correct",
        "total",
        "accuracy",
        "schema_retry_count_total",
        "qa_calls_total",
        "qa_schema_retry_count_total",
        "summary_path",
        "hard_blockers",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(row.get(key), ensure_ascii=False) if isinstance(row.get(key), (list, dict)) else row.get(key) for key in fieldnames})


def write_markdown(path: Path, audit: dict[str, Any]) -> None:
    rows = audit["method_table"]
    lines = [
        "# Group 1 Formal Completion Audit",
        "",
        f"- Created at: `{audit['created_at_utc']}`",
        f"- Base run id: `{audit['base_run_id']}`",
        f"- Expected evaluation samples per method: `{audit['expected_samples']}`",
        f"- Decision: `{audit['decision']}`",
        f"- Hard blocker count: `{audit['hard_blocker_count']}`",
        "",
        "## Method Table",
        "",
        "| method | status | total | schema_valid | scored | method_failures | correct | score_total | accuracy | retries | qa_retries |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        accuracy = row.get("accuracy")
        accuracy_text = f"{accuracy:.6f}" if isinstance(accuracy, (float, int)) else ""
        lines.append(
            "| {method} | {status} | {samples_total} | {schema_valid} | {samples_scored} | {method_failure_count} | {correct} | {total} | {accuracy} | {schema_retry_count_total} | {qa_schema_retry_count_total} |".format(
                method=row.get("method"),
                status=row.get("status"),
                samples_total=row.get("samples_total"),
                schema_valid=row.get("schema_valid"),
                samples_scored=row.get("samples_scored"),
                method_failure_count=row.get("method_failure_count"),
                correct=row.get("correct"),
                total=row.get("total"),
                accuracy=accuracy_text,
                schema_retry_count_total=row.get("schema_retry_count_total"),
                qa_schema_retry_count_total=row.get("qa_schema_retry_count_total"),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- Accuracy is the field-level scorer's `correct / total` over schema-valid scored samples.",
            "- Parse/schema/API failures are retained as method failures; they are not silently repaired or counted as correct.",
            "- C2 is combined from the interrupted source C2 slice plus all C2 continuation chunks.",
            "- The source C2 slice has no `method_summary.json`; its 14 scored samples are reconstructed from saved score and validation artifacts.",
            "- A hard blocker means the run package is structurally incomplete, for example missing summaries, missing score totals, duplicated sample ids, or wrong sample count.",
            "",
            "## Failure Counts",
            "",
        ]
    )
    for method, details in audit["failure_details"].items():
        lines.append(f"- `{method}`: {len(details)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit completed Group 1 formal run artifacts.")
    parser.add_argument("--base-run-id", required=True)
    parser.add_argument("--expected-samples", type=int, default=200)
    parser.add_argument("--group1-root", type=Path, default=GROUP1_ROOT)
    args = parser.parse_args()

    group1_root = args.group1_root if args.group1_root.is_absolute() else ROOT / args.group1_root
    source_run_dir = group1_root / args.base_run_id
    reports_dir = source_run_dir / "reports"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    method_rows: list[dict[str, Any]] = []
    failure_details: dict[str, list[dict[str, Any]]] = {}
    result_key_index: dict[str, list[dict[str, Any]]] = {}
    hard_blockers: list[dict[str, Any]] = []

    for method in SOURCE_METHODS:
        summary_path = source_run_dir / method / "method_summary.json"
        if not summary_path.exists():
            row = {
                "method": method,
                "run_id": source_run_dir.name,
                "status": "hard_blocked",
                "hard_blockers": ["missing_method_summary"],
                "summary_path": display(summary_path),
            }
            method_rows.append(row)
            hard_blockers.append({"method": method, "blocker": "missing_method_summary", "path": display(summary_path)})
            continue
        row, failures, results = normalize_summary(method, read_json(summary_path), summary_path, source_run_dir / method, args.expected_samples)
        method_rows.append(row)
        failure_details[method] = failures
        result_key_index[method] = [{"sample_id": item.get("sample_id"), "chart_id": item.get("chart_id")} for item in results]
        for blocker in row.get("hard_blockers", []):
            hard_blockers.append({"method": method, "blocker": blocker})

    c2_row, c2_failures, c2_results = combine_c2(source_run_dir, group1_root, args.base_run_id, args.expected_samples)
    method_rows.append(c2_row)
    failure_details["C2"] = c2_failures
    result_key_index["C2"] = [{"sample_id": item.get("sample_id"), "chart_id": item.get("chart_id")} for item in c2_results]
    for blocker in c2_row.get("hard_blockers", []):
        hard_blockers.append({"method": "C2", "blocker": blocker})

    for method in ["C3", "C4"]:
        run_dir = group1_root / f"{args.base_run_id}_{method}"
        summary_path = run_dir / method / "method_summary.json"
        if not summary_path.exists():
            row = {
                "method": method,
                "run_id": run_dir.name,
                "status": "hard_blocked",
                "hard_blockers": ["missing_method_summary"],
                "summary_path": display(summary_path),
            }
            method_rows.append(row)
            hard_blockers.append({"method": method, "blocker": "missing_method_summary", "path": display(summary_path)})
            continue
        row, failures, results = normalize_summary(method, read_json(summary_path), summary_path, run_dir / method, args.expected_samples)
        method_rows.append(row)
        failure_details[method] = failures
        result_key_index[method] = [{"sample_id": item.get("sample_id"), "chart_id": item.get("chart_id")} for item in results]
        for blocker in row.get("hard_blockers", []):
            hard_blockers.append({"method": method, "blocker": blocker})

    d_summary_path = find_d_sft_summary(group1_root, args.base_run_id)
    if d_summary_path is None:
        row = {
            "method": "D_SFT",
            "run_id": f"{args.base_run_id}_D_SFT",
            "status": "hard_blocked",
            "hard_blockers": ["missing_d_sft_summary"],
            "summary_path": None,
        }
        method_rows.append(row)
        hard_blockers.append({"method": "D_SFT", "blocker": "missing_d_sft_summary"})
    else:
        d_method_dir = d_summary_path.parents[2]
        row, failures, results = normalize_summary("D_SFT", read_json(d_summary_path), d_summary_path, d_method_dir, args.expected_samples)
        method_rows.append(row)
        failure_details["D_SFT"] = failures
        result_key_index["D_SFT"] = [{"sample_id": item.get("sample_id"), "chart_id": item.get("chart_id")} for item in results]
        for blocker in row.get("hard_blockers", []):
            hard_blockers.append({"method": "D_SFT", "blocker": blocker})

    missing_methods = [method for method in EXPECTED_METHODS if method not in {row.get("method") for row in method_rows}]
    for method in missing_methods:
        hard_blockers.append({"method": method, "blocker": "missing_from_method_table"})

    decision = "formal_group1_outputs_complete_for_reporting_with_method_failures_counted"
    if hard_blockers:
        decision = "blocked_structural_artifact_issue"

    audit = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_run_id": args.base_run_id,
        "source_run_dir": display(source_run_dir),
        "expected_samples": args.expected_samples,
        "expected_methods": EXPECTED_METHODS,
        "methods_audited": [row.get("method") for row in method_rows],
        "missing_methods": missing_methods,
        "decision": decision,
        "hard_blocker_count": len(hard_blockers),
        "hard_blockers": hard_blockers,
        "method_table": method_rows,
        "failure_details": failure_details,
        "result_key_index": result_key_index,
        "notes": [
            "Accuracy is field-level correct/total over schema-valid scored samples.",
            "Method parse/schema/API failures are retained as method failures, not repaired.",
            "C2 is combined from the interrupted source slice and continuation chunks.",
        ],
    }

    json_path = reports_dir / f"final_completion_audit_{stamp}.json"
    csv_path = reports_dir / f"final_combined_summary_{stamp}.csv"
    failures_path = reports_dir / f"final_failure_details_{stamp}.json"
    md_path = reports_dir / f"FORMAL_GROUP1_COMPLETION_AUDIT_{stamp}.md"
    write_json(json_path, audit)
    write_csv(csv_path, method_rows)
    write_json(failures_path, failure_details)
    write_markdown(md_path, audit)

    write_json(reports_dir / "final_completion_audit_latest.json", audit)
    write_csv(reports_dir / "final_combined_summary_latest.csv", method_rows)
    write_json(reports_dir / "final_failure_details_latest.json", failure_details)
    write_markdown(reports_dir / "FORMAL_GROUP1_COMPLETION_AUDIT_latest.md", audit)

    print(json.dumps(
        {
            "decision": decision,
            "hard_blocker_count": len(hard_blockers),
            "json": display(json_path),
            "csv": display(csv_path),
            "failure_details": display(failures_path),
            "markdown": display(md_path),
            "method_table": [
                {
                    "method": row.get("method"),
                    "status": row.get("status"),
                    "samples_total": row.get("samples_total"),
                    "samples_scored": row.get("samples_scored"),
                    "method_failure_count": row.get("method_failure_count"),
                    "accuracy": row.get("accuracy"),
                }
                for row in method_rows
            ],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0 if not hard_blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
