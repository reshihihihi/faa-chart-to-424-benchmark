from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DEV_RUN_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_dev50_20260503_r1"
DEFAULT_OUT_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_dev50_20260504_r3_strict_no_leak"

FORBIDDEN_KEYS = {
    "annotation_pr28_json",
    "target",
    "score",
    "canonical_answer",
    "canonical_leg_index",
    "Q_terminator",
    "leg_type",
    "field_review_v2",
    "candidate_leg_id",
}

ANSWER_DERIVED_KEYS = {
    "annotation_pr28_json",
    "canonical_answer",
    "canonical_leg_index",
    "leg_type",
    "Q_terminator",
}

VISIBLE_LABEL_REGION_TYPES = {
    "ALTITUDE_TEXT",
    "FIX_TEXT",
    "HEADING_TEXT",
    "COURSE_TEXT",
    "RADIAL_TEXT",
    "NAVAID_TEXT",
    "TURN_TEXT",
    "HOLD_TEXT",
}

VISIBLE_ICON_REGION_TYPES = {
    "CLIMB_ARROW",
    "FIX_SYMBOL",
    "HOLDING_PATTERN",
    "PATH_SEGMENT",
    "TRACK_SEGMENT",
    "PROCEDURE_TURN_SYMBOL",
    "OUTBOUND_INBOUND_MARK",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def flatten_key_paths(value: Any, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        paths: list[str] = []
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            paths.append(child_prefix)
            paths.extend(flatten_key_paths(child, child_prefix))
        return paths
    if isinstance(value, list):
        paths = []
        for child in value[:5]:
            child_prefix = f"{prefix}[]"
            paths.extend(flatten_key_paths(child, child_prefix))
        return paths
    return []


def key_tail(path: str) -> str:
    return path.split(".")[-1].replace("[]", "")


def forbidden_key_hits(rows: list[dict[str, Any]]) -> Counter[str]:
    hits: Counter[str] = Counter()
    for row in rows:
        for path in flatten_key_paths(row):
            if key_tail(path) in FORBIDDEN_KEYS:
                hits[path] += 1
    return hits


def label_visible_part(label: Any) -> str:
    if not isinstance(label, str):
        return ""
    return re.split(r"\s*->\s*", label, maxsplit=1)[0].strip()


def has_interpreted_suffix(label: Any) -> bool:
    return isinstance(label, str) and "->" in label


def classify_region_text(row: dict[str, Any]) -> str:
    region_type = row.get("region_type")
    ocr_text = str(row.get("ocr_text") or "").strip()
    label = str(row.get("label") or "").strip()
    visible = label_visible_part(label)
    if ocr_text:
        return "ocr_text_available"
    if region_type in VISIBLE_LABEL_REGION_TYPES and visible:
        return "visible_label_literal_available"
    if region_type in VISIBLE_ICON_REGION_TYPES:
        return "visible_icon_available"
    if region_type in {"MISSED_APPROACH_TEXT", "PLAN_VIEW", "MISSED_APPROACH_DETAIL_AREA"}:
        return "bbox_only_no_text"
    return "unknown_or_generic_label"


def summarize_artifact(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    key_counts: Counter[str] = Counter()
    nested_key_counts: Counter[str] = Counter()
    for row in rows:
        key_counts.update(str(key) for key in row.keys())
        nested_key_counts.update(flatten_key_paths(row))
    return {
        "name": name,
        "rows": len(rows),
        "top_level_keys": dict(key_counts.most_common()),
        "forbidden_key_hits": dict(forbidden_key_hits(rows).most_common()),
        "sample_nested_keys": [key for key, _ in nested_key_counts.most_common(80)],
    }


def summarize_regions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_type = Counter(str(row.get("region_type") or "") for row in rows)
    by_review_action = Counter(str(row.get("review_action") or "") for row in rows)
    by_scope = Counter(str(row.get("annotation_scope") or "") for row in rows)
    by_text_class = Counter(classify_region_text(row) for row in rows)
    ocr_by_type: dict[str, dict[str, int]] = defaultdict(lambda: {"nonempty": 0, "empty": 0})
    label_suffix_by_type: dict[str, dict[str, int]] = defaultdict(lambda: {"with_arrow_suffix": 0, "without_arrow_suffix": 0})
    sample_visible_literals: list[dict[str, Any]] = []

    for row in rows:
        region_type = str(row.get("region_type") or "")
        if str(row.get("ocr_text") or "").strip():
            ocr_by_type[region_type]["nonempty"] += 1
        else:
            ocr_by_type[region_type]["empty"] += 1
        if has_interpreted_suffix(row.get("label")):
            label_suffix_by_type[region_type]["with_arrow_suffix"] += 1
        else:
            label_suffix_by_type[region_type]["without_arrow_suffix"] += 1
        if len(sample_visible_literals) < 30 and classify_region_text(row) in {
            "visible_label_literal_available",
            "visible_icon_available",
        }:
            sample_visible_literals.append(
                {
                    "chart_id": row.get("chart_id"),
                    "region_id": row.get("region_id"),
                    "region_type": region_type,
                    "review_action": row.get("review_action"),
                    "visible_literal": label_visible_part(row.get("label")),
                    "original_label_had_interpreted_suffix": has_interpreted_suffix(row.get("label")),
                }
            )

    chart_ids = sorted({str(row.get("chart_id")) for row in rows if row.get("chart_id")})
    ma_rows = [row for row in rows if row.get("region_type") == "MISSED_APPROACH_TEXT"]
    ma_nonempty_ocr = sum(1 for row in ma_rows if str(row.get("ocr_text") or "").strip())
    pd_visible = [
        row
        for row in rows
        if classify_region_text(row) in {"visible_label_literal_available", "visible_icon_available"}
        and row.get("region_type") not in {"MISSED_APPROACH_TEXT"}
    ]

    return {
        "charts": len(chart_ids),
        "region_type_counts": dict(by_type.most_common()),
        "review_action_counts": dict(by_review_action.most_common()),
        "annotation_scope_counts": dict(by_scope.most_common()),
        "text_class_counts": dict(by_text_class.most_common()),
        "ocr_text_availability_by_region_type": dict(sorted(ocr_by_type.items())),
        "label_interpretation_suffix_by_region_type": dict(sorted(label_suffix_by_type.items())),
        "ma_text_region_rows": len(ma_rows),
        "ma_text_nonempty_ocr_rows": ma_nonempty_ocr,
        "pd_visible_observable_rows": len(pd_visible),
        "sample_visible_literals": sample_visible_literals,
    }


def method_availability(region_summary: dict[str, Any]) -> dict[str, Any]:
    charts = region_summary["charts"]
    ma_rows = region_summary["ma_text_region_rows"]
    ma_nonempty = region_summary["ma_text_nonempty_ocr_rows"]
    pd_visible = region_summary["pd_visible_observable_rows"]
    a3_status = "ready" if ma_nonempty == ma_rows and ma_rows == charts else "blocked_missing_visible_ma_text"
    b3_t_status = "ready" if ma_nonempty > 0 and ma_nonempty == charts else "blocked_missing_roi_text"
    pd_status = "ready_visible_region_labels" if pd_visible > 0 else "blocked_missing_pd_observables"
    tpd_status = "ready" if b3_t_status == "ready" and pd_status.startswith("ready") else "partial_missing_text"
    return {
        "A3": {
            "status": a3_status,
            "reason": f"MISSED_APPROACH_TEXT rows={ma_rows}, nonempty ocr_text={ma_nonempty}; strict A3 needs real visible MA text.",
        },
        "B2": {
            "status": a3_status,
            "reason": "B2 depends on the same legal MA_TEXT prose as A3.",
        },
        "B3_T": {
            "status": b3_t_status,
            "reason": f"ROI text requires nonempty OCR/corrected text; available MA_TEXT OCR rows={ma_nonempty}/{charts}.",
        },
        "B3_PD": {
            "status": pd_status,
            "reason": f"Plan/detail visible label or icon rows available={pd_visible}; values must use literal label left side only.",
        },
        "B3_TPD": {
            "status": tpd_status,
            "reason": "TPD can combine PD observables with text only after legal ROI text exists.",
        },
        "B4_TPD": {
            "status": tpd_status,
            "reason": "B4 uses the same strict TPD evidence base before extra relation handling.",
        },
        "G": {
            "status": "requires_rebuild_from_visible_observables",
            "reason": "Existing gold_observable files include interpreted value objects; rebuild as visible facts only.",
        },
    }


def render_markdown(audit: dict[str, Any]) -> str:
    region_summary = audit["region_summary"]
    availability = audit["method_availability"]
    artifact_summaries = audit["artifact_summaries"]
    lines: list[str] = []
    lines.append("# Experiment 5 strict source audit")
    lines.append("")
    lines.append(f"Generated: {audit['generated_at']}")
    lines.append("")
    lines.append("## 总结")
    lines.append("")
    lines.append("- `admin_regions` 可以作为 strict 输入来源，但必须只使用 bbox、region_type、review_action、可见 label 左侧 literal、图元类型和 provenance。")
    lines.append("- `admin_field_review` 含 `canonical_answer`、`canonical_leg_index`、`leg_type` 等答案级字段，不能直接作为方法输入。")
    lines.append("- `admin_gold_answer` 只能用于评分或事后审计，不能用于构造输入。")
    lines.append("- `admin_evidence_links` 可作为关系来源候选，但必须先剥离字段名和答案字段，只保留 evidence region 关系。")
    lines.append("")
    lines.append("## admin_regions 可用性")
    lines.append("")
    lines.append(f"- charts: {region_summary['charts']}")
    lines.append(f"- MA_TEXT rows: {region_summary['ma_text_region_rows']}")
    lines.append(f"- MA_TEXT nonempty ocr_text rows: {region_summary['ma_text_nonempty_ocr_rows']}")
    lines.append(f"- plan/detail visible observable rows: {region_summary['pd_visible_observable_rows']}")
    lines.append("")
    lines.append("region_type counts:")
    for key, value in region_summary["region_type_counts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    lines.append("text class counts:")
    for key, value in region_summary["text_class_counts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    lines.append("## 方法 gate")
    lines.append("")
    for method, info in availability.items():
        lines.append(f"- `{method}`: `{info['status']}` - {info['reason']}")
    lines.append("")
    lines.append("## artifact forbidden-key scan")
    lines.append("")
    for name, summary in artifact_summaries.items():
        lines.append(f"### {name}")
        lines.append("")
        lines.append(f"- rows: {summary['rows']}")
        if summary["forbidden_key_hits"]:
            lines.append("- forbidden key hits:")
            for key, count in summary["forbidden_key_hits"].items():
                lines.append(f"  - `{key}`: {count}")
        else:
            lines.append("- forbidden key hits: 0")
        lines.append("")
    lines.append("## 可见 label 抽样")
    lines.append("")
    for sample in region_summary["sample_visible_literals"][:20]:
        suffix = "had_suffix" if sample["original_label_had_interpreted_suffix"] else "literal_only"
        lines.append(
            f"- `{sample['chart_id']}` `{sample['region_type']}` `{sample['review_action']}` "
            f"{suffix}: {sample['visible_literal']}"
        )
    lines.append("")
    lines.append("## 审计结论")
    lines.append("")
    lines.append("dev50 后台导出的框和关系可以支持 B3_PD 类 strict 输入的重建；但当前 admin_regions 中 MA_TEXT 的 `ocr_text` 为空，因此 A3/B2/B3_T/B3_TPD/B4_TPD 的文本侧仍需要合法的图面 OCR 或人工校正文本文本，不能再用 r2 的 answer-derived prose 补。")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev-run-dir", type=Path, default=DEFAULT_DEV_RUN_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    artifact_dir = args.dev_run_dir / "admin_artifacts"
    artifact_paths = {
        "admin_regions": artifact_dir / "admin_regions_dev50.jsonl",
        "admin_evidence_links": artifact_dir / "admin_evidence_links_dev50.jsonl",
        "admin_field_review": artifact_dir / "admin_field_review_dev50.jsonl",
        "admin_gold_answer": artifact_dir / "admin_gold_answer_dev50.jsonl",
    }
    artifacts = {name: read_jsonl(path) for name, path in artifact_paths.items()}
    region_summary = summarize_regions(artifacts["admin_regions"])
    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dev_run_dir": str(args.dev_run_dir),
        "artifact_paths": {name: str(path) for name, path in artifact_paths.items()},
        "artifact_summaries": {
            name: summarize_artifact(name, rows)
            for name, rows in artifacts.items()
        },
        "region_summary": region_summary,
        "method_availability": method_availability(region_summary),
        "strict_source_decision": {
            "admin_regions": "allowed_with_sanitization",
            "admin_evidence_links": "relation_source_only_after_field_answer_stripping",
            "admin_field_review": "blocked_for_method_inputs_except_manual_audit",
            "admin_gold_answer": "scoring_only_never_input",
        },
        "forbidden_keys": sorted(FORBIDDEN_KEYS),
        "answer_derived_keys": sorted(ANSWER_DERIVED_KEYS),
    }

    reports_dir = args.out_dir / "reports"
    write_json(reports_dir / "admin_artifact_field_audit.json", audit)
    (reports_dir / "admin_artifact_field_audit_zh.md").write_text(render_markdown(audit), encoding="utf-8")
    print(json.dumps({"out_dir": str(args.out_dir), "reports_dir": str(reports_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
