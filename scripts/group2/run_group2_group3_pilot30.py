import csv
import hashlib
import json
import os
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


EXPERIMENT_ROOT = Path(os.environ.get("EXPERIMENT3_ROOT", r"E:\experiment3"))
REPO_ROOT = Path(
    os.environ.get(
        "FAA_BENCH_REPO",
        str(EXPERIMENT_ROOT / "github_work" / "faa-chart-to-424-benchmark"),
    )
)
ROOT = Path(os.environ.get("GROUP23_ROOT", str(EXPERIMENT_ROOT / "zu2+3")))
EXPORT_PATH = Path(
    os.environ.get(
        "GROUP2_EXPORT_PATH",
        str(
            EXPERIMENT_ROOT
            / "group2_annotation_status_20260502"
            / "shujuji_annotation_export_2026-05-02T07-17-55-090Z.json"
        ),
    )
)
OVERVIEW_PATH = Path(
    os.environ.get(
        "GROUP2_OVERVIEW_PATH",
        str(EXPERIMENT_ROOT / "group2_annotation_status_20260502" / "admin_overview_formal300.json"),
    )
)
GROUP1_RUN = Path(
    os.environ.get(
        "GROUP1_RUN",
        str(
            REPO_ROOT
            / "formal_runs"
            / "group1"
            / "group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2"
        ),
    )
)
TARGET_DIR = Path(
    os.environ.get(
        "GROUP2_TARGET_DIR",
        str(REPO_ROOT / "benchmark_exports" / "derived" / "v2" / "formal300" / "targets" / "scoring_equivalence_v2"),
    )
)
FIELD_TARGETS = TARGET_DIR / "field_targets_chart_display_v2.jsonl"
COMPARISON_POLICY = TARGET_DIR / "comparison_policy_v2.jsonl"
FORMAL_MANIFEST = Path(
    os.environ.get(
        "GROUP2_FORMAL_MANIFEST",
        str(REPO_ROOT / "benchmark_exports" / "derived" / "v2" / "formal300" / "manifest.json"),
    )
)
EXISTING_CHALLENGE_TAGS = Path(
    os.environ.get(
        "GROUP2_CHALLENGE_TAGS",
        str(REPO_ROOT / "benchmark_exports" / "derived" / "v2" / "formal300" / "challenge_tags.jsonl"),
    )
)

METHOD_SOURCES = [
    ("A1", "A1"),
    ("A2", "A2"),
    ("B1", "B1"),
    ("B1_prime", "B1_prime"),
    ("B1_prime_link", "B1_prime_link"),
    ("C1", "C1"),
    ("C2", "C2"),
    ("C3", "C3"),
    ("C4", "C4"),
    ("D_SFT", "D1"),
]


def ensure_dirs():
    for sub in [
        "inputs/shujuji_export",
        "inputs/group1_score_refs",
        "selection",
        "group2/reports",
        "group3/reports",
        "scripts",
        "reports",
    ]:
        (ROOT / sub).mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path):
    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def flatten_field_key(leg_index, field_name):
    if field_name == "leg_count" or leg_index is None:
        return "leg_count"
    return f"leg_{leg_index}.{field_name}"


def field_path_from_key(leg_index, field_name):
    if field_name == "leg_count" or leg_index is None:
        return "missed_approach.leg_count"
    return f"missed_approach.legs[{leg_index}].answers.{field_name}"


def field_family(field_name):
    if field_name == "leg_count":
        return "航段数量"
    if field_name == "Q_terminator":
        return "path terminator"
    if field_name == "Q1_fix_ident":
        return "fix / navaid"
    if field_name == "Q2_altitude_constraint":
        return "高度"
    if field_name == "Q3_turn":
        return "转弯"
    if field_name == "Q4_course_or_radial":
        return "course / radial"
    if field_name == "Q5_hold_params":
        return "holding"
    return "其他"


def normalize_source(source):
    if source is None:
        return []
    if isinstance(source, list):
        return [str(x) for x in source if x]
    return [str(source)]


def evidence_bucket(support_mode, evidence_source):
    sources = set(normalize_source(evidence_source))
    if support_mode in {"pending", "uncertain", "insufficient_for_encoding", "rule_default_completion", "visible_joint"}:
        return {
            "pending": "未完成",
            "uncertain": "不确定",
            "insufficient_for_encoding": "图上证据不足",
            "rule_default_completion": "规则或默认补全",
            "visible_joint": "多证据共同支持",
        }[support_mode]
    if support_mode == "direct_visible":
        if "ma_text" in sources:
            return "文本直接证据"
        if "plan_view" in sources:
            return "平面图直接证据"
        if sources & {"chart_text", "detail_area", "detail", "icon", "icon_area", "small_box"}:
            return "下方细节区或图中文字证据"
        return "其他直接证据"
    if not support_mode:
        return "未标注support_mode"
    return f"其他:{support_mode}"


