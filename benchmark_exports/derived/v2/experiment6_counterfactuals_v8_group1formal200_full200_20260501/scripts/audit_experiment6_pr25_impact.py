#!/usr/bin/env python3
"""Audit PR #25 display-equivalence impact on Experiment 6 artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def sha256_file(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def pr25_category(field: str) -> str:
    value = str(field)
    if "fix_ident" in value:
        return "pr25_direct_fix_ident"
    if "course_or_radial" in value:
        return "pr25_direct_course_or_radial"
    if "inbound_course_deg" in value:
        return "pr25_direct_inbound_course_deg"
    if value.endswith(".hold_params") or ".hold_params" in value:
        return "pr25_possible_broad_hold_params"
    return "non_pr25"


def summarize_prediction_fields(cases: Sequence[Dict[str, Any]], preds: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    labels = {row["verification_case_id"]: row["label"] for row in cases}
    result: Dict[str, Any] = {
        "total_cases": len(cases),
        "valid_predictions": 0,
        "invalid_or_missing": 0,
        "positive_cases": 0,
        "positive_false_alarm_cases": 0,
        "positive_false_alarm_cases_with_pr25_direct": 0,
        "positive_false_alarm_cases_with_pr25_possible": 0,
        "positive_false_alarm_field_occurrences": Counter(),
        "positive_false_alarm_category_occurrences": Counter(),
        "all_error_field_occurrences": Counter(),
        "all_error_field_category_occurrences": Counter(),
        "examples_positive_false_alarm": [],
    }
    for case in cases:
        cid = case["verification_case_id"]
        label = labels[cid]
        pred = preds.get(cid)
        if bool(label["consistent"]):
            result["positive_cases"] += 1
        if pred is None or not pred.get("parse_ok") or not pred.get("parsed_output"):
            result["invalid_or_missing"] += 1
            continue
        result["valid_predictions"] += 1
        parsed = pred["parsed_output"]
        fields = [str(x) for x in parsed.get("error_fields", []) if isinstance(x, str)]
        for field in fields:
            result["all_error_field_occurrences"][field] += 1
            result["all_error_field_category_occurrences"][pr25_category(field)] += 1
        if bool(label["consistent"]) and not bool(parsed.get("consistent")):
            result["positive_false_alarm_cases"] += 1
            categories = {pr25_category(field) for field in fields}
            if any(cat.startswith("pr25_direct") for cat in categories):
                result["positive_false_alarm_cases_with_pr25_direct"] += 1
            if "pr25_possible_broad_hold_params" in categories:
                result["positive_false_alarm_cases_with_pr25_possible"] += 1
            for field in fields:
                result["positive_false_alarm_field_occurrences"][field] += 1
                result["positive_false_alarm_category_occurrences"][pr25_category(field)] += 1
            if len(result["examples_positive_false_alarm"]) < 20:
                result["examples_positive_false_alarm"].append(
                    {
                        "verification_case_id": cid,
                        "chart_id": case.get("chart_id"),
                        "sample_id": case.get("sample_id"),
                        "error_fields": fields,
                        "categories": sorted(categories),
                    }
                )
    for key in [
        "positive_false_alarm_field_occurrences",
        "positive_false_alarm_category_occurrences",
        "all_error_field_occurrences",
        "all_error_field_category_occurrences",
    ]:
        result[key] = dict(result[key].most_common())
    return result


def load_predictions(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    return {row["verification_case_id"]: row for row in read_jsonl(path)}


def pct(n: int, d: int) -> Optional[float]:
    return None if d == 0 else n / d


def md_pct(x: Optional[float]) -> str:
    return "" if x is None else f"{x * 100:.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()

    package_dir = Path(args.package_dir)
    run_dir = Path(args.run_dir)
    reports = run_dir / "reports"
    cases_path = package_dir / "selection" / "e6_core_200pos_200neg_seed20260501.jsonl"
    cases = list(read_jsonl(cases_path))

    important_files = {
        "e6_core_cases": cases_path,
        "v2_prompt": package_dir / "prompts" / "formal_v2_direct_vlm_verifier.md",
        "v2_run_config": package_dir / "configs" / "formal_v2_e6_core_run_config_20260501_r1.json",
        "v2_predictions": run_dir / "V2_direct_image_e6_core_20260501_r1" / "predictions.jsonl",
        "v2_score_summary": run_dir / "V2_direct_image_e6_core_20260501_r1" / "score_summary.json",
        "v3_c4_predictions": run_dir / "V3_C4" / "predictions.jsonl",
        "v3_dsft_predictions": run_dir / "V3_D_SFT" / "predictions.jsonl",
        "v4_c4_predictions": run_dir / "V4_C4_tolerant" / "predictions.jsonl",
        "v4_dsft_predictions": run_dir / "V4_D_SFT_tolerant" / "predictions.jsonl",
        "v4_broad_policy": package_dir / "configs" / "v4_tolerant_compare_policy.md",
        "v4_pr25_narrowed_policy": package_dir / "configs" / "v4_pr25_narrowed_compare_policy.md",
    }
    manifest = {
        "status": "pre_pr25_equivalence_alignment_state",
        "created_date": "2026-05-01",
        "pr25": {
            "url": "https://github.com/reshihihihi/faa-chart-to-424-benchmark/pull/25",
            "state_at_audit": "open_docs_only",
            "allowed_equivalence": ["normalized_string for fix/navaid display forms", "degree_display_rounding for course/radial/inbound_course degrees"],
            "does_not_modify_existing_experiment6_outputs": True,
        },
        "files": {
            name: {"path": str(path), "sha256": sha256_file(path), "exists": path.exists()}
            for name, path in important_files.items()
        },
    }
    write_json(reports / "experiment6_pre_pr25_state_manifest.json", manifest)

    manifest_lines = [
        "# 实验组 6 pre-PR25 状态 Manifest",
        "",
        "状态：`pre_pr25_equivalence_alignment_state`",
        "",
        "该 manifest 固化当前实验组 6 结果状态，后续 PR25-aligned 结果必须使用新 run_id，不覆盖现有 V2/V3/V4。",
        "",
        "## 文件与 Hash",
        "",
        "| name | exists | sha256 | path |",
        "|---|---:|---|---|",
    ]
    for name, info in manifest["files"].items():
        manifest_lines.append(f"| {name} | {info['exists']} | `{info['sha256']}` | `{info['path']}` |")
    (reports / "experiment6_pre_pr25_state_manifest_zh.md").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

    relationship_note = """# 实验组 6 与 PR #25 的关系说明

