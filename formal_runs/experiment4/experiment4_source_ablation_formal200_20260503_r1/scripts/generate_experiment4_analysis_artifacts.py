from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


VARIANTS = [
    "V0_full_chart",
    "V1_ma_text_only",
    "V2_full_minus_ma_prose",
    "V3_plan_view_only",
    "V4_icon_detail_only",
    "V5_plan_detail_no_ma",
]

VARIANT_LABELS = {
    "V0_full_chart": "V0 full",
    "V1_ma_text_only": "V1 MA text",
    "V2_full_minus_ma_prose": "V2 no MA prose",
    "V3_plan_view_only": "V3 plan",
    "V4_icon_detail_only": "V4 detail",
    "V5_plan_detail_no_ma": "V5 plan+detail",
}

VARIANT_CN = {
    "V0_full_chart": "V0 整图 baseline",
    "V1_ma_text_only": "V1 只保留 missed approach 文本框",
    "V2_full_minus_ma_prose": "V2 遮挡 missed approach 文字说明，保留其它区域",
    "V3_plan_view_only": "V3 只保留 plan view",
    "V4_icon_detail_only": "V4 只保留 detail/icon 大框",
    "V5_plan_detail_no_ma": "V5 保留 plan view + detail/icon，不含 MA 文字说明",
}

METHODS = ["B1", "C4", "D_SFT", "D1"]
V2_MODE = "chart_display_aware_v2"
STRICT_MODE = "strict_group1_freeze"

COLORS = {
    "B1": "#4e79a7",
    "C4": "#59a14f",
    "D_SFT": "#f28e2b",
    "D1": "#e15759",
    "coverage": "#4e79a7",
    "failure": "#e15759",
    "d1_coverage": "#59a14f",
}


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "NotoSansCJK-Bold.ttc" if bold else "NotoSansCJK-Regular.ttc",
        "Microsoft YaHei Bold" if bold else "Microsoft YaHei",
        "SimHei",
        "Arial Bold" if bold else "Arial",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_TITLE = load_font(34, bold=True)
FONT_SUBTITLE = load_font(22)
FONT_AXIS = load_font(20)
FONT_SMALL = load_font(17)
FONT_TINY = load_font(15)


def read_metrics(root: Path) -> list[dict[str, Any]]:
    path = root / "reports" / "experiment4_final_metrics_table.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for key in ["samples", "schema_valid", "scored", "failures", "correct", "total"]:
            row[key] = int(row[key])
        for key in ["accuracy", "coverage", "failure_rate"]:
            row[key] = float(row[key])
    return rows