def error_type(row):
    if row.get("correct"):
        return "correct"
    field = row.get("question_field") or ""
    pred = row.get("pred") or {}
    target = row.get("target") or {}
    pred_status = pred.get("status")
    target_status = target.get("status")
    policy = row.get("match_policy") or ""
    if field == "leg_count":
        return "wrong_leg_count"
    if field == "Q_terminator":
        return "terminator_error"
    if target_status == "present" and pred_status in {"unknown", "not_applicable", None}:
        return "missing_present_field"
    if target_status in {"not_applicable", "unknown", None} and pred_status == "present":
        return "over_assertion"
    if "status_mismatch" in policy:
        return "wrong_status"
    return "wrong_value"


def load_score_rows(method_source, chart_id):
    score_path = GROUP1_RUN / method_source / "scores" / f"{chart_id}.json"
    if not score_path.exists():
        return None
    score = load_json(score_path)
    return score


def load_method_summary(method_source):
    path = GROUP1_RUN / method_source / "method_summary.json"
    if not path.exists():
        return {}
    return load_json(path)


def choose_pilot30(export_obj, overview_obj):
    formal = export_obj["datasets"]["formal300"]
    by_annotator = formal["annotations"]["by_annotator"]
    by_chart = {}
    for entry in by_annotator:
        data = entry.get("data") or {}
        chart_id = data.get("chart_id")
        if not chart_id:
            continue
        prev = by_chart.get(chart_id)
        if prev is None or str(data.get("saved_at", "")) > str((prev.get("data") or {}).get("saved_at", "")):
            by_chart[chart_id] = entry

    overview_rows = (overview_obj.get("dataset") or {}).get("rows") or []
    row_index = {row.get("chart_id"): row.get("row_index", 999999) for row in overview_rows}
    overview_meta = {row.get("chart_id"): row for row in overview_rows}
    submitted = sorted(by_chart.values(), key=lambda e: (row_index.get((e.get("data") or {}).get("chart_id"), 999999), (e.get("data") or {}).get("chart_id", "")))

    selected = []
    spare = []
    excluded = []
    for entry in submitted:
        data = entry.get("data") or {}
        chart_id = data.get("chart_id")
        missing_methods = [
            label for source, label in METHOD_SOURCES
            if not (GROUP1_RUN / source / "scores" / f"{chart_id}.json").exists()
        ]
        item = {
            "chart_id": chart_id,
            "row_index": row_index.get(chart_id),
            "annotator": data.get("annotator"),
            "saved_at": data.get("saved_at"),
            "relative_path": entry.get("relative_path"),
            "field_review_count": len(data.get("field_reviews") or []),
            "missing_group1_methods": missing_methods,
            "airport": overview_meta.get(chart_id, {}).get("airport", ""),
            "proc_ident": overview_meta.get(chart_id, {}).get("proc_ident", ""),
            "chart_name": overview_meta.get(chart_id, {}).get("chart_name", ""),
            "kind": overview_meta.get(chart_id, {}).get("kind", ""),
        }
        item["has_all_group1_method_scores"] = not missing_methods
        if len(selected) < 30:
            selected.append(item)
        else:
            spare.append(item)
    if len(selected) < 30:
        raise RuntimeError(f"Only {len(selected)} submitted charts are available.")
    return selected, spare, excluded, by_chart