生成时间：2026-05-01

## 1. PR #25 是什么

PR #25 是实验组 1 scoring-equivalence v2 的收窄版计划文档。它目前是 docs-only，不直接修改实验组 1 prediction、canonical schema、scorer 代码，也不直接修改实验组 6 已有结果。

PR #25 只允许两类等价：

1. fix / navaid 名称显示形式差异：`normalized_string`。
2. course / radial / inbound course 的小数与整数显示差异：`degree_display_rounding`。

## 2. 对实验组 6 的影响边界

实验组 6 当前 V1/V2/V3/V4 结果均保留，不覆盖、不删除，标记为 pre-PR25-equivalence-alignment。

PR #25 提醒实验组 6：candidate 中的 424 canonical value 与航图 display value 可能存在显示等价，例如 `243.1` 与 `R-243`。因此 V2 direct-image 的正例误拒可能有一部分来自 display-equivalence 校准不足。

## 3. 方法处理决策

- V3 strict 不加入 PR25 equivalence。V3 的目的就是展示 naive strict extract-then-compare 的 failure mode。
- 当前 V4 broad tolerant 保留，但不能说它等同于 PR #25。它比 PR #25 更宽，包含 leg alignment、partial compare、数值容差和 mismatch threshold。
- 新增 `V4_PR25_narrowed` 作为低成本 diagnostic，只允许 PR #25 的两类等价。
- 是否新增 V2_r2，要看 V2 false alarm 审计结果；如果误拒主要集中在 PR25 字段，才值得跑新的图像模型版本。
"""
    (reports / "experiment6_pr25_relationship_note_zh.md").write_text(relationship_note, encoding="utf-8")

    v2_preds = load_predictions(run_dir / "V2_direct_image_e6_core_20260501_r1" / "predictions.jsonl")
    v2_audit = summarize_prediction_fields(cases, v2_preds)
    v2_audit["false_alarm_rate"] = pct(v2_audit["positive_false_alarm_cases"], v2_audit["positive_cases"])
    v2_audit["pr25_direct_share_of_false_alarm_cases"] = pct(v2_audit["positive_false_alarm_cases_with_pr25_direct"], v2_audit["positive_false_alarm_cases"])
    v2_audit["pr25_direct_or_possible_share_of_false_alarm_cases"] = pct(
        v2_audit["positive_false_alarm_cases_with_pr25_direct"] + v2_audit["positive_false_alarm_cases_with_pr25_possible"],
        v2_audit["positive_false_alarm_cases"],
    )
    write_json(reports / "experiment6_v2_false_alarm_pr25_audit.json", v2_audit)

    v2_lines = [
        "# V2 False Alarm 的 PR25 影响审计",
        "",
        "## 总览",
        "",
        f"- positive cases: {v2_audit['positive_cases']}",
        f"- positive false alarm cases: {v2_audit['positive_false_alarm_cases']}",
        f"- false alarm rate: {md_pct(v2_audit['false_alarm_rate'])}",
        f"- false alarm 中含 PR25 direct 字段的 case: {v2_audit['positive_false_alarm_cases_with_pr25_direct']} ({md_pct(v2_audit['pr25_direct_share_of_false_alarm_cases'])})",
        f"- false alarm 中含 PR25 direct 或 broad hold_params possible 字段的 case: {v2_audit['positive_false_alarm_cases_with_pr25_direct'] + v2_audit['positive_false_alarm_cases_with_pr25_possible']} ({md_pct(v2_audit['pr25_direct_or_possible_share_of_false_alarm_cases'])})",
        "",
        "## False Alarm 字段类别",
        "",
        "| category | occurrences |",
        "|---|---:|",
    ]
    for k, v in v2_audit["positive_false_alarm_category_occurrences"].items():
        v2_lines.append(f"| {k} | {v} |")
    v2_lines.extend(["", "## False Alarm 字段 Top", "", "| field | occurrences |", "|---|---:|"])
    for k, v in list(v2_audit["positive_false_alarm_field_occurrences"].items())[:30]:
        v2_lines.append(f"| `{k}` | {v} |")
    v2_lines.extend(["", "## 示例", ""])
    for item in v2_audit["examples_positive_false_alarm"][:10]:
        v2_lines.append(f"- `{item['verification_case_id']}`: {item['error_fields']}")
    (reports / "experiment6_v2_false_alarm_pr25_audit_zh.md").write_text("\n".join(v2_lines) + "\n", encoding="utf-8")

    methods = {
        "V3_C4_strict": run_dir / "V3_C4" / "predictions.jsonl",
        "V3_D_SFT_strict": run_dir / "V3_D_SFT" / "predictions.jsonl",
        "V4_C4_broad_tolerant": run_dir / "V4_C4_tolerant" / "predictions.jsonl",
        "V4_D_SFT_broad_tolerant": run_dir / "V4_D_SFT_tolerant" / "predictions.jsonl",
    }
    v3_v4_audit = {}
    for method, path in methods.items():
        v3_v4_audit[method] = summarize_prediction_fields(cases, load_predictions(path))
    write_json(reports / "experiment6_v3_v4_pr25_field_impact_audit.json", v3_v4_audit)

    lines = [
        "# V3/V4 PR25 字段影响审计",
        "",
        "本审计只统计已有输出中的 error_fields，不修改 V3/V4 结果。",
        "",
        "| method | valid | positive false alarms | PR25 direct FA cases | PR25 possible hold FA cases | top categories |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for method, audit in v3_v4_audit.items():
        cats = ", ".join(f"{k}:{v}" for k, v in list(audit["positive_false_alarm_category_occurrences"].items())[:5])
        lines.append(
            f"| {method} | {audit['valid_predictions']} | {audit['positive_false_alarm_cases']} | "
            f"{audit['positive_false_alarm_cases_with_pr25_direct']} | {audit['positive_false_alarm_cases_with_pr25_possible']} | {cats} |"
        )
    lines.extend(
        [
            "",
            "## 决策",
            "",
            "V3 strict 保持不动，因为它是 failure-mode baseline。",
            "",
            "当前 V4 broad tolerant 保留为宽容诊断比较器，但不等同于 PR #25。",
            "",
            "新增 `V4_PR25_narrowed`，只允许 fix/navaid normalized_string 与 degree_display_rounding。",
        ]
    )
    (reports / "experiment6_v3_v4_pr25_field_impact_audit_zh.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"reports_dir": str(reports), "v2_false_alarms": v2_audit["positive_false_alarm_cases"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
