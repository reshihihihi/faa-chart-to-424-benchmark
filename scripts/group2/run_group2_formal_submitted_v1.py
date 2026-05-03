import argparse
import hashlib
import importlib.util
import json
import os
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT_DEFAULT = SCRIPT_DIR.parents[1]
FIX_SCRIPT = SCRIPT_DIR / "run_group2_group3_direct_q4_fix.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


q4fix = load_module(FIX_SCRIPT, "group2_group3_direct_q4_fix_base")
base = q4fix.base
v3 = q4fix.v3


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, rows, fieldnames=None):
    v3.write_csv(path, rows, fieldnames=fieldnames)


def table_md(rows, columns, max_rows=80):
    rows = rows[:max_rows]
    if not rows:
        return "_无数据_\n"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        vals = []
        for col in columns:
            value = row.get(col, "")
            if col in {"accuracy", "share"} and isinstance(value, (int, float)):
                value = f"{100 * value:.2f}%"
            vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def default_run_id():
    return "group2_formal_submitted_v1_" + datetime.now().strftime("%Y%m%d_%H%M%S")


def path_from_optional(value):
    return Path(value) if value else None


def sha256_or_none(path: Path):
    return base.sha256_file(path) if path and path.exists() and path.is_file() else None


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Run Group 2 formal/submitted evidence-source analysis using submitted "
            "annotations, Group 1 scoring-equivalence v2 field scores, and the "
            "same-leg direct-Q4 evidence completion rule."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=Path(os.environ.get("FAA_BENCH_REPO", REPO_ROOT_DEFAULT)))
    parser.add_argument("--export-path", type=Path, default=path_from_optional(os.environ.get("GROUP2_EXPORT_PATH")))
    parser.add_argument("--overview-path", type=Path, default=path_from_optional(os.environ.get("GROUP2_OVERVIEW_PATH")))
    parser.add_argument("--group1-run", type=Path, default=path_from_optional(os.environ.get("GROUP1_RUN")))
    parser.add_argument("--target-dir", type=Path, default=path_from_optional(os.environ.get("GROUP2_TARGET_DIR")))
    parser.add_argument("--run-id", default=os.environ.get("GROUP2_RUN_ID") or default_run_id())
    parser.add_argument("--output-root", type=Path, default=path_from_optional(os.environ.get("GROUP2_OUTPUT_ROOT")))
    parser.add_argument("--expected-submitted-count", type=int, default=300)
    parser.add_argument("--expected-analysis-count", type=int, default=None)
    parser.add_argument("--min-analysis-count", type=int, default=1)
    parser.add_argument(
        "--previous-run-root",
        type=Path,
        default=path_from_optional(os.environ.get("GROUP2_PREVIOUS_RUN_ROOT")),
        help="Optional previous run root. When provided, writes chart/field/region annotation change audits.",
    )
    parser.add_argument(
        "--allow-submitted-subset",
        action="store_true",
        help="Allow running when submitted annotations are fewer than --expected-submitted-count.",
    )
    parser.add_argument(
        "--include-missing-score-charts",
        action="store_true",
        help="Include submitted charts even when at least one Group 1 method score is missing.",
    )
    parser.add_argument(
        "--copy-export",
        action="store_true",
        help="Copy the annotation export into the local output directory. Leave off for sensitive exports.",
    )
    return parser.parse_args()


def configure_paths(args):
    repo_root = args.repo_root.resolve()
    group1_run = args.group1_run or (
        repo_root
        / "formal_runs"
        / "group1"
        / "group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2"
    )
    target_dir = args.target_dir or (
        repo_root
        / "benchmark_exports"
        / "derived"
        / "v2"
        / "formal300"
        / "targets"
        / "scoring_equivalence_v2"
    )
    group23_root = Path(os.environ.get("GROUP23_ROOT", str(repo_root.parent)))
    output_root = args.output_root or (group23_root / "group2_formal" / args.run_id)

    base.REPO_ROOT = repo_root
    base.EXPORT_PATH = args.export_path
    base.OVERVIEW_PATH = args.overview_path
    base.GROUP1_RUN = group1_run
    base.TARGET_DIR = target_dir
    base.FIELD_TARGETS = target_dir / "field_targets_chart_display_v2.jsonl"
    base.COMPARISON_POLICY = target_dir / "comparison_policy_v2.jsonl"
    base.FORMAL_MANIFEST = repo_root / "benchmark_exports" / "derived" / "v2" / "formal300" / "manifest.json"

    return repo_root, group1_run, target_dir, output_root


