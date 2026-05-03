import importlib.util
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


EXPERIMENT_ROOT = Path(os.environ.get("EXPERIMENT3_ROOT", ".")).resolve()
ROOT = Path(os.environ.get("GROUP23_ROOT", str(EXPERIMENT_ROOT / "zu2+3")))
SCRIPT_DIR = Path(os.environ.get("GROUP2_SCRIPT_DIR", str(Path(__file__).resolve().parent)))
BASE_SCRIPT = SCRIPT_DIR / "run_group2_group3_pilot30.py"
V3_SCRIPT = SCRIPT_DIR / "run_group2_group3_complete19_v3.py"
RUN_ID = "direct_q4_fix_20260503"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load_module(BASE_SCRIPT, "group2_group3_pilot30_base")
v3 = load_module(V3_SCRIPT, "group2_group3_complete19_v3_base")


def is_direct_q4_mapping(mapping):
    answer = mapping.get("canonical_answer") or {}
    value = answer.get("value")
    return (
        mapping.get("field_name") == "Q4_course_or_radial"
        and mapping.get("leg_type") == "DF"
        and answer.get("status") == "present"
        and isinstance(value, dict)
        and value.get("type") == "direct"
    )


def reviewed_as_accepted(data, mapping):
    for review in data.get("regions") or []:
        for candidate in review.get("candidate_mappings_reviewed") or []:
            if (
                candidate.get("candidate_leg_id") == mapping.get("candidate_leg_id")
                and candidate.get("canonical_leg_index") == mapping.get("canonical_leg_index")
                and candidate.get("field_name") == mapping.get("field_name")
                and candidate.get("human_decision") == "accepted"
            ):
                return True
    return False


def source_from_region(region):
    region_type = region.get("region_type")
    if region_type == "MISSED_APPROACH_TEXT":
        return ["ma_text"]
    if region_type == "PLAN_VIEW":
        return ["plan_view"]
    return ["chart_text"]


