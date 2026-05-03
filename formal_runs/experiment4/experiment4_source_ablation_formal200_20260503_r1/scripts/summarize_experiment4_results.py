from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VARIANTS = [
    "V0_full_chart",
    "V1_ma_text_only",
    "V2_full_minus_ma_prose",
    "V3_plan_view_only",
    "V4_icon_detail_only",
    "V5_plan_detail_no_ma",
]

NEW_VARIANTS = VARIANTS[1:]
METHODS = ["B1", "C4", "D_SFT", "D1"]
SCORING_MODES = ["strict_group1_freeze", "chart_display_aware_v2"]
BASELINE_D1_SUMMARY_V2 = Path(
    r"."
    r"\formal_runs\group1"
    r"\group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2"
    r"\reports\D1_summary_v2.json"
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def with_rates(row: dict[str, Any]) -> dict[str, Any]:
    samples = row.get("samples")
    scored = row.get("scored")
    failures = row.get("failures")
    correct = row.get("correct")
    total = row.get("total")
    row["accuracy"] = correct / total if total else row.get("accuracy")
    row["coverage"] = scored / samples if samples and scored is not None else row.get("coverage")
    row["failure_rate"] = failures / samples if samples and failures is not None else row.get("failure_rate")
    return row


def row_template(
    *,
    variant: str,
    method: str,
    scoring_mode: str,
    status: str,
    samples: int | None = 200,
    schema_valid: int | None = None,
    scored: int | None = None,
    failures: int | None = None,
    correct: int | None = None,
    total: int | None = None,
    accuracy: float | None = None,
    coverage: float | None = None,
    failure_rate: float | None = None,
    notes: str = "",
) -> dict[str, Any]:
    return with_rates(
        {
            "variant": variant,
            "method": method,
            "scoring_mode": scoring_mode,
            "status": status,
            "samples": samples,
            "schema_valid": schema_valid,
            "scored": scored,
            "failures": failures,
            "correct": correct,
            "total": total,
            "accuracy": accuracy,
            "coverage": coverage,
            "failure_rate": failure_rate,
            "notes": notes,
        }
    )


def baseline_rows(output_root: Path) -> list[dict[str, Any]]:
    baseline_path = output_root / "baseline" / "V0_group1_frozen_baseline_manifest.json"
    baseline = read_json(baseline_path)
    rows: list[dict[str, Any]] = []
    for method in METHODS:
        if method == "D1" and BASELINE_D1_SUMMARY_V2.exists():
            d1 = read_json(BASELINE_D1_SUMMARY_V2)
            strict_score = d1.get("old_strict_score") or {}
            v2_score = d1.get("chart_display_v2_score") or {}
            samples = as_int(d1.get("prediction_files"))
            scored = as_int(d1.get("schema_valid_predictions"))
            failures = samples - scored if samples is not None and scored is not None else None
            rows.append(
                row_template(
                    variant="V0_full_chart",
                    method="D1",
                    scoring_mode="strict_group1_freeze",
                    status="complete",
                    samples=samples,
                    schema_valid=scored,
                    scored=scored,
                    failures=failures,
                    correct=as_int(strict_score.get("correct")),
                    total=as_int(strict_score.get("total")),
                    accuracy=as_float(strict_score.get("accuracy")),
                    notes="复用 PR25 D1 fixed-output-interface full-chart baseline。",
                )
            )
            rows.append(
                row_template(
                    variant="V0_full_chart",
                    method="D1",
                    scoring_mode="chart_display_aware_v2",
                    status="complete",
                    samples=samples,
                    schema_valid=scored,
                    scored=scored,
                    failures=failures,
                    correct=as_int(v2_score.get("correct")),
                    total=as_int(v2_score.get("total")),
                    accuracy=as_float(v2_score.get("accuracy")),
                    notes="复用 PR25 D1 v2 rescore full-chart baseline。",
                )
            )
            continue
        item = baseline.get("methods", {}).get(method, {})
        strict = item.get("strict_group1_freeze") or {}
        samples = as_int(strict.get("samples_total"))
        scored = as_int(strict.get("samples_scored"))
        strict_failures = samples - scored if samples is not None and scored is not None else None
        rows.append(
            row_template(
                variant="V0_full_chart",
                method=method,
                scoring_mode="strict_group1_freeze",
                status=strict.get("status") or "missing",
                samples=samples,
                schema_valid=as_int(strict.get("schema_valid")),
                scored=scored,
                failures=strict_failures,
                correct=as_int(strict.get("correct")),
                total=as_int(strict.get("total")),
                accuracy=as_float(strict.get("accuracy")),
                notes="复用实验组1冻结整图 baseline；未重跑。",
            )
        )

        v2_delta = item.get("v2_delta_row") or {}
        v2_score = ((item.get("v2_rescore_summary") or {}).get("chart_display_v2_score") or {})
        v2_scored = as_int(v2_delta.get("schema_valid_predictions"))
        v2_samples = samples or as_int(v2_delta.get("prediction_files")) or item.get("canonical_json_count")
        v2_failures = v2_samples - v2_scored if v2_samples is not None and v2_scored is not None else None
        rows.append(
            row_template(
                variant="V0_full_chart",
                method=method,
                scoring_mode="chart_display_aware_v2",
                status="complete" if v2_score else "missing",
                samples=v2_samples,
                schema_valid=v2_scored,
                scored=v2_scored,
                failures=v2_failures,
                correct=as_int(v2_score.get("correct")),
                total=as_int(v2_score.get("total")),
                accuracy=as_float(v2_score.get("accuracy")),
                notes="复用实验组1 PR25 v2 rescore 结果。",
            )
        )
    return rows


def strict_summary_path(output_root: Path, variant: str, method: str) -> Path:
    return output_root / "runs" / "formal_eval200" / variant / method / "method_summary.json"


def strict_new_variant_rows(output_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for variant in NEW_VARIANTS:
        for method in METHODS:
            path = strict_summary_path(output_root, variant, method)
            if not path.exists():
                rows.append(
                    row_template(
                        variant=variant,
                        method=method,
                        scoring_mode="strict_group1_freeze",
                        status="missing",
                        samples=200,
                        notes=f"缺少 method_summary：{path}",
                    )
                )
                continue

            summary = read_json(path)
            samples = as_int(summary.get("samples_total"))
            scored = as_int(summary.get("samples_scored"))
            failures = (
                samples - scored
                if samples is not None and scored is not None
                else as_int(summary.get("parse_or_schema_failures"))
            )
            score = summary.get("score") or {}
            rows.append(
                row_template(
                    variant=variant,
                    method=method,
                    scoring_mode="strict_group1_freeze",
                    status="complete" if scored is not None else "unknown",
                    samples=samples,
                    schema_valid=as_int(summary.get("schema_valid")),
                    scored=scored,
                    failures=failures,
                    correct=as_int(score.get("correct")),
                    total=as_int(score.get("total")),
                    accuracy=as_float(score.get("accuracy")),
                )
            )
    return rows


def v2_new_variant_rows(output_root: Path) -> list[dict[str, Any]]:
    summary_path = output_root / "reports" / "experiment4_v2_scoring_summary.json"
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    if summary_path.exists():
        report = read_json(summary_path)
        by_key = {(item["variant"], item["method"]): item for item in report.get("summaries", [])}

    rows: list[dict[str, Any]] = []
    for variant in NEW_VARIANTS:
        for method in METHODS:
            item = by_key.get((variant, method))
            if not item:
                rows.append(
                    row_template(
                        variant=variant,
                        method=method,
                        scoring_mode="chart_display_aware_v2",
                        status="missing",
                        samples=200,
                        notes="尚未找到该 method/variant 的 v2 scoring summary。",
                    )
                )
                continue

            rows.append(
                row_template(
                    variant=variant,
                    method=method,
                    scoring_mode="chart_display_aware_v2",
                    status=item.get("status") or "unknown",
                    samples=as_int(item.get("samples")),
                    schema_valid=as_int(item.get("schema_valid")),
                    scored=as_int(item.get("scored")),
                    failures=as_int(item.get("failures")),
                    correct=as_int(item.get("correct")),
                    total=as_int(item.get("total")),
                    accuracy=as_float(item.get("accuracy")),
                    coverage=as_float(item.get("coverage")),
                    failure_rate=as_float(item.get("failure_rate")),
                )
            )
    return rows


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def markdown_table(rows: list[dict[str, Any]], scoring_mode: str) -> str:
    headers = [
        "variant",
        "method",
        "status",
        "samples",
        "schema_valid",
        "scored",
        "failures",
        "accuracy",
        "coverage",
        "failure_rate",
    ]
    selected = [row for row in rows if row["scoring_mode"] == scoring_mode]
    lines = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in selected:
        lines.append("|" + "|".join(fmt(row.get(header)) for header in headers) + "|")
    return "\n".join(lines)


def best_available_summary(rows: list[dict[str, Any]], scoring_mode: str) -> str:
    selected = [
        row
        for row in rows
        if row["scoring_mode"] == scoring_mode and row.get("accuracy") is not None and row.get("status") == "complete"
    ]
    if not selected:
        return "暂无可排序的 complete 结果。"
    selected.sort(key=lambda row: float(row["accuracy"]), reverse=True)
    top = selected[0]
    return f"当前 {scoring_mode} 最高准确率为 {top['variant']} / {top['method']}：{top['accuracy']:.6f}。"


def make_report(output_root: Path, rows: list[dict[str, Any]]) -> str:
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "# 实验组4 source-view ablation 最终执行报告",
        "",
        f"生成时间：{now}",
        "",
        "## 实验目的",
        "",
        "实验组4用于检查 missed approach 信息来自不同航图区域时，对 Group1 冻结方法输出质量的影响。V0 复用实验组1整图 baseline；V1-V5 使用人工确认后的 source-view 图像。",
        "",
        "## 输入与边界",
        "",
        "- 评估集：Group1 冻结 formal300 split 中的 evaluation 200 张。",
        "- ROI 来源：`prelabel_not_gold`，已经人工检查确认可用于本实验；报告中不得把该 ROI 当成 gold。",
        "- OCR：B1/C4 使用与实验组1一致的 OCR-1 路径；D_SFT 不使用 OCR。",
        "- V0：复用实验组1冻结整图结果，不重跑。",
        "- C4：已在 `formal_eval200` 下找到 V1-V5 的正式输出，并纳入 strict 与 PR25 v2 分析。",
        "- D1：按 PR #25 的 D1 fixed-output-interface 策略，对 D_SFT raw output 做统一 canonicalization 后纳入评分；D1 不使用 target、score、424/CIFP raw、OCR 或其他方法输出来修字段答案。",
        "",
        "## Variant 定义",
        "",
        "- `V0_full_chart`：实验组1整图 baseline。",
        "- `V1_ma_text_only`：只保留 missed approach 文本框。",
        "- `V2_full_minus_ma_prose`：整图遮挡 missed approach 文字说明。",
        "- `V3_plan_view_only`：只保留 plan view 大框。",
        "- `V4_icon_detail_only`：只保留 missed approach detail/icon 大框。",
        "- `V5_plan_detail_no_ma`：保留 plan view 与 detail/icon，但不保留 missed approach 文字说明。",
        "",
        "## Strict Scoring 汇总",
        "",
        markdown_table(rows, "strict_group1_freeze"),
        "",
        best_available_summary(rows, "strict_group1_freeze"),
        "",
        "## PR25 v2 Scoring 汇总",
        "",
        markdown_table(rows, "chart_display_aware_v2"),
        "",
        best_available_summary(rows, "chart_display_aware_v2"),
        "",
        "## 文件位置",
        "",
        f"- source-view 图像：`{output_root / 'source_views' / 'images'}`",
        f"- source-view manifest：`{output_root / 'source_views' / 'manifests' / 'source_view_manifest.jsonl'}`",
        f"- OCR 输出：`{output_root / 'ocr_artifacts'}`",
        f"- 正式运行输出：`{output_root / 'runs' / 'formal_eval200'}`",
        f"- v2 分样本评分：`{output_root / 'scores' / 'v2'}`",
        f"- 最终结果表 CSV：`{output_root / 'reports' / 'experiment4_final_metrics_table.csv'}`",
        "",
        "## 参数解释",
        "",
        "`samples` 是该方法/variant 应评估样本数；`schema_valid` 是输出 JSON 通过 schema 的样本数；`scored` 是实际进入评分的样本数；`failures = samples - scored`；`accuracy = correct / total`；`coverage = scored / samples`；`failure_rate = failures / samples`。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Experiment 4 strict/v2 metrics and write final Chinese report.")
    parser.add_argument("--output-root", type=Path, default=Path(r"formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1"))
    args = parser.parse_args()
    output_root = args.output_root

    rows: list[dict[str, Any]] = []
    rows.extend(baseline_rows(output_root))
    rows.extend(strict_new_variant_rows(output_root))
    rows.extend(v2_new_variant_rows(output_root))

    fieldnames = [
        "variant",
        "method",
        "scoring_mode",
        "status",
        "samples",
        "schema_valid",
        "scored",
        "failures",
        "correct",
        "total",
        "accuracy",
        "coverage",
        "failure_rate",
        "notes",
    ]
    json_path = output_root / "reports" / "experiment4_final_metrics_summary.json"
    csv_path = output_root / "reports" / "experiment4_final_metrics_table.csv"
    md_path = output_root / "reports" / "experiment4_final_execution_report_zh.md"
    write_json(
        json_path,
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "variants": VARIANTS,
            "methods": METHODS,
            "scoring_modes": SCORING_MODES,
            "rows": rows,
        },
    )
    write_csv(csv_path, rows, fieldnames)
    write_text(md_path, make_report(output_root, rows))
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