def build_evidence(selected, by_chart):
    selected_ids = {item["chart_id"] for item in selected}
    rows = []
    review_queue = []
    for chart_id in selected_ids:
        data = (by_chart[chart_id].get("data") or {})
        for review in data.get("field_reviews") or []:
            field_name = review.get("field_name")
            leg_index = review.get("canonical_leg_index")
            support = review.get("support_mode") or review.get("review_status") or ""
            sources = normalize_source(review.get("evidence_source") or review.get("checked_sources"))
            required = review.get("required_evidence_region_ids") or []
            secondary = review.get("secondary_evidence_region_ids") or []
            evidence_ids = review.get("evidence_region_ids") or list(dict.fromkeys(required + secondary))
            checked = review.get("checked_scopes") or review.get("checked_sources") or []
            leg_type = review.get("leg_type")
            score_field = flatten_field_key(leg_index, field_name)
            bucket = evidence_bucket(support, sources)
            semantic_tags = []
            if field_name == "Q_terminator" or leg_type in {"CA", "DF", "HM"}:
                semantic_tags.append("424编码语义字段")
            row = {
                "chart_id": chart_id,
                "field_key": review.get("field_key") or score_field,
                "score_field": score_field,
                "field_path": field_path_from_key(leg_index, field_name),
                "canonical_leg_index": leg_index,
                "field_name": field_name,
                "question_field": field_name,
                "field_family": field_family(field_name),
                "leg_type": leg_type,
                "canonical_answer": review.get("canonical_answer"),
                "support_mode": support,
                "review_status": review.get("review_status"),
                "evidence_source": sources,
                "evidence_bucket": bucket,
                "semantic_tags": semantic_tags,
                "evidence_region_ids": evidence_ids,
                "required_evidence_region_ids": required,
                "secondary_evidence_region_ids": secondary,
                "evidence_count": len(set(map(str, evidence_ids))),
                "checked_scopes": checked,
                "checked_scope_count": len(set(map(str, checked))),
                "reviewed_by": review.get("reviewed_by") or data.get("annotator"),
                "reviewed_at": review.get("reviewed_at"),
                "annotation_saved_at": data.get("saved_at"),
                "source_schema": review.get("schema"),
            }
            rows.append(row)
            reasons = []
            if support in {"uncertain", "insufficient_for_encoding", "rule_default_completion", "pending"}:
                reasons.append(f"support_mode={support}")
            if field_name == "Q_terminator":
                reasons.append("Q_terminator")
            if leg_type in {"CA", "DF", "HM"}:
                reasons.append(f"leg_type={leg_type}")
            if not evidence_ids:
                reasons.append("missing_evidence_region_ids")
            if not checked:
                reasons.append("missing_checked_scopes")
            if reasons:
                review_queue.append({**row, "review_reasons": reasons})
    return sorted(rows, key=lambda r: (r["chart_id"], str(r["canonical_leg_index"]), r["field_name"])), review_queue


def build_score_indices(selected):
    selected_ids = {x["chart_id"] for x in selected}
    chart_scores = []
    field_scores = []
    for source, label in METHOD_SOURCES:
        summary = load_method_summary(source)
        result_by_chart = {r.get("chart_id"): r for r in summary.get("results", [])}
        for chart_id in sorted(selected_ids):
            score = load_score_rows(source, chart_id)
            result = result_by_chart.get(chart_id, {})
            if score is None:
                chart_scores.append({
                    "method": label,
                    "source_method": source,
                    "chart_id": chart_id,
                    "score_available": False,
                    "schema_valid": False,
                    "method_failure": True,
                    "correct": 0,
                    "total": 0,
                    "accuracy": None,
                })
                continue
            chart_scores.append({
                "method": label,
                "source_method": source,
                "chart_id": chart_id,
                "score_available": True,
                "schema_valid": result.get("schema_valid", True),
                "validation_error_count": result.get("validation_error_count", 0),
                "method_failure": not result.get("schema_valid", True),
                "correct": score.get("correct"),
                "total": score.get("total"),
                "accuracy": score.get("accuracy"),
                "comparison_policy": score.get("comparison_policy"),
            })
            for r in score.get("rows") or []:
                field_scores.append({
                    "method": label,
                    "source_method": source,
                    "chart_id": chart_id,
                    "score_field": r.get("field"),
                    "question_field": r.get("question_field"),
                    "field_family": field_family(r.get("question_field")),
                    "correct": bool(r.get("correct")),
                    "strict_correct": bool(r.get("strict_correct")),
                    "v2_corrected": bool(r.get("correct")) and not bool(r.get("strict_correct")),
                    "match_policy": r.get("match_policy"),
                    "pred": r.get("pred"),
                    "target": r.get("target"),
                    "error_type": error_type(r),
                })
    return chart_scores, field_scores


def join_group2(field_scores, evidence_rows):
    evidence_by_key = {(r["chart_id"], r["score_field"]): r for r in evidence_rows}
    joined = []
    unmatched_scores = []
    matched_keys = set()
    for row in field_scores:
        key = (row["chart_id"], row["score_field"])
        ev = evidence_by_key.get(key)
        if ev:
            matched_keys.add(key)
            joined.append({**row, **{f"evidence_{k}": v for k, v in ev.items() if k not in {"chart_id", "score_field"}}})
        else:
            out = {**row, "unmatched_reason": "no_field_review_for_score_field"}
            unmatched_scores.append(out)
            joined.append(out)
    unmatched_evidence = [
        {**r, "unmatched_reason": "no_group1_score_field"}
        for r in evidence_rows
        if (r["chart_id"], r["score_field"]) not in matched_keys
    ]
    return joined, unmatched_scores, unmatched_evidence


def aggregate(rows, dims, correct_key="correct", total_filter=None):
    stats = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in rows:
        if total_filter and not total_filter(r):
            continue
        key = tuple(r.get(d, "") for d in dims)
        stats[key]["total"] += 1
        if r.get(correct_key):
            stats[key]["correct"] += 1
    out = []
    for key, val in sorted(stats.items()):
        row = {dim: key[i] for i, dim in enumerate(dims)}
        row.update(val)
        row["accuracy"] = val["correct"] / val["total"] if val["total"] else None
        out.append(row)
    return out