def build_direct_q4_rows(selected, by_chart, existing_rows, field_targets):
    selected_ids = {item["chart_id"] for item in selected}
    existing_keys = {(r["chart_id"], r["score_field"]) for r in existing_rows}
    added = []
    skipped = []

    for chart_id in sorted(selected_ids):
        data = (by_chart[chart_id].get("data") or {})
        for region in data.get("regions") or []:
            region_id = region.get("final_region_id") or region.get("source_region_id")
            source = source_from_region(region)
            for mapping in region.get("accepted_mappings") or []:
                if not is_direct_q4_mapping(mapping):
                    continue

                leg_index = mapping.get("canonical_leg_index")
                field_name = mapping.get("field_name")
                score_field = base.flatten_field_key(leg_index, field_name)
                key = (chart_id, score_field)

                if key in existing_keys:
                    skipped.append({
                        "chart_id": chart_id,
                        "score_field": score_field,
                        "reason": "已有字段级证据，未重复生成",
                        "region_id": region_id,
                    })
                    continue

                accepted_in_review = reviewed_as_accepted(data, mapping)
                if not accepted_in_review:
                    skipped.append({
                        "chart_id": chart_id,
                        "score_field": score_field,
                        "reason": "区域映射存在，但未找到人工接受复核记录",
                        "region_id": region_id,
                    })
                    continue

                row = {
                    "chart_id": chart_id,
                    "field_key": f"leg{leg_index}.{field_name}",
                    "score_field": score_field,
                    "field_path": base.field_path_from_key(leg_index, field_name),
                    "canonical_leg_index": leg_index,
                    "field_name": field_name,
                    "question_field": field_name,
                    "field_family": base.field_family(field_name),
                    "leg_type": mapping.get("leg_type"),
                    "canonical_answer": mapping.get("canonical_answer"),
                    "support_mode": "rule_default_completion",
                    "review_status": "由已接受区域映射补充生成",
                    "evidence_source": source,
                    "evidence_bucket": base.evidence_bucket("rule_default_completion", source),
                    "semantic_tags": ["424编码语义字段", "区域映射补充"],
                    "evidence_region_ids": [region_id],
                    "required_evidence_region_ids": [region_id],
                    "secondary_evidence_region_ids": [],
                    "evidence_count": 1,
                    "checked_scopes": source,
                    "checked_scope_count": len(source),
                    "reviewed_by": data.get("annotator"),
                    "reviewed_at": data.get("saved_at"),
                    "annotation_saved_at": data.get("saved_at"),
                    "source_schema": "区域已接受映射转字段级证据_v1",
                    "derived_rule": "同一航段的直接飞向区域映射补成字段证据",
                    "source_region_type": region.get("region_type"),
                    "source_accepted_mapping": {
                        "candidate_leg_id": mapping.get("candidate_leg_id"),
                        "canonical_leg_index": mapping.get("canonical_leg_index"),
                        "leg_type": mapping.get("leg_type"),
                        "field_name": mapping.get("field_name"),
                        "final_value": mapping.get("final_value"),
                    },
                }
                existing_keys.add(key)
                added.append(row)

    rows_by_key = {(r["chart_id"], r["score_field"]): r for r in existing_rows + added}
    q1_by_chart_leg = {
        (r["chart_id"], r["canonical_leg_index"]): r
        for r in existing_rows + added
        if r.get("field_name") == "Q1_fix_ident"
    }
    terminator_by_chart_leg = {
        (r["chart_id"], r["canonical_leg_index"]): r
        for r in existing_rows + added
        if r.get("field_name") == "Q_terminator"
        and (r.get("canonical_answer") or {}).get("value") == "DF"
    }

    for target_row in field_targets:
        chart_id = target_row.get("chart_id")
        if chart_id not in selected_ids:
            continue
        if target_row.get("question_field") != "Q4_course_or_radial":
            continue
        target = target_row.get("target") or {}
        value = target.get("value")
        if target.get("status") != "present" or not isinstance(value, dict) or value.get("type") != "direct":
            continue

        leg_index = target_row.get("leg_index")
        score_field = base.flatten_field_key(leg_index, "Q4_course_or_radial")
        key = (chart_id, score_field)
        if key in rows_by_key:
            continue

        terminator = terminator_by_chart_leg.get((chart_id, leg_index))
        if not terminator:
            skipped.append({
                "chart_id": chart_id,
                "score_field": score_field,
                "reason": "目标要求直接飞向，但没有找到同一航段已接受的直接飞向航段类型证据",
            })
            continue

        q1 = q1_by_chart_leg.get((chart_id, leg_index))
        required = terminator.get("evidence_region_ids") or []
        secondary = q1.get("evidence_region_ids") if q1 else []
        evidence_ids = list(dict.fromkeys(list(required) + list(secondary or [])))
        source = list(dict.fromkeys((terminator.get("evidence_source") or []) + ((q1 or {}).get("evidence_source") or [])))
        if not source:
            source = ["ma_text"]

        data = (by_chart[chart_id].get("data") or {})
        row = {
            "chart_id": chart_id,
            "field_key": f"leg{leg_index}.Q4_course_or_radial",
            "score_field": score_field,
            "field_path": base.field_path_from_key(leg_index, "Q4_course_or_radial"),
            "canonical_leg_index": leg_index,
            "field_name": "Q4_course_or_radial",
            "question_field": "Q4_course_or_radial",
            "field_family": base.field_family("Q4_course_or_radial"),
            "leg_type": "DF",
            "canonical_answer": target,
            "support_mode": "rule_default_completion",
            "review_status": "由同一航段直接飞向航段类型补充生成",
            "evidence_source": source,
            "evidence_bucket": base.evidence_bucket("rule_default_completion", source),
            "semantic_tags": ["424编码语义字段", "同一航段直接飞向补充"],
            "evidence_region_ids": evidence_ids,
            "required_evidence_region_ids": list(required),
            "secondary_evidence_region_ids": list(secondary or []),
            "evidence_count": len(set(map(str, evidence_ids))),
            "checked_scopes": source,
            "checked_scope_count": len(set(map(str, source))),
            "reviewed_by": data.get("annotator"),
            "reviewed_at": data.get("saved_at"),
            "annotation_saved_at": data.get("saved_at"),
            "source_schema": "同航段直接飞向航段类型转字段级证据_v1",
            "derived_rule": "同一航段的直接飞向航段类型推出航向/航迹/径向为直接飞向",
            "source_terminator_evidence": {
                "score_field": terminator.get("score_field"),
                "canonical_answer": terminator.get("canonical_answer"),
                "evidence_region_ids": terminator.get("evidence_region_ids"),
            },
            "source_fix_evidence": {
                "score_field": q1.get("score_field"),
                "canonical_answer": q1.get("canonical_answer"),
                "evidence_region_ids": q1.get("evidence_region_ids"),
            } if q1 else None,
        }
        rows_by_key[key] = row
        existing_keys.add(key)
        added.append(row)

    return added, skipped