def score_file_path(method_source, chart_id):
    candidates = [
        base.GROUP1_RUN / method_source / "scores" / f"{chart_id}.json",
        base.GROUP1_RUN / "scores" / method_source / f"{chart_id}.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def load_score_rows_compatible(method_source, chart_id):
    path = score_file_path(method_source, chart_id)
    if not path.exists():
        return None
    raw = base.load_json(path)
    score = raw.get("score") if isinstance(raw.get("score"), dict) else raw
    rows = []
    for row in score.get("rows") or []:
        field = row.get("field") or ""
        question_field = row.get("question_field")
        if not question_field and "." in field:
            question_field = field.split(".", 1)[1]
        if not question_field and field == "leg_count":
            question_field = "leg_count"
        rows.append({
            **row,
            "question_field": question_field,
            "match_policy": row.get("match_policy") or row.get("comparison_policy"),
            "strict_correct": row.get("strict_correct", row.get("correct")),
        })
    return {**score, "rows": rows}


def load_method_summary_compatible(method_source):
    candidates = [
        base.GROUP1_RUN / method_source / "method_summary.json",
        base.GROUP1_RUN / "reports" / f"{method_source}_summary_v2.json",
        base.GROUP1_RUN / "reports" / f"{'D1' if method_source == 'D_SFT' else method_source}_summary_v2.json",
    ]
    for path in candidates:
        if path.exists():
            return base.load_json(path)
    return {}


def install_group1_layout_compat():
    base.load_score_rows = load_score_rows_compatible
    base.load_method_summary = load_method_summary_compatible


def validate_inputs(args, repo_root, group1_run, target_dir):
    required = {
        "annotation export": args.export_path,
        "admin overview": args.overview_path,
        "Group 1 scoring-equivalence v2 run": group1_run,
        "target dir": target_dir,
        "field targets v2": target_dir / "field_targets_chart_display_v2.jsonl",
        "comparison policy v2": target_dir / "comparison_policy_v2.jsonl",
    }
    missing = [f"{name}: {path}" for name, path in required.items() if not path or not Path(path).exists()]
    if missing:
        raise SystemExit("Missing required inputs:\n- " + "\n- ".join(missing))
    if not repo_root.exists():
        raise SystemExit(f"Repo root does not exist: {repo_root}")


def stable_json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def stable_hash(obj):
    return hashlib.sha256(stable_json(obj).encode("utf-8")).hexdigest()


def read_jsonl_optional(path: Path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig") as f:
        return [json.loads(line) for line in f if line.strip()]


def field_review_score_field(review):
    field_name = review.get("field_name")
    leg_index = review.get("canonical_leg_index")
    if field_name == "leg_count":
        return "leg_count"
    return base.flatten_field_key(leg_index, field_name)


def build_annotation_snapshots(submitted):
    chart_rows = []
    field_rows = []
    region_rows = []
    for entry in submitted:
        data = entry.get("data") or {}
        chart_id = data.get("chart_id")
        field_reviews = data.get("field_reviews") or []
        regions = data.get("regions") or []
        evidence_provenance = data.get("evidence_provenance") or []
        chart_rows.append({
            "chart_id": chart_id,
            "annotator": data.get("annotator"),
            "saved_at": data.get("saved_at"),
            "relative_path": entry.get("relative_path"),
            "field_review_count": len(field_reviews),
            "region_count": len(regions),
            "evidence_provenance_count": len(evidence_provenance),
            "annotation_sha256": stable_hash(data),
            "field_reviews_sha256": stable_hash(field_reviews),
            "regions_sha256": stable_hash(regions),
            "evidence_provenance_sha256": stable_hash(evidence_provenance),
        })

        for review in field_reviews:
            score_field = field_review_score_field(review)
            canonical_answer = review.get("canonical_answer")
            evidence_region_ids = review.get("evidence_region_ids") or []
            field_rows.append({
                "chart_id": chart_id,
                "field_key": review.get("field_key") or score_field,
                "score_field": score_field,
                "canonical_leg_index": review.get("canonical_leg_index"),
                "field_name": review.get("field_name"),
                "leg_type": review.get("leg_type"),
                "support_mode": review.get("support_mode"),
                "review_status": review.get("review_status"),
                "evidence_region_ids": evidence_region_ids,
                "evidence_source": review.get("evidence_source") or review.get("checked_sources") or [],
                "canonical_answer_sha256": stable_hash(canonical_answer),
                "row_sha256": stable_hash(review),
            })

        for region in regions:
            region_id = region.get("final_region_id") or region.get("source_region_id")
            region_rows.append({
                "chart_id": chart_id,
                "region_id": region_id,
                "source_region_id": region.get("source_region_id"),
                "region_type": region.get("region_type"),
                "label": region.get("label"),
                "bbox_sha256": stable_hash(region.get("bbox")),
                "ocr_text_sha256": stable_hash(region.get("ocr_text")),
                "accepted_mapping_count": len(region.get("accepted_mappings") or []),
                "reviewed_mapping_count": len(region.get("candidate_mappings_reviewed") or []),
                "row_sha256": stable_hash(region),
            })
    return (
        sorted(chart_rows, key=lambda r: r["chart_id"] or ""),
        sorted(field_rows, key=lambda r: (r["chart_id"] or "", r["score_field"] or "")),
        sorted(region_rows, key=lambda r: (r["chart_id"] or "", r["region_id"] or "")),
    )


def compare_snapshot_rows(previous_rows, current_rows, key_fields, hash_field, value_fields):
    previous = {tuple(row.get(field) for field in key_fields): row for row in previous_rows}
    current = {tuple(row.get(field) for field in key_fields): row for row in current_rows}
    changes = []
    for key in sorted(set(previous) | set(current), key=lambda x: tuple("" if value is None else str(value) for value in x)):
        old = previous.get(key)
        new = current.get(key)
        base_row = {field: key[index] for index, field in enumerate(key_fields)}
        if old is None:
            changes.append({
                **base_row,
                "change_type": "added",
                "new_hash": new.get(hash_field),
                **{f"new_{field}": new.get(field) for field in value_fields},
            })
        elif new is None:
            changes.append({
                **base_row,
                "change_type": "removed",
                "old_hash": old.get(hash_field),
                **{f"old_{field}": old.get(field) for field in value_fields},
            })
        elif old.get(hash_field) != new.get(hash_field):
            changes.append({
                **base_row,
                "change_type": "changed",
                "old_hash": old.get(hash_field),
                "new_hash": new.get(hash_field),
                **{f"old_{field}": old.get(field) for field in value_fields},
                **{f"new_{field}": new.get(field) for field in value_fields},
            })
    return changes


def write_annotation_change_tracking(output_root, submitted, previous_run_root):
    chart_snapshot, field_snapshot, region_snapshot = build_annotation_snapshots(submitted)
    inputs_dir = output_root / "inputs"
    write_jsonl(inputs_dir / "annotation_chart_snapshot.jsonl", chart_snapshot)
    write_jsonl(inputs_dir / "annotation_field_snapshot.jsonl", field_snapshot)
    write_jsonl(inputs_dir / "annotation_region_snapshot.jsonl", region_snapshot)

    audit = {
        "current_snapshot_paths": {
            "charts": str(inputs_dir / "annotation_chart_snapshot.jsonl"),
            "fields": str(inputs_dir / "annotation_field_snapshot.jsonl"),
            "regions": str(inputs_dir / "annotation_region_snapshot.jsonl"),
        },
        "previous_run_root": str(previous_run_root) if previous_run_root else None,
        "has_previous_snapshot": False,
        "changed_chart_count": 0,
        "changed_field_count": 0,
        "changed_region_count": 0,
        "changed_chart_ids": [],
    }
    if not previous_run_root:
        write_json(inputs_dir / "annotation_change_audit.json", audit)
        return audit

    prev_inputs = previous_run_root / "inputs"
    previous_chart = read_jsonl_optional(prev_inputs / "annotation_chart_snapshot.jsonl")
    previous_field = read_jsonl_optional(prev_inputs / "annotation_field_snapshot.jsonl")
    previous_region = read_jsonl_optional(prev_inputs / "annotation_region_snapshot.jsonl")
    audit["has_previous_snapshot"] = bool(previous_chart or previous_field or previous_region)
    if not audit["has_previous_snapshot"]:
        audit["warning"] = "previous run root does not contain annotation snapshot files"
        write_json(inputs_dir / "annotation_change_audit.json", audit)
        return audit

    chart_changes = compare_snapshot_rows(
        previous_chart,
        chart_snapshot,
        ["chart_id"],
        "annotation_sha256",
        ["saved_at", "field_review_count", "region_count", "evidence_provenance_count"],
    )
    field_changes = compare_snapshot_rows(
        previous_field,
        field_snapshot,
        ["chart_id", "score_field"],
        "row_sha256",
        ["field_key", "field_name", "support_mode", "review_status", "evidence_region_ids", "evidence_source"],
    )
    region_changes = compare_snapshot_rows(
        previous_region,
        region_snapshot,
        ["chart_id", "region_id"],
        "row_sha256",
        ["region_type", "label", "accepted_mapping_count", "reviewed_mapping_count"],
    )
    changed_chart_ids = sorted({
        row.get("chart_id")
        for rows in (chart_changes, field_changes, region_changes)
        for row in rows
        if row.get("chart_id")
    })
    changed_chart_rows = [{"chart_id": chart_id} for chart_id in changed_chart_ids]
    write_jsonl(inputs_dir / "annotation_changed_charts.jsonl", changed_chart_rows)
    write_jsonl(inputs_dir / "annotation_changed_fields.jsonl", field_changes)
    write_jsonl(inputs_dir / "annotation_changed_regions.jsonl", region_changes)

    audit.update({
        "changed_chart_count": len(changed_chart_ids),
        "changed_field_count": len(field_changes),
        "changed_region_count": len(region_changes),
        "changed_chart_ids": changed_chart_ids,
        "change_paths": {
            "changed_charts": str(inputs_dir / "annotation_changed_charts.jsonl"),
            "changed_fields": str(inputs_dir / "annotation_changed_fields.jsonl"),
            "changed_regions": str(inputs_dir / "annotation_changed_regions.jsonl"),
        },
    })
    write_json(inputs_dir / "annotation_change_audit.json", audit)
    return audit


def is_non_final_annotation(entry, overview_meta):
    data = entry.get("data") or {}
    chart_id = data.get("chart_id")
    status_values = [
        data.get("status"),
        data.get("annotation_status"),
        data.get("submission_status"),
        entry.get("status"),
        entry.get("annotation_status"),
        overview_meta.get(chart_id, {}).get("status"),
        overview_meta.get(chart_id, {}).get("annotation_status"),
        overview_meta.get(chart_id, {}).get("submission_status"),
    ]
    statuses = {str(x).strip().lower() for x in status_values if x is not None}
    blocked = {"draft", "claimed", "assigned", "in_progress", "unsubmitted", "not_submitted", "pending"}
    return bool(statuses & blocked)


def latest_annotations(export_obj, overview_obj):
    formal = export_obj.get("datasets", {}).get("formal300", {})
    entries = formal.get("annotations", {}).get("by_annotator", [])
    overview_rows = (overview_obj.get("dataset") or {}).get("rows") or []
    row_index = {row.get("chart_id"): row.get("row_index", 999999) for row in overview_rows}
    overview_meta = {row.get("chart_id"): row for row in overview_rows}

    by_chart = {}
    excluded = []
    for entry in entries:
        data = entry.get("data") or {}
        chart_id = data.get("chart_id")
        if not chart_id:
            excluded.append({"reason": "missing_chart_id", "relative_path": entry.get("relative_path")})
            continue
        if is_non_final_annotation(entry, overview_meta):
            excluded.append({"chart_id": chart_id, "reason": "non_final_annotation", "relative_path": entry.get("relative_path")})
            continue
        prev = by_chart.get(chart_id)
        if prev is None or str(data.get("saved_at", "")) > str((prev.get("data") or {}).get("saved_at", "")):
            by_chart[chart_id] = entry

    submitted = sorted(
        by_chart.values(),
        key=lambda e: (row_index.get((e.get("data") or {}).get("chart_id"), 999999), (e.get("data") or {}).get("chart_id", "")),
    )
    return submitted, excluded, by_chart, row_index, overview_meta


def build_selection(submitted, row_index, overview_meta, include_missing_score_charts):
    selected = []
    skipped_missing = []
    for entry in submitted:
        data = entry.get("data") or {}
        chart_id = data.get("chart_id")
        missing_methods = [
            label
            for source, label in base.METHOD_SOURCES
            if not score_file_path(source, chart_id).exists()
        ]
        item = {
            "chart_id": chart_id,
            "row_index": row_index.get(chart_id),
            "annotator": data.get("annotator"),
            "saved_at": data.get("saved_at"),
            "relative_path": entry.get("relative_path"),
            "field_review_count": len(data.get("field_reviews") or []),
            "missing_group1_methods": missing_methods,
            "has_all_group1_method_scores": not missing_methods,
            "airport": overview_meta.get(chart_id, {}).get("airport", ""),
            "proc_ident": overview_meta.get(chart_id, {}).get("proc_ident", ""),
            "chart_name": overview_meta.get(chart_id, {}).get("chart_name", ""),
            "kind": overview_meta.get(chart_id, {}).get("kind", ""),
        }
        if include_missing_score_charts or not missing_methods:
            selected.append(item)
        else:
            skipped_missing.append(item)
    return selected, skipped_missing


def split_group2_rows(joined):
    evidence_by_chart_question = {}
    for row in joined:
        if not v3.has_evidence(row):
            continue
        key = (row.get("chart_id"), row.get("question_field"))
        evidence_by_chart_question.setdefault(
            key,
            {k: val for k, val in row.items() if k.startswith("evidence_")},
        )

    positive = []
    positive_question_fallback = []
    size_control_present = []
    negative = []
    diagnostic = []
    unmatched_present = []
    unmatched_not_applicable = []
    evidence_on_negative = []

    for row in joined:
        status = v3.target_status(row)
        enriched = {**row, "target_status": status, "pred_status": v3.pred_status(row)}
        if status == "present":
            if row.get("score_field") == "leg_count":
                size_control_present.append({**enriched, "audit_reason": "leg_count_size_control_not_evidence_source"})
            elif v3.has_evidence(row):
                enriched["semantic_overlay"] = v3.semantic_overlay(row)
                positive.append(enriched)
            elif (row.get("chart_id"), row.get("question_field")) in evidence_by_chart_question:
                fallback = evidence_by_chart_question[(row.get("chart_id"), row.get("question_field"))]
                positive_question_fallback.append(
                    {
                        **enriched,
                        **fallback,
                        "semantic_overlay": v3.semantic_overlay({**enriched, **fallback}),
                        "audit_reason": "same_chart_same_question_field_not_same_leg",
                        "evidence_match_scope": "same_chart_same_question_field_not_same_leg",
                    }
                )
            else:
                unmatched_present.append({**enriched, "audit_reason": "present_score_field_without_evidence"})
        elif status == "not_applicable":
            enriched["negative_error_type"] = v3.negative_error_type(row)
            negative.append(enriched)
            if v3.has_evidence(row):
                evidence_on_negative.append({**enriched, "audit_reason": "evidence_attached_to_not_applicable_score_field"})
            else:
                unmatched_not_applicable.append({**enriched, "audit_reason": "not_applicable_score_field_without_evidence_expected"})
        else:
            diagnostic.append({**enriched, "audit_reason": f"target_status={status}"})

    return {
        "positive": positive,
        "positive_question_fallback": positive_question_fallback,
        "size_control_present": size_control_present,
        "negative": negative,
        "diagnostic": diagnostic,
        "unmatched_present": unmatched_present,
        "unmatched_not_applicable": unmatched_not_applicable,
        "evidence_on_negative": evidence_on_negative,
    }


def write_group2_tables(output_root, split):
    tables = {
        "positive_evidence_bucket": v3.aggregate_bool(split["positive"], ["method", "evidence_evidence_bucket"]),
        "positive_support_mode": v3.aggregate_bool(split["positive"], ["method", "evidence_support_mode"]),
        "positive_field_family": v3.aggregate_bool(split["positive"], ["method", "field_family"]),
        "positive_semantic_overlay": v3.aggregate_bool(split["positive"], ["method", "semantic_overlay"]),
        "question_fallback_evidence_bucket": v3.aggregate_bool(split["positive_question_fallback"], ["method", "evidence_evidence_bucket"]),
        "size_control_present_field": v3.aggregate_bool(split["size_control_present"], ["method", "score_field"], correct_key="correct"),
        "not_applicable_error_type": v3.aggregate_bool(split["negative"], ["method", "negative_error_type"], correct_key="correct"),
        "not_applicable_error_share": v3.aggregate_category_share(split["negative"], ["method"], "negative_error_type"),
        "not_applicable_by_field_family": v3.aggregate_bool(split["negative"], ["method", "field_family", "negative_error_type"], correct_key="correct"),
        "not_applicable_by_question_field": v3.aggregate_bool(split["negative"], ["method", "question_field", "negative_error_type"], correct_key="correct"),
    }
    for name, rows in tables.items():
        write_csv(output_root / "group2" / "reports" / f"{name}_table.csv", rows)
    return tables


def hard_blockers(audit):
    blockers = []
    if audit["submitted_annotation_count"] != audit["expected_submitted_count"]:
        blockers.append("submitted annotation count is below the expected formal dataset count")
    if audit["field_score_rows"] == 0:
        blockers.append("no Group 1 field score rows were read")
    if audit["positive_question_fallback_rows"] > 0:
        blockers.append("positive present fields still require same-question but not same-leg fallback review")
    if audit["unmatched_present_rows"] > 0:
        blockers.append("present score fields without same-leg evidence remain")
    if audit["analysis_chart_count"] < audit["min_analysis_count"]:
        blockers.append("analysis chart count is below minimum")
    if audit.get("expected_analysis_count") is not None and audit["analysis_chart_count"] != audit["expected_analysis_count"]:
        blockers.append("analysis chart count differs from expected")
    return blockers


def main():
    args = parse_args()
    repo_root, group1_run, target_dir, output_root = configure_paths(args)
    install_group1_layout_compat()
    validate_inputs(args, repo_root, group1_run, target_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    export_obj = read_json(args.export_path)
    overview_obj = read_json(args.overview_path)
    field_targets = list(base.read_jsonl(base.FIELD_TARGETS))

    submitted, excluded_annotations, by_chart, row_index, overview_meta = latest_annotations(export_obj, overview_obj)
    submitted_count = len(submitted)
    if submitted_count != args.expected_submitted_count and not args.allow_submitted_subset:
        raise SystemExit(
            f"Submitted annotation count is {submitted_count}, expected {args.expected_submitted_count}. "
            "Use --allow-submitted-subset only if this is intentionally a submitted-subset run."
        )
    change_audit = write_annotation_change_tracking(output_root, submitted, args.previous_run_root)

    selected, skipped_missing_scores = build_selection(
        submitted,
        row_index,
        overview_meta,
        include_missing_score_charts=args.include_missing_score_charts,
    )
    if len(selected) < args.min_analysis_count:
        raise SystemExit(f"Only {len(selected)} analysis charts selected; minimum is {args.min_analysis_count}.")

    if args.copy_export:
        shutil.copy2(args.export_path, output_root / "inputs" / args.export_path.name)

    input_manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "run_id": args.run_id,
        "purpose": "Group 2 formal/submitted evidence-source analysis. No model rerun.",
        "inputs": {
            "shujuji_export": {"path": str(args.export_path), "sha256": sha256_or_none(args.export_path)},
            "admin_overview": {"path": str(args.overview_path), "sha256": sha256_or_none(args.overview_path)},
            "group1_scoring_equivalence_v2": {"path": str(group1_run)},
            "field_targets_chart_display_v2": {"path": str(base.FIELD_TARGETS), "sha256": sha256_or_none(base.FIELD_TARGETS)},
            "comparison_policy_v2": {"path": str(base.COMPARISON_POLICY), "sha256": sha256_or_none(base.COMPARISON_POLICY)},
        },
        "selection_policy": {
            "expected_submitted_count": args.expected_submitted_count,
            "allow_submitted_subset": args.allow_submitted_subset,
            "include_missing_score_charts": args.include_missing_score_charts,
            "expected_analysis_count": args.expected_analysis_count,
        },
        "constraints": [
            "No OCR/LLM/VLM rerun.",
            "Use submitted/final annotations only.",
            "Use narrowed scoring-equivalence v2 targets and policies.",
            "Direct-Q4 completion only fills same-chart, same-leg direct-to evidence.",
            "not_applicable fields are analyzed as applicability negatives, not evidence-source positives.",
            "leg_count is a size control, not an evidence-source field.",
        ],
        "method_sources": [{"source_method": s, "method": label} for s, label in base.METHOD_SOURCES],
    }
    write_json(output_root / "inputs" / "input_manifest.json", input_manifest)

    write_jsonl(output_root / "selection" / "submitted_manifest.jsonl", [
        {
            "chart_id": (entry.get("data") or {}).get("chart_id"),
            "saved_at": (entry.get("data") or {}).get("saved_at"),
            "annotator": (entry.get("data") or {}).get("annotator"),
            "relative_path": entry.get("relative_path"),
            "row_index": row_index.get((entry.get("data") or {}).get("chart_id")),
        }
        for entry in submitted
    ])
    write_jsonl(output_root / "selection" / "analysis_manifest.jsonl", selected)
    write_jsonl(output_root / "selection" / "skipped_missing_group1_scores.jsonl", skipped_missing_scores)
    write_jsonl(output_root / "selection" / "excluded_annotations.jsonl", excluded_annotations)

    original_evidence, evidence_review_queue = base.build_evidence(selected, by_chart)
    added_direct_q4, skipped_direct_q4 = q4fix.build_direct_q4_rows(selected, by_chart, original_evidence, field_targets)
    fixed_evidence = sorted(
        original_evidence + added_direct_q4,
        key=lambda r: (r["chart_id"], str(r["canonical_leg_index"]), r["field_name"], r.get("source_schema", "")),
    )

    chart_scores, field_scores = base.build_score_indices(selected)
    joined, unmatched_scores, unmatched_evidence = base.join_group2(field_scores, fixed_evidence)
    split = split_group2_rows(joined)
    tables = write_group2_tables(output_root, split)

    write_jsonl(output_root / "group2" / "evidence_provenance.jsonl", fixed_evidence)
    write_jsonl(output_root / "group2" / "evidence_review_queue.jsonl", evidence_review_queue)
    write_jsonl(output_root / "group2" / "direct_q4_added_evidence.jsonl", added_direct_q4)
    write_jsonl(output_root / "group2" / "direct_q4_skipped_evidence.jsonl", skipped_direct_q4)
    write_jsonl(output_root / "group1_chart_scores.jsonl", chart_scores)
    write_jsonl(output_root / "group1_field_scores.jsonl", field_scores)
    write_jsonl(output_root / "group2" / "joined_field_scores.jsonl", joined)
    write_jsonl(output_root / "group2" / "unmatched_score_fields.jsonl", unmatched_scores)
    write_jsonl(output_root / "group2" / "unmatched_evidence_fields.jsonl", unmatched_evidence)
    write_jsonl(output_root / "group2" / "positive_joined_field_scores.jsonl", split["positive"])
    write_jsonl(output_root / "group2" / "positive_question_fallback.jsonl", split["positive_question_fallback"])
    write_jsonl(output_root / "group2" / "size_control_present.jsonl", split["size_control_present"])
    write_jsonl(output_root / "group2" / "negative_not_applicable.jsonl", split["negative"])
    write_jsonl(output_root / "group2" / "diagnostic_fields.jsonl", split["diagnostic"])
    write_jsonl(output_root / "group2" / "unmatched_present_fields.jsonl", split["unmatched_present"])
    write_jsonl(output_root / "group2" / "unmatched_not_applicable_fields.jsonl", split["unmatched_not_applicable"])
    write_jsonl(output_root / "group2" / "evidence_on_not_applicable_audit.jsonl", split["evidence_on_negative"])

    missing_method_chart_counts = Counter(
        method for item in submitted for method in item.get("missing_group1_methods", [])
    )
    audit = {
        "run_id": args.run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "submitted_annotation_count": submitted_count,
        "expected_submitted_count": args.expected_submitted_count,
        "analysis_chart_count": len(selected),
        "expected_analysis_count": args.expected_analysis_count,
        "min_analysis_count": args.min_analysis_count,
        "skipped_missing_group1_score_chart_count": len(skipped_missing_scores),
        "excluded_annotation_count": len(excluded_annotations),
        "original_evidence_rows": len(original_evidence),
        "fixed_evidence_rows": len(fixed_evidence),
        "added_direct_q4_evidence_rows": len(added_direct_q4),
        "added_direct_q4_rule_counts": Counter(row.get("derived_rule") for row in added_direct_q4),
        "field_score_rows": len(field_scores),
        "chart_score_rows": len(chart_scores),
        "joined_rows": len(joined),
        "unmatched_score_rows": len(unmatched_scores),
        "unmatched_evidence_rows": len(unmatched_evidence),
        "positive_present_strict_evidence_rows": len(split["positive"]),
        "positive_question_fallback_rows": len(split["positive_question_fallback"]),
        "size_control_present_rows": len(split["size_control_present"]),
        "negative_not_applicable_rows": len(split["negative"]),
        "diagnostic_rows": len(split["diagnostic"]),
        "unmatched_present_rows": len(split["unmatched_present"]),
        "unmatched_not_applicable_rows": len(split["unmatched_not_applicable"]),
        "evidence_on_not_applicable_rows": len(split["evidence_on_negative"]),
        "missing_group1_method_chart_counts": missing_method_chart_counts,
        "positive_evidence_bucket_counts": Counter(row.get("evidence_evidence_bucket") for row in split["positive"]),
        "negative_error_type_counts": Counter(row.get("negative_error_type") for row in split["negative"]),
        "output_root": str(output_root),
        "annotation_change_audit": change_audit,
    }
    warnings = []
    if args.expected_submitted_count < 300:
        warnings.append("this run intentionally uses a submitted subset; do not label it formal300")
    if audit["skipped_missing_group1_score_chart_count"] > 0:
        warnings.append("some submitted charts were excluded from the paired main table because at least one Group 1 method score file is missing")
    if args.include_missing_score_charts:
        warnings.append("available-score mode uses unequal per-method denominators; do not use it as paired method comparison")
    if change_audit.get("has_previous_snapshot") and change_audit.get("changed_chart_count", 0) > 0:
        warnings.append("annotation changes were detected relative to the previous run; review annotation_changed_* files")
    blockers = hard_blockers(audit)
    audit["warnings"] = warnings
    audit["hard_blockers"] = blockers
    audit["ready_for_group2_main_claim"] = not blockers
    write_json(output_root / "group2" / "group2_formal_submitted_v1_audit.json", audit)
    write_json(output_root / "selection" / "selection_audit.json", {
        "submitted_annotation_count": submitted_count,
        "analysis_chart_count": len(selected),
        "skipped_missing_group1_score_chart_count": len(skipped_missing_scores),
        "selected_chart_ids": [row["chart_id"] for row in selected],
        "skipped_missing_group1_scores": skipped_missing_scores,
        "excluded_annotations": excluded_annotations,
    })

    report = [
        "# 实验组2正式/已提交标注分析报告",
        "",
        f"生成时间：{audit['created_at']}",
        f"Run ID：`{args.run_id}`",
        "",
        "## 输入与口径",
        "",
        f"- 人工提交标注：{submitted_count} / {args.expected_submitted_count}",
        f"- 进入分析的航图：{len(selected)}",
        f"- 因 Group1 方法分数不完整跳过：{len(skipped_missing_scores)}",
        "- 没有重新跑模型；只读取已提交人工标注、Group1 scoring-equivalence v2 字段分数和 v2 target/policy。",
        "- `not_applicable` 字段只用于乱填/over-assertion 分析，不进入正类证据来源主表。",
        "- `leg_count` 只作为规模控制变量，不进入证据来源主表。",
        f"- 标注快照变更图数：{change_audit.get('changed_chart_count', 0)}",
        "",
        "## 关键审计",
        "",
        f"- 原字段级证据行：{len(original_evidence)}",
        f"- direct-Q4 同航段补证据后字段级证据行：{len(fixed_evidence)}",
        f"- 新增 direct-Q4 证据行：{len(added_direct_q4)}",
        f"- 正类主表行：{len(split['positive'])}",
        f"- 跨航段/同字段 fallback 行：{len(split['positive_question_fallback'])}",
        f"- 应填写但无同航段证据行：{len(split['unmatched_present'])}",
        f"- 不适用字段行：{len(split['negative'])}",
        f"- 不适用字段挂证据审计行：{len(split['evidence_on_negative'])}",
        "",
    ]
    if warnings:
        report.extend([
            "## 警告",
            "",
            *[f"- {item}" for item in warnings],
            "",
        ])
    report.extend([
        "## Main Table: method × evidence bucket",
        "",
        table_md(tables["positive_evidence_bucket"], ["method", "evidence_evidence_bucket", "correct", "total", "accuracy"], max_rows=120),
        "## Negative Boundary: method × error type",
        "",
        table_md(tables["not_applicable_error_type"], ["method", "negative_error_type", "correct", "total", "accuracy"], max_rows=120),
        "## 结论状态",
        "",
    ])
    if blockers:
        report.extend([
            "当前不能直接写成实验组2正式主结论，原因：",
            "",
            *[f"- {item}" for item in blockers],
            "",
            "先处理上述审计项，再冻结正式结论。",
        ])
    else:
        report.extend([
            "审计项没有发现阻塞性问题，可以进入实验组2主结论撰写阶段。",
            "",
            "仍建议在论文正文中报告 direct-Q4 同航段补证据规则和不适用字段负类口径。",
        ])
    (output_root / "group2" / "reports" / "group2_formal_submitted_v1_report_zh.md").write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    summary = {
        "run_id": args.run_id,
        "output_root": str(output_root),
        "submitted_annotation_count": submitted_count,
        "analysis_chart_count": len(selected),
        "positive_present_strict_evidence_rows": len(split["positive"]),
        "positive_question_fallback_rows": len(split["positive_question_fallback"]),
        "unmatched_present_rows": len(split["unmatched_present"]),
        "ready_for_group2_main_claim": not blockers,
        "hard_blockers": blockers,
        "annotation_change_audit": str(output_root / "inputs" / "annotation_change_audit.json"),
        "report": str(output_root / "group2" / "reports" / "group2_formal_submitted_v1_report_zh.md"),
        "audit": str(output_root / "group2" / "group2_formal_submitted_v1_audit.json"),
    }
    write_json(output_root / "reports" / "run_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
