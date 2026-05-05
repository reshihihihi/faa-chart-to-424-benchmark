from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT5_DIR = REPO_ROOT / "benchmark_exports" / "derived" / "v2" / "experiment5_diagnostic"
SMOKE_MANIFEST = EXPERIMENT5_DIR / "smoke20_manifest.jsonl"
GOLD_MA_TEMPLATE = EXPERIMENT5_DIR / "gold_ma_text_smoke20_template.jsonl"
GOLD_OBSERVABLE_TEMPLATE = EXPERIMENT5_DIR / "gold_observable_smoke20_template.jsonl"
DEFAULT_ANNOTATION_EXPORT = Path(
    os.environ.get(
        "SHUJUJI_ANNOTATION_EXPORT",
        str(REPO_ROOT / "downloads" / "experiment5_admin" / "latest_formal300_export.json"),
    )
)


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


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def latest_submissions(annotation_export: Path, chart_ids: list[str]) -> dict[str, dict[str, Any]]:
    obj = json.loads(annotation_export.read_text(encoding="utf-8"))
    submissions = obj["datasets"]["formal300"]["annotations"].get("submissions", [])
    by_chart: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in submissions:
        data = item.get("data") or {}
        chart_id = data.get("chart_id")
        if chart_id in chart_ids:
            by_chart[chart_id].append({"relative_path": item.get("relative_path"), "data": data})
    latest: dict[str, dict[str, Any]] = {}
    for chart_id, items in by_chart.items():
        items.sort(key=lambda item: item["data"].get("saved_at") or "")
        latest[chart_id] = items[-1]
    return latest


def template_status(rows: list[dict[str, Any]], value_key: str, todo_values: set[str]) -> dict[str, Any]:
    def is_empty(value: Any) -> bool:
        return value is None or value == "" or value == [] or value == {}

    status_counter = Counter(row.get("review_status") for row in rows)
    filled = []
    todo = []
    for row in rows:
        value = row.get(value_key)
        if isinstance(value, dict):
            is_filled = any(not is_empty(v) for v in value.values())
        else:
            is_filled = value not in todo_values and not is_empty(value)
        (filled if is_filled else todo).append(row.get("chart_id"))
    return {
        "rows": len(rows),
        "review_status_counts": dict(sorted(status_counter.items())),
        "filled_count": len(filled),
        "todo_count": len(todo),
        "filled_chart_ids": filled,
        "todo_chart_ids": todo,
    }