def row_lookup(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {(row["variant"], row["method"], row["scoring_mode"]): row for row in rows}


def fmt_float(value: float, places: int = 3) -> str:
    return f"{value:.{places}f}"


def draw_axes(
    draw: ImageDraw.ImageDraw,
    left: int,
    top: int,
    right: int,
    bottom: int,
    y_max: float = 1.0,
) -> None:
    axis_color = "#2f3340"
    grid_color = "#d9dde7"
    draw.line([(left, top), (left, bottom), (right, bottom)], fill=axis_color, width=2)
    for i in range(6):
        value = i * y_max / 5
        y = bottom - int((value / y_max) * (bottom - top))
        draw.line([(left, y), (right, y)], fill=grid_color, width=1)
        draw.text((left - 64, y - 12), f"{value:.1f}", fill="#2f3340", font=FONT_SMALL)


def draw_legend(
    draw: ImageDraw.ImageDraw,
    items: list[tuple[str, str]],
    x: int,
    y: int,
) -> None:
    cursor = x
    for label, color in items:
        draw.rectangle([cursor, y, cursor + 22, y + 22], fill=color)
        draw.text((cursor + 30, y - 1), label, fill="#2f3340", font=FONT_SMALL)
        cursor += 34 + int(draw.textlength(label, font=FONT_SMALL)) + 28


def save_bar_chart(
    path: Path,
    title: str,
    subtitle: str,
    series: list[tuple[str, list[float], str]],
    variants: list[str],
    y_label: str = "score",
) -> None:
    width, height = 1500, 940
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = 120, 160, width - 70, height - 180
    draw.text((60, 40), title, fill="#202431", font=FONT_TITLE)
    draw.text((62, 88), subtitle, fill="#4d5668", font=FONT_SUBTITLE)
    draw.text((28, top - 36), y_label, fill="#4d5668", font=FONT_SMALL)
    draw_axes(draw, left, top, right, bottom)
    draw_legend(draw, [(label, color) for label, _, color in series], left, 124)

    group_width = (right - left) / len(variants)
    gap = 18
    bar_gap = 7
    bars_per_group = len(series)
    bar_width = max(12, int((group_width - 2 * gap - (bars_per_group - 1) * bar_gap) / bars_per_group))

    for vi, variant in enumerate(variants):
        group_left = left + vi * group_width
        for si, (label, values, color) in enumerate(series):
            value = values[vi]
            x0 = int(group_left + gap + si * (bar_width + bar_gap))
            x1 = x0 + bar_width
            y1 = bottom
            y0 = bottom - int(value * (bottom - top))
            draw.rectangle([x0, y0, x1, y1], fill=color)
            draw.text((x0, y0 - 24), fmt_float(value), fill="#202431", font=FONT_TINY)
        label = VARIANT_LABELS[variant]
        label_width = draw.textlength(label, font=FONT_SMALL)
        draw.text(
            (int(group_left + group_width / 2 - label_width / 2), bottom + 18),
            label,
            fill="#202431",
            font=FONT_SMALL,
        )

    image.save(path)


def write_analysis_md(
    path: Path,
    rows: list[dict[str, Any]],
    charts: dict[str, Path],
) -> None:
    lookup = row_lookup(rows)
    root = path.parent.parent

    def metric(variant: str, method: str, mode: str = V2_MODE) -> dict[str, Any]:
        return lookup[(variant, method, mode)]

    d1_v2 = {variant: metric(variant, "D1", V2_MODE) for variant in VARIANTS}
    d1_strict = {variant: metric(variant, "D1", STRICT_MODE) for variant in VARIANTS}
    c4_v2 = {variant: metric(variant, "C4", V2_MODE) for variant in VARIANTS}
    dsft_v2 = {variant: metric(variant, "D_SFT", V2_MODE) for variant in VARIANTS}

    v0 = d1_v2["V0_full_chart"]["accuracy"]
    v2 = d1_v2["V2_full_minus_ma_prose"]["accuracy"]
    v3 = d1_v2["V3_plan_view_only"]["accuracy"]
    v4 = d1_v2["V4_icon_detail_only"]["accuracy"]
    v5 = d1_v2["V5_plan_detail_no_ma"]["accuracy"]
    v1 = d1_v2["V1_ma_text_only"]["accuracy"]
    v1_d1_summary_path = (
        root
        / "runs"
        / "formal_eval200"
        / "V1_ma_text_only"
        / "D1"
        / "reports"
        / "D1_summary.json"
    )
    with v1_d1_summary_path.open(encoding="utf-8") as handle:
        v1_d1_summary = json.load(handle)
    v1_actions = v1_d1_summary.get("action_counts", {})

    lines: list[str] = []
    lines.extend(
        [
            "# 实验组4 source-view ablation 结果分析",
            "",
            f"生成时间：{datetime.now(timezone.utc).isoformat()}",
            "",
            "## 1. 分析口径",
            "",
            "实验组4的主分析口径采用 `D1 + chart_display_aware_v2`。原因是 D1 沿用实验组1 PR #25 的 fixed-output-interface 处理，只把 D_SFT raw output 统一成可评分 canonical JSON，不使用 target、score、424/CIFP raw、OCR 或其它方法输出修字段答案。因此 D1 比 D_SFT raw 更适合做 200 张全量公平比较。",
            "",
            "`D_SFT raw` 仍然保留，但主要用于分析输出格式稳定性、coverage 和 failure_rate；不应只看 raw accuracy。",
            "",
            "## 2. 输入变体",
            "",
            "|variant|含义|",
            "|---|---|",
        ]
    )
    for variant in VARIANTS:
        lines.append(f"|`{variant}`|{VARIANT_CN[variant]}|")

    lines.extend(
        [
            "",
            "## 3. D1 主结果",
            "",
            "|variant|D1 strict accuracy|D1 v2 accuracy|coverage|failure_rate|",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for variant in VARIANTS:
        strict = d1_strict[variant]
        row = d1_v2[variant]
        lines.append(
            f"|`{variant}`|{fmt_float(strict['accuracy'], 6)}|{fmt_float(row['accuracy'], 6)}|{fmt_float(row['coverage'], 3)}|{fmt_float(row['failure_rate'], 3)}|"
        )

    lines.extend(
        [
            "",
            f"![D1 v2 accuracy]({charts['d1_v2'].name})",
            "",
            "## 4. 可以说明的问题",
            "",
            f"第一，D_SFT/D1 并不是只靠 missed approach 文字框。`V1_ma_text_only` 的 D1 v2 accuracy 只有 {fmt_float(v1, 6)}，但 `V2_full_minus_ma_prose` 在遮挡 missed approach 文字说明后仍有 {fmt_float(v2, 6)}。这说明 D_SFT/D1 的有效信息大量来自航图其它区域，而不是简单抄 MA prose。",
            "",
            f"第二，plan view 是最关键的信息来源。`V3_plan_view_only` 仍有 {fmt_float(v3, 6)}；`V4_icon_detail_only` 只有 {fmt_float(v4, 6)}；`V5_plan_detail_no_ma` 提升到 {fmt_float(v5, 6)}。这说明 plan view 承载了主要的路径、fix、course/radial 等信息，detail/icon 有补充价值，但单独不足。",
            "",
            f"第三，MA prose 对 D1 有帮助，但不是唯一来源。整图 `V0_full_chart` 为 {fmt_float(v0, 6)}，遮挡 MA prose 的 `V2` 为 {fmt_float(v2, 6)}，下降约 {fmt_float(v0 - v2, 6)}。这表示 MA prose 提供增量信息，但航图存在明显多区域冗余。",
            "",
            f"第四，OCR/规则方法和 D_SFT/D1 的依赖方式不同。C4 在 `V1_ma_text_only` 上的 v2 accuracy 为 {fmt_float(c4_v2['V1_ma_text_only']['accuracy'], 6)}，高于 C4 整图 {fmt_float(c4_v2['V0_full_chart']['accuracy'], 6)}。这说明 C4 更像文本驱动方法，直接依赖 missed approach 文字；D1 则更依赖图形结构、布局和上下文。",
            "",
            "第五，D_SFT raw accuracy 不能单独解释。`V1_ma_text_only` 的 D_SFT raw v2 accuracy 为 "
            f"{fmt_float(dsft_v2['V1_ma_text_only']['accuracy'], 6)}，但 coverage 只有 {fmt_float(dsft_v2['V1_ma_text_only']['coverage'], 3)}；"
            "`V4_icon_detail_only` 的 raw v2 accuracy 为 "
            f"{fmt_float(dsft_v2['V4_icon_detail_only']['accuracy'], 6)}，但 coverage 只有 {fmt_float(dsft_v2['V4_icon_detail_only']['coverage'], 3)}。"
            "这些高分是少量幸存 schema-valid 样本上的分数，不能代表全量能力。D1 把 200 张全部纳入评分后，才暴露了局部裁剪输入下的真实表现。",
            "",
            f"![Method v2 accuracy]({charts['method_v2'].name})",
            "",
            f"![D_SFT raw vs D1 coverage/failure]({charts['coverage'].name})",
            "",
            "## 5. V1_ma_text_only 为什么 D1 很低",
            "",
            "这一点需要单独解释：`V1_ma_text_only` 的低分不应被解读为 missed approach 文字框没有信息。更准确的解释是，D_SFT 在只给局部文本框时输出结构严重失稳，D1 只是把这些失败输出转成可评分格式，不会替模型补答案。",
            "",
            "|证据|数值|说明|",
            "|---|---:|---|",
            f"|D_SFT raw v2 accuracy|{fmt_float(dsft_v2['V1_ma_text_only']['accuracy'], 6)}|只在少数可评分样本上计算。|",
            f"|D_SFT raw coverage|{fmt_float(dsft_v2['V1_ma_text_only']['coverage'], 3)}|200 张里只有约 {dsft_v2['V1_ma_text_only']['scored']} 张能直接评分。|",
            f"|D1 v2 accuracy|{fmt_float(d1_v2['V1_ma_text_only']['accuracy'], 6)}|D1 把 200 张全部纳入全量评分后得到的结果。|",
            f"|D1 schema_valid/scored|{v1_d1_summary['schema_valid']} / {v1_d1_summary['samples_scored']}|D1 统一格式后全部可评分。|",
            f"|raw object 不可转 canonical|{v1_actions.get('raw_object_not_convertible_to_canonical_shape', 0)}|说明大部分 raw output 没有形成实验要求的结构。|",
            f"|missing missed_approach fallback|{v1_actions.get('fallback_missing_missed_approach', 0)}|说明大量输出缺少 missed_approach 层级。|",
            f"|missing legs fallback|{v1_actions.get('fallback_missing_legs', 0)}|说明大量输出缺少 legs 结构。|",
            f"|no parseable JSON fallback|{v1_actions.get('fallback_no_parseable_json_to_empty_canonical', 0)}|说明很多输出甚至不能解析成可用 JSON。|",
            f"|C4 V1 v2 accuracy|{fmt_float(c4_v2['V1_ma_text_only']['accuracy'], 6)}|C4 能从文字框中取得信息，证明文字框本身并非无效。|",
            "",
            "因此，V1 的正确解释是：MA 文本框含有有效信息，但 D_SFT 的训练/提示/输出接口更适应整图或航图式输入；只给一小块文本图像时，模型很难稳定输出 424-style canonical JSON。D1 不使用 target、score、OCR、CIFP 或其它方法结果修字段答案，所以它只能把失败输出补成合法但基本为空的 canonical 结构，最终全量 accuracy 很低。",
            "",
            "这一结果反而加强了实验组4的结论：D_SFT/D1 的有效能力主要来自航图布局、plan view、程序上下文和图文对应关系，而不是单独 OCR missed approach prose。",
            "",
            "## 6. 对实验假设的回答",
            "",
            "|问题|结论|证据|",
            "|---|---|---|",
            "|D_SFT 是否只是在读 MA 文字说明？|不是。|V1 D1 v2 只有 "
            f"{fmt_float(v1, 3)}，V2 遮挡 MA prose 后仍有 {fmt_float(v2, 3)}。|",
            "|plan view 是否重要？|非常重要。|V3 单独 plan view 有 "
            f"{fmt_float(v3, 3)}，明显高于 V4 detail-only 的 {fmt_float(v4, 3)}。|",
            "|detail/icon 是否有用？|有补充作用，但单独不够。|V5 plan+detail 为 "
            f"{fmt_float(v5, 3)}，高于 V3 的 {fmt_float(v3, 3)}，但 V4 单独只有 {fmt_float(v4, 3)}。|",
            "|OCR/规则方法和 D_SFT 是否同源依赖？|不是。|C4 在 V1 最高，D1 在 V1 几乎失败。|",
            "|D1 是否必要？|必要。|D_SFT raw 在 V1/V4 coverage 极低，D1 提供了 200 张全量可比结果。|",
            "",
            "## 7. 建议写入正式报告的结论",
            "",
            "实验组4表明，D_SFT 的 missed approach 提取能力并不是单纯来自 missed approach 文本框，而是显著依赖 plan view 中的空间路径、fix、course/radial 以及整图上下文。遮挡 missed approach prose 后，D1 仍保持较高准确率，说明航图中存在多区域信息冗余。相反，OCR/规则类方法 C4 更直接依赖 MA prose，在 text-only 输入上表现最好。D_SFT raw 在局部裁剪输入下存在明显输出格式不稳定，因此应将 D1 作为 D_SFT 的主公平比较结果，并将 raw coverage/failure_rate 作为稳定性证据单独报告。",
            "",
            "## 8. 相关文件",
            "",
            "- `experiment4_final_metrics_table.csv`：最终 48 行指标表。",
            "- `experiment4_final_metrics_summary.json`：最终指标 JSON。",
            "- `experiment4_final_execution_report_zh.md`：最终执行报告。",
            "- `experiment4_v2_scoring_summary.json`：PR25 v2 scoring 明细汇总。",
            "- `experiment4_freeze_manifest.json`：冻结清单。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_submission_manifest(root: Path, charts: dict[str, Path]) -> tuple[Path, Path]:
    reports = root / "reports"
    required_rel_paths = [
        "reports/experiment4_final_execution_report_zh.md",
        "reports/experiment4_result_analysis_zh.md",
        "reports/experiment4_final_metrics_table.csv",
        "reports/experiment4_final_metrics_summary.json",
        "reports/experiment4_v2_scoring_summary.csv",
        "reports/experiment4_v2_scoring_summary.json",
        "reports/experiment4_freeze_manifest.json",
        "reports/experiment4_analysis_artifacts_manifest.json",
        "reports/experiment4_d1_v2_accuracy_by_variant.png",
        "reports/experiment4_method_v2_accuracy_by_variant.png",
        "reports/experiment4_dsft_raw_vs_d1_coverage_failure.png",
        "manifests/experiment4_evaluation200_chart_ids.json",
        "source_views/manifests/source_view_manifest.jsonl",
        "validation/input_manifest_no_leakage_final_report.json",
        "validation/source_view_validation_after_residual_guard_report.json",
        "scripts/build_source_views.py",
        "scripts/prepare_experiment4_manifests.py",
        "scripts/run_d1_output_canonicalizer.py",
        "scripts/score_d1_strict.py",
        "scripts/rescore_experiment4_v2.py",
        "scripts/summarize_experiment4_results.py",
        "scripts/create_experiment4_freeze_manifest.py",
        "scripts/generate_experiment4_analysis_artifacts.py",
    ]
    for chart in charts.values():
        rel = chart.relative_to(root).as_posix()
        if rel not in required_rel_paths:
            required_rel_paths.append(rel)

    records: list[dict[str, Any]] = []
    for rel in required_rel_paths:
        path = root / rel
        records.append(
            {
                "relative_path": rel,
                "path": str(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else None,
            }
        )

    d1_variants = [
        "V1_ma_text_only",
        "V2_full_minus_ma_prose",
        "V3_plan_view_only",
        "V4_icon_detail_only",
        "V5_plan_detail_no_ma",
    ]
    d1_dirs = [
        {
            "variant": variant,
            "d1_root": str(root / "runs" / "formal_eval200" / variant / "D1"),
            "canonical_json_dir": str(root / "runs" / "formal_eval200" / variant / "D1" / "canonical_json"),
            "report": str(root / "runs" / "formal_eval200" / variant / "D1" / "reports" / "D1_summary.json"),
        }
        for variant in d1_variants
    ]

    json_path = reports / "experiment4_submission_file_list.json"
    json_payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Experiment 4 final submission/archive file list.",
        "output_root": str(root),
        "required_files": records,
        "d1_output_dirs": d1_dirs,
    }
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_path = reports / "experiment4_submission_package_manifest_zh.md"
    lines = [
        "# 实验组4最终提交/归档清单",
        "",
        f"生成时间：{datetime.now(timezone.utc).isoformat()}",
        "",
        "## 1. 使用口径",
        "",
        "- 主结果：`D1 + chart_display_aware_v2`。",
        "- 补充结果：`D_SFT raw` 用于说明 coverage/failure_rate 和输出格式稳定性。",
        "- ROI 来源：`prelabel_not_gold`，已人工确认，但不能写成 gold。",
        "",
        "## 2. 必带文件",
        "",
        "|文件|状态|大小 bytes|",
        "|---|---:|---:|",
    ]
    for record in records:
        status = "存在" if record["exists"] else "缺失"
        size = "" if record["size_bytes"] is None else str(record["size_bytes"])
        lines.append(f"|`{record['relative_path']}`|{status}|{size}|")

    lines.extend(
        [
            "",
            "## 3. D1 输出目录",
            "",
            "|variant|D1 root|",
            "|---|---|",
        ]
    )
    for item in d1_dirs:
        lines.append(f"|`{item['variant']}`|`{item['d1_root']}`|")

    lines.extend(
        [
            "",
            "## 4. 提交说明",
            "",
            "提交或归档时，优先带上 `reports`、`scripts`、`manifests`、`validation`、`source_views/manifests`，以及 `runs/formal_eval200/*/D1/reports` 和 D1 canonical JSON 输出。大体积 source-view PNG 可按需要单独归档，但冻结清单中已经记录了 source-view 图片目录摘要。",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path


def main() -> int:
    root = Path(r"formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1")
    reports = root / "reports"
    rows = read_metrics(root)
    lookup = row_lookup(rows)

    charts = {
        "d1_v2": reports / "experiment4_d1_v2_accuracy_by_variant.png",
        "method_v2": reports / "experiment4_method_v2_accuracy_by_variant.png",
        "coverage": reports / "experiment4_dsft_raw_vs_d1_coverage_failure.png",
    }

    d1_values = [lookup[(variant, "D1", V2_MODE)]["accuracy"] for variant in VARIANTS]
    save_bar_chart(
        charts["d1_v2"],
        "Experiment 4: D1 v2 accuracy by source view",
        "D1 is the fixed-output-interface version of D_SFT; all variants have coverage=1.0.",
        [("D1 v2 accuracy", d1_values, COLORS["D1"])],
        VARIANTS,
        y_label="accuracy",
    )

    method_series = [
        (method, [lookup[(variant, method, V2_MODE)]["accuracy"] for variant in VARIANTS], COLORS[method])
        for method in METHODS
    ]
    save_bar_chart(
        charts["method_v2"],
        "Experiment 4: method comparison under PR25 v2 scoring",
        "B1/C4/D_SFT/D1 compared on the same formal200 source-view inputs.",
        method_series,
        VARIANTS,
        y_label="accuracy",
    )

    coverage_series = [
        (
            "D_SFT raw coverage",
            [lookup[(variant, "D_SFT", V2_MODE)]["coverage"] for variant in VARIANTS],
            COLORS["coverage"],
        ),
        (
            "D_SFT raw failure",
            [lookup[(variant, "D_SFT", V2_MODE)]["failure_rate"] for variant in VARIANTS],
            COLORS["failure"],
        ),
        (
            "D1 coverage",
            [lookup[(variant, "D1", V2_MODE)]["coverage"] for variant in VARIANTS],
            COLORS["d1_coverage"],
        ),
    ]
    save_bar_chart(
        charts["coverage"],
        "D_SFT raw output stability vs D1",
        "Raw D_SFT accuracy must be read with coverage; D1 normalizes all 200 outputs.",
        coverage_series,
        VARIANTS,
        y_label="rate",
    )

    analysis_path = reports / "experiment4_result_analysis_zh.md"
    write_analysis_md(analysis_path, rows, charts)
    package_md, package_json = write_submission_manifest(root, charts)

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_markdown": str(analysis_path),
        "charts": {key: str(value) for key, value in charts.items()},
        "submission_package_manifest": str(package_md),
        "submission_file_list": str(package_json),
    }
    manifest_path = reports / "experiment4_analysis_artifacts_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {analysis_path}")
    for chart in charts.values():
        print(f"Wrote {chart}")
    print(f"Wrote {package_md}")
    print(f"Wrote {package_json}")
    print(f"Wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
