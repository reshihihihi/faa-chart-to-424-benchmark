#!/usr/bin/env python3
"""Score Experiment 6 audit decision predictions against verification cases."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Set


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


BASE_FIELD_NAMES = [
    "path_terminator",
    "fix_ident",
    "altitude_constraint",
    "turn",
    "course_or_radial",
    "hold_params",
]


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
    value = re.sub(r"\.value$", "", value)
    return value


def norm_fields(fields: Any, normalize: bool = False) -> Set[str]:
    if not isinstance(fields, list):
        return set()
    if normalize:
        return {normalize_field_path(str(x)) for x in fields}
    return {str(x) for x in fields}


def pct(n: int, d: int) -> float | None:
    return None if d == 0 else n / d


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-jsonl", required=True)
    parser.add_argument("--predictions-jsonl", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--summary-md", required=True)
    args = parser.parse_args()

    labels = {row["verification_case_id"]: row["label"] for row in read_jsonl(Path(args.cases_jsonl))}
    preds = {row["verification_case_id"]: row for row in read_jsonl(Path(args.predictions_jsonl))}
    method_names = sorted({row.get("method", "unknown") for row in preds.values()})
    method_name = method_names[0] if len(method_names) == 1 else "mixed_methods"
    is_candidate_only = "V0" in method_name or "candidate_only" in method_name

    totals = Counter()
    by_type: Dict[str, Counter] = defaultdict(Counter)

    for case_id, label in labels.items():
        pred_row = preds.get(case_id)
        ctype = label["counterfactual_type"]
        is_positive = bool(label["consistent"])
        actual_consistent = bool(label["consistent"])
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
                totals["false_positive"] += 1
                by_type[ctype]["false_positive"] += 1
        else:
            totals["negative"] += 1
            by_type[ctype]["negative"] += 1
            if pred_consistent:
                totals["false_negative"] += 1
                by_type[ctype]["false_negative"] += 1
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
        negative = counter["negative"]
        positive = counter["positive"]
        return {
            **dict(counter),
            "binary_accuracy_all_invalid_wrong": pct(counter["binary_correct"], total),
            "binary_accuracy_valid_only": pct(counter["binary_correct"], valid),
            "positive_accept_rate": pct(counter["positive_accept"], positive),
            "false_positive_rate": pct(counter["false_positive"], positive),
            "negative_reject_rate_artifact_score": pct(counter["negative_reject"], negative),
            "false_negative_rate": pct(counter["false_negative"], negative),
            "error_field_exact_rate_on_negatives": pct(counter["error_fields_exact"], negative),
            "error_field_overlap_rate_on_negatives": pct(counter["error_fields_overlap"], negative),
            "error_field_exact_normalized_rate_on_negatives": pct(counter["error_fields_exact_normalized"], negative),
            "error_field_overlap_normalized_rate_on_negatives": pct(counter["error_fields_overlap_normalized"], negative),
            "invalid_rate": pct(counter["invalid"] + counter["missing"], total),
        }

    summary = {
        "cases_jsonl": args.cases_jsonl,
        "predictions_jsonl": args.predictions_jsonl,
        "method": method_name,
        "overall": summarize(totals),
        "by_counterfactual_type": {k: summarize(v) for k, v in sorted(by_type.items())},
        "interpretation": {
            "negative_reject_rate_artifact_score": "For V0 candidate-only, a high value suggests counterfactual artifacts are detectable without chart evidence.",
            "false_negative_rate": "For V0 candidate-only, a high value means the baseline tends to let negative candidates pass, which is expected if artifacts are weak.",
        },
    }

    out_json = Path(args.summary_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines: List[str] = []
    o = summary["overall"]
    lines.append(f"# Experiment 6 Verification Score: {method_name}")
    lines.append("")
    lines.append("Status: pre-freeze artifact check, not formal paper result.")
    lines.append("")
    lines.append("## Overall")
    lines.append("")
    lines.append(f"- total cases: {o.get('total', 0)}")
    lines.append(f"- valid parsed predictions: {o.get('valid', 0)}")
    lines.append(f"- invalid/missing predictions: {o.get('invalid', 0) + o.get('missing', 0)}")
    lines.append(f"- binary accuracy, invalid counted wrong: {o.get('binary_accuracy_all_invalid_wrong')}")
    if is_candidate_only:
        lines.append(f"- candidate-only negative reject rate / artifact score: {o.get('negative_reject_rate_artifact_score')}")
    else:
        lines.append(f"- negative reject rate: {o.get('negative_reject_rate_artifact_score')}")
    lines.append(f"- false negative rate on negative cases: {o.get('false_negative_rate')}")
    lines.append(f"- positive accept rate: {o.get('positive_accept_rate')}")
    lines.append(f"- error-field exact rate on negative cases: {o.get('error_field_exact_rate_on_negatives')}")
    lines.append(f"- normalized error-field exact rate on negative cases: {o.get('error_field_exact_normalized_rate_on_negatives')}")
    lines.append(f"- normalized error-field overlap rate on negative cases: {o.get('error_field_overlap_normalized_rate_on_negatives')}")
    lines.append("")
    lines.append("## By Counterfactual Type")
    lines.append("")
    third_col = "artifact score / negative reject" if is_candidate_only else "negative reject rate"
    lines.append(f"| type | total | valid | {third_col} | false negative rate | binary acc all |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for ctype, vals in summary["by_counterfactual_type"].items():
        lines.append(
            f"| {ctype} | {vals.get('total', 0)} | {vals.get('valid', 0)} | "
            f"{vals.get('negative_reject_rate_artifact_score')} | {vals.get('false_negative_rate')} | "
            f"{vals.get('binary_accuracy_all_invalid_wrong')} |"
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    if is_candidate_only:
        lines.append("For V0, high negative reject rate means the candidate-only baseline can detect synthetic negatives without chart evidence. That is a warning sign for counterfactual artifacts.")
        lines.append("")
        lines.append("For V0, high false negative rate means the candidate-only baseline usually accepts negative records, which is expected when counterfactuals require chart evidence.")
    else:
        lines.append("For chart-aware verification, negative reject rate measures how often the verifier flags inconsistent candidates.")
        lines.append("")
        lines.append("False negative rate is safety-critical: it measures inconsistent candidates accepted as consistent.")
    Path(args.summary_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary["overall"], ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