def audit_annotations(latest: dict[str, dict[str, Any]], chart_ids: list[str]) -> dict[str, Any]:
    coverage = {}
    total_field_reviews = 0
    support_modes = Counter()
    review_statuses = Counter()
    evidence_sources = Counter()
    qfields = Counter()
    prohibited_payload_hits = Counter()
    region_type_counts = Counter()
    nonempty_region_ocr_count = 0
    region_label_examples: list[dict[str, Any]] = []
    field_review_examples: list[dict[str, Any]] = []

    prohibited_keys = {
        "canonical_answer",
        "canonical_leg_index",
        "leg_type",
        "field_key",
        "candidate_leg_id",
        "support_mode",
    }
    for chart_id in chart_ids:
        item = latest.get(chart_id)
        if not item:
            coverage[chart_id] = {"has_latest_submission": False}
            continue
        data = item["data"]
        regions = data.get("regions") or []
        field_reviews = data.get("field_reviews") or []
        coverage[chart_id] = {
            "has_latest_submission": True,
            "relative_path": item.get("relative_path"),
            "saved_at": data.get("saved_at"),
            "annotator": data.get("annotator"),
            "region_count": len(regions),
            "field_review_count": len(field_reviews),
            "has_annotation_pr28_json": bool(data.get("annotation_pr28_json")),
            "has_pr28_comparison_summary": bool(data.get("pr28_comparison_summary")),
        }
        total_field_reviews += len(field_reviews)
        for region in regions:
            region_type_counts[region.get("region_type")] += 1
            if str(region.get("ocr_text") or "").strip():
                nonempty_region_ocr_count += 1
            if len(region_label_examples) < 8 and region.get("accepted_mappings"):
                region_label_examples.append(
                    {
                        "chart_id": chart_id,
                        "region_type": region.get("region_type"),
                        "region_id": region.get("final_region_id") or region.get("region_id"),
                        "label": region.get("label"),
                        "accepted_mapping_keys": sorted(
                            set().union(*(mapping.keys() for mapping in region.get("accepted_mappings", [])))
                        ),
                    }
                )
        for field_review in field_reviews:
            support_modes[field_review.get("support_mode")] += 1
            review_statuses[field_review.get("review_status")] += 1
            qfields[field_review.get("field_name")] += 1
            for source in field_review.get("evidence_source") or []:
                evidence_sources[source] += 1
            for key in prohibited_keys:
                if key in field_review:
                    prohibited_payload_hits[key] += 1
            if len(field_review_examples) < 8:
                field_review_examples.append(
                    {
                        key: field_review.get(key)
                        for key in [
                            "chart_id",
                            "field_key",
                            "canonical_leg_index",
                            "leg_type",
                            "field_name",
                            "canonical_answer",
                            "review_status",
                            "support_mode",
                            "evidence_source",
                            "evidence_region_ids",
                        ]
                    }
                )

    return {
        "latest_submission_chart_count": sum(1 for item in coverage.values() if item.get("has_latest_submission")),
        "missing_latest_submission_chart_ids": [
            chart_id for chart_id, item in coverage.items() if not item.get("has_latest_submission")
        ],
        "coverage_by_chart": coverage,
        "total_field_reviews": total_field_reviews,
        "support_mode_counts": dict(sorted(support_modes.items())),
        "review_status_counts": dict(sorted(review_statuses.items())),
        "evidence_source_counts": dict(sorted(evidence_sources.items())),
        "question_field_counts": dict(sorted(qfields.items())),
        "region_type_counts": dict(sorted(region_type_counts.items())),
        "nonempty_region_ocr_count": nonempty_region_ocr_count,
        "prohibited_payload_hits_if_used_as_method_input": dict(sorted(prohibited_payload_hits.items())),
        "field_review_examples": field_review_examples,
        "region_mapping_examples": region_label_examples,
    }