def write_csv(path, rows):
    v3.write_csv(path, rows)


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def complete19_chart_ids(manifest_rows):
    return {
        row["chart_id"]
        for row in manifest_rows
        if row.get("has_all_group1_method_scores")
    }


def run_complete19_fixed(complete_ids, fixed_joined, fixed_tags, field_scores, chart_scores):
    g2_joined = [row for row in fixed_joined if row.get("chart_id") in complete_ids]
    evidence_by_chart_question = {}
    for row in g2_joined:
        if not v3.has_evidence(row):
            continue
        key = (row.get("chart_id"), row.get("question_field"))
        if key not in evidence_by_chart_question:
            evidence_by_chart_question[key] = {
                k: val for k, val in row.items() if k.startswith("evidence_")
            }

    positive = []
    positive_question_fallback = []
    size_control_present = []
    negative = []
    diagnostic = []
    unmatched_present = []
    unmatched_not_applicable = []
    evidence_on_negative = []

    for row in g2_joined:
        status = v3.target_status(row)
        enriched = {**row, "target_status": status, "pred_status": v3.pred_status(row)}
        if status == "present":
            if row.get("score_field") == "leg_count":
                size_control_present.append({**enriched, "audit_reason": "航段数量是规模控制变量，不作为证据来源"})
            elif v3.has_evidence(row):
                enriched["semantic_overlay"] = v3.semantic_overlay(row)
                positive.append(enriched)
            elif (row.get("chart_id"), row.get("question_field")) in evidence_by_chart_question:
                fallback = evidence_by_chart_question[(row.get("chart_id"), row.get("question_field"))]
                positive_question_fallback.append({
                    **enriched,
                    **fallback,
                    "semantic_overlay": v3.semantic_overlay({**enriched, **fallback}),
                    "audit_reason": "同一张图同一字段名但航段未严格对齐，不能进主表",
                    "evidence_match_scope": "同图同字段名但不同航段",
                })
            else:
                unmatched_present.append({**enriched, "audit_reason": "应填写字段没有字段级证据"})
        elif status == "not_applicable":
            enriched["negative_error_type"] = v3.negative_error_type(row)
            negative.append(enriched)
            if v3.has_evidence(row):
                evidence_on_negative.append({**enriched, "audit_reason": "不适用字段却挂了证据"})
            else:
                unmatched_not_applicable.append({**enriched, "audit_reason": "不适用字段没有证据，这是预期情况"})
        else:
            diagnostic.append({**enriched, "audit_reason": f"目标状态={status}"})

    out_prefix = ROOT / "group2"
    write_jsonl(out_prefix / f"group2_positive_joined_field_scores_complete19_{RUN_ID}.jsonl", positive)
    write_jsonl(out_prefix / f"group2_positive_question_fallback_complete19_{RUN_ID}.jsonl", positive_question_fallback)
    write_jsonl(out_prefix / f"group2_size_control_present_complete19_{RUN_ID}.jsonl", size_control_present)
    write_jsonl(out_prefix / f"group2_negative_not_applicable_complete19_{RUN_ID}.jsonl", negative)
    write_jsonl(out_prefix / f"group2_diagnostic_fields_complete19_{RUN_ID}.jsonl", diagnostic)
    write_jsonl(out_prefix / f"group2_unmatched_present_fields_complete19_{RUN_ID}.jsonl", unmatched_present)
    write_jsonl(out_prefix / f"group2_unmatched_not_applicable_fields_complete19_{RUN_ID}.jsonl", unmatched_not_applicable)
    write_jsonl(out_prefix / f"group2_evidence_on_not_applicable_audit_complete19_{RUN_ID}.jsonl", evidence_on_negative)

    g2_tables = {
        "positive_evidence_bucket": v3.aggregate_bool(positive, ["method", "evidence_evidence_bucket"]),
        "positive_support_mode": v3.aggregate_bool(positive, ["method", "evidence_support_mode"]),
        "positive_field_family": v3.aggregate_bool(positive, ["method", "field_family"]),
        "positive_semantic_overlay": v3.aggregate_bool(positive, ["method", "semantic_overlay"]),
        "question_fallback_evidence_bucket": v3.aggregate_bool(positive_question_fallback, ["method", "evidence_evidence_bucket"]),
        "size_control_present_field": v3.aggregate_bool(size_control_present, ["method", "score_field"], correct_key="correct"),
        "not_applicable_error_type": v3.aggregate_bool(negative, ["method", "negative_error_type"], correct_key="correct"),
        "not_applicable_error_share": v3.aggregate_category_share(negative, ["method"], "negative_error_type"),
        "not_applicable_by_field_family": v3.aggregate_bool(negative, ["method", "field_family", "negative_error_type"], correct_key="correct"),
        "not_applicable_by_question_field": v3.aggregate_bool(negative, ["method", "question_field", "negative_error_type"], correct_key="correct"),
    }
    for name, rows in g2_tables.items():
        write_csv(ROOT / "group2" / "reports" / f"complete19_{RUN_ID}_{name}_table.csv", rows)

    g2_audit = {
        "run_id": RUN_ID,
        "complete19_chart_count": len(complete_ids),
        "all_complete19_score_rows": len(g2_joined),
        "positive_present_strict_evidence_rows": len(positive),
        "positive_present_question_fallback_rows": len(positive_question_fallback),
        "size_control_present_rows": len(size_control_present),
        "negative_not_applicable_rows": len(negative),
        "diagnostic_rows": len(diagnostic),
        "unmatched_present_rows": len(unmatched_present),
        "unmatched_not_applicable_rows": len(unmatched_not_applicable),
        "evidence_on_not_applicable_rows": len(evidence_on_negative),
        "question_fallback_reason_counts": Counter(row.get("audit_reason") for row in positive_question_fallback),
        "positive_evidence_bucket_counts": Counter(row.get("evidence_evidence_bucket") for row in positive),
    }
    write_json(ROOT / "group2" / f"group2_complete19_{RUN_ID}_audit.json", g2_audit)

    group1_field_rows = [row for row in field_scores if row.get("chart_id") in complete_ids]
    group1_chart_rows = [row for row in chart_scores if row.get("chart_id") in complete_ids]
    tags_old = {row["chart_id"]: row for row in fixed_tags if row.get("chart_id") in complete_ids}

    target_by_chart = defaultdict(list)
    for row in group1_field_rows:
        if row.get("method") == "A1":
            target_by_chart[row["chart_id"]].append(row)

    text_missing_key = defaultdict(bool)
    for row in positive:
        sources = set(row.get("evidence_evidence_source") or [])
        key_field = row.get("question_field") in {"Q4_course_or_radial", "Q5_hold_params", "Q_terminator"}
        if key_field and "ma_text" not in sources:
            text_missing_key[row["chart_id"]] = True

    size_controls = []
    for chart_id in sorted(complete_ids):
        rows = target_by_chart[chart_id]
        leg_count = None
        present_count = 0
        family_counts = Counter()
        holding_leg_count = 0
        course_radial_count = 0
        for row in rows:
            status = v3.target_status(row)
            q = row.get("question_field")
            if q == "leg_count" and status == "present":
                leg_count = (row.get("target") or {}).get("value")
            if status == "present":
                present_count += 1
                family_counts[v3.field_family(row)] += 1
                if q == "Q_terminator" and (row.get("target") or {}).get("value") == "HM":
                    holding_leg_count += 1
                if q == "Q4_course_or_radial":
                    course_radial_count += 1
        size_controls.append({
            "chart_id": chart_id,
            "leg_count": int(leg_count or 0),
            "present_field_count": present_count,
            "field_count_by_family": dict(family_counts),
            "holding_leg_count": holding_leg_count,
            "course_radial_field_count": course_radial_count,
        })
    q1, q2 = v3.quantile_bins([row["present_field_count"] for row in size_controls])
    size_by_chart = {}
    for row in size_controls:
        row["leg_count_bin"] = v3.leg_count_bin(row["leg_count"])
        row["present_field_count_bin"] = v3.present_field_count_bin(row["present_field_count"], q1, q2)
        size_by_chart[row["chart_id"]] = row

    weak_descriptive = {
        "has_altitude_constraint",
        "has_course_radial",
        "terminator_derived",
        "has_holding",
        "rule_default_completion_case",
        "text_missing_visual_present",
    }
    moderate_base = {
        "has_ca_leg",
        "has_hm_leg",
        "implicit_hold_time",
        "multi_leg_complex",
        "plan_profile_only_holding",
    }
    strong_base = {
        "ca_df_sequence",
        "cross_modal_required",
        "insufficient_for_encoding_case",
    }

    tags_fixed = []
    review_queue = []
    for chart_id in sorted(complete_ids):
        old = tags_old.get(chart_id, {})
        old_tags = set(old.get("challenge_tags") or [])
        weak = sorted(old_tags & weak_descriptive)
        moderate = set(old_tags & moderate_base)
        if text_missing_key[chart_id]:
            moderate.add("关键字段缺少复飞文字证据")
        strong = set(old_tags & strong_base)
        evidence_derived = {
            tag for tag, source in (old.get("tag_sources") or {}).items()
            if "evidence_derived" in str(source)
        }
        if "ca_df_sequence" in old_tags and evidence_derived:
            strong.add("连续航段加证据信号")
        if "implicit_hold_time" in old_tags and "plan_profile_only_holding" in old_tags:
            moderate.add("等待程序时间加平面图信号")

        if strong:
            level = "hard"
        elif len(moderate) >= 2:
            level = "moderate"
        else:
            level = "ordinary"

        item = {
            "chart_id": chart_id,
            **size_by_chart[chart_id],
            "weak_descriptive_tags": weak,
            "moderate_signals": sorted(moderate),
            "strong_signals": sorted(strong),
            "difficulty_level": level,
            "old_challenge_tags": sorted(old_tags),
            "tag_sources": old.get("tag_sources") or {},
            "review_status": "修复后仍需审查" if strong or moderate else "自动生成",
            "difficulty_policy": f"complete19_{RUN_ID}_size_controlled_signals",
        }
        tags_fixed.append(item)
        if item["review_status"] == "修复后仍需审查":
            review_queue.append(item)

    write_jsonl(ROOT / "group3" / f"complete19_{RUN_ID}_size_controls.jsonl", size_controls)
    write_jsonl(ROOT / "group3" / f"challenge_tags_complete19_{RUN_ID}.jsonl", tags_fixed)
    write_jsonl(ROOT / "group3" / f"challenge_tag_review_queue_complete19_{RUN_ID}.jsonl", review_queue)

    tag_by_chart = {row["chart_id"]: row for row in tags_fixed}
    chart_joined = [{**row, **tag_by_chart[row["chart_id"]]} for row in group1_chart_rows]
    field_joined = [{**row, **tag_by_chart[row["chart_id"]]} for row in group1_field_rows]
    write_jsonl(ROOT / "group3" / f"group3_joined_chart_scores_complete19_{RUN_ID}.jsonl", chart_joined)
    write_jsonl(ROOT / "group3" / f"group3_joined_field_scores_complete19_{RUN_ID}.jsonl", field_joined)

    signal_chart_rows = []
    for row in chart_joined:
        for signal in row.get("moderate_signals") or []:
            signal_chart_rows.append({**row, "signal_type": "中等信号", "signal": signal})
        for signal in row.get("strong_signals") or []:
            signal_chart_rows.append({**row, "signal_type": "强信号", "signal": signal})

    g3_tables = {
        "difficulty_level": v3.aggregate_score(chart_joined, ["method", "difficulty_level"]),
        "moderate_signal": v3.aggregate_score([r for r in signal_chart_rows if r["signal_type"] == "中等信号"], ["method", "signal"]),
        "strong_signal": v3.aggregate_score([r for r in signal_chart_rows if r["signal_type"] == "强信号"], ["method", "signal"]),
        "difficulty_by_leg_count_bin": v3.aggregate_score(chart_joined, ["method", "difficulty_level", "leg_count_bin"]),
        "difficulty_by_present_field_count_bin": v3.aggregate_score(chart_joined, ["method", "difficulty_level", "present_field_count_bin"]),
    }
    for name, rows in g3_tables.items():
        write_csv(ROOT / "group3" / "reports" / f"complete19_{RUN_ID}_{name}_table.csv", rows)

    g3_audit = {
        "run_id": RUN_ID,
        "complete19_chart_count": len(complete_ids),
        "difficulty_level_counts": Counter(row["difficulty_level"] for row in tags_fixed),
        "leg_count_bin_counts": Counter(row["leg_count_bin"] for row in tags_fixed),
        "present_field_count_bin_counts": Counter(row["present_field_count_bin"] for row in tags_fixed),
        "moderate_signal_counts": Counter(signal for row in tags_fixed for signal in row["moderate_signals"]),
        "strong_signal_counts": Counter(signal for row in tags_fixed for signal in row["strong_signals"]),
        "present_field_count_quantile_cutoffs": {"q1": q1, "q2": q2},
        "note": "航段数量和应填字段数量只作为规模控制变量，不直接当作难例标签。",
    }
    write_json(ROOT / "group3" / f"group3_complete19_{RUN_ID}_audit.json", g3_audit)

    return {
        "g2_audit": g2_audit,
        "g3_audit": g3_audit,
        "positive": positive,
        "positive_question_fallback": positive_question_fallback,
        "unmatched_present": unmatched_present,
        "tags_fixed": tags_fixed,
        "g2_tables": g2_tables,
        "g3_tables": g3_tables,
    }