def aggregate_score_counts(rows, dims, total_filter=None):
    stats = defaultdict(lambda: {"correct": 0, "total": 0, "row_count": 0})
    for r in rows:
        if total_filter and not total_filter(r):
            continue
        if not r.get("score_available", True):
            continue
        total = r.get("total") or 0
        correct = r.get("correct") or 0
        if total <= 0:
            continue
        key = tuple(r.get(d, "") for d in dims)
        stats[key]["total"] += total
        stats[key]["correct"] += correct
        stats[key]["row_count"] += 1
    out = []
    for key, val in sorted(stats.items()):
        row = {dim: key[i] for i, dim in enumerate(dims)}
        row.update(val)
        row["accuracy"] = val["correct"] / val["total"] if val["total"] else None
        out.append(row)
    return out


def build_group2_tables(joined):
    has_ev = lambda r: bool(r.get("evidence_evidence_bucket"))
    return {
        "evidence_bucket": aggregate(joined, ["method", "evidence_evidence_bucket"], total_filter=has_ev),
        "support_mode": aggregate(joined, ["method", "evidence_support_mode"], total_filter=has_ev),
        "field_family": aggregate(joined, ["method", "field_family"]),
        "error_type": aggregate(joined, ["method", "error_type"]),
        "v2_delta": aggregate(joined, ["method", "v2_corrected"]),
    }


def build_group3_tags(selected, evidence_rows, field_targets):
    selected_ids = {x["chart_id"] for x in selected}
    targets_by_chart = defaultdict(list)
    for row in field_targets:
        if row.get("chart_id") in selected_ids:
            targets_by_chart[row["chart_id"]].append(row)

    evidence_by_chart = defaultdict(list)
    for row in evidence_rows:
        evidence_by_chart[row["chart_id"]].append(row)

    out = []
    review_queue = []
    core_tags = {
        "has_ca_leg",
        "has_hm_leg",
        "ca_df_sequence",
        "multi_leg_complex",
        "implicit_hold_time",
        "plan_profile_only_holding",
        "text_missing_visual_present",
        "rule_default_completion_case",
    }
    for item in selected:
        chart_id = item["chart_id"]
        tags = set()
        tag_sources = {}
        terminators = []
        for row in targets_by_chart[chart_id]:
            q = row.get("question_field")
            target = row.get("target") or {}
            status = target.get("status")
            value = target.get("value")
            leg_index = row.get("leg_index")
            if q == "leg_count" and status == "present":
                try:
                    if int(value) >= 4:
                        tags.add("multi_leg_complex")
                        tag_sources["multi_leg_complex"] = "target_derived"
                    tags.add(f"leg_count:{int(value)}")
                    tag_sources[f"leg_count:{int(value)}"] = "target_derived"
                except Exception:
                    pass
            if q == "Q_terminator" and status == "present":
                tags.add("terminator_derived")
                tag_sources["terminator_derived"] = "target_derived"
                terminators.append((leg_index, value))
                if value == "CA":
                    tags.add("has_ca_leg")
                    tag_sources["has_ca_leg"] = "target_derived"
                if value == "HM":
                    tags.add("has_hm_leg")
                    tag_sources["has_hm_leg"] = "target_derived"
            if q == "Q5_hold_params" and status == "present":
                tags.add("has_holding")
                tag_sources["has_holding"] = "target_derived"
            if q == "Q4_course_or_radial" and status == "present":
                tags.add("has_course_radial")
                tag_sources["has_course_radial"] = "target_derived"
            if q == "Q2_altitude_constraint" and status == "present":
                tags.add("has_altitude_constraint")
                tag_sources["has_altitude_constraint"] = "target_derived"
        ordered_terms = [v for _, v in sorted((i, v) for i, v in terminators if i is not None)]
        for a, b in zip(ordered_terms, ordered_terms[1:]):
            if a == "CA" and b == "DF":
                tags.add("ca_df_sequence")
                tag_sources["ca_df_sequence"] = "target_derived"

        evs = evidence_by_chart[chart_id]
        if any(e["support_mode"] == "rule_default_completion" and e["field_name"] == "Q5_hold_params" for e in evs):
            tags.add("implicit_hold_time")
            tag_sources["implicit_hold_time"] = "evidence_derived_needs_review"
        if any(e["field_name"] == "Q5_hold_params" and set(e["evidence_source"]) == {"plan_view"} for e in evs):
            tags.add("plan_profile_only_holding")
            tag_sources["plan_profile_only_holding"] = "evidence_derived_needs_review"
        if any(e["support_mode"] in {"direct_visible", "visible_joint"} and "ma_text" not in set(e["evidence_source"]) for e in evs):
            tags.add("text_missing_visual_present")
            tag_sources["text_missing_visual_present"] = "evidence_derived_needs_review"
        if any(e["support_mode"] == "visible_joint" for e in evs):
            tags.add("cross_modal_required")
            tag_sources["cross_modal_required"] = "evidence_derived"
        if any(e["support_mode"] == "insufficient_for_encoding" for e in evs):
            tags.add("insufficient_for_encoding_case")
            tag_sources["insufficient_for_encoding_case"] = "evidence_derived_needs_review"
        if any(e["support_mode"] == "rule_default_completion" for e in evs):
            tags.add("rule_default_completion_case")
            tag_sources["rule_default_completion_case"] = "evidence_derived_needs_review"
        if any(e["support_mode"] == "uncertain" for e in evs):
            tags.add("uncertain_case")
            tag_sources["uncertain_case"] = "evidence_derived_exclude_main"

        hit_core = sorted(tags & core_tags)
        challenge_level = len(hit_core)
        review_status = "auto_pilot_needs_review" if any("needs_review" in src for src in tag_sources.values()) else "auto_pilot"
        row = {
            "chart_id": chart_id,
            "dataset_split": "pilot30",
            "challenge_tags": sorted(tags),
            "core_challenge_tags": hit_core,
            "is_challenge": bool(hit_core),
            "challenge_level": challenge_level,
            "tag_sources": tag_sources,
            "review_status": review_status,
        }
        out.append(row)
        if review_status == "auto_pilot_needs_review" or "uncertain_case" in tags:
            review_queue.append(row)
    return out, review_queue


