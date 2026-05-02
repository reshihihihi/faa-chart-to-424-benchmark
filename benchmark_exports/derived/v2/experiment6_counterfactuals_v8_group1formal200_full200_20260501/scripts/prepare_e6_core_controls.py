#!/usr/bin/env python3
"""Prepare low-cost Experiment 6 controls and E6-core scoring artifacts.

This script does not call any model API. It creates deterministic baselines,
an oracle-target comparer sanity check, a rule-based candidate-only control,
and a balanced E6-core subset for rescoring already completed predictions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


BASE_FIELD_NAMES = [
    "path_terminator",
    "fix_ident",
    "altitude_constraint",
    "turn",
    "course_or_radial",
    "hold_params",
]


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_sort_key(seed: str, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()


def pct(n: int, d: int) -> Optional[float]:
    return None if d == 0 else n / d


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
    if value.endswith(".value"):
        value = value[: -len(".value")]
    return value


def norm_fields(fields: Any, normalize: bool = False) -> Set[str]:
    if not isinstance(fields, list):
        return set()
    if normalize:
        return {normalize_field_path(str(x)) for x in fields}
    return {str(x) for x in fields}


def score_predictions(cases: Sequence[Dict[str, Any]], predictions: Sequence[Dict[str, Any]], method_name: str) -> Dict[str, Any]:
    labels = {row["verification_case_id"]: row["label"] for row in cases}
    preds = {row["verification_case_id"]: row for row in predictions}
    totals = Counter()
    by_type: Dict[str, Counter] = defaultdict(Counter)

    for case_id, label in labels.items():
        pred_row = preds.get(case_id)
        ctype = label["counterfactual_type"]
        actual_consistent = bool(label["consistent"])
        is_positive = actual_consistent
        totals["total"] += 1
        by_type[ctype]["total"] += 1
        if pred_row is None:
            totals["missing"] += 1
            by_type[ctype]["missing"] += 1
            continue
        if pred_row.get("api_error"):
            totals["api_error"] += 1
            by_type[ctype]["api_error"] += 1
        if not pred_row.get("parse_ok") or pred_row.get("parsed_output") is None:
            totals["invalid"] += 1
            by_type[ctype]["invalid"] += 1
            continue

        pred = pred_row["parsed_output"]
        pred_consistent = bool(pred["consistent"])
        pred_fields = norm_fields(pred.get("error_fields"))
        gold_fields = norm_fields(label.get("error_fields"))
        pred_fields_normalized = norm_fields(pred.get("error_fields"), normalize=True)
        gold_fields_normalized = norm_fields(label.get("error_fields"), normalize=True)

        totals["valid"] += 1
        by_type[ctype]["valid"] += 1
        if pred_consistent == actual_consistent:
            totals["binary_correct"] += 1
            by_type[ctype]["binary_correct"] += 1
        else:
            totals["binary_wrong"] += 1
            by_type[ctype]["binary_wrong"] += 1
        if is_positive:
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
            if pred_fields_normalized == gold_fields_normalized:
                totals["error_fields_exact_normalized"] += 1
                by_type[ctype]["error_fields_exact_normalized"] += 1
            if pred_fields_normalized & gold_fields_normalized:
                totals["error_fields_overlap_normalized"] += 1
                by_type[ctype]["error_fields_overlap_normalized"] += 1

    def summarize(counter: Counter) -> Dict[str, Any]:
        total = counter["total"]
        valid = counter["valid"]
        pos = counter["positive"]
        neg = counter["negative"]
        positive_accept = pct(counter["positive_accept"], pos)
        negative_reject = pct(counter["negative_reject"], neg)
        balanced = None
        if positive_accept is not None and negative_reject is not None:
            balanced = (positive_accept + negative_reject) / 2
        return {
            **dict(counter),
            "binary_accuracy_all_invalid_wrong": pct(counter["binary_correct"], total),
            "binary_accuracy_valid_only": pct(counter["binary_correct"], valid),
            "positive_accept_rate": positive_accept,
            "false_alarm_rate": pct(counter["false_alarm"], pos),
            "negative_reject_rate": negative_reject,
            "miss_rate": pct(counter["miss"], neg),
            "balanced_accuracy": balanced,
            "error_field_exact_rate_on_negatives": pct(counter["error_fields_exact"], neg),
            "error_field_overlap_rate_on_negatives": pct(counter["error_fields_overlap"], neg),
            "error_field_exact_normalized_rate_on_negatives": pct(counter["error_fields_exact_normalized"], neg),
            "error_field_overlap_normalized_rate_on_negatives": pct(counter["error_fields_overlap_normalized"], neg),
            "invalid_rate": pct(counter["invalid"] + counter["missing"], total),
        }

    return {
        "method": method_name,
        "overall": summarize(totals),
        "by_counterfactual_type": {k: summarize(v) for k, v in sorted(by_type.items())},
    }


def write_score_report(path: Path, summary: Dict[str, Any], title: str) -> None:
    o = summary["overall"]

    def fmt(x: Any) -> str:
        if x is None:
            return ""
        if isinstance(x, float):
            return f"{x:.4f}"
        return str(x)

    lines = [
        f"# {title}",
        "",
        "Status: Experiment 6 low-cost control / rescoring artifact.",
        "",
        "## Overall",
        "",
        "| metric | value |",
        "|---|---:|",
        f"| total | {o.get('total', 0)} |",
        f"| valid | {o.get('valid', 0)} |",
        f"| invalid/missing | {o.get('invalid', 0) + o.get('missing', 0)} |",
        f"| positive accept | {fmt(o.get('positive_accept_rate'))} |",
        f"| false alarm | {fmt(o.get('false_alarm_rate'))} |",
        f"| negative reject | {fmt(o.get('negative_reject_rate'))} |",
        f"| miss rate | {fmt(o.get('miss_rate'))} |",
        f"| balanced accuracy | {fmt(o.get('balanced_accuracy'))} |",
        f"| binary accuracy, invalid wrong | {fmt(o.get('binary_accuracy_all_invalid_wrong'))} |",
        f"| normalized error-field overlap | {fmt(o.get('error_field_overlap_normalized_rate_on_negatives'))} |",
        f"| invalid rate | {fmt(o.get('invalid_rate'))} |",
        "",
        "## By Counterfactual Type",
        "",
        "| type | total | valid | positive accept | negative reject | balanced acc | miss rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for ctype, vals in summary["by_counterfactual_type"].items():
        lines.append(
            f"| {ctype} | {vals.get('total', 0)} | {vals.get('valid', 0)} | "
            f"{fmt(vals.get('positive_accept_rate'))} | {fmt(vals.get('negative_reject_rate'))} | "
            f"{fmt(vals.get('balanced_accuracy'))} | {fmt(vals.get('miss_rate'))} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_prediction(case: Dict[str, Any], method: str, consistent: bool, error_fields: List[str]) -> Dict[str, Any]:
    return {
        "verification_case_id": case["verification_case_id"],
        "chart_id": case["chart_id"],
        "sample_id": case["sample_id"],
        "method": method,
        "model": "deterministic_control",
        "raw_output": json.dumps({"consistent": consistent, "error_fields": error_fields}, ensure_ascii=False, sort_keys=True),
        "parsed_output": {"consistent": consistent, "error_fields": error_fields},
        "parse_ok": True,
        "parse_error": None,
        "api_error": None,
    }


def candidate_integrity_errors(record: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    ma = record.get("missed_approach", {})
    legs = ma.get("legs")
    if not isinstance(legs, list):
        return ["missed_approach.legs"]
    if ma.get("leg_count") != len(legs):
        errors.append("missed_approach.leg_count")
    for leg in legs:
        idx = leg.get("leg_index", "?")
        for field in BASE_FIELD_NAMES:
            value = leg.get(field)
            path = f"missed_approach.legs[{idx}].{field}"
            if not isinstance(value, dict):
                errors.append(path)
                continue
            status = value.get("status")
            has_value = value.get("value") is not None
            if status == "present" and not has_value:
                errors.append(path)
            if status in {"not_applicable", "unknown", "absent"} and has_value:
                errors.append(path)
    return sorted(set(errors))


def make_rule_v0_predictions(cases: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for case in cases:
        errors = candidate_integrity_errors(case["candidate_record"])
        rows.append(make_prediction(case, "V0_rule_candidate_integrity", not errors, errors))
    return rows


def make_all_predictions(cases: Sequence[Dict[str, Any]], method: str, consistent: bool) -> List[Dict[str, Any]]:
    return [make_prediction(case, method, consistent, [] if consistent else ["candidate_record"]) for case in cases]


def field_path_from_parts(parts: List[Any]) -> Optional[str]:
    if parts[:2] == ["missed_approach", "leg_count"]:
        return "missed_approach.leg_count"
    if len(parts) >= 4 and parts[0] == "missed_approach" and parts[1] == "legs":
        leg = parts[2]
        field = parts[3]
        if field in BASE_FIELD_NAMES:
            return f"missed_approach.legs[{leg}].{field}"
        if field in {"leg_index", "sequence"}:
            return "missed_approach.legs.sequence"
    return None


def collect_record_diffs(a: Any, b: Any, parts: Optional[List[Any]] = None, out: Optional[Set[str]] = None) -> Set[str]:
    if parts is None:
        parts = []
    if out is None:
        out = set()
    mapped = field_path_from_parts(parts)
    if mapped and a != b:
        out.add(mapped)
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            collect_record_diffs(a.get(key), b.get(key), parts + [key], out)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.add("missed_approach.legs.sequence")
        for i, (left, right) in enumerate(zip(a, b)):
            leg_index = left.get("leg_index") if isinstance(left, dict) else i + 1
            collect_record_diffs(left, right, parts + [leg_index], out)
        return out
    if a != b:
        mapped = field_path_from_parts(parts)
        if mapped:
            out.add(mapped)
    return out


def make_oracle_predictions(cases: Sequence[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    positives: Dict[str, Dict[str, Any]] = {}
    duplicate_positive_samples: List[str] = []
    for case in cases:
        if case["label"]["consistent"]:
            key = case["sample_id"]
            if key in positives:
                duplicate_positive_samples.append(key)
            positives[key] = case["candidate_record"]

    rows = []
    missing_oracles = []
    for case in cases:
        oracle = positives.get(case["sample_id"])
        if oracle is None:
            missing_oracles.append(case["verification_case_id"])
            rows.append(make_prediction(case, "oracle_target_projection_compare", False, ["oracle_missing"]))
            continue
        diffs = collect_record_diffs(oracle, case["candidate_record"])
        mutation_rule = case.get("construction", {}).get("mutation_rule")
        if mutation_rule in {"ca_omission", "ca_to_df_sequence_error"} and diffs:
            diffs = {"missed_approach.legs.sequence"}
        rows.append(make_prediction(case, "oracle_target_projection_compare", not diffs, sorted(diffs)))

    qc = {
        "positive_oracles": len(positives),
        "duplicate_positive_samples": sorted(set(duplicate_positive_samples)),
        "missing_oracle_cases": missing_oracles,
    }
    return rows, qc


def select_e6_core(cases: Sequence[Dict[str, Any]], seed: str, negatives_target: int = 200) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    positives = [row for row in cases if row["label"]["consistent"]]
    negatives_by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in cases:
        if not row["label"]["consistent"]:
            negatives_by_type[row["label"]["counterfactual_type"]].append(row)

    types = sorted(negatives_by_type)
    base = negatives_target // len(types)
    remainder = negatives_target % len(types)
    type_order_for_extra = sorted(types, key=lambda t: (-len(negatives_by_type[t]), t))
    quotas = {t: base for t in types}
    for t in type_order_for_extra[:remainder]:
        quotas[t] += 1

    selected_negatives: List[Dict[str, Any]] = []
    for t in types:
        rows = sorted(negatives_by_type[t], key=lambda r: stable_sort_key(seed, r["verification_case_id"]))
        selected_negatives.extend(rows[: quotas[t]])

    selected = sorted(positives + selected_negatives, key=lambda r: (r["sample_id"], r["verification_case_id"]))
    report = {
        "selection_name": f"E6-core balanced 200 positive + {negatives_target} stratified negative",
        "seed": seed,
        "total_cases": len(selected),
        "positive_cases": len(positives),
        "negative_cases": len(selected_negatives),
        "negative_quotas": quotas,
        "negative_selected_by_type": Counter(row["label"]["counterfactual_type"] for row in selected_negatives),
        "unique_positive_charts": len({row["sample_id"] for row in positives}),
        "unique_negative_charts": len({row["sample_id"] for row in selected_negatives}),
        "case_ids_sha256": hashlib.sha256("\n".join(row["verification_case_id"] for row in selected).encode("utf-8")).hexdigest(),
    }
    report["negative_selected_by_type"] = dict(sorted(report["negative_selected_by_type"].items()))
    return selected, report


def read_predictions_if_exists(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return list(read_jsonl(path))


def write_table_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "split",
        "method",
        "total",
        "valid",
        "invalid",
        "positive_accept",
        "false_alarm",
        "negative_reject",
        "miss_rate",
        "balanced_accuracy",
        "binary_accuracy",
        "error_field_overlap_norm",
        "invalid_rate",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def table_row(split: str, summary: Dict[str, Any]) -> Dict[str, Any]:
    o = summary["overall"]
    return {
        "split": split,
        "method": summary["method"],
        "total": o.get("total", 0),
        "valid": o.get("valid", 0),
        "invalid": o.get("invalid", 0) + o.get("missing", 0),
        "positive_accept": o.get("positive_accept_rate"),
        "false_alarm": o.get("false_alarm_rate"),
        "negative_reject": o.get("negative_reject_rate"),
        "miss_rate": o.get("miss_rate"),
        "balanced_accuracy": o.get("balanced_accuracy"),
        "binary_accuracy": o.get("binary_accuracy_all_invalid_wrong"),
        "error_field_overlap_norm": o.get("error_field_overlap_normalized_rate_on_negatives"),
        "invalid_rate": o.get("invalid_rate"),
    }


def write_summary_md(path: Path, rows: List[Dict[str, Any]], title: str) -> None:
    def fmt(x: Any) -> str:
        if x is None or x == "":
            return ""
        if isinstance(x, float):
            return f"{x * 100:.1f}%"
        return str(x)

    lines = [
        f"# {title}",
        "",
        "## Result Table",
        "",
        "| split | method | total | valid | invalid | positive accept | false alarm | negative reject | miss rate | balanced acc | binary acc | error-field overlap | invalid rate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['split']} | {row['method']} | {row['total']} | {row['valid']} | {row['invalid']} | "
            f"{fmt(row['positive_accept'])} | {fmt(row['false_alarm'])} | {fmt(row['negative_reject'])} | "
            f"{fmt(row['miss_rate'])} | {fmt(row['balanced_accuracy'])} | {fmt(row['binary_accuracy'])} | "
            f"{fmt(row['error_field_overlap_norm'])} | {fmt(row['invalid_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- balanced accuracy = (positive accept + negative reject) / 2.",
            "- all-reject is expected to have high binary accuracy on the imbalanced fullbank, so it is a control rather than a real verifier.",
            "- oracle-target projection compare is a builder/scorer sanity check, not a model method.",
            "- V0 rule candidate integrity uses only candidate_record structure and no chart evidence.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--seed", default="20260501")
    args = parser.parse_args()

    package_dir = Path(args.package_dir)
    run_dir = Path(args.run_dir)
    cases_path = package_dir / "cases" / "verification_counterfactuals_v8_group1formal200_full200.jsonl"
    cases = list(read_jsonl(cases_path))

    controls_dir = run_dir / "controls"
    reports_dir = run_dir / "reports"
    core_dir = run_dir / "E6_core"
    selection_dir = package_dir / "selection"

    generated_predictions = {
        "all_accept": make_all_predictions(cases, "all_accept_control", True),
        "all_reject": make_all_predictions(cases, "all_reject_control", False),
        "v0_rule_candidate_integrity": make_rule_v0_predictions(cases),
    }
    oracle_preds, oracle_qc = make_oracle_predictions(cases)
    generated_predictions["oracle_target_projection_compare"] = oracle_preds
    write_json(controls_dir / "oracle_target_projection_compare" / "oracle_qc.json", oracle_qc)

    fullbank_summaries: List[Dict[str, Any]] = []
    for name, preds in generated_predictions.items():
        out_dir = controls_dir / name
        write_jsonl(out_dir / "predictions.jsonl", preds)
        summary = score_predictions(cases, preds, name)
        write_json(out_dir / "score_summary.json", summary)
        write_score_report(out_dir / "score_report.md", summary, f"Experiment 6 Control: {name}")
        fullbank_summaries.append(summary)

    existing_methods = {
        "V1_OCR_text": run_dir / "V1" / "predictions.jsonl",
        "V3_C4_strict": run_dir / "V3_C4" / "predictions.jsonl",
        "V3_D_SFT_strict": run_dir / "V3_D_SFT" / "predictions.jsonl",
        "V4_C4_tolerant": run_dir / "V4_C4_tolerant" / "predictions.jsonl",
        "V4_D_SFT_tolerant": run_dir / "V4_D_SFT_tolerant" / "predictions.jsonl",
    }
    for method, pred_path in existing_methods.items():
        preds = read_predictions_if_exists(pred_path)
        if preds:
            fullbank_summaries.append(score_predictions(cases, preds, method))

    core_cases, core_report = select_e6_core(cases, seed=args.seed)
    core_cases_path = core_dir / "cases" / f"e6_core_200pos_200neg_seed{args.seed}.jsonl"
    package_core_path = selection_dir / f"e6_core_200pos_200neg_seed{args.seed}.jsonl"
    write_jsonl(core_cases_path, core_cases)
    write_jsonl(package_core_path, core_cases)
    write_json(core_dir / "selection_report.json", core_report)
    write_json(selection_dir / f"e6_core_200pos_200neg_seed{args.seed}_selection_report.json", core_report)

    core_lines = [
        "# E6-core Balanced Subset Selection Report",
        "",
        f"- seed: `{args.seed}`",
        f"- total cases: {core_report['total_cases']}",
        f"- positive cases: {core_report['positive_cases']}",
        f"- negative cases: {core_report['negative_cases']}",
        f"- unique positive charts: {core_report['unique_positive_charts']}",
        f"- unique negative charts: {core_report['unique_negative_charts']}",
        f"- case_ids_sha256: `{core_report['case_ids_sha256']}`",
        "",
        "## Negative Selection By Type",
        "",
        "| type | selected | quota |",
        "|---|---:|---:|",
    ]
    for ctype in sorted(core_report["negative_quotas"]):
        core_lines.append(
            f"| {ctype} | {core_report['negative_selected_by_type'].get(ctype, 0)} | {core_report['negative_quotas'][ctype]} |"
        )
    (core_dir / "selection_report.md").write_text("\n".join(core_lines) + "\n", encoding="utf-8")

    core_summaries: List[Dict[str, Any]] = []
    for name, preds in generated_predictions.items():
        summary = score_predictions(core_cases, preds, name)
        out_dir = core_dir / "scores" / name
        write_json(out_dir / "score_summary.json", summary)
        write_score_report(out_dir / "score_report.md", summary, f"E6-core Score: {name}")
        core_summaries.append(summary)
    for method, pred_path in existing_methods.items():
        preds = read_predictions_if_exists(pred_path)
        if preds:
            summary = score_predictions(core_cases, preds, method)
            out_dir = core_dir / "scores" / method
            write_json(out_dir / "score_summary.json", summary)
            write_score_report(out_dir / "score_report.md", summary, f"E6-core Score: {method}")
            core_summaries.append(summary)

    fullbank_rows = [table_row("fullbank2055", s) for s in fullbank_summaries]
    core_rows = [table_row("E6-core400", s) for s in core_summaries]
    all_rows = fullbank_rows + core_rows
    write_table_csv(reports_dir / "experiment6_controls_and_e6_core_scores_20260501.csv", all_rows)
    write_summary_md(reports_dir / "experiment6_controls_and_e6_core_scores_zh_20260501.md", all_rows, "实验组6控制项与E6-core重评分结果")
    write_json(reports_dir / "experiment6_controls_and_e6_core_scores_20260501.json", all_rows)

    print(json.dumps({"cases": len(cases), "core_cases": len(core_cases), "report": str(reports_dir / "experiment6_controls_and_e6_core_scores_zh_20260501.md")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