def table_md(rows, columns, max_rows=80):
    rows = rows[:max_rows]
    if not rows:
        return "_无数据_\n"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        vals = []
        for col in columns:
            value = row.get(col, "")
            if col == "accuracy" and isinstance(value, (int, float)):
                value = f"{100 * value:.2f}%"
            vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def main():
    base.ensure_dirs()
    export_obj = base.load_json(base.EXPORT_PATH)
    overview_obj = base.load_json(base.OVERVIEW_PATH)
    field_targets = list(base.read_jsonl(base.FIELD_TARGETS))
    selected, spare, excluded, by_chart = base.choose_pilot30(export_obj, overview_obj)

    original_evidence, original_review_queue = base.build_evidence(selected, by_chart)
    added_rows, skipped_rows = build_direct_q4_rows(selected, by_chart, original_evidence, field_targets)
    fixed_evidence = sorted(
        original_evidence + added_rows,
        key=lambda r: (r["chart_id"], str(r["canonical_leg_index"]), r["field_name"], r.get("source_schema", "")),
    )

    chart_scores, field_scores = base.build_score_indices(selected)
    fixed_joined, fixed_unmatched_scores, fixed_unmatched_evidence = base.join_group2(field_scores, fixed_evidence)
    fixed_tags, fixed_tag_review_queue = base.build_group3_tags(selected, fixed_evidence, field_targets)
    group3_chart, group3_field = base.join_group3(chart_scores, field_scores, fixed_tags)

    write_jsonl(ROOT / "selection" / f"pilot30_manifest_{RUN_ID}.jsonl", selected)
    write_jsonl(ROOT / "group2" / f"evidence_provenance_pilot30_{RUN_ID}.jsonl", fixed_evidence)
    write_jsonl(ROOT / "group2" / f"evidence_review_queue_pilot30_{RUN_ID}.jsonl", original_review_queue)
    write_jsonl(ROOT / "group2" / f"direct_q4_added_evidence_{RUN_ID}.jsonl", added_rows)
    write_jsonl(ROOT / "group2" / f"direct_q4_skipped_evidence_{RUN_ID}.jsonl", skipped_rows)
    write_jsonl(ROOT / f"group1_field_scores_pilot30_{RUN_ID}.jsonl", field_scores)
    write_jsonl(ROOT / f"group1_chart_scores_pilot30_{RUN_ID}.jsonl", chart_scores)
    write_jsonl(ROOT / "group2" / f"group2_joined_field_scores_pilot30_{RUN_ID}.jsonl", fixed_joined)
    write_jsonl(ROOT / "group2" / f"group2_unmatched_score_fields_pilot30_{RUN_ID}.jsonl", fixed_unmatched_scores)
    write_jsonl(ROOT / "group2" / f"group2_unmatched_evidence_fields_pilot30_{RUN_ID}.jsonl", fixed_unmatched_evidence)
    write_jsonl(ROOT / "group3" / f"challenge_tags_pilot30_{RUN_ID}.jsonl", fixed_tags)
    write_jsonl(ROOT / "group3" / f"challenge_tag_review_queue_pilot30_{RUN_ID}.jsonl", fixed_tag_review_queue)
    write_jsonl(ROOT / "group3" / f"group3_joined_chart_scores_pilot30_{RUN_ID}.jsonl", group3_chart)
    write_jsonl(ROOT / "group3" / f"group3_joined_field_scores_pilot30_{RUN_ID}.jsonl", group3_field)

    complete_ids = complete19_chart_ids(selected)
    write_jsonl(
        ROOT / "selection" / f"complete19_manifest_{RUN_ID}.jsonl",
        [row for row in selected if row["chart_id"] in complete_ids],
    )
    complete_result = run_complete19_fixed(complete_ids, fixed_joined, fixed_tags, field_scores, chart_scores)

    old_fallback_path = ROOT / "group2" / "group2_positive_question_fallback_complete19_v3.jsonl"
    old_fallback = list(v3.read_jsonl(old_fallback_path)) if old_fallback_path.exists() else []
    fixed_fallback = complete_result["positive_question_fallback"]
    fixed_direct_fallback = [
        row for row in fixed_fallback
        if row.get("question_field") == "Q4_course_or_radial"
        and ((row.get("target") or {}).get("value") or {}).get("type") == "direct"
    ]

    audit = {
        "run_id": RUN_ID,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "修复直接飞向字段没有进入字段级证据表的问题；只补同一航段的直接飞向字段。",
        "selected_count": len(selected),
        "complete19_count": len(complete_ids),
        "original_evidence_rows": len(original_evidence),
        "fixed_evidence_rows": len(fixed_evidence),
        "added_direct_q4_evidence_rows": len(added_rows),
        "added_direct_q4_rule_counts": Counter(row.get("derived_rule") for row in added_rows),
        "skipped_direct_q4_rows": len(skipped_rows),
        "old_complete19_question_fallback_rows": len(old_fallback),
        "fixed_complete19_question_fallback_rows": len(fixed_fallback),
        "fixed_direct_q4_question_fallback_rows": len(fixed_direct_fallback),
        "added_charts": sorted({row["chart_id"] for row in added_rows}),
        "added_score_fields": sorted({f'{row["chart_id"]}:{row["score_field"]}' for row in added_rows}),
        "output_files": {
            "fixed_evidence": str(ROOT / "group2" / f"evidence_provenance_pilot30_{RUN_ID}.jsonl"),
            "added_evidence": str(ROOT / "group2" / f"direct_q4_added_evidence_{RUN_ID}.jsonl"),
            "fixed_joined": str(ROOT / "group2" / f"group2_joined_field_scores_pilot30_{RUN_ID}.jsonl"),
            "complete19_group2_audit": str(ROOT / "group2" / f"group2_complete19_{RUN_ID}_audit.json"),
            "complete19_group3_audit": str(ROOT / "group3" / f"group3_complete19_{RUN_ID}_audit.json"),
        },
    }
    write_json(ROOT / "reports" / f"{RUN_ID}_audit.json", audit)

    report = [
        "# 实验组2/3 直接飞向证据映射修复报告",
        "",
        f"生成时间：{audit['created_at']}",
        "",
        "## 这次修了什么",
        "",
        "这次只修一个程序问题：原始人工标注区域里已经接受的“同一航段直接飞向”映射，没有进入实验组2使用的字段级证据表。",
        "",
        "修复范围严格限制为两种同航段情况：",
        "",
        "1. 区域框里已经接受了“本航段的航向/航迹/径向 = 直接飞向”，但字段级证据表漏了这一行。",
        "2. 字段级证据表里已经接受了“本航段的航段类型 = 直接飞向某点”，且标准答案要求“本航段的航向/航迹/径向 = 直接飞向”，则补出这一行。",
        "",
        "两种情况都必须同一张图、同一航段；不能跨航段补证据。",
        "",
        "没有重新跑模型，没有改实验组1结果，没有把第1段证据补给第2段。",
        "",
        "## 数量变化",
        "",
        f"- 原字段级证据行数：{audit['original_evidence_rows']}",
        f"- 修复后字段级证据行数：{audit['fixed_evidence_rows']}",
        f"- 新增“直接飞向”字段证据行：{audit['added_direct_q4_evidence_rows']}",
        f"- 其中，区域映射直接补证据：{audit['added_direct_q4_rule_counts'].get('同一航段的直接飞向区域映射补成字段证据', 0)}",
        f"- 其中，由同航段“直接飞向某点”航段类型补证据：{audit['added_direct_q4_rule_counts'].get('同一航段的直接飞向航段类型推出航向/航迹/径向为直接飞向', 0)}",
        f"- 旧的同字段名但航段不对齐回退行：{audit['old_complete19_question_fallback_rows']}",
        f"- 修复后的同字段名但航段不对齐回退行：{audit['fixed_complete19_question_fallback_rows']}",
        f"- 修复后仍属于“直接飞向”的回退行：{audit['fixed_direct_q4_question_fallback_rows']}",
        "",
        "## 新增证据涉及的航图",
        "",
        table_md(added_rows, ["chart_id", "score_field", "evidence_region_ids", "canonical_answer", "derived_rule"], max_rows=50),
        "## 实验组2修复后主表概况",
        "",
        table_md(complete_result["g2_tables"]["positive_evidence_bucket"], ["method", "evidence_evidence_bucket", "correct", "total", "accuracy"], max_rows=80),
        "## 实验组3修复后难度分布",
        "",
        table_md(
            [{"difficulty_level": k, "count": v} for k, v in sorted(complete_result["g3_audit"]["difficulty_level_counts"].items())],
            ["difficulty_level", "count"],
            max_rows=20,
        ),
        "## 当前判断",
        "",
        "如果修复后“直接飞向”回退行为 0，说明这类问题已经从程序层面补上；后续可以用这套规则继续扩展到更多已标注样本。",
        "",
        "如果仍有其他回退行，它们不能进入主表，需要继续逐类审查，不能直接当作实验组2正式结论。",
    ]
    report_path = ROOT / "reports" / f"{RUN_ID}_report_zh.md"
    report_path.write_text("\n".join(report), encoding="utf-8")

    summary = {
        **audit,
        "report": str(report_path),
        "group2_positive_strict_rows": complete_result["g2_audit"]["positive_present_strict_evidence_rows"],
        "group2_question_fallback_rows": complete_result["g2_audit"]["positive_present_question_fallback_rows"],
        "group3_difficulty_level_counts": dict(complete_result["g3_audit"]["difficulty_level_counts"]),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
