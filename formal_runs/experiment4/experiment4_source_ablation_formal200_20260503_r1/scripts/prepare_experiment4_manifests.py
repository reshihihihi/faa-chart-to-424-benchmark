from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VARIANTS = [
    "V1_ma_text_only",
    "V2_full_minus_ma_prose",
    "V3_plan_view_only",
    "V4_icon_detail_only",
    "V5_plan_detail_no_ma",
]

METHODS = ["B1", "C4", "D_SFT"]
OCR1_RUN_NAME = "ocr1_paddleocr_ppocrv5_source_view_20260501_r1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def artifact(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "exists": path.exists(),
        "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
    }


def build(args: argparse.Namespace) -> int:
    output_root = args.output_root.resolve()
    repo_root = args.repo_root.resolve()
    created_at = datetime.now(timezone.utc).isoformat()

    split_rows = read_jsonl(args.split_manifest)
    evaluation_rows = [row for row in split_rows if row.get("dataset_split") == "evaluation"]
    if len(evaluation_rows) != 200:
        raise RuntimeError(f"expected 200 evaluation rows, got {len(evaluation_rows)}")
    evaluation_chart_ids = [row["chart_id"] for row in evaluation_rows]
    if len(set(evaluation_chart_ids)) != 200:
        raise RuntimeError("evaluation chart ids are not unique")

    source_view_rows = read_jsonl(args.source_view_manifest)
    source_by_key = {(row["chart_id"], row["variant"]): row for row in source_view_rows}
    missing_source_views: list[dict[str, str]] = []
    for chart_id in evaluation_chart_ids:
        for variant in ["V0_full_chart", *VARIANTS]:
            if (chart_id, variant) not in source_by_key:
                missing_source_views.append({"chart_id": chart_id, "variant": variant})
    if missing_source_views:
        raise RuntimeError(f"missing source-view rows: {missing_source_views[:10]}")

    scoring_source_rows = read_jsonl(args.group1_scoring_manifest)
    scoring_by_chart = {row["chart_id"]: row for row in scoring_source_rows}
    missing_scoring = [chart_id for chart_id in evaluation_chart_ids if chart_id not in scoring_by_chart]
    if missing_scoring:
        raise RuntimeError(f"missing scoring rows for charts: {missing_scoring[:10]}")

    eval_summary_rows = []
    for row in evaluation_rows:
        eval_summary_rows.append(
            {
                "sample_id": row["sample_id"],
                "chart_id": row["chart_id"],
                "airport": row["airport"],
                "proc_ident": row["proc_ident"],
                "chart_name": row["chart_name"],
                "dataset_split": row["dataset_split"],
                "split_candidate_id": row.get("split_candidate_id"),
                "source_view_variants_available": ["V0_full_chart", *VARIANTS],
            }
        )
    write_json(
        output_root / "manifests" / "experiment4_evaluation200_chart_ids.json",
        {
            "created_at_utc": created_at,
            "source_split_manifest": str(args.split_manifest.resolve()),
            "source_split_manifest_sha256": sha256_file(args.split_manifest),
            "chart_count": len(eval_summary_rows),
            "chart_ids": evaluation_chart_ids,
            "rows": eval_summary_rows,
        },
    )

    scoring_rows = []
    for row in evaluation_rows:
        source = scoring_by_chart[row["chart_id"]]
        target_info = source["target"]
        target_path = Path(target_info["path"])
        if not target_path.is_absolute():
            target_path = repo_root / target_path
        scoring_rows.append(
            {
                "sample_id": row["sample_id"],
                "chart_id": row["chart_id"],
                "scoring_phase_only": True,
                "target": {
                    "path": str(target_path.resolve()),
                    "exists": target_path.exists(),
                    "sha256": sha256_file(target_path) if target_path.exists() else target_info.get("sha256"),
                },
                "field_targets_path": str((repo_root / "benchmark_exports/derived/v2/formal300/targets/field_targets.jsonl").resolve()),
            }
        )
    scoring_manifest = output_root / "manifests" / "experiment4_scoring_manifest_eval200.jsonl"
    write_jsonl(scoring_manifest, scoring_rows)

    selected_source_rows = []
    ocr_manifest_counts = Counter()
    input_counts = Counter()
    for row in evaluation_rows:
        chart_id = row["chart_id"]
        for variant in ["V0_full_chart", *VARIANTS]:
            source_view = source_by_key[(chart_id, variant)]
            selected_source_rows.append(source_view)
    write_jsonl(output_root / "manifests" / "experiment4_evaluation200_source_view_manifest.jsonl", selected_source_rows)

    for variant in VARIANTS:
        ocr_rows = []
        for row in evaluation_rows:
            chart_id = row["chart_id"]
            source_view = source_by_key[(chart_id, variant)]
            image_path = Path(source_view["output_image_path"]).resolve()
            ocr_rows.append(
                {
                    "sample_id": f"{row['sample_id']}__{variant}",
                    "chart_id": chart_id,
                    "image_path": str(image_path),
                    "variant": variant,
                }
            )
        ocr_manifest = output_root / "manifests" / "ocr_inputs" / f"{variant}_ocr_manifest_eval200.jsonl"
        write_jsonl(ocr_manifest, ocr_rows)
        ocr_manifest_counts[variant] = len(ocr_rows)

        for method in METHODS:
            method_rows = []
            for row in evaluation_rows:
                chart_id = row["chart_id"]
                source_view = source_by_key[(chart_id, variant)]
                image_path = Path(source_view["output_image_path"]).resolve()
                sample_id = f"{row['sample_id']}__{variant}"
                base = {
                    "sample_id": sample_id,
                    "base_sample_id": row["sample_id"],
                    "chart_id": chart_id,
                    "airport": row["airport"],
                    "proc_ident": row["proc_ident"],
                    "chart_name": row["chart_name"],
                    "variant": variant,
                    "source_view_row_sha256": hashlib.sha256(
                        json.dumps(source_view, ensure_ascii=False, sort_keys=True).encode("utf-8")
                    ).hexdigest(),
                    "image": artifact(image_path),
                }
                if method in {"B1", "C4"}:
                    ocr_text_path = (
                        output_root
                        / "ocr_artifacts"
                        / variant
                        / OCR1_RUN_NAME
                        / "full_text"
                        / f"{chart_id}.txt"
                    )
                    base["OCR-1_full_text"] = artifact(ocr_text_path)
                method_rows.append(base)

            run_input_path = output_root / "run_inputs" / variant / f"{method}_input_manifest.jsonl"
            formal_input_path = output_root / "runs" / "formal_eval200" / variant / method / "input_manifest.jsonl"
            write_jsonl(run_input_path, method_rows)
            write_jsonl(formal_input_path, method_rows)
            input_counts[f"{variant}/{method}"] = len(method_rows)

        formal_run_dir = output_root / "runs" / "formal_eval200" / variant
        write_jsonl(formal_run_dir / "scoring_manifest.jsonl", scoring_rows)

    summary = {
        "created_at_utc": created_at,
        "evaluation_chart_count": len(evaluation_chart_ids),
        "variants_for_new_runs": VARIANTS,
        "methods": METHODS,
        "ocr1_run_name": OCR1_RUN_NAME,
        "scoring_manifest": str(scoring_manifest.resolve()),
        "scoring_manifest_sha256": sha256_file(scoring_manifest),
        "ocr_manifest_counts": dict(sorted(ocr_manifest_counts.items())),
        "input_manifest_counts": dict(sorted(input_counts.items())),
        "source_split_manifest": str(args.split_manifest.resolve()),
        "source_view_manifest": str(args.source_view_manifest.resolve()),
        "group1_scoring_manifest": str(args.group1_scoring_manifest.resolve()),
    }
    write_json(output_root / "manifests" / "experiment4_manifest_preparation_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Experiment 4 evaluation200 manifests.")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--source-view-manifest", type=Path, required=True)
    parser.add_argument("--group1-scoring-manifest", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(build(parse_args()))

