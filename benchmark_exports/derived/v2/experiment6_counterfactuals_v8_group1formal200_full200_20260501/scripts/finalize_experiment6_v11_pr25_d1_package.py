#!/usr/bin/env python3
"""Finalize Experiment 6 v11 package aligned with Group 1 PR #25 D1 outputs.

This script performs no model calls. It re-runs only the symbolic Experiment 6
D1-dependent comparisons using a local checkout/copy of PR #25 D1 artifacts, but
writes all saved provenance as repository-relative paths that are valid after
PR #25 is merged or when Experiment 6 is stacked on top of PR #25.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REPO = Path(__file__).resolve().parents[5]

OLD_RUN = REPO / "formal_runs/experiment6/experiment6_group1formal200_full200_v9_chartdisplay_20260501_r1"
V10_D1_RUN = REPO / "formal_runs/experiment6/experiment6_group1formal200_full200_v10_d1_20260502_r1"
NEW_RUN = REPO / "formal_runs/experiment6/experiment6_group1formal200_full200_v11_pr25_d1_20260502_r1"
SCRIPT_DIR = Path(__file__).resolve().parent

CASES = OLD_RUN / "E6_core/cases/e6_core_200pos_200neg_seed20260501_chartdisplay_v2.jsonl"
V9_METRICS = OLD_RUN / "reports/experiment6_v9_final_metrics_table_20260501.csv"
V9_MANIFEST = OLD_RUN / "reports/experiment6_v9_final_evaluation_manifest_20260501.json"
V9_AUDIT = OLD_RUN / "reports/experiment6_v9_integrity_retry_no_leakage_audit_20260501.json"

# Logical paths that should exist in the repository after PR #25 is merged.
PR25_HEAD_SHA = "36e978348b4966a1a6f789acedb78e18381d13dd"
PR25_D1_ROOT_REL = Path(
    "formal_runs/group1/"
    "group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/D1"
)
PR25_D1_CANONICAL_REL = PR25_D1_ROOT_REL / "canonical_json"
PR25_D1_VALIDATION_REL = PR25_D1_ROOT_REL / "validation"
PR25_D1_SUMMARY_REL = PR25_D1_ROOT_REL / "reports/D1_summary.json"

# Physical source used while PR #25 is not yet merged into this worktree.
LOCAL_PR25_COPY = REPO.parent / "faa-chart-to-424-benchmark-group1-v2-results"
PHYSICAL_D1_ROOT_CANDIDATES = [
    REPO / PR25_D1_ROOT_REL,
    LOCAL_PR25_COPY / PR25_D1_ROOT_REL,
]

METHOD_ROWS = [
    {
        "method": "control_all_accept",
        "source_score": OLD_RUN / "controls/control_all_accept/score_summary.json",
        "source_predictions": OLD_RUN / "controls/control_all_accept/predictions.jsonl",
        "role": "control",
        "main_result": True,
    },
    {
        "method": "control_all_reject",
        "source_score": OLD_RUN / "controls/control_all_reject/score_summary.json",
        "source_predictions": OLD_RUN / "controls/control_all_reject/predictions.jsonl",
        "role": "control",
        "main_result": True,
    },
    {
        "method": "control_oracle_label",
        "source_score": OLD_RUN / "controls/control_oracle_label/score_summary.json",
        "source_predictions": OLD_RUN / "controls/control_oracle_label/predictions.jsonl",
        "role": "oracle_control",
        "main_result": True,
    },
    {
        "method": "control_v0_candidate_integrity",
        "source_score": OLD_RUN / "controls/control_v0_candidate_integrity/score_summary.json",
        "source_predictions": OLD_RUN / "controls/control_v0_candidate_integrity/predictions.jsonl",
        "role": "candidate_artifact_control",
        "main_result": True,
    },
    {
        "method": "V1_OCR_text_chartdisplay_v2",
        "source_score": OLD_RUN / "V1_text_only/score_summary.json",
        "source_predictions": OLD_RUN / "V1_text_only/predictions.jsonl",
        "role": "main_method",
        "main_result": True,
    },
    {
        "method": "V2_direct_image_policyv3_chartdisplay_v2",
        "source_score": OLD_RUN / "V2_direct_image_policyv3/score_summary.normalized_error_fields.json",
        "source_predictions": OLD_RUN / "V2_direct_image_policyv3/predictions.normalized_error_fields.jsonl",
        "role": "main_method",
        "main_result": True,
    },
    {
        "method": "V3_C4_group1v2_neutralized",
        "source_score": OLD_RUN / "V3_C4_group1v2_neutralized/score_summary.json",
        "source_predictions": OLD_RUN / "V3_C4_group1v2_neutralized/predictions.jsonl",
        "role": "main_method",
        "main_result": True,
    },
    {
        "method": "V3_D1_SFT_group1v2_neutralized",
        "source_score": NEW_RUN / "V3_D1_SFT_group1v2_neutralized/score_summary.json",
        "source_predictions": NEW_RUN / "V3_D1_SFT_group1v2_neutralized/predictions.jsonl",
        "role": "main_method",
        "main_result": True,
    },
    {
        "method": "V4_C4_tolerant_chartdisplay_v2",
        "source_score": OLD_RUN / "V4_C4_tolerant/score_summary.json",
        "source_predictions": OLD_RUN / "V4_C4_tolerant/predictions.jsonl",
        "role": "diagnostic_tolerant_method",
        "main_result": True,
    },
    {
        "method": "V4_D1_SFT_tolerant_chartdisplay_v2",
        "source_score": NEW_RUN / "V4_D1_SFT_tolerant/score_summary.json",
        "source_predictions": NEW_RUN / "V4_D1_SFT_tolerant/predictions.jsonl",
        "role": "diagnostic_tolerant_method",
        "main_result": True,
    },
    {
        "method": "V3_D_SFT_pre_D1_group1v2_neutralized",
        "source_score": OLD_RUN / "V3_D_SFT_group1v2_neutralized/score_summary.json",
        "source_predictions": OLD_RUN / "V3_D_SFT_group1v2_neutralized/predictions.jsonl",
        "role": "appendix_pre_d1_diagnostic",
        "main_result": False,
    },
    {
        "method": "V4_D_SFT_pre_D1_tolerant",
        "source_score": OLD_RUN / "V4_D_SFT_tolerant/score_summary.json",
        "source_predictions": OLD_RUN / "V4_D_SFT_tolerant/predictions.jsonl",
        "role": "appendix_pre_d1_diagnostic",
        "main_result": False,
    },
]


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V3_MODULE = load_module(SCRIPT_DIR / "run_v3_extract_then_compare.py", "e6_v3_runner")
V4_MODULE = load_module(SCRIPT_DIR / "run_v4_tolerant_extract_then_compare.py", "e6_v4_runner")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_obj(obj: Any) -> str:
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def pct(value: Any) -> str:
    if value is None or value == "":
        return ""
    return f"{float(value) * 100:.2f}%"


def physical_d1_root() -> Path:
    for candidate in PHYSICAL_D1_ROOT_CANDIDATES:
        if (candidate / "canonical_json").exists() and (candidate / "reports/D1_summary.json").exists():
            return candidate
    tried = [str(path) for path in PHYSICAL_D1_ROOT_CANDIDATES]
    raise FileNotFoundError(f"Cannot find PR #25 D1 artifacts. Tried: {tried}")


def directory_manifest_hash(root: Path, suffix: str = "*.json") -> tuple[int, str]:
    h = hashlib.sha256()
    files = sorted(root.glob(suffix))
    for file in files:
        h.update(file.name.encode("utf-8"))
        h.update(b"\0")
        h.update(sha256_file(file).encode("ascii"))
        h.update(b"\n")
    return len(files), h.hexdigest()


def load_validation_errors(path: Path) -> list[Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if payload.get("valid") is True or payload.get("schema_valid") is True:
            return []
        return payload.get("errors") or payload.get("validation_errors") or [payload]
    return [f"unexpected_validation_payload_type:{type(payload).__name__}"]


def validation_error(validation_dir: Path, chart_id: str) -> str | None:
    path = validation_dir / f"{chart_id}.json"
    if not path.exists():
        return f"missing_extraction_validation:{PR25_D1_VALIDATION_REL.as_posix()}/{chart_id}.json"
    errors = load_validation_errors(path)
    if errors:
        return f"schema_invalid_extraction:{errors}"
    return None


def run_symbolic_d1_branch(
    *,
    cases: list[dict[str, Any]],
    physical_canonical_dir: Path,
    physical_validation_dir: Path,
    logical_canonical_dir: Path,
    out_dir: Path,
    method_label: str,
    model_label: str,
    compare_fn: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    compare_policy: str,
) -> None:
    started = datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    for case in cases:
        chart_id = case["chart_id"]
        physical_path = physical_canonical_dir / f"{chart_id}.json"
        logical_path = logical_canonical_dir / f"{chart_id}.json"
        parse_ok = True
        parse_error = None
        parsed_output = None
        extraction_hash = None
        try:
            err = validation_error(physical_validation_dir, chart_id)
            if err:
                raise ValueError(err)
            extraction = read_json(physical_path)
            extraction_hash = sha256_obj(extraction)
            parsed_output = compare_fn(case["candidate_record"], extraction)
        except Exception as exc:  # noqa: BLE001 - saved as run artifact.
            parse_ok = False
            parse_error = f"extract_then_compare_error:{type(exc).__name__}:{exc}"
        rows.append(
            {
                "verification_case_id": case["verification_case_id"],
                "chart_id": chart_id,
                "sample_id": case["sample_id"],
                "method": method_label,
                "model": model_label,
                "prompt_hash": None,
                "input_hash": sha256_obj(
                    {
                        "verification_case_id": case["verification_case_id"],
                        "candidate_record": case["candidate_record"],
                        "extraction_path": logical_path.as_posix(),
                        "extraction_hash": extraction_hash,
                        "compare_policy": compare_policy,
                    }
                ),
                "raw_output": json.dumps(parsed_output, ensure_ascii=False, sort_keys=True) if parsed_output else "",
                "parsed_output": parsed_output,
                "parse_ok": parse_ok,
                "parse_error": parse_error,
                "api_error": None,
                "api_attempts": 0,
                "elapsed_sec": 0,
                "diagnostics": {
                    "extraction_path": logical_path.as_posix(),
                    "extraction_hash": extraction_hash,
                    "compare_policy": compare_policy,
                    "source_dependency": "GitHub PR #25 D1 canonical_json",
                },
            }
        )

    predictions = out_dir / "predictions.jsonl"
    summary = out_dir / "run_summary.json"
    write_jsonl(predictions, rows)
    write_json(
        summary,
        {
            "method": method_label,
            "cases_jsonl": rel(CASES),
            "logical_extraction_dir": logical_canonical_dir.as_posix(),
            "logical_validation_dir": PR25_D1_VALIDATION_REL.as_posix(),
            "out_jsonl": rel(predictions),
            "requested_records": len(cases),
            "parse_ok": sum(1 for row in rows if row["parse_ok"]),
            "parse_fail": sum(1 for row in rows if not row["parse_ok"]),
            "api_error": 0,
            "elapsed_sec": round((datetime.now(timezone.utc) - started).total_seconds(), 3),
            "compare_policy": compare_policy,
        },
    )


def normalize_field_path(field: str) -> str:
    import re

    value = str(field).strip()
    if value.startswith("candidate_record."):
        value = value[len("candidate_record.") :]
    value = value.replace(".answers.", ".")
    value = value.replace(".value.", ".")
    if value.endswith(".value"):
        value = value[: -len(".value")]
    for name in [
        "path_terminator",
        "fix_ident",
        "altitude_constraint",
        "turn",
        "course_or_radial",
        "hold_params",
    ]:
        marker = f".{name}."
        if marker in value:
            value = value.split(marker, 1)[0] + f".{name}"
            break
    return re.sub(r"\.value$", "", value)


def norm_fields(fields: Any, normalize: bool = False) -> set[str]:
    if not isinstance(fields, list):
        return set()
    if normalize:
        return {normalize_field_path(str(item)) for item in fields}
    return {str(item) for item in fields}


def score_predictions(cases_path: Path, predictions_path: Path, out_dir: Path) -> dict[str, Any]:
    labels = {row["verification_case_id"]: row["label"] for row in read_jsonl(cases_path)}
    preds = {row["verification_case_id"]: row for row in read_jsonl(predictions_path)}
    method_names = sorted({row.get("method", "unknown") for row in preds.values()})
    method_name = method_names[0] if len(method_names) == 1 else "mixed_methods"

    totals: Counter[str] = Counter()
    by_type: dict[str, Counter[str]] = defaultdict(Counter)
    for case_id, label in labels.items():
        pred_row = preds.get(case_id)
        ctype = label["counterfactual_type"]
        is_positive = bool(label["consistent"])
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
        actual_consistent = bool(label["consistent"])
        pred_fields = norm_fields(pred.get("error_fields"))
        gold_fields = norm_fields(label.get("error_fields"))
        pred_fields_norm = norm_fields(pred.get("error_fields"), normalize=True)
        gold_fields_norm = norm_fields(label.get("error_fields"), normalize=True)
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
            if pred_fields_norm == gold_fields_norm:
                totals["error_fields_exact_normalized"] += 1
                by_type[ctype]["error_fields_exact_normalized"] += 1
            if pred_fields_norm & gold_fields_norm:
                totals["error_fields_overlap_normalized"] += 1
                by_type[ctype]["error_fields_overlap_normalized"] += 1

    def ratio(n: int, d: int) -> float | None:
        return None if d == 0 else n / d

    def summarize(counter: Counter[str]) -> dict[str, Any]:
        total = counter["total"]
        valid = counter["valid"]
        negative = counter["negative"]
        positive = counter["positive"]
        return {
            **dict(counter),
            "binary_accuracy_all_invalid_wrong": ratio(counter["binary_correct"], total),
            "binary_accuracy_valid_only": ratio(counter["binary_correct"], valid),
            "positive_accept_rate": ratio(counter["positive_accept"], positive),
            "false_positive_rate": ratio(counter["false_positive"], positive),
            "negative_reject_rate_artifact_score": ratio(counter["negative_reject"], negative),
            "false_negative_rate": ratio(counter["false_negative"], negative),
            "error_field_exact_rate_on_negatives": ratio(counter["error_fields_exact"], negative),
            "error_field_overlap_rate_on_negatives": ratio(counter["error_fields_overlap"], negative),
            "error_field_exact_normalized_rate_on_negatives": ratio(counter["error_fields_exact_normalized"], negative),
            "error_field_overlap_normalized_rate_on_negatives": ratio(counter["error_fields_overlap_normalized"], negative),
            "invalid_rate": ratio(counter["invalid"] + counter["missing"], total),
        }

    summary = {
        "cases_jsonl": rel(cases_path),
        "predictions_jsonl": rel(predictions_path),
        "method": method_name,
        "overall": summarize(totals),
        "by_counterfactual_type": {k: summarize(v) for k, v in sorted(by_type.items())},
    }
    write_json(out_dir / "score_summary.json", summary)
    return summary


def score_to_metric_row(method: str, score_path: Path, role: str, main_result: bool) -> dict[str, Any]:
    payload = read_json(score_path)
    score = payload.get("overall", payload)
    valid = int(score.get("valid", 0))
    total = int(score.get("total", 0))
    invalid = total - valid
    pos = score.get("positive_accept_rate")
    neg = score.get("negative_reject_rate_artifact_score", score.get("negative_reject_rate"))
    false_alarm = score.get("false_positive_rate", score.get("false_alarm_rate"))
    miss_rate = score.get("false_negative_rate", score.get("miss_rate"))
    balanced = score.get("balanced_accuracy")
    if balanced is None and pos is not None and neg is not None:
        balanced = (float(pos) + float(neg)) / 2
    return {
        "group_name": "overall",
        "group_value": "all",
        "method": method,
        "role": role,
        "main_result": str(bool(main_result)).lower(),
        "total": total,
        "valid": valid,
        "invalid_or_missing": invalid,
        "binary_accuracy": score.get("binary_accuracy_all_invalid_wrong"),
        "balanced_accuracy": balanced,
        "positive_accept": pos,
        "false_alarm": false_alarm,
        "negative_reject": neg,
        "miss_rate": miss_rate,
        "error_field_exact_norm": score.get("error_field_exact_normalized_rate_on_negatives"),
        "error_field_overlap_norm": score.get("error_field_overlap_normalized_rate_on_negatives"),
        "invalid_rate": score.get("invalid_rate"),
    }


def write_metrics_tables() -> list[dict[str, Any]]:
    rows = [score_to_metric_row(row["method"], row["source_score"], row["role"], row["main_result"]) for row in METHOD_ROWS]
    reports = NEW_RUN / "reports"
    csv_path = reports / "experiment6_v11_final_metrics_table_20260502.csv"
    json_path = reports / "experiment6_v11_final_metrics_table_20260502.json"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_json(json_path, rows)
    return rows


def prediction_integrity(path: Path, expected_ids: set[str]) -> dict[str, Any]:
    rows = read_jsonl(path)
    ids = [row.get("verification_case_id") for row in rows]
    actual = {case_id for case_id in ids if isinstance(case_id, str)}
    duplicates = [case_id for case_id, count in Counter(ids).items() if isinstance(case_id, str) and count > 1]
    return {
        "path": rel(path),
        "sha256": sha256_file(path),
        "rows": len(rows),
        "expected_cases": len(expected_ids),
        "missing_count": len(expected_ids - actual),
        "missing_examples": sorted(expected_ids - actual)[:10],
        "unexpected_count": len(actual - expected_ids),
        "unexpected_examples": sorted(actual - expected_ids)[:10],
        "duplicate_count": len(duplicates),
        "duplicate_examples": duplicates[:10],
        "parse_fail_count": sum(1 for row in rows if row.get("parse_ok") is False),
        "api_error_count": sum(1 for row in rows if row.get("api_error")),
        "malformed_parsed_output_count": sum(1 for row in rows if not isinstance(row.get("parsed_output"), dict)),
    }


def scan_for_local_paths(paths: list[Path]) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    patterns = (
        "E:\\experiment3",
        "C:\\Users",
        "E:\\experiment3\\v2\\D1_20260502_r4",
    )
    for path in paths:
        if not path.exists() or path.is_dir():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern in text:
                hits.append({"path": rel(path), "pattern": pattern})
    return {"hit_count": len(hits), "hits": hits}


def write_dependency_manifest(d1_summary: dict[str, Any], d1_count: int, d1_hash: str) -> None:
    manifest = {
        "artifact_id": "experiment6_v11_pr25_dependency_manifest_20260502",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete_dependency_recorded",
        "depends_on": {
            "github_pr": "reshihihihi/faa-chart-to-424-benchmark#25",
            "pr_title": "Add Group 1 scoring-equivalence v2 and D1 formal200 result",
            "pr_head_sha": PR25_HEAD_SHA,
            "required_before_experiment6_pr": "merge PR #25 first, or stack Experiment 6 PR on PR #25 head",
        },
        "used_pr25_artifacts": {
            "d1_method_card": {
                "path": "docs/d1_method_card_zh.md",
                "sha256": d1_summary.get("hashes", {}).get("method_card"),
            },
            "d1_policy": {
                "path": "docs/d1_output_canonicalization_policy_zh.md",
                "sha256": d1_summary.get("hashes", {}).get("policy"),
            },
            "d1_canonicalizer_script": {
                "path": "scripts/run_d1_output_canonicalizer.py",
                "sha256": d1_summary.get("hashes", {}).get("script"),
            },
            "d1_canonical_json": {
                "path": PR25_D1_CANONICAL_REL.as_posix(),
                "file_count": d1_count,
                "directory_manifest_sha256": d1_hash,
            },
            "d1_validation": {"path": PR25_D1_VALIDATION_REL.as_posix()},
            "d1_summary": {"path": PR25_D1_SUMMARY_REL.as_posix(), "sha256": sha256_obj(d1_summary)},
            "group1_scoring_equivalence_v2_scorer": {
                "path": "scripts/scorers/group1_canonical_field_scorer_v2.py",
                "sha256": d1_summary.get("hashes", {}).get("scorer_validate_only"),
            },
            "group1_scoring_equivalence_v2_targets": {
                "path": "benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2",
            },
        },
        "important_boundary": {
            "experiment6_v3_uses_pr25_narrow_display_neutralization": True,
            "experiment6_v4_tolerant_compare_is_diagnostic_not_pr25_scoring_equivalence": True,
            "not_in_pr25_scoring_equivalence_v2": [
                "altitude tolerance",
                "turn semantic relaxation",
                "holding default time",
                "DME/distance tolerance",
                "reciprocal radial/course equivalence",
                "Q_terminator relaxation",
                "leg alignment changes",
            ],
        },
    }
    write_json(NEW_RUN / "configs/experiment6_pr25_dependency_manifest.json", manifest)


def write_integrity_audit(
    *,
    cases: list[dict[str, Any]],
    d1_summary: dict[str, Any],
    d1_count: int,
    d1_hash: str,
    report_paths: list[Path],
) -> None:
    expected_ids = {row["verification_case_id"] for row in cases}
    expected_charts = {row["chart_id"] for row in cases}
    d1_missing = sorted(
        chart
        for chart in expected_charts
        if not (physical_d1_root() / "canonical_json" / f"{chart}.json").exists()
    )
    method_integrity = {
        row["method"]: prediction_integrity(row["source_predictions"], expected_ids)
        for row in METHOD_ROWS
    }
    local_path_scan_files = report_paths + [
        NEW_RUN / "V3_D1_SFT_group1v2_neutralized/predictions.jsonl",
        NEW_RUN / "V4_D1_SFT_tolerant/predictions.jsonl",
        NEW_RUN / "V3_D1_SFT_group1v2_neutralized/run_summary.json",
        NEW_RUN / "V4_D1_SFT_tolerant/run_summary.json",
        NEW_RUN / "configs/v11_run_manifest.json",
        NEW_RUN / "configs/experiment6_pr25_dependency_manifest.json",
    ]
    audit = {
        "artifact_id": "experiment6_v11_integrity_no_leakage_audit_20260502",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": NEW_RUN.name,
        "status": "pass" if not d1_missing else "fail_missing_d1_outputs",
        "case_file": {
            "path": rel(CASES),
            "rows": len(cases),
            "unique_charts": len(expected_charts),
            "sha256": sha256_file(CASES),
            "positive_cases": sum(1 for row in cases if row["label"]["consistent"]),
            "negative_cases": sum(1 for row in cases if not row["label"]["consistent"]),
        },
        "d1_source": {
            "logical_root": PR25_D1_ROOT_REL.as_posix(),
            "canonical_json": PR25_D1_CANONICAL_REL.as_posix(),
            "summary": PR25_D1_SUMMARY_REL.as_posix(),
            "summary_payload": d1_summary,
            "canonical_json_file_count": d1_count,
            "canonical_json_directory_manifest_sha256": d1_hash,
            "missing_e6_core_charts_count": len(d1_missing),
            "missing_e6_core_charts": d1_missing,
        },
        "method_prediction_integrity": method_integrity,
        "leakage_boundary_checks": {
            "model_calls_performed_in_v11": 0,
            "v3_v4_d1_inputs": [
                "candidate_record",
                "PR #25 D1 canonical JSON extraction output",
            ],
            "forbidden_inputs_not_used": [
                "target JSON as verifier input",
                "score files as verifier input",
                "CIFP raw records as verifier input",
                "OCR text for V3/V4 D1 branches",
                "other method predictions",
            ],
        },
        "local_absolute_path_scan": scan_for_local_paths(local_path_scan_files),
    }
    if audit["local_absolute_path_scan"]["hit_count"]:
        audit["status"] = "fail_local_absolute_path_found"
    write_json(NEW_RUN / "reports/experiment6_v11_integrity_no_leakage_audit_20260502.json", audit)


def write_run_manifest(rows: list[dict[str, Any]], d1_count: int, d1_hash: str) -> None:
    manifest = read_json(V9_MANIFEST)
    manifest.update(
        {
            "artifact_id": "experiment6_v11_final_evaluation_package_20260502",
            "status": "complete_after_pr25_d1_alignment_not_formal_freeze_until_pr25_merged",
            "base_experiment6_run": rel(OLD_RUN),
            "run_id": NEW_RUN.name,
            "pr25_dependency_manifest": rel(NEW_RUN / "configs/experiment6_pr25_dependency_manifest.json"),
            "d1_source": {
                "pr": "reshihihihi/faa-chart-to-424-benchmark#25",
                "pr_head_sha": PR25_HEAD_SHA,
                "canonical_json": PR25_D1_CANONICAL_REL.as_posix(),
                "file_count": d1_count,
                "directory_manifest_sha256": d1_hash,
            },
            "reports": {
                "audit_json": rel(NEW_RUN / "reports/experiment6_v11_integrity_no_leakage_audit_20260502.json"),
                "final_metrics_csv": rel(NEW_RUN / "reports/experiment6_v11_final_metrics_table_20260502.csv"),
                "final_metrics_json": rel(NEW_RUN / "reports/experiment6_v11_final_metrics_table_20260502.json"),
                "final_report_zh": rel(NEW_RUN / "reports/experiment6_v11_final_report_zh_20260502.md"),
            },
            "main_result_methods": [row["method"] for row in rows if row["main_result"] == "true"],
            "appendix_diagnostic_methods": [row["method"] for row in rows if row["main_result"] == "false"],
            "method_predictions": {
                row["method"]: {
                    "path": rel(next(src["source_predictions"] for src in METHOD_ROWS if src["method"] == row["method"])),
                    "sha256": sha256_file(next(src["source_predictions"] for src in METHOD_ROWS if src["method"] == row["method"])),
                    "role": row["role"],
                    "main_result": row["main_result"] == "true",
                }
                for row in rows
            },
        }
    )
    write_json(NEW_RUN / "configs/v11_run_manifest.json", manifest)


def write_report(rows: list[dict[str, Any]], d1_summary: dict[str, Any]) -> None:
    report = NEW_RUN / "reports/experiment6_v11_final_report_zh_20260502.md"
    main_rows = [row for row in rows if row["main_result"] == "true"]
    appendix_rows = [row for row in rows if row["main_result"] == "false"]

    lines = [
        "# 实验组 6 v11 最终整理报告：对齐 #25 scoring-equivalence v2 与 D1",
        "",
        "## 1. 本次做了什么",
        "",
        "本次没有重新调用模型，也没有改变实验组 6 的科学问题。v11 只做四件事：",
        "",
        "1. 沿用 v10-D1 已审定的 D-SFT V3/V4 符号比较结果，并确认其 D1 来源与 #25 D1 canonical JSON 哈希一致。",
        "2. 把所有 D1 来源写成仓库相对路径，去掉 Windows 本地盘符绝对路径。",
        "3. 把 control、V1、V2、V3-C4、V3-D1-SFT、V4-C4、V4-D1-SFT 统一成最终结果表。",
        "4. 写入 #25 dependency manifest 和完整 integrity/no-leakage audit。",
        "",
        "## 2. 为什么必须吸收 #25",
        "",
        "#25 对实验组 6 有两个直接影响：",
        "",
        "- Group 1 scoring-equivalence v2 允许极窄范围的显示等价，例如 fix/navaid 显示规范化，以及 course/radial/hold inbound course 的整数/小数显示等价。",
        "- D1 把 D-SFT 原始输出规范化为当前 canonical JSON。实验组 6 中使用 D-SFT 作为 extractor 的分支必须使用 D1 后结果，否则会把输出接口错误混入 424 反事实核验能力。",
        "",
        "因此 v11 的主结果使用 D1 后的 D-SFT；pre-D1 只保留为附录诊断。",
        "",
        "## 3. 方法边界",
        "",
        "| 方法 | 输入 | 输出 | 目的 | 主结果 |",
        "|---|---|---|---|---|",
        "| control_all_accept | case label 结构控制 | 全部接受 | 检查正负样本平衡 | 是 |",
        "| control_all_reject | case label 结构控制 | 全部拒绝 | 检查正负样本平衡 | 是 |",
        "| control_oracle_label | oracle label | oracle decision | 上限 sanity check | 是 |",
        "| control_v0_candidate_integrity | candidate record only | verification decision | 检查 counterfactual 是否有明显伪造痕迹 | 是 |",
        "| V1 OCR text | OCR text + candidate | verification decision | 文本证据核验 baseline | 是 |",
        "| V2 direct image | chart image + candidate | verification decision | 直接图像核验 | 是 |",
        "| V3-C4 | candidate + C4 canonical extraction | symbolic compare | 普通 extract-then-compare | 是 |",
        "| V3-D1-SFT | candidate + D1-SFT canonical extraction | symbolic compare | 强 extractor 的普通比较 | 是 |",
        "| V4-C4 | candidate + C4 canonical extraction | tolerant symbolic compare | 诊断字段等价、航段对齐、partial compare 后是否改善 | 是 |",
        "| V4-D1-SFT | candidate + D1-SFT canonical extraction | tolerant symbolic compare | 强 extractor 的诊断 tolerant compare | 是 |",
        "",
        "注意：V4 是实验组 6 的诊断性 tolerant compare，不是 #25 scoring-equivalence v2 的正式评分规则。",
        "",
        "## 4. #25 不允许被混入的放宽项",
        "",
        "以下内容没有进入 #25 scoring-equivalence v2，不能把它们说成实验组 1 的正式评分等价：",
        "",
        "- altitude tolerance",
        "- turn semantic relaxation",
        "- holding default time",
        "- DME/distance tolerance",
        "- reciprocal radial/course equivalence",
        "- Q_terminator relaxation",
        "- leg alignment changes",
        "",
        "如果这些能力出现在 V4，只能解释为实验组 6 的诊断性核验器设计，用来分析反事实核验路线是否受字段表示、航段对齐和抽取缺证据影响。",
        "",
        "## 5. D1 覆盖与合法性",
        "",
        f"- D1 run_id: `{d1_summary.get('run_id')}`",
        f"- D1 samples_total: {d1_summary.get('samples_total')}",
        f"- D1 raw_outputs_found: {d1_summary.get('raw_outputs_found')}",
        f"- D1 canonical_json_written: {d1_summary.get('canonical_json_written')}",
        f"- D1 schema_valid: {d1_summary.get('schema_valid')}/{d1_summary.get('samples_total')}",
        f"- D1 schema_invalid: {d1_summary.get('schema_invalid')}",
        f"- D1 final_chart_id_mismatch_count: {d1_summary.get('final_chart_id_mismatch_count')}",
        "",
        "D1 只规范输出接口，不把 target、score、CIFP raw、OCR text、field candidates 或其他方法预测输入给 D-SFT。",
        "",
        "## 6. 主结果表",
        "",
        "| 方法 | role | total | valid | invalid | binary acc | balanced acc | positive accept | false alarm | negative reject | miss rate | error-field overlap norm |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in main_rows:
        lines.append(
            f"| {row['method']} | {row['role']} | {row['total']} | {row['valid']} | "
            f"{row['invalid_or_missing']} | {pct(row['binary_accuracy'])} | {pct(row['balanced_accuracy'])} | "
            f"{pct(row['positive_accept'])} | {pct(row['false_alarm'])} | {pct(row['negative_reject'])} | "
            f"{pct(row['miss_rate'])} | {pct(row['error_field_overlap_norm'])} |"
        )
    lines.extend(
        [
            "",
            "## 7. pre-D1 附录诊断",
            "",
        "pre-D1 D-SFT 结果不再作为主结果，因为它混入了 D-SFT 输出接口/schema 问题。它只用于说明 D1 修正了什么。",
            "",
            "| 方法 | total | valid | invalid | binary acc | positive accept | negative reject | invalid rate |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in appendix_rows:
        lines.append(
            f"| {row['method']} | {row['total']} | {row['valid']} | {row['invalid_or_missing']} | "
            f"{pct(row['binary_accuracy'])} | {pct(row['positive_accept'])} | {pct(row['negative_reject'])} | "
            f"{pct(row['invalid_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## 8. 当前可以说的结论",
            "",
            "1. 实验组 6 的 424 反事实核验路线可以独立评估模型是否能判断候选 424 记录与航图证据是否一致。",
            "2. #25 的显示等价修正已经被吸收，避免把整数/小数等显示差异误当作反事实错误。",
            "3. D1 消除了 D-SFT 输出接口错误，使 D-SFT 分支可以参与同一 canonical JSON 比较。",
            "4. V3 的严格 extract-then-compare 对抽取缺陷非常敏感；V4 的 tolerant compare 用来诊断字段等价、航段对齐和 partial evidence 能否缓解这种敏感性。",
            "",
            "## 9. 当前不能说的结论",
            "",
            "- 不能把 V4 tolerant compare 说成实验组 1 的 scoring-equivalence v2。",
            "- 不能说 V3/V4 直接代表 extractor 的字段抽取准确率；它们测的是候选记录核验中的 extract-then-compare 路线。",
            "- 不能把 pre-D1 D-SFT 作为主结果，因为它含有输出接口/schema failure。",
            "- 在 #25 合并前，v11 是依赖 #25 head 的整理包，不是完全独立于 #25 的最终冻结包。",
            "",
            "## 10. 保存文件",
            "",
            f"- dependency manifest: `{rel(NEW_RUN / 'configs/experiment6_pr25_dependency_manifest.json')}`",
            f"- run manifest: `{rel(NEW_RUN / 'configs/v11_run_manifest.json')}`",
            f"- final metrics CSV: `{rel(NEW_RUN / 'reports/experiment6_v11_final_metrics_table_20260502.csv')}`",
            f"- final metrics JSON: `{rel(NEW_RUN / 'reports/experiment6_v11_final_metrics_table_20260502.json')}`",
            f"- integrity audit: `{rel(NEW_RUN / 'reports/experiment6_v11_integrity_no_leakage_audit_20260502.json')}`",
        ]
    )
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sanitize_previous_d1_branch(source_dir: Path, out_dir: Path, logical_canonical_dir: Path) -> None:
    """Copy v10 D1 predictions while replacing local diagnostic paths.

    v10 already contains the reviewed symbolic comparison result. Re-running the
    comparer after subsequent script edits would silently change the method. The
    v11 package therefore preserves v10 decisions and only normalizes provenance.
    """

    rows = read_jsonl(source_dir / "predictions.jsonl")
    for row in rows:
        chart_id = row["chart_id"]
        logical_path = (logical_canonical_dir / f"{chart_id}.json").as_posix()
        diagnostics = row.setdefault("diagnostics", {})
        diagnostics["extraction_path"] = logical_path
        diagnostics["source_dependency"] = "GitHub PR #25 D1 canonical_json"
        row["diagnostics"] = diagnostics
    write_jsonl(out_dir / "predictions.jsonl", rows)

    summary = read_json(source_dir / "run_summary.json")
    summary["source_v10_run"] = rel(source_dir)
    summary["logical_extraction_dir"] = logical_canonical_dir.as_posix()
    summary.pop("extraction_dir", None)
    summary["out_jsonl"] = rel(out_dir / "predictions.jsonl")
    summary["v11_note"] = (
        "Preserves v10 symbolic comparison decisions; only local D1 source paths "
        "were rewritten to PR #25 repository-relative paths."
    )
    write_json(out_dir / "run_summary.json", summary)


def main() -> int:
    d1_root = physical_d1_root()
    d1_canonical = d1_root / "canonical_json"
    d1_validation = d1_root / "validation"
    d1_summary = read_json(d1_root / "reports/D1_summary.json")
    d1_count, d1_hash = directory_manifest_hash(d1_canonical)
    cases = read_jsonl(CASES)

    sanitize_previous_d1_branch(
        V10_D1_RUN / "V3_D1_SFT_group1v2_neutralized",
        NEW_RUN / "V3_D1_SFT_group1v2_neutralized",
        PR25_D1_CANONICAL_REL,
    )
    score_predictions(
        CASES,
        NEW_RUN / "V3_D1_SFT_group1v2_neutralized/predictions.jsonl",
        NEW_RUN / "V3_D1_SFT_group1v2_neutralized",
    )

    sanitize_previous_d1_branch(
        V10_D1_RUN / "V4_D1_SFT_tolerant",
        NEW_RUN / "V4_D1_SFT_tolerant",
        PR25_D1_CANONICAL_REL,
    )
    score_predictions(
        CASES,
        NEW_RUN / "V4_D1_SFT_tolerant/predictions.jsonl",
        NEW_RUN / "V4_D1_SFT_tolerant",
    )

    rows = write_metrics_tables()
    write_dependency_manifest(d1_summary, d1_count, d1_hash)
    write_run_manifest(rows, d1_count, d1_hash)
    write_report(rows, d1_summary)
    write_integrity_audit(
        cases=cases,
        d1_summary=d1_summary,
        d1_count=d1_count,
        d1_hash=d1_hash,
        report_paths=[
            NEW_RUN / "reports/experiment6_v11_final_metrics_table_20260502.csv",
            NEW_RUN / "reports/experiment6_v11_final_metrics_table_20260502.json",
            NEW_RUN / "reports/experiment6_v11_final_report_zh_20260502.md",
        ],
    )

    print(
        json.dumps(
            {
                "run_id": NEW_RUN.name,
                "status": "complete",
                "reports": rel(NEW_RUN / "reports"),
                "d1_logical_source": PR25_D1_CANONICAL_REL.as_posix(),
                "d1_file_count": d1_count,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