def join_group3(chart_scores, field_scores, tags):
    tags_by_chart = {r["chart_id"]: r for r in tags}
    chart_joined = []
    for r in chart_scores:
        tag = tags_by_chart.get(r["chart_id"], {})
        chart_joined.append({**r, **{k: v for k, v in tag.items() if k != "chart_id"}})
    field_joined = []
    for r in field_scores:
        tag = tags_by_chart.get(r["chart_id"], {})
        field_joined.append({**r, **{k: v for k, v in tag.items() if k != "chart_id"}})
    return chart_joined, field_joined


def group3_tables(chart_joined, field_joined):
    core_rows = []
    for r in chart_joined:
        group = "challenge" if r.get("is_challenge") else "core"
        core_rows.append({**r, "core_or_challenge": group})

    by_tag_source = []
    for r in chart_joined:
        for tag in r.get("challenge_tags") or []:
            by_tag_source.append({**r, "challenge_tag": tag})

    by_level = [{**r, "challenge_level_label": str(r.get("challenge_level", 0))} for r in chart_joined]

    field_by_tag = []
    for r in field_joined:
        for tag in r.get("challenge_tags") or []:
            field_by_tag.append({**r, "challenge_tag": tag})

    return {
        "core_vs_challenge": aggregate_score_counts(core_rows, ["method", "core_or_challenge"]),
        "by_tag": aggregate_score_counts(by_tag_source, ["method", "challenge_tag"]),
        "by_level": aggregate_score_counts(by_level, ["method", "challenge_level_label"]),
        "tag_field_family": aggregate(field_by_tag, ["method", "challenge_tag", "field_family"]),
        "tag_error_type": aggregate(field_by_tag, ["method", "challenge_tag", "error_type"]),
    }


def pct(x):
    if x is None:
        return ""
    return f"{x * 100:.2f}%"