def build_method_readiness(
    gold_ma_status: dict[str, Any],
    gold_obs_status: dict[str, Any],
    *,
    run_dir: Path,
) -> dict[str, Any]:
    gold_ma_ready = gold_ma_status["filled_count"] == gold_ma_status["rows"] and gold_ma_status["rows"] > 0
    gold_obs_ready = gold_obs_status["filled_count"] == gold_obs_status["rows"] and gold_obs_status["rows"] > 0
    a3_summary = run_dir / "reports" / "a3_gold_text_summary.json"
    a3_completed = False
    if a3_summary.exists():
        try:
            summary = json.loads(a3_summary.read_text(encoding="utf-8"))
            a3_completed = (
                summary.get("method") == "A3_GoldText_Rules"
                and summary.get("samples_total") == gold_ma_status["rows"]
                and summary.get("schema_valid") == summary.get("samples_total")
                and summary.get("failure_count", 0) == 0
            )
        except json.JSONDecodeError:
            a3_completed = False
    b2_summary = run_dir / "reports" / "b2_gold_text_summary.json"
    completed_b2_methods: set[str] = set()
    if b2_summary.exists():
        try:
            summary = json.loads(b2_summary.read_text(encoding="utf-8"))
            if summary.get("failure_count", 0) == 0:
                for method, item in (summary.get("summaries") or {}).items():
                    if (
                        method in {"B2a_GoldText_LLM", "B2b_GoldText_FieldCandidates_LLM"}
                        and item.get("samples_total") == gold_ma_status["rows"]
                        and item.get("schema_valid") == item.get("samples_total")
                    ):
                        completed_b2_methods.add(method)
        except json.JSONDecodeError:
            completed_b2_methods = set()
    return {
        "A3_GoldText_Rules": {
            "status": (
                "completed_smoke20_candidate_rules_formal_claim_needs_rule_review"
                if a3_completed
                else "blocked"
                if not gold_ma_ready
                else "ready_after_rule_registry_review"
            ),
            "required_input": "adjudicated gold_ma_prose only",
            "reason": (
                "A3 smoke run completed; rule_registry still requires formal review before formal claim"
                if a3_completed
                else "gold_ma_text template is not completed"
                if not gold_ma_ready
                else "gold text exists; rule_registry still requires formal review before formal claim"
            ),
            "must_not_use": [
                "field_review_v2",
                "canonical_answer",
                "Q_terminator",
                "leg_type",
                "support_mode",
                "candidate_mappings",
            ],
        },
        "B2a_GoldText_LLM": {
            "status": (
                "completed_smoke20"
                if "B2a_GoldText_LLM" in completed_b2_methods
                else "blocked"
                if not gold_ma_ready
                else "ready_after_prompt_freeze"
            ),
            "required_input": "adjudicated gold_ma_prose only",
            "reason": (
                "B2a smoke run completed"
                if "B2a_GoldText_LLM" in completed_b2_methods
                else "gold_ma_text template is not completed"
                if not gold_ma_ready
                else "gold text exists"
            ),
            "must_not_use": ["field_review_v2", "canonical target", "score", "candidate_mappings"],
        },
        "B2b_GoldText_FieldCandidates_LLM": {
            "status": (
                "completed_smoke20"
                if "B2b_GoldText_FieldCandidates_LLM" in completed_b2_methods
                else "blocked"
                if not gold_ma_ready
                else "ready_after_candidate_scope_freeze"
            ),
            "required_input": "adjudicated gold_ma_prose + automatic field candidates",
            "reason": (
                "B2b smoke run completed"
                if "B2b_GoldText_FieldCandidates_LLM" in completed_b2_methods
                else "gold_ma_text template is not completed"
                if not gold_ma_ready
                else "gold text exists"
            ),
            "must_not_use": ["field_review_v2", "canonical target", "support_mode", "human decision"],
        },
        "B3_T": {"status": "completed_smoke20_r4", "required_input": "MA_TEXT ROI OCR + automatic candidates"},
        "B3_TPD": {"status": "completed_smoke20_r4", "required_input": "T/P/D ROI OCR + automatic candidates"},
        "B3_PD": {"status": "completed_smoke20_r4", "required_input": "P/D ROI OCR + automatic candidates"},
        "B4_TPD": {"status": "completed_smoke20_r4", "required_input": "T/P/D ROI OCR + automatic candidates + frozen rules"},
        "G0_Direct": {
            "status": "blocked" if not gold_obs_ready else "ready_after_schema_review",
            "required_input": "adjudicated gold observable facts, explicit absence, source evidence ids",
            "reason": "gold_observable template is not completed" if not gold_obs_ready else "gold observable exists",
            "must_not_use": ["canonical_answer", "canonical_leg_index", "Q_terminator", "final canonical JSON"],
        },
        "G1_Rules": {
            "status": "blocked" if not gold_obs_ready else "ready_after_rule_registry_review",
            "required_input": "adjudicated gold observable facts + frozen rules",
            "reason": "gold_observable template is not completed" if not gold_obs_ready else "gold observable exists",
            "must_not_use": ["canonical_answer", "canonical_leg_index", "Q_terminator", "score"],
        },
        "G2_LLM": {
            "status": "optional_blocked" if not gold_obs_ready else "optional_ready_after_prompt_freeze",
            "required_input": "adjudicated gold observable facts",
            "reason": "optional method; gold_observable template is not completed" if not gold_obs_ready else "gold observable exists",
            "must_not_use": ["scorer", "answer key", "target JSON", "method predictions"],
        },
        "G3_LLM_Rules": {
            "status": "blocked" if not gold_obs_ready else "ready_after_prompt_and_rule_review",
            "required_input": "adjudicated gold observable facts + frozen rule descriptions",
            "reason": "gold_observable template is not completed" if not gold_obs_ready else "gold observable exists",
            "must_not_use": ["canonical_answer", "canonical_leg_index", "Q_terminator", "score"],
        },
    }


