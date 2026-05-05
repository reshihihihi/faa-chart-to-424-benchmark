from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SPLIT_MANIFEST = (
    REPO_ROOT
    / "benchmark_exports"
    / "derived"
    / "v2"
    / "formal300"
    / "split_candidates"
    / "split_50_200_50_seed20260437"
    / "sample_manifest_50_200_50_seed20260437.jsonl"
)
DEFAULT_RUN_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_dev50_20260503_r1"
DEFAULT_ADMIN_EXPORT = (
    REPO_ROOT
    / "formal_runs"
    / "experiment5"
    / "admin_exports"
    / "shujuji_annotation_export_2026-05-03T08-34-13-795Z.json"
)

SOURCE_VIEW_MANIFEST = Path(r"<experiment4-source-view-artifact-root>\source_views\manifests\source_view_manifest.jsonl")
OCR_ARTIFACT_MANIFESTS = {
    "MISSED_APPROACH_TEXT": Path(
        r"<experiment4-source-view-artifact-root>\ocr_artifacts\V1_ma_text_only\ocr1_paddleocr_ppocrv5_source_view_20260501_r1\manifest.jsonl"
    ),
    "PLAN_VIEW": Path(
        r"<experiment4-source-view-artifact-root>\ocr_artifacts\V3_plan_view_only\ocr1_paddleocr_ppocrv5_source_view_20260501_r1\manifest.jsonl"
    ),
    "MISSED_APPROACH_DETAIL_AREA": Path(
        r"<experiment4-source-view-artifact-root>\ocr_artifacts\V4_icon_detail_only\ocr1_paddleocr_ppocrv5_source_view_20260501_r1\manifest.jsonl"
    ),
    "PLAN_DETAIL_NO_MA": Path(
        r"<experiment4-source-view-artifact-root>\ocr_artifacts\V5_plan_detail_no_ma\ocr1_paddleocr_ppocrv5_source_view_20260501_r1\manifest.jsonl"
    ),
}

FORBIDDEN_METHOD_INPUT_KEYS = {
    "target",
    "score",
    "canonical_answer",
    "canonical_leg_index",
    "Q_terminator",
    "leg_type",
    "field_review_v2",
    "field_reviews",
}
FORBIDDEN_ADMIN_REGION_KEYS = {
    "accepted_mappings",
    "candidate_mappings_reviewed",
    "rejected_mappings",
    "source_candidate_leg_id",
    "source_leg_type",
    "source_field_name",
    "expected_visual_value",
}
SANITIZED_REGION_KEYS = {
    "final_region_id",
    "source_region_id",
    "region_type",
    "bbox",
    "label",
    "ocr_text",
    "annotation_scope",
    "element_role",
    "step_id",
    "parent_step_region_id",
    "is_formal_annotation_candidate",
    "notes",
    "review_action",
    "needs_discussion",
}


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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def strip_to_method_safe_sample_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": row.get("sample_id"),
        "chart_id": row["chart_id"],
        "airport": row.get("airport"),
        "chart_name": row.get("chart_name"),
        "procedure_type": row.get("procedure_type"),
        "dataset_split": row.get("dataset_split"),
        "split_candidate_id": row.get("split_candidate_id"),
        "sample_source": row.get("sample_source"),
        "sample_type": row.get("sample_type"),
        "pdf_url": row.get("pdf_url"),
        "pdf_file": row.get("pdf_file"),
        "image_file": row.get("image_file"),
        "image_dimensions": row.get("image_dimensions"),
        "scope_note": "sample boundary and non-answer metadata only",
    }