def table_md(rows, columns):
    if not rows:
        return "_无数据_\n"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        vals = []
        for c in columns:
            v = row.get(c, "")
            if c == "accuracy" and isinstance(v, (int, float)):
                v = pct(v)
            vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def main():
    ensure_dirs()
    export_obj = load_json(EXPORT_PATH)
    overview_obj = load_json(OVERVIEW_PATH)
    field_targets = list(read_jsonl(FIELD_TARGETS))

    shutil.copy2(EXPORT_PATH, ROOT / "inputs" / "shujuji_export" / EXPORT_PATH.name)

    input_manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "run_id": "group2_group3_pilot30_20260502",
        "purpose": "Run Group 2 and Group 3 pilot on 30 submitted formal annotations.",
        "inputs": {
            "shujuji_export": {"path": str(EXPORT_PATH), "sha256": sha256_file(EXPORT_PATH)},
            "admin_overview": {"path": str(OVERVIEW_PATH), "sha256": sha256_file(OVERVIEW_PATH)},
            "group1_scoring_equivalence_v2": {"path": str(GROUP1_RUN)},
            "field_targets_chart_display_v2": {"path": str(FIELD_TARGETS), "sha256": sha256_file(FIELD_TARGETS)},
            "comparison_policy_v2": {"path": str(COMPARISON_POLICY), "sha256": sha256_file(COMPARISON_POLICY)},
            "formal_manifest": {"path": str(FORMAL_MANIFEST), "sha256": sha256_file(FORMAL_MANIFEST) if FORMAL_MANIFEST.exists() else None},
        },
        "method_sources": [{"source_method": s, "method": l} for s, l in METHOD_SOURCES],
        "constraints": [
            "No model rerun.",
            "Use submitted/final annotations only; drafts excluded from main analysis.",
            "Use PR #25 narrowed scoring-equivalence v2.",
            "pilot30 is pipeline validation, not formal300 conclusion.",
        ],
    }
    write_json(ROOT / "inputs" / "input_manifest.json", input_manifest)

    selected, spare, excluded, by_chart = choose_pilot30(export_obj, overview_obj)
    write_jsonl(ROOT / "selection" / "pilot30_manifest.jsonl", selected)
    write_json(ROOT / "selection" / "pilot30_selection_audit.json", {
        "selected_count": len(selected),
        "spare_count": len(spare),
        "excluded_count": len(excluded),
        "selected_with_all_group1_method_scores": sum(1 for x in selected if x.get("has_all_group1_method_scores")),
        "selected_with_missing_group1_method_scores": sum(1 for x in selected if not x.get("has_all_group1_method_scores")),
        "selected_chart_ids": [x["chart_id"] for x in selected],
        "spare_chart_ids": [x["chart_id"] for x in spare],
        "excluded": excluded,
    })

    evidence_rows, evidence_review_queue = build_evidence(selected, by_chart)
    write_jsonl(ROOT / "group2" / "evidence_provenance_pilot30.jsonl", evidence_rows)
    write_jsonl(ROOT / "group2" / "evidence_review_queue_pilot30.jsonl", evidence_review_queue)
    evidence_summary = {
        "chart_count": len(selected),
        "field_review_rows": len(evidence_rows),
        "review_queue_rows": len(evidence_review_queue),
        "support_mode_counts": Counter(r["support_mode"] for r in evidence_rows),
        "evidence_bucket_counts": Counter(r["evidence_bucket"] for r in evidence_rows),
        "field_family_counts": Counter(r["field_family"] for r in evidence_rows),
    }
    write_json(ROOT / "group2" / "evidence_provenance_pilot30_summary.json", evidence_summary)

    chart_scores, field_scores = build_score_indices(selected)
    write_jsonl(ROOT / "group1_field_scores_pilot30.jsonl", field_scores)
    write_jsonl(ROOT / "group1_chart_scores_pilot30.jsonl", chart_scores)

    group2_joined, unmatched_scores, unmatched_evidence = join_group2(field_scores, evidence_rows)
    write_jsonl(ROOT / "group2" / "group2_joined_field_scores_pilot30.jsonl", group2_joined)
    write_jsonl(ROOT / "group2" / "group2_unmatched_score_fields_pilot30.jsonl", unmatched_scores)
    write_jsonl(ROOT / "group2" / "group2_unmatched_evidence_fields_pilot30.jsonl", unmatched_evidence)
    group2_audit = {
        "score_field_rows": len(field_scores),
        "evidence_rows": len(evidence_rows),
        "joined_rows": len(group2_joined),
        "score_rows_with_evidence": sum(1 for r in group2_joined if r.get("evidence_evidence_bucket")),
        "unmatched_score_rows": len(unmatched_scores),
        "unmatched_evidence_rows": len(unmatched_evidence),
        "note": "Score rows include all scored fields, including not_applicable fields that are not always present in human field_reviews.",
    }
    write_json(ROOT / "group2" / "group2_join_audit_pilot30.json", group2_audit)

    g2_tables = build_group2_tables(group2_joined)
    for name, rows in g2_tables.items():
        write_csv(ROOT / "group2" / "reports" / f"group2_pilot30_{name}_table.csv", rows, list(rows[0].keys()) if rows else ["empty"])

    tags, tag_review_queue = build_group3_tags(selected, evidence_rows, field_targets)
    write_jsonl(ROOT / "group3" / "challenge_tags_pilot30.jsonl", tags)
    write_jsonl(ROOT / "group3" / "challenge_tag_review_queue_pilot30.jsonl", tag_review_queue)
    tag_audit = {
        "chart_count": len(tags),
        "review_queue_count": len(tag_review_queue),
        "tag_counts": Counter(tag for row in tags for tag in row["challenge_tags"]),
        "core_challenge_chart_count": sum(1 for row in tags if row["is_challenge"]),
        "core_chart_count": sum(1 for row in tags if not row["is_challenge"]),
    }
    write_json(ROOT / "group3" / "challenge_tag_audit_pilot30.json", tag_audit)

    group3_chart, group3_field = join_group3(chart_scores, field_scores, tags)
    write_jsonl(ROOT / "group3" / "group3_joined_chart_scores_pilot30.jsonl", group3_chart)
    write_jsonl(ROOT / "group3" / "group3_joined_field_scores_pilot30.jsonl", group3_field)
    g3_tables = group3_tables(group3_chart, group3_field)
    for name, rows in g3_tables.items():
        write_csv(ROOT / "group3" / "reports" / f"group3_pilot30_{name}_table.csv", rows, list(rows[0].keys()) if rows else ["empty"])

    selection_report = [
        "# pilot30 样本选择报告",
        "",
        f"生成时间：{datetime.now().isoformat(timespec='seconds')}",
        "",
        "## 选择规则",
        "",
        "- 仅使用 PR #18 admin export 中 formal300 的 submitted/final annotation。",
        "- 不使用 draft。",
        "- 按后台 overview row_index 排序，取前 30 张且要求实验组1全部方法均有 score 文件。",
        "- 不根据模型分数、字段正确率或难度选择样本。",
        "",
        "## 数量",
        "",
        f"- 已选：{len(selected)} 张",
        f"- spare：{len(spare)} 张",
        f"- 已选样本中实验组1全方法分数完整：{sum(1 for x in selected if x.get('has_all_group1_method_scores'))} 张",
        f"- 已选样本中缺少部分实验组1分数：{sum(1 for x in selected if not x.get('has_all_group1_method_scores'))} 张",
        "",
        "说明：当前 submitted/final annotation 只有 34 张，其中与实验组1 formal200 完全重合的不足 30 张。因此本次 pilot30 固定 30 张标注样本用于跑通 evidence/tag 链路；评分分析只统计已有实验组1 score 的图和字段，缺失项进入 audit。",
        "",
        "## 已选 chart_id",
        "",
        table_md(selected, ["row_index", "chart_id", "airport", "proc_ident", "chart_name", "annotator", "field_review_count"]),
    ]
    (ROOT / "selection" / "pilot30_selection_report_zh.md").write_text("\n".join(selection_report), encoding="utf-8")

    g2_report = [
        "# 实验组2 pilot30 报告",
        "",
        "本报告只用于验证字段证据来源分析流程，不作为 formal300 正式结论。",
        "",
        "## 运行摘要",
        "",
        f"- pilot charts：{len(selected)}",
        f"- evidence provenance rows：{len(evidence_rows)}",
        f"- score field rows：{len(field_scores)}",
        f"- score rows with evidence：{group2_audit['score_rows_with_evidence']}",
        f"- unmatched score rows：{len(unmatched_scores)}",
        f"- unmatched evidence rows：{len(unmatched_evidence)}",
        "",
        "未匹配 score row 很多是正常的：实验组1 scorer 包含 not_applicable 字段，而人工 field_reviews 不一定逐一标注所有 not_applicable 字段。",
        "",
        "## support_mode 分布",
        "",
        table_md([{"support_mode": k, "count": v} for k, v in evidence_summary["support_mode_counts"].items()], ["support_mode", "count"]),
        "## evidence_bucket 分布",
        "",
        table_md([{"evidence_bucket": k, "count": v} for k, v in evidence_summary["evidence_bucket_counts"].items()], ["evidence_bucket", "count"]),
        "## method × evidence_bucket",
        "",
        table_md(g2_tables["evidence_bucket"][:80], ["method", "evidence_evidence_bucket", "correct", "total", "accuracy"]),
        "## method × field_family",
        "",
        table_md(g2_tables["field_family"][:80], ["method", "field_family", "correct", "total", "accuracy"]),
        "## 审查重点",
        "",
        f"- evidence review queue：{len(evidence_review_queue)} 行，主要来自 rule_default_completion、Q_terminator、CA/DF/HM 等高风险字段。",
        "- 后续正式分析前，需要人工抽查 evidence_bucket 映射，尤其是 424 编码语义字段是否应该作为 overlay tag 而非覆盖证据来源。",
    ]
    (ROOT / "group2" / "reports" / "group2_pilot30_final_report_zh.md").write_text("\n".join(g2_report), encoding="utf-8")

    g3_report = [
        "# 实验组3 pilot30 报告",
        "",
        "本报告只用于验证普通样本与难例样本分析流程，不作为 formal300 正式结论。",
        "",
        "## 运行摘要",
        "",
        f"- pilot charts：{len(tags)}",
        f"- challenge charts：{tag_audit['core_challenge_chart_count']}",
        f"- core charts：{tag_audit['core_chart_count']}",
        f"- tag review queue：{len(tag_review_queue)}",
        "",
        "## challenge tag 分布",
        "",
        table_md([{"challenge_tag": k, "count": v} for k, v in sorted(tag_audit["tag_counts"].items())], ["challenge_tag", "count"]),
        "## method × core/challenge",
        "",
        table_md(g3_tables["core_vs_challenge"], ["method", "core_or_challenge", "correct", "total", "accuracy"]),
        "## method × challenge_tag",
        "",
        table_md(g3_tables["by_tag"][:120], ["method", "challenge_tag", "correct", "total", "accuracy"]),
        "## 审查重点",
        "",
        "- evidence-derived tags 是自动 pilot 标签，后续正式分析前需要人工复核。",
        "- challenge tag 生成没有使用模型正确/错误信息，满足不以后验错误定义难例的要求。",
    ]
    (ROOT / "group3" / "reports" / "group3_pilot30_final_report_zh.md").write_text("\n".join(g3_report), encoding="utf-8")

    execution_report = [
        "# 实验组2/3 pilot30 执行报告",
        "",
        f"生成时间：{datetime.now().isoformat(timespec='seconds')}",
        "",
        "## 已完成步骤",
        "",
        "1. 已建立输出目录和输入 manifest。",
        "2. 已从 34 张 submitted/final annotation 中固定 pilot30。",
        "3. 已生成实验组2 evidence provenance。",
        "4. 已将实验组2 evidence provenance 与实验组1字段级 score 合并。",
        "5. 已生成实验组2 pilot 表格。",
        "6. 已生成实验组3 target-derived 与 evidence-derived challenge tags。",
        "7. 已将实验组3 challenge tags 与实验组1图级/字段级 score 合并。",
        "8. 已生成实验组3 pilot 表格。",
        "",
        "## 关键数量",
        "",
        f"- pilot30 charts：{len(selected)}",
        f"- charts with all Group 1 method scores：{sum(1 for x in selected if x.get('has_all_group1_method_scores'))}",
        f"- charts missing some Group 1 method scores：{sum(1 for x in selected if not x.get('has_all_group1_method_scores'))}",
        f"- evidence rows：{len(evidence_rows)}",
        f"- evidence review queue rows：{len(evidence_review_queue)}",
        f"- field score rows：{len(field_scores)}",
        f"- group2 score rows with evidence：{group2_audit['score_rows_with_evidence']}",
        f"- group3 challenge charts：{tag_audit['core_challenge_chart_count']}",
        f"- group3 core charts：{tag_audit['core_chart_count']}",
        f"- group3 tag review queue rows：{len(tag_review_queue)}",
        "",
        "## 当前结论",
        "",
        "pilot30 数据链路已经跑通。当前结果只能说明实验组2/3的分析 pipeline 可行，不能作为 formal300 论文正式结论。",
        "",
        "重要限制：30 张标注样本中不是每张都落在实验组1 formal200 评分集合内。因此 evidence provenance 和 challenge tags 是 30 张，method score 分析按已有实验组1 score 的重合部分统计。",
        "",
        "## 后续需要审查",
        "",
        "1. PR #18 field_review 与实验组1 scorer 字段对齐是否需要更细的 mapping。",
        "2. not_applicable 字段是否需要人工 evidence provenance，或在实验组2主表中明确排除。",
        "3. evidence-derived challenge tags 是否经人工复核后才能进入主表。",
        "4. D1 在文件系统中的来源目录仍为 D_SFT，本次输出中 method 使用 D1，source_method 保留 D_SFT 以便追溯。",
        "5. 等更多标注完成后，扩展到全部已提交样本，再决定是否等待 formal300 全量。",
    ]
    (ROOT / "reports" / "pilot30_execution_report_zh.md").write_text("\n".join(execution_report), encoding="utf-8")

    final_summary = {
        "root": str(ROOT),
        "selected_count": len(selected),
        "selected_with_all_group1_method_scores": sum(1 for x in selected if x.get("has_all_group1_method_scores")),
        "selected_with_missing_group1_method_scores": sum(1 for x in selected if not x.get("has_all_group1_method_scores")),
        "evidence_rows": len(evidence_rows),
        "group2_score_rows_with_evidence": group2_audit["score_rows_with_evidence"],
        "field_score_rows": len(field_scores),
        "group3_challenge_charts": tag_audit["core_challenge_chart_count"],
        "group3_core_charts": tag_audit["core_chart_count"],
        "group2_report": str(ROOT / "group2" / "reports" / "group2_pilot30_final_report_zh.md"),
        "group3_report": str(ROOT / "group3" / "reports" / "group3_pilot30_final_report_zh.md"),
        "execution_report": str(ROOT / "reports" / "pilot30_execution_report_zh.md"),
    }
    write_json(ROOT / "reports" / "pilot30_run_summary.json", final_summary)
    print(json.dumps(final_summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