def render_markdown(audit: dict[str, Any]) -> str:
    annotation_audit = audit["annotation_audit"]
    annotation_status = annotation_audit.get("status", "available")
    a3_status = audit["method_readiness"]["A3_GoldText_Rules"]["status"]
    a3_completed = str(a3_status).startswith("completed")
    b2_completed = all(
        str(audit["method_readiness"][method]["status"]).startswith("completed")
        for method in ["B2a_GoldText_LLM", "B2b_GoldText_FieldCandidates_LLM"]
    )
    lines = [
        "# 实验组5剩余方法输入合规审计",
        "",
        f"- 生成时间 UTC: `{audit['created_at_utc']}`",
        f"- smoke20 样本数: {len(audit['chart_ids'])}",
        f"- 标注导出: `{audit['annotation_export']}`",
        "",
        "## 结论",
        "",
        "- 已经可以合法执行并已跑通：`B3_T`、`B3_TPD`、`B3_PD`、`B4_TPD`。"
        + ("`A3_GoldText_Rules` 也已完成 smoke20 candidate run。" if a3_completed else "")
        + ("`B2a_GoldText_LLM` / `B2b_GoldText_FieldCandidates_LLM` 也已完成 smoke20 run。" if b2_completed else ""),
        "- 现在不能直接执行："
        + (
            "`G0`、`G1`、`G2`、`G3`。"
            if b2_completed
            else "`B2a`、`B2b`、`G0`、`G1`、`G2`、`G3`。"
            if a3_completed
            else "`A3`、`B2a`、`B2b`、`G0`、`G1`、`G2`、`G3`。"
        ),
        "- 原因不是没有标注文件，而是现有标注导出属于字段级 evidence review，里面混有 `canonical_answer`、`canonical_leg_index`、`Q_terminator/leg_type`、`support_mode` 等方法输入禁用项。",
        "- 因此不能把这些字段审查记录直接当作 gold MA text 或 gold observable 输入；否则会把答案结构带给方法，破坏实验组5的 oracle 诊断边界。",
        "",
        "## Gold Text 状态",
        "",
        f"- 模板行数: {audit['gold_ma_text_template']['rows']}",
        f"- 已填写: {audit['gold_ma_text_template']['filled_count']}",
        f"- 未填写: {audit['gold_ma_text_template']['todo_count']}",
        "- A3/B2 只允许输入人工校正后的 `gold_ma_prose`，不能输入 field review、leg type、Q_terminator 或 canonical answer。",
        "",
        "## Gold Observable 状态",
        "",
        f"- 模板行数: {audit['gold_observable_template']['rows']}",
        f"- 已填写: {audit['gold_observable_template']['filled_count']}",
        f"- 未填写: {audit['gold_observable_template']['todo_count']}",
        "- G 系列只允许输入人工确认的图上事实、显式缺失、证据区域和 checked scopes。",
        "- G 系列禁止输入 canonical target、Q_terminator 答案、canonical leg index、final canonical JSON 和 score。",
        "",
        "## 标注导出中发现了什么",
        "",
        f"- annotation audit status: `{annotation_status}`",
        f"- smoke20 中有最新 submission 的样本: {annotation_audit.get('latest_submission_chart_count', 0)} / {len(audit['chart_ids'])}",
        f"- 字段审查记录总数: {annotation_audit.get('total_field_reviews', 'unknown_missing_export')}",
        f"- 非空 region OCR 数量: {annotation_audit.get('nonempty_region_ocr_count', 'unknown_missing_export')}",
        f"- 如果直接作为方法输入会命中的禁用字段: `{annotation_audit.get('prohibited_payload_hits_if_used_as_method_input', {})}`",
        "",
        "这说明标注导出对实验组2/3分析很有价值，但不能原样喂给实验组5的 A3/B2/G 方法。若 annotation export 缺失，本节只保留方法边界判断，不能复现字段审查计数。",
        "",
        "## 方法 readiness",
        "",
        "| 方法 | 状态 | 需要输入 | 当前原因 |",
        "|---|---|---|---|",
    ]
    for method, item in audit["method_readiness"].items():
        lines.append(
            f"| `{method}` | `{item['status']}` | {item.get('required_input', '')} | {item.get('reason', '')} |"
        )
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "1. `gold_ma_text_smoke20_template.jsonl` 已填写；A3/B2 已跑通。",
            "2. 单独建立符合 schema 的 `gold_observable_smoke20.jsonl`，只写可观察事实和显式缺失，不写 canonical answer 或 target leg index；完成后再跑 G0/G1/G3。",
            "3. 在跑 G1/G3 前审查并冻结 `rule_registry.yaml`，明确哪些规则属于 direct fill、convention default、424-derived 程序语义。",
            "4. 已跑通的 B3/B4 层可以先用于 smoke 诊断报告，但正式结论仍需要扩展到 formal200 或冻结的 diagnostic subset。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Experiment 5 remaining method input readiness.")
    parser.add_argument("--annotation-export", type=Path, default=DEFAULT_ANNOTATION_EXPORT)
    parser.add_argument("--smoke-manifest", type=Path, default=SMOKE_MANIFEST)
    parser.add_argument("--gold-ma-template", type=Path, default=GOLD_MA_TEMPLATE)
    parser.add_argument("--gold-observable-template", type=Path, default=GOLD_OBSERVABLE_TEMPLATE)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--report-prefix", default="experiment5_remaining_methods_input_audit")
    args = parser.parse_args()

    chart_ids = [row["chart_id"] for row in read_jsonl(args.smoke_manifest)]
    gold_ma_rows = read_jsonl(args.gold_ma_template)
    gold_obs_rows = read_jsonl(args.gold_observable_template)
    annotation_export_exists = args.annotation_export.exists()
    latest = latest_submissions(args.annotation_export, chart_ids) if annotation_export_exists else {}
    gold_ma_status = template_status(
        gold_ma_rows,
        "gold_ma_prose",
        {"TBD_HUMAN_CORRECTED_MISSED_APPROACH_TEXT"},
    )
    gold_obs_status = template_status(gold_obs_rows, "facts", {""})
    audit = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "chart_ids": chart_ids,
        "annotation_export": str(args.annotation_export),
        "annotation_export_exists": annotation_export_exists,
        "annotation_export_sha256": sha256_file(args.annotation_export),
        "smoke_manifest": str(args.smoke_manifest),
        "smoke_manifest_sha256": sha256_file(args.smoke_manifest),
        "gold_ma_text_template": gold_ma_status,
        "gold_observable_template": gold_obs_status,
        "annotation_audit": audit_annotations(latest, chart_ids)
        if annotation_export_exists
        else {
            "status": "blocked_missing_annotation_export",
            "latest_submission_chart_count": 0,
            "missing_latest_submission_chart_ids": chart_ids,
            "note": "Annotation export is required only to reproduce the prior field-review audit; template readiness can still be checked.",
        },
        "method_readiness": build_method_readiness(gold_ma_status, gold_obs_status, run_dir=args.run_dir),
    }
    write_json(args.run_dir / "reports" / f"{args.report_prefix}.json", audit)
    write_text(args.run_dir / "reports" / f"{args.report_prefix}_zh.md", render_markdown(audit))
    print(json.dumps(audit["method_readiness"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
