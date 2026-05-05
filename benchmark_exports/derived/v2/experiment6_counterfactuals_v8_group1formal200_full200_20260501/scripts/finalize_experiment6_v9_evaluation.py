#!/usr/bin/env python3
"""Finalize Experiment 6 v9 chart-display evaluation artifacts.

This script only reads v9 cases, packed inputs, and method predictions. It
creates deterministic controls, scores them, audits input leakage and prediction
integrity, summarizes retry behavior, and writes stratified evaluation tables.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
PACKAGE_DIR = REPO_ROOT / "benchmark_exports/derived/v2/experiment6_counterfactuals_v8_group1formal200_full200_20260501"
RUN_DIR = REPO_ROOT / "formal_runs/experiment6/experiment6_group1formal200_full200_v9_chartdisplay_20260501_r1"
REPORT_DIR = RUN_DIR / "reports"
CASE_PATH = RUN_DIR / "E6_core/cases/e6_core_200pos_200neg_seed20260501_chartdisplay_v2.jsonl"
SAMPLE_MANIFEST_PATH = PACKAGE_DIR / "selection/sample_manifest_group1formal200_full200_v8.jsonl"

METHOD_PREDICTIONS = {
    "V1_OCR_text_chartdisplay_v2": RUN_DIR / "V1_text_only/predictions.jsonl",
    "V2_direct_image_policyv3_chartdisplay_v2": RUN_DIR
    / "V2_direct_image_policyv3/predictions.normalized_error_fields.jsonl",
    "V3_C4_group1v2_neutralized": RUN_DIR / "V3_C4_group1v2_neutralized/predictions.jsonl",
    "V3_D_SFT_group1v2_neutralized": RUN_DIR / "V3_D_SFT_group1v2_neutralized/predictions.jsonl",
    "V4_C4_tolerant_chartdisplay_v2": RUN_DIR / "V4_C4_tolerant/predictions.jsonl",
    "V4_D_SFT_tolerant_chartdisplay_v2": RUN_DIR / "V4_D_SFT_tolerant/predictions.jsonl",
}

PACKED_INPUTS = {
    "V1_text_only": PACKAGE_DIR / "packed_inputs/v1_text_only_inputs_v9_chartdisplay_e6core.jsonl",
    "V2_direct_image": PACKAGE_DIR / "packed_inputs/v2_direct_vlm_inputs_v9_chartdisplay_e6core.jsonl",
    "V3_extract_then_compare": PACKAGE_DIR / "packed_inputs/v3_extract_then_compare_inputs_v9_chartdisplay_e6core.jsonl",
}

BASE_FIELD_NAMES = [
    "path_terminator",
    "fix_ident",
    "altitude_constraint",
    "turn",
    "course_or_radial",
    "hold_params",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


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


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def pct(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def normalize_field_path(field: str) -> str:
    value = str(field).strip()
    if value.startswith("candidate_record."):
        value = value[len("candidate_record.") :]
    value = value.replace(".answers.", ".")
    value = value.replace(".value.", ".")
    if value.endswith(".value"):
        value = value[: -len(".value")]
    for name in BASE_FIELD_NAMES:
        marker = f".{name}."
        if marker in value:
            value = value.split(marker, 1)[0] + f".{name}"
            break
    return re.sub(r"\.value$", "", value)


def norm_fields(fields: Any, normalize: bool = False) -> set[str]:
    if not isinstance(fields, list):
        return set()
    if normalize:
        return {normalize_field_path(str(field)) for field in fields}
    return {str(field) for field in fields}


def allowed_error_fields(candidate_record: dict[str, Any]) -> set[str]:
    fields = {"missed_approach.leg_count", "missed_approach.legs.sequence"}
    for leg in candidate_record.get("missed_approach", {}).get("legs", []):
        leg_index = leg.get("leg_index")
        if not isinstance(leg_index, int):
            continue
        fields.update(
            {
                f"missed_approach.legs[{leg_index}].path_terminator",
                f"missed_approach.legs[{leg_index}].fix_ident",
                f"missed_approach.legs[{leg_index}].altitude_constraint",
                f"missed_approach.legs[{leg_index}].turn",
                f"missed_approach.legs[{leg_index}].course_or_radial",
                f"missed_approach.legs[{leg_index}].hold_params",
                f"missed_approach.legs[{leg_index}].hold_params.value.leg_time_min",
                f"missed_approach.legs[{leg_index}].hold_params.value.inbound_course_deg",
                f"missed_approach.legs[{leg_index}].hold_params.value.leg_distance_nm",
            }
        )
    return fields


def score_predictions(cases: list[dict[str, Any]], predictions: list[dict[str, Any]], method: str) -> dict[str, Any]:
    pred_map = {row["verification_case_id"]: row for row in predictions}
    totals: Counter[str] = Counter()
    by_type: dict[str, Counter[str]] = defaultdict(Counter)

    for case in cases:
        case_id = case["verification_case_id"]
        label = case["label"]
        ctype = label["counterfactual_type"]
        actual = bool(label["consistent"])
        pred_row = pred_map.get(case_id)
        totals["total"] += 1
        by_type[ctype]["total"] += 1
        if pred_row is None:
            totals["missing"] += 1
            by_type[ctype]["missing"] += 1
            continue
        if pred_row.get("api_error"):
            totals["api_error"] += 1
            by_type[ctype]["api_error"] += 1
        parsed = pred_row.get("parsed_output")
        if not pred_row.get("parse_ok") or not isinstance(parsed, dict):
            totals["invalid"] += 1
            by_type[ctype]["invalid"] += 1
            continue

        pred_consistent = bool(parsed.get("consistent"))
        pred_fields = norm_fields(parsed.get("error_fields"))
        gold_fields = norm_fields(label.get("error_fields"))
        pred_fields_norm = norm_fields(parsed.get("error_fields"), normalize=True)
        gold_fields_norm = norm_fields(label.get("error_fields"), normalize=True)

        totals["valid"] += 1
        by_type[ctype]["valid"] += 1
        if pred_consistent == actual:
            totals["binary_correct"] += 1
            by_type[ctype]["binary_correct"] += 1
        else:
            totals["binary_wrong"] += 1
            by_type[ctype]["binary_wrong"] += 1

        if actual:
            totals["positive"] += 1
            by_type[ctype]["positive"] += 1
            if pred_consistent:
                totals["positive_accept"] += 1
                by_type[ctype]["positive_accept"] += 1
            else:
                totals["false_alarm"] += 1
                by_type[ctype]["false_alarm"] += 1
        else:
            totals["negative"] += 1
            by_type[ctype]["negative"] += 1
            if pred_consistent:
                totals["miss"] += 1
                by_type[ctype]["miss"] += 1
            else:
                totals["negative_reject"] += 1
                by_type[ctype]["negative_reject"] += 1
            if pred_fields == gold_fields:
                totals["error_fields_exact"] += 1
                by_type[ctype]["error_fields_exact"] += 1
            if pred_fields & gold_fields:
                totals["error_fields_overlap"] += 1
                by_type[ctype]["error_fields_overlap"] += 1
            if pred_fields_norm == gold_fields_norm:
                totals["error_fields_exact_normalized"] += 1
                by_type[ctype]["error_fields_exact_normalized"] += 1
            if pred_fields_norm & gold_fields_norm:
                totals["error_fields_overlap_normalized"] += 1
                by_type[ctype]["error_fields_overlap_normalized"] += 1

    def summarize(counter: Counter[str]) -> dict[str, Any]:
        positive_accept = pct(counter["positive_accept"], counter["positive"])
        negative_reject = pct(counter["negative_reject"], counter["negative"])
        balanced = None
        if positive_accept is not None and negative_reject is not None:
            balanced = (positive_accept + negative_reject) / 2
        return {
            **dict(counter),
            "binary_accuracy_all_invalid_wrong": pct(counter["binary_correct"], counter["total"]),
            "binary_accuracy_valid_only": pct(counter["binary_correct"], counter["valid"]),
            "positive_accept_rate": positive_accept,
            "false_alarm_rate": pct(counter["false_alarm"], counter["positive"]),
            "negative_reject_rate": negative_reject,
            "miss_rate": pct(counter["miss"], counter["negative"]),
            "balanced_accuracy": balanced,
            "error_field_exact_rate_on_negatives": pct(counter["error_fields_exact"], counter["negative"]),
            "error_field_overlap_rate_on_negatives": pct(counter["error_fields_overlap"], counter["negative"]),
            "error_field_exact_normalized_rate_on_negatives": pct(
                counter["error_fields_exact_normalized"], counter["negative"]
            ),
            "error_field_overlap_normalized_rate_on_negatives": pct(
                counter["error_fields_overlap_normalized"], counter["negative"]
            ),
            "invalid_rate": pct(counter["invalid"] + counter["missing"], counter["total"]),
        }

    return {
        "method": method,
        "overall": summarize(totals),
        "by_counterfactual_type": {key: summarize(value) for key, value in sorted(by_type.items())},
    }


def prediction_row(case: dict[str, Any], method: str, consistent: bool, error_fields: list[str]) -> dict[str, Any]:
    parsed = {"consistent": consistent, "error_fields": error_fields}
    return {
        "verification_case_id": case["verification_case_id"],
        "chart_id": case["chart_id"],
        "sample_id": case["sample_id"],
        "method": method,
        "model": "deterministic_control",
        "raw_output": json.dumps(parsed, ensure_ascii=False, sort_keys=True),
        "parsed_output": parsed,
        "parse_ok": True,
        "parse_error": None,
        "api_error": None,
        "api_attempts": 0,
    }


def candidate_integrity_errors(candidate: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ma = candidate.get("missed_approach", {})
    legs = ma.get("legs")
    if not isinstance(legs, list):
        return ["missed_approach.legs.sequence"]
    if ma.get("leg_count") != len(legs):
        errors.append("missed_approach.leg_count")
    for leg in legs:
        leg_index = leg.get("leg_index", "?")
        for field_name in BASE_FIELD_NAMES:
            item = leg.get(field_name)
            path = f"missed_approach.legs[{leg_index}].{field_name}"
            if not isinstance(item, dict):
                errors.append(path)
                continue
            status = item.get("status")
            has_value = item.get("value") is not None
            if status == "present" and not has_value:
                errors.append(path)
            if status in {"not_applicable", "absent", "unknown"} and has_value:
                errors.append(path)
    return sorted(set(errors))


def make_controls(cases: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    controls: dict[str, list[dict[str, Any]]] = {}
    controls["control_all_accept"] = [prediction_row(case, "control_all_accept", True, []) for case in cases]
    controls["control_all_reject"] = [
        prediction_row(case, "control_all_reject", False, ["missed_approach.legs.sequence"]) for case in cases
    ]
    controls["control_oracle_label"] = [
        prediction_row(
            case,
            "control_oracle_label",
            bool(case["label"]["consistent"]),
            list(case["label"].get("error_fields") or []),
        )
        for case in cases
    ]
    controls["control_v0_candidate_integrity"] = []
    for case in cases:
        errors = candidate_integrity_errors(case["candidate_record"])
        controls["control_v0_candidate_integrity"].append(
            prediction_row(case, "control_v0_candidate_integrity", not errors, errors)
        )
    return controls


def summary_row(summary: dict[str, Any], group_name: str = "overall", group_value: str = "all") -> dict[str, Any]:
    o = summary["overall"]
    return {
        "group_name": group_name,
        "group_value": group_value,
        "method": summary["method"],
        "total": o.get("total", 0),
        "valid": o.get("valid", 0),
        "invalid_or_missing": o.get("invalid", 0) + o.get("missing", 0),
        "binary_accuracy": o.get("binary_accuracy_all_invalid_wrong"),
        "balanced_accuracy": o.get("balanced_accuracy"),
        "positive_accept": o.get("positive_accept_rate"),
        "false_alarm": o.get("false_alarm_rate"),
        "negative_reject": o.get("negative_reject_rate"),
        "miss_rate": o.get("miss_rate"),
        "error_field_exact_norm": o.get("error_field_exact_normalized_rate_on_negatives"),
        "error_field_overlap_norm": o.get("error_field_overlap_normalized_rate_on_negatives"),
        "invalid_rate": o.get("invalid_rate"),
    }


def field_category(case: dict[str, Any]) -> str:
    if case["label"]["consistent"]:
        return "positive"
    fields = {normalize_field_path(field) for field in case["label"].get("error_fields", [])}
    if not fields:
        return "negative_no_field"
    categories = set()
    for field in fields:
        if "fix_ident" in field:
            categories.add("fix_ident")
        elif "altitude_constraint" in field:
            categories.add("altitude_constraint")
        elif "course_or_radial" in field:
            categories.add("course_or_radial")
        elif "hold_params" in field:
            categories.add("hold_params")
        elif "path_terminator" in field:
            categories.add("path_terminator")
        elif "turn" in field:
            categories.add("turn")
        elif "sequence" in field:
            categories.add("sequence")
        else:
            categories.add("other")
    if len(categories) == 1:
        return next(iter(categories))
    return "multi_field"


def leg_count_bucket(case: dict[str, Any]) -> str:
    count = case.get("candidate_record", {}).get("missed_approach", {}).get("leg_count")
    if not isinstance(count, int):
        return "unknown"
    if count <= 1:
        return "1"
    if count == 2:
        return "2"
    if count == 3:
        return "3"
    return "4_plus"


def subset_score(
    cases: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    method: str,
    group_name: str,
    group_fn,
) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        buckets[str(group_fn(case))].append(case)
    rows = []
    for group_value, group_cases in sorted(buckets.items()):
        rows.append(summary_row(score_predictions(group_cases, predictions, method), group_name, group_value))
    return rows


def audit_prediction_file(cases: list[dict[str, Any]], predictions: list[dict[str, Any]], method: str) -> dict[str, Any]:
    case_ids = [case["verification_case_id"] for case in cases]
    case_id_set = set(case_ids)
    pred_ids = [row.get("verification_case_id") for row in predictions]
    pred_id_counts = Counter(pred_ids)
    duplicates = sorted([case_id for case_id, count in pred_id_counts.items() if count > 1])
    missing = sorted(case_id_set - set(pred_ids))
    unexpected = sorted(set(pred_ids) - case_id_set)
    malformed = 0
    disallowed_error_field_rows = 0
    consistent_false_empty_error_fields = 0
    consistent_true_nonempty_error_fields = 0
    case_index = {case["verification_case_id"]: case for case in cases}
    for row in predictions:
        parsed = row.get("parsed_output")
        if not isinstance(parsed, dict):
            malformed += 1
            continue
        if set(parsed) != {"consistent", "error_fields"}:
            malformed += 1
            continue
        if not isinstance(parsed.get("consistent"), bool):
            malformed += 1
        if not isinstance(parsed.get("error_fields"), list) or not all(isinstance(x, str) for x in parsed["error_fields"]):
            malformed += 1
            continue
        case = case_index.get(row.get("verification_case_id"))
        if case is not None:
            allowed = allowed_error_fields(case["candidate_record"])
            if any(field not in allowed for field in parsed["error_fields"]):
                disallowed_error_field_rows += 1
        if parsed.get("consistent") is False and not parsed.get("error_fields"):
            consistent_false_empty_error_fields += 1
        if parsed.get("consistent") is True and parsed.get("error_fields"):
            consistent_true_nonempty_error_fields += 1

    return {
        "method": method,
        "expected_cases": len(cases),
        "rows": len(predictions),
        "missing_count": len(missing),
        "duplicate_count": len(duplicates),
        "unexpected_count": len(unexpected),
        "parse_fail_count": sum(1 for row in predictions if not row.get("parse_ok")),
        "api_error_count": sum(1 for row in predictions if row.get("api_error")),
        "malformed_parsed_output_count": malformed,
        "disallowed_error_field_rows": disallowed_error_field_rows,
        "consistent_false_empty_error_fields": consistent_false_empty_error_fields,
        "consistent_true_nonempty_error_fields": consistent_true_nonempty_error_fields,
        "missing_examples": missing[:10],
        "duplicate_examples": duplicates[:10],
        "unexpected_examples": unexpected[:10],
    }


def audit_retries(predictions: list[dict[str, Any]], method: str) -> dict[str, Any]:
    attempts = Counter(int(row.get("api_attempts") or 0) for row in predictions)
    return {
        "method": method,
        "rows": len(predictions),
        "attempt_distribution": dict(sorted(attempts.items())),
        "retry_rows": sum(1 for row in predictions if int(row.get("api_attempts") or 0) > 1),
        "max_attempts": max(attempts) if attempts else 0,
        "api_error_rows": sum(1 for row in predictions if row.get("api_error")),
        "parse_fail_rows": sum(1 for row in predictions if not row.get("parse_ok")),
    }


FORBIDDEN_INPUT_KEYS = {
    "label",
    "consistent",
    "error_fields",
    "counterfactual_type",
    "target",
    "canonical_target",
    "canonical_proxy_gt",
    "score",
    "expected",
    "answer_key",
    "evidence_provenance",
    "challenge_tags",
    "raw_cifp",
    "source_target_sha256",
    "mutation_rule",
    "mutation_notes",
    "construction",
}


def walk_keys(obj: Any, path: str = "$"):
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_path = f"{path}.{key}"
            yield key_path, key
            yield from walk_keys(value, key_path)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from walk_keys(value, f"{path}[{index}]")


def audit_no_leakage() -> dict[str, Any]:
    reports: dict[str, Any] = {}
    for name, path in PACKED_INPUTS.items():
        rows = read_jsonl(path)
        findings = []
        for line_no, row in enumerate(rows, start=1):
            for key_path, key in walk_keys(row):
                if str(key).lower() in FORBIDDEN_INPUT_KEYS:
                    findings.append(
                        {
                            "line": line_no,
                            "verification_case_id": row.get("verification_case_id"),
                            "path": key_path,
                            "key": key,
                        }
                    )
        reports[name] = {
            "input_jsonl": rel(path),
            "checked_records": len(rows),
            "finding_count": len(findings),
            "findings": findings[:20],
            "status": "pass" if not findings else "fail",
        }
    return reports


def pct_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value * 100:.1f}%"
    return str(value)


def write_final_report(rows: list[dict[str, Any]], audits: dict[str, Any], retry_rows: list[dict[str, Any]]) -> None:
    main_rows = [row for row in rows if row["group_name"] == "overall"]
    lines = [
        "# 实验组6 v9 最终评估整理报告",
        "",
        "## 1. 评估口径",
        "",
        "本轮使用 v9 chart-display candidate。PR #25 的显示值等价功能已经作为前置规范被消除，不再作为实验组6的新方法。",
        "",
        "本报告补齐了 control/oracle、自检审计、retry 汇总和分层统计。",
        "",
        "## 2. 主结果与 control/oracle",
        "",
        "| method | total | valid | invalid | binary acc | balanced acc | positive accept | false alarm | negative reject | miss rate | norm field overlap |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in main_rows:
        lines.append(
            f"| {row['method']} | {row['total']} | {row['valid']} | {row['invalid_or_missing']} | "
            f"{pct_text(row['binary_accuracy'])} | {pct_text(row['balanced_accuracy'])} | "
            f"{pct_text(row['positive_accept'])} | {pct_text(row['false_alarm'])} | "
            f"{pct_text(row['negative_reject'])} | {pct_text(row['miss_rate'])} | "
            f"{pct_text(row['error_field_overlap_norm'])} |"
        )

    lines.extend(
        [
            "",
            "## 3. 完整性审计",
            "",
            "| method | rows | missing | duplicate | unexpected | parse fail | api error | disallowed fields | malformed |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for method, audit in audits["prediction_integrity"].items():
        lines.append(
            f"| {method} | {audit['rows']} | {audit['missing_count']} | {audit['duplicate_count']} | "
            f"{audit['unexpected_count']} | {audit['parse_fail_count']} | {audit['api_error_count']} | "
            f"{audit['disallowed_error_field_rows']} | {audit['malformed_parsed_output_count']} |"
        )

    lines.extend(
        [
            "",
            "## 4. No-leakage 审计",
            "",
            "| input | checked | findings | status |",
            "|---|---:|---:|---|",
        ]
    )
    for name, audit in audits["no_leakage"].items():
        lines.append(f"| {name} | {audit['checked_records']} | {audit['finding_count']} | {audit['status']} |")

    lines.extend(
        [
            "",
            "## 5. Retry / attempt 汇总",
            "",
            "| method | rows | retry rows | max attempts | api errors | parse fails | attempt distribution |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in retry_rows:
        lines.append(
            f"| {row['method']} | {row['rows']} | {row['retry_rows']} | {row['max_attempts']} | "
            f"{row['api_error_rows']} | {row['parse_fail_rows']} | `{json.dumps(row['attempt_distribution'], sort_keys=True)}` |"
        )

    lines.extend(
        [
            "",
            "## 6. 分层统计文件",
            "",
            "- `experiment6_v9_stratified_by_counterfactual_type.csv`",
            "- `experiment6_v9_stratified_by_procedure_type.csv`",
            "- `experiment6_v9_stratified_by_sample_type.csv`",
            "- `experiment6_v9_stratified_by_leg_count.csv`",
            "- `experiment6_v9_stratified_by_field_category.csv`",
            "",
            "## 7. 结论",
            "",
            "v9 的核心实验运行和最终评估整理已经完成。旧 v8 应只作为 pre-fix 诊断记录；实验组6当前主口径应使用本 v9 package。",
        ]
    )
    (REPORT_DIR / "experiment6_v9_final_evaluation_package_zh_20260501.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    cases = read_jsonl(CASE_PATH)
    sample_meta = {row["chart_id"]: row for row in read_jsonl(SAMPLE_MANIFEST_PATH)}

    controls = make_controls(cases)
    control_dir = RUN_DIR / "controls"
    method_predictions: dict[str, list[dict[str, Any]]] = {}
    for method, rows in controls.items():
        method_dir = control_dir / method
        write_jsonl(method_dir / "predictions.jsonl", rows)
        summary = score_predictions(cases, rows, method)
        write_json(method_dir / "score_summary.json", summary)
        method_predictions[method] = rows

    for method, path in METHOD_PREDICTIONS.items():
        method_predictions[method] = read_jsonl(path)

    summaries = {method: score_predictions(cases, preds, method) for method, preds in method_predictions.items()}
    rows = [summary_row(summary) for summary in summaries.values()]
    write_csv(
        REPORT_DIR / "experiment6_v9_final_metrics_table_20260501.csv",
        rows,
        list(rows[0].keys()),
    )
    write_json(REPORT_DIR / "experiment6_v9_final_metrics_table_20260501.json", rows)

    integrity = {
        method: audit_prediction_file(cases, preds, method) for method, preds in sorted(method_predictions.items())
    }
    retry_rows = [audit_retries(preds, method) for method, preds in sorted(method_predictions.items())]
    no_leakage = audit_no_leakage()
    audits = {
        "prediction_integrity": integrity,
        "retry_attempts": retry_rows,
        "no_leakage": no_leakage,
    }
    write_json(REPORT_DIR / "experiment6_v9_integrity_retry_no_leakage_audit_20260501.json", audits)
    write_csv(REPORT_DIR / "experiment6_v9_retry_attempt_summary_20260501.csv", retry_rows, list(retry_rows[0].keys()))

    case_meta: dict[str, dict[str, Any]] = {}
    for case in cases:
        meta = sample_meta.get(case["chart_id"], {})
        case_meta[case["verification_case_id"]] = {
            "procedure_type": meta.get("procedure_type", "unknown"),
            "sample_type": meta.get("sample_type", "unknown"),
            "leg_count_bucket": leg_count_bucket(case),
            "field_category": field_category(case),
            "counterfactual_type": case["label"]["counterfactual_type"],
        }

    stratified_specs = {
        "counterfactual_type": lambda c: c["label"]["counterfactual_type"],
        "procedure_type": lambda c: case_meta[c["verification_case_id"]]["procedure_type"],
        "sample_type": lambda c: case_meta[c["verification_case_id"]]["sample_type"],
        "leg_count": lambda c: case_meta[c["verification_case_id"]]["leg_count_bucket"],
        "field_category": lambda c: case_meta[c["verification_case_id"]]["field_category"],
    }
    for group_name, group_fn in stratified_specs.items():
        strat_rows: list[dict[str, Any]] = []
        for method, preds in method_predictions.items():
            buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for case in cases:
                buckets[str(group_fn(case))].append(case)
            for group_value, subset_cases in sorted(buckets.items()):
                strat_rows.append(
                    summary_row(score_predictions(subset_cases, preds, method), group_name, group_value)
                )
        write_csv(
            REPORT_DIR / f"experiment6_v9_stratified_by_{group_name}_20260501.csv",
            strat_rows,
            list(strat_rows[0].keys()),
        )

    manifest = {
        "artifact_id": "experiment6_v9_final_evaluation_package_20260501",
        "status": "complete_not_formal_freeze_until_pr25_merged",
        "case_file": {"path": rel(CASE_PATH), "sha256": sha256_file(CASE_PATH)},
        "sample_manifest": {"path": rel(SAMPLE_MANIFEST_PATH), "sha256": sha256_file(SAMPLE_MANIFEST_PATH)},
        "packed_inputs": {
            name: {"path": rel(path), "sha256": sha256_file(path)} for name, path in PACKED_INPUTS.items()
        },
        "method_predictions": {
            method: {"path": rel(path), "sha256": sha256_file(path)}
            for method, path in METHOD_PREDICTIONS.items()
        },
        "generated_controls": {
            method: {
                "path": rel(control_dir / method / "predictions.jsonl"),
                "sha256": sha256_file(control_dir / method / "predictions.jsonl"),
            }
            for method in controls
        },
        "reports": {
            "final_metrics_csv": rel(REPORT_DIR / "experiment6_v9_final_metrics_table_20260501.csv"),
            "audit_json": rel(REPORT_DIR / "experiment6_v9_integrity_retry_no_leakage_audit_20260501.json"),
            "final_report_zh": rel(REPORT_DIR / "experiment6_v9_final_evaluation_package_zh_20260501.md"),
        },
    }
    write_json(REPORT_DIR / "experiment6_v9_final_evaluation_manifest_20260501.json", manifest)
    write_final_report(rows, audits, retry_rows)

    print(json.dumps({"status": "complete", "reports_dir": rel(REPORT_DIR), "methods": len(method_predictions)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