def latest_submissions_by_chart(admin_export: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if not admin_export.exists():
        return {}, {"admin_export_exists": False}
    export = json.loads(admin_export.read_text(encoding="utf-8"))
    submissions = export.get("datasets", {}).get("formal300", {}).get("annotations", {}).get("submissions", [])
    latest: dict[str, dict[str, Any]] = {}
    duplicate_counts: Counter[str] = Counter()
    for submission in submissions:
        data = submission.get("data") or {}
        chart_id = data.get("chart_id")
        if not chart_id:
            continue
        duplicate_counts[chart_id] += 1
        current = latest.get(chart_id)
        saved_at = str(data.get("saved_at") or "")
        current_saved_at = str((current or {}).get("data", {}).get("saved_at") or "")
        if current is None or saved_at >= current_saved_at:
            latest[chart_id] = submission
    meta = {
        "admin_export_exists": True,
        "admin_export_path": rel(admin_export),
        "admin_export_sha256": sha256_file(admin_export),
        "exported_at": export.get("exported_at"),
        "submission_rows": len(submissions),
        "unique_chart_submissions": len(latest),
        "charts_with_multiple_submissions": sum(1 for count in duplicate_counts.values() if count > 1),
    }
    return latest, meta


def sanitized_regions_from_submission(chart_id: str, submission: dict[str, Any]) -> list[dict[str, Any]]:
    data = submission.get("data") or {}
    sanitized: list[dict[str, Any]] = []
    for index, region in enumerate(data.get("regions") or [], start=1):
        clean = {key: region.get(key) for key in SANITIZED_REGION_KEYS if key in region}
        clean["chart_id"] = chart_id
        clean["region_index"] = index
        clean["sanitization"] = {
            "source": "admin_export_regions_only",
            "dropped_key_count": sum(1 for key in FORBIDDEN_ADMIN_REGION_KEYS if key in region),
        }
        sanitized.append(clean)
    return sanitized


def scan_for_forbidden_key_names(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows, start=1):
        payload = json.dumps(row, ensure_ascii=False, sort_keys=True)
        for key in sorted(FORBIDDEN_METHOD_INPUT_KEYS):
            if key in payload:
                hits.append({"row_index": row_index, "chart_id": row.get("chart_id"), "forbidden_key": key})
    return {"hit_count": len(hits), "hits": hits[:50], "truncated": len(hits) > 50}


def build_readiness(
    *,
    dev_rows: list[dict[str, Any]],
    latest_admin_by_chart: dict[str, dict[str, Any]],
    admin_export_meta: dict[str, Any],
    sanitized_region_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    dev_ids = [row["chart_id"] for row in dev_rows]
    present_admin = sorted(chart_id for chart_id in dev_ids if chart_id in latest_admin_by_chart)
    missing_admin = sorted(set(dev_ids) - set(present_admin))
    region_counts_by_chart: dict[str, Counter[str]] = defaultdict(Counter)
    for region in sanitized_region_rows:
        region_counts_by_chart[region["chart_id"]][str(region.get("region_type") or "UNKNOWN")] += 1

    repo_pdf_present = [
        row["chart_id"] for row in dev_rows if row.get("pdf_path") and (REPO_ROOT / row["pdf_path"]).exists()
    ]
    repo_image_present = [
        row["chart_id"] for row in dev_rows if row.get("image_path") and (REPO_ROOT / row["image_path"]).exists()
    ]

    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dev50_chart_count": len(dev_rows),
        "method_sample_boundary": "dataset_split == development",
        "do_not_use_previous_dataset_split": True,
        "repo_pdf_present_count": len(repo_pdf_present),
        "repo_image_present_count": len(repo_image_present),
        "source_view_manifest_exists": SOURCE_VIEW_MANIFEST.exists(),
        "source_view_manifest_path": str(SOURCE_VIEW_MANIFEST),
        "ocr_artifact_manifests": {
            region: {"path": str(path), "exists": path.exists()} for region, path in OCR_ARTIFACT_MANIFESTS.items()
        },
        "admin_export": admin_export_meta,
        "dev50_admin_submission_present_count": len(present_admin),
        "dev50_admin_submission_missing_count": len(missing_admin),
        "dev50_admin_submission_missing_chart_ids": missing_admin,
        "sanitized_admin_region_rows": len(sanitized_region_rows),
        "sanitized_admin_region_counts_by_chart": {
            chart_id: dict(sorted(counter.items())) for chart_id, counter in sorted(region_counts_by_chart.items())
        },
        "method_readiness": {
            "A3_GoldText_Rules": {
                "status": "blocked_until_dev50_gold_ma_prose",
                "reason": "dev50 gold_ma_prose is not yet adjudicated.",
            },
            "B2a_GoldText_LLM": {
                "status": "blocked_until_dev50_gold_ma_prose",
                "reason": "dev50 gold_ma_prose is not yet adjudicated.",
            },
            "B2b_GoldText_FieldCandidates_LLM": {
                "status": "blocked_until_dev50_gold_ma_prose",
                "reason": "gold text field candidates must be derived only from dev50 gold_ma_prose.",
            },
            "B3_T_B3_TPD_B3_PD_B4_TPD": {
                "status": "blocked_missing_local_roi_source_views_and_ocr",
                "reason": "The original source_view manifest and ROI OCR artifact manifests are not present on this machine.",
            },
            "G0_G1_G3": {
                "status": "source_available_needs_gold_observable_conversion",
                "reason": "Admin export has region annotations, but a method-safe gold_observable file still needs to be constructed and audited.",
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Experiment 5 dev50 boundary and readiness artifacts.")
    parser.add_argument("--split-manifest", type=Path, default=SPLIT_MANIFEST)
    parser.add_argument("--admin-export", type=Path, default=DEFAULT_ADMIN_EXPORT)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    args = parser.parse_args()

    split_rows = read_jsonl(args.split_manifest)
    counts = Counter(row.get("dataset_split") for row in split_rows)
    dev_rows = [row for row in split_rows if row.get("dataset_split") == "development"]
    evaluation_rows = [row for row in split_rows if row.get("dataset_split") == "evaluation"]
    probe_rows = [row for row in split_rows if row.get("dataset_split") == "probe"]

    dev_chart_ids = {row["chart_id"] for row in dev_rows}
    evaluation_chart_ids = {row["chart_id"] for row in evaluation_rows}
    probe_chart_ids = {row["chart_id"] for row in probe_rows}
    dev_sample_ids = {row["sample_id"] for row in dev_rows}
    evaluation_sample_ids = {row["sample_id"] for row in evaluation_rows}
    probe_sample_ids = {row["sample_id"] for row in probe_rows}

    method_safe_dev_rows = [strip_to_method_safe_sample_row(row) for row in dev_rows]

    latest_admin_by_chart, admin_export_meta = latest_submissions_by_chart(args.admin_export)
    sanitized_region_rows: list[dict[str, Any]] = []
    for row in dev_rows:
        submission = latest_admin_by_chart.get(row["chart_id"])
        if submission:
            sanitized_region_rows.extend(sanitized_regions_from_submission(row["chart_id"], submission))

    forbidden_scan = scan_for_forbidden_key_names(method_safe_dev_rows + sanitized_region_rows)
    readiness = build_readiness(
        dev_rows=dev_rows,
        latest_admin_by_chart=latest_admin_by_chart,
        admin_export_meta=admin_export_meta,
        sanitized_region_rows=sanitized_region_rows,
    )
    audit = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "split_manifest": rel(args.split_manifest),
        "split_manifest_sha256": sha256_file(args.split_manifest),
        "split_counts": dict(sorted(counts.items())),
        "dev50_count": len(dev_rows),
        "dev50_chart_id_unique_count": len(dev_chart_ids),
        "dev50_sample_id_unique_count": len(dev_sample_ids),
        "evaluation_count": len(evaluation_rows),
        "probe_count": len(probe_rows),
        "dev50_evaluation_chart_overlap": sorted(dev_chart_ids & evaluation_chart_ids),
        "dev50_probe_chart_overlap": sorted(dev_chart_ids & probe_chart_ids),
        "dev50_evaluation_sample_overlap": sorted(dev_sample_ids & evaluation_sample_ids),
        "dev50_probe_sample_overlap": sorted(dev_sample_ids & probe_sample_ids),
        "previous_dataset_split_counts_inside_dev50": dict(
            sorted(Counter(row.get("previous_dataset_split") for row in dev_rows).items())
        ),
        "selection_rule": "row.dataset_split == 'development'",
        "previous_dataset_split_used_for_selection": False,
        "pass": (
            len(dev_rows) == 50
            and len(dev_chart_ids) == 50
            and len(dev_sample_ids) == 50
            and not (dev_chart_ids & evaluation_chart_ids)
            and not (dev_chart_ids & probe_chart_ids)
            and not (dev_sample_ids & evaluation_sample_ids)
            and not (dev_sample_ids & probe_sample_ids)
            and counts == Counter({"development": 50, "evaluation": 200, "probe": 50})
            and forbidden_scan["hit_count"] == 0
        ),
        "forbidden_key_name_scan_over_method_safe_outputs": forbidden_scan,
    }

    write_jsonl(args.run_dir / "manifests" / "dev50_chart_manifest.jsonl", method_safe_dev_rows)
    write_jsonl(args.run_dir / "inputs" / "admin_regions_sanitized_dev50.jsonl", sanitized_region_rows)
    write_json(args.run_dir / "reports" / "dev50_split_audit.json", audit)
    write_json(args.run_dir / "reports" / "dev50_input_readiness.json", readiness)

    report_zh = [
        "# 实验组5 dev50 样本边界与输入可用性审计",
        "",
        f"- 生成时间 UTC: `{audit['created_at_utc']}`",
        f"- split manifest: `{audit['split_manifest']}`",
        f"- 选择规则: `{audit['selection_rule']}`",
        f"- 是否使用 previous_dataset_split: `{audit['previous_dataset_split_used_for_selection']}`",
        f"- split 计数: `{audit['split_counts']}`",
        f"- dev50 样本数: {audit['dev50_count']}",
        f"- dev50 与 evaluation chart/sample 交集: {len(audit['dev50_evaluation_chart_overlap'])}/{len(audit['dev50_evaluation_sample_overlap'])}",
        f"- dev50 与 probe chart/sample 交集: {len(audit['dev50_probe_chart_overlap'])}/{len(audit['dev50_probe_sample_overlap'])}",
        f"- 审计结论 pass: `{audit['pass']}`",
        "",
        "## 关键说明",
        "",
        "- 这 50 个样本来自 `dataset_split=development`，不是文件前 50 行，也不是 `previous_dataset_split=development`。",
        "- dev50 内部的 `previous_dataset_split` 分布不一致，这是历史字段，不能用于本轮选择。",
        "- 输出的 `dev50_chart_manifest.jsonl` 删除了 target/canonical/CIFP 路径和答案字段，只保留样本边界与非答案元数据。",
        "- 从 admin export 抽出的 `admin_regions_sanitized_dev50.jsonl` 只保留区域框、区域类型、label/notes/OCR 文本等可观察来源；已丢弃 accepted/candidate mappings 与 field review 结构。",
        "",
        "## 输入可用性",
        "",
        f"- 本地完整 formal300 PDF 文件数: {readiness['repo_pdf_present_count']}/50",
        f"- 本地完整 formal300 image 文件数: {readiness['repo_image_present_count']}/50",
        f"- source_view manifest 存在: `{readiness['source_view_manifest_exists']}`",
        f"- admin export dev50 submission: {readiness['dev50_admin_submission_present_count']}/50",
        f"- 去泄漏 admin region 行数: {readiness['sanitized_admin_region_rows']}",
        "",
        "## 方法状态",
        "",
        "| 方法 | 当前状态 | 原因 |",
        "|---|---|---|",
    ]
    for method, item in readiness["method_readiness"].items():
        report_zh.append(f"| `{method}` | `{item['status']}` | {item['reason']} |")
    report_zh.extend(
        [
            "",
            "## 下一步",
            "",
            "1. 先制作 dev50 的 `gold_ma_prose`，再用同一个 A3/B2 runner 跑 50 样本。",
            "2. 用 `admin_regions_sanitized_dev50.jsonl` 构建无泄漏 `gold_observable_dev50.jsonl`，通过 forbidden-key 审计后再跑 G0/G1/G3。",
            "3. B3/B4 需要恢复原始 source_views 与 ROI OCR artifacts；当前机器没有这些工件，不能重新 prepare ROI 输入。",
        ]
    )
    write_text(args.run_dir / "reports" / "dev50_split_and_readiness_audit_zh.md", "\n".join(report_zh) + "\n")

    print(json.dumps({"audit_pass": audit["pass"], "readiness": readiness}, ensure_ascii=False, indent=2))
    return 0 if audit["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
