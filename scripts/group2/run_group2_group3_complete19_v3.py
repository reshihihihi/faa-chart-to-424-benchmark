import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


EXPERIMENT_ROOT = Path(os.environ.get("EXPERIMENT3_ROOT", ".")).resolve()
ROOT = Path(os.environ.get("GROUP23_ROOT", str(EXPERIMENT_ROOT / "zu2+3")))
METHOD_ORDER = ["A1", "A2", "B1", "B1_prime", "B1_prime_link", "C1", "C2", "C3", "C4", "D1"]


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


def write_csv(path: Path, rows, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys or ["empty"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def pct(value):
    if value is None:
        return ""
    return f"{100 * value:.2f}%"


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
                value = pct(value)
            vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def target_status(row):
    return (row.get("target") or {}).get("status")


def pred_status(row):
    return (row.get("pred") or {}).get("status")


def has_evidence(row):
    return bool(row.get("evidence_evidence_bucket"))


def field_family(row):
    return row.get("field_family") or row.get("evidence_field_family") or "其他"


def aggregate_bool(rows, dims, correct_key="correct"):
    stats = defaultdict(lambda: {"correct": 0, "total": 0})
    for row in rows:
        key = tuple(str(row.get(dim, "")) for dim in dims)
        stats[key]["total"] += 1
        if row.get(correct_key):
            stats[key]["correct"] += 1
    out = []
    for key, val in sorted(stats.items()):
        item = {dim: key[i] for i, dim in enumerate(dims)}
        item.update(val)
        item["accuracy"] = val["correct"] / val["total"] if val["total"] else None
        out.append(item)
    return out


def aggregate_score(rows, dims):
    stats = defaultdict(lambda: {"correct": 0, "total": 0, "row_count": 0})
    for row in rows:
        total = row.get("total") or 0
        correct = row.get("correct") or 0
        if total <= 0:
            continue
        key = tuple(str(row.get(dim, "")) for dim in dims)
        stats[key]["correct"] += correct
        stats[key]["total"] += total
        stats[key]["row_count"] += 1
    out = []
    for key, val in sorted(stats.items()):
        item = {dim: key[i] for i, dim in enumerate(dims)}
        item.update(val)
        item["accuracy"] = val["correct"] / val["total"] if val["total"] else None
        out.append(item)
    return out


def aggregate_category_share(rows, group_dims, category_dim):
    group_totals = Counter(tuple(str(row.get(dim, "")) for dim in group_dims) for row in rows)
    counts = Counter(
        tuple(str(row.get(dim, "")) for dim in group_dims) + (str(row.get(category_dim, "")),)
        for row in rows
    )
    out = []
    for key, count in sorted(counts.items()):
        group_key = key[:-1]
        category = key[-1]
        item = {dim: group_key[i] for i, dim in enumerate(group_dims)}
        item[category_dim] = category
        item["count"] = count
        item["group_total"] = group_totals[group_key]
        item["share"] = count / group_totals[group_key] if group_totals[group_key] else None
        out.append(item)
    return out


def negative_error_type(row):
    ps = pred_status(row)
    if ps == "not_applicable":
        return "true_negative"
    if ps == "present":
        return "over_assertion"
    if ps == "unknown":
        return "unknown_on_negative"
    if ps is None:
        return "missing_prediction_status"
    return "other_negative_error"


def semantic_overlay(row):
    tags = row.get("evidence_semantic_tags") or row.get("semantic_tags") or []
    if isinstance(tags, str):
        tags = [tags]
    if tags:
        return ";".join(tags)
    if row.get("question_field") == "Q_terminator":
        return "424编码语义字段"
    return "none"


def complete19_chart_ids(manifest_rows):
    return {
        row["chart_id"]
        for row in manifest_rows
        if row.get("has_all_group1_method_scores")
    }


def quantile_bins(values):
    values = sorted(values)
    if not values:
        return 0, 0
    q1 = values[len(values) // 3]
    q2 = values[(2 * len(values)) // 3]
    return q1, q2


def present_field_count_bin(value, q1, q2):
    if value <= q1:
        return "low"
    if value <= q2:
        return "medium"
    return "high"


def leg_count_bin(value):
    if value <= 2:
        return "small"
    if value == 3:
        return "medium"
    return "large"


def main():
    manifest = list(read_jsonl(ROOT / "selection" / "pilot30_manifest.jsonl"))
    complete_ids = complete19_chart_ids(manifest)
    write_jsonl(
        ROOT / "selection" / "complete19_manifest_v3.jsonl",
        [row for row in manifest if row["chart_id"] in complete_ids],
    )
    (ROOT / "selection" / "complete19_chart_ids.txt").write_text(
        "\n".join(sorted(complete_ids)) + "\n",
        encoding="utf-8",
    )

    g2_joined_all = list(read_jsonl(ROOT / "group2" / "group2_joined_field_scores_pilot30.jsonl"))
    g2_joined = [row for row in g2_joined_all if row.get("chart_id") in complete_ids]
    evidence_by_chart_question = {}
    for row in g2_joined:
        if not has_evidence(row):
            continue
        key = (row.get("chart_id"), row.get("question_field"))
        if key not in evidence_by_chart_question:
            evidence_by_chart_question[key] = {
                k: v for k, v in row.items() if k.startswith("evidence_")
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
        status = target_status(row)
        enriched = {**row, "target_status": status, "pred_status": pred_status(row)}
        if status == "present":
            if row.get("score_field") == "leg_count":
                size_control_present.append({**enriched, "audit_reason": "leg_count_size_control_not_evidence_source"})
            elif has_evidence(row):
                enriched["semantic_overlay"] = semantic_overlay(row)
                positive.append(enriched)
            elif (row.get("chart_id"), row.get("question_field")) in evidence_by_chart_question:
                fallback = evidence_by_chart_question[(row.get("chart_id"), row.get("question_field"))]
                positive_question_fallback.append({
                    **enriched,
                    **fallback,
                    "semantic_overlay": semantic_overlay({**enriched, **fallback}),
                    "audit_reason": "question_field_fallback_requires_leg_alignment_review",
                    "evidence_match_scope": "same_chart_same_question_field_not_same_leg",
                })
            else:
                unmatched_present.append({**enriched, "audit_reason": "present_score_field_without_evidence"})
        elif status == "not_applicable":
            enriched["negative_error_type"] = negative_error_type(row)
            negative.append(enriched)
            if has_evidence(row):
                evidence_on_negative.append({**enriched, "audit_reason": "evidence_attached_to_not_applicable_score_field"})
            else:
                unmatched_not_applicable.append({**enriched, "audit_reason": "not_applicable_score_field_without_evidence_expected"})
        else:
            diagnostic.append({**enriched, "audit_reason": f"target_status={status}"})

    write_jsonl(ROOT / "group2" / "group2_positive_joined_field_scores_complete19_v3.jsonl", positive)
    write_jsonl(ROOT / "group2" / "group2_positive_question_fallback_complete19_v3.jsonl", positive_question_fallback)
    write_jsonl(ROOT / "group2" / "group2_size_control_present_complete19_v3.jsonl", size_control_present)
    write_jsonl(ROOT / "group2" / "group2_negative_not_applicable_complete19_v3.jsonl", negative)
    write_jsonl(ROOT / "group2" / "group2_diagnostic_fields_complete19_v3.jsonl", diagnostic)
    write_jsonl(ROOT / "group2" / "group2_unmatched_present_fields_complete19_v3.jsonl", unmatched_present)
    write_jsonl(ROOT / "group2" / "group2_unmatched_not_applicable_fields_complete19_v3.jsonl", unmatched_not_applicable)
    write_jsonl(ROOT / "group2" / "group2_evidence_on_not_applicable_audit_complete19_v3.jsonl", evidence_on_negative)

    g2_tables = {
        "positive_evidence_bucket": aggregate_bool(positive, ["method", "evidence_evidence_bucket"]),
        "positive_support_mode": aggregate_bool(positive, ["method", "evidence_support_mode"]),
        "positive_field_family": aggregate_bool(positive, ["method", "field_family"]),
        "positive_semantic_overlay": aggregate_bool(positive, ["method", "semantic_overlay"]),
        "question_fallback_evidence_bucket": aggregate_bool(positive_question_fallback, ["method", "evidence_evidence_bucket"]),
        "size_control_present_field": aggregate_bool(size_control_present, ["method", "score_field"], correct_key="correct"),
        "not_applicable_error_type": aggregate_bool(negative, ["method", "negative_error_type"], correct_key="correct"),
        "not_applicable_error_share": aggregate_category_share(negative, ["method"], "negative_error_type"),
        "not_applicable_by_field_family": aggregate_bool(negative, ["method", "field_family", "negative_error_type"], correct_key="correct"),
        "not_applicable_by_field_family_share": aggregate_category_share(negative, ["method", "field_family"], "negative_error_type"),
        "not_applicable_by_question_field": aggregate_bool(negative, ["method", "question_field", "negative_error_type"], correct_key="correct"),
        "not_applicable_by_question_field_share": aggregate_category_share(negative, ["method", "question_field"], "negative_error_type"),
    }
    for name, rows in g2_tables.items():
        write_csv(ROOT / "group2" / "reports" / f"complete19_v3_{name}_table.csv", rows)

    g2_audit = {
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
        "negative_error_type_counts": Counter(row["negative_error_type"] for row in negative),
        "positive_evidence_bucket_counts": Counter(row.get("evidence_evidence_bucket") for row in positive),
        "question_fallback_reason_counts": Counter(row.get("audit_reason") for row in positive_question_fallback),
        "size_control_reason_counts": Counter(row.get("audit_reason") for row in size_control_present),
    }
    write_json(ROOT / "group2" / "group2_complete19_v3_audit.json", g2_audit)

    # Group 3 v3.
    group1_field_rows = [
        row
        for row in read_jsonl(ROOT / "group1_field_scores_pilot30.jsonl")
        if row.get("chart_id") in complete_ids
    ]
    group1_chart_rows = [
        row
        for row in read_jsonl(ROOT / "group1_chart_scores_pilot30.jsonl")
        if row.get("chart_id") in complete_ids
    ]
    tags_old = {
        row["chart_id"]: row
        for row in read_jsonl(ROOT / "group3" / "challenge_tags_pilot30.jsonl")
        if row.get("chart_id") in complete_ids
    }

    # Use A1 target rows as method-independent target structure.
    target_by_chart = defaultdict(list)
    for row in group1_field_rows:
        if row.get("method") == "A1":
            target_by_chart[row["chart_id"]].append(row)

    # Evidence-derived key-field signal from positive evidence rows.
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
            status = target_status(row)
            q = row.get("question_field")
            if q == "leg_count" and status == "present":
                leg_count = (row.get("target") or {}).get("value")
            if status == "present":
                present_count += 1
                family_counts[field_family(row)] += 1
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
    q1, q2 = quantile_bins([row["present_field_count"] for row in size_controls])
    size_by_chart = {}
    for row in size_controls:
        row["leg_count_bin"] = leg_count_bin(row["leg_count"])
        row["present_field_count_bin"] = present_field_count_bin(row["present_field_count"], q1, q2)
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

    tags_v3 = []
    review_queue = []
    for chart_id in sorted(complete_ids):
        old = tags_old.get(chart_id, {})
        old_tags = set(old.get("challenge_tags") or [])
        weak = sorted(old_tags & weak_descriptive)
        moderate = set(old_tags & moderate_base)
        if text_missing_key[chart_id]:
            moderate.add("text_missing_visual_present_on_key_field")
        strong = set(old_tags & strong_base)
        evidence_derived = {
            tag for tag, source in (old.get("tag_sources") or {}).items()
            if "evidence_derived" in str(source)
        }
        if "ca_df_sequence" in old_tags and evidence_derived:
            strong.add("ca_df_sequence_plus_evidence_signal")
        if "implicit_hold_time" in old_tags and "plan_profile_only_holding" in old_tags:
            moderate.add("implicit_hold_time_plus_plan_profile_only")

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
            "review_status": "auto_v3_pilot_needs_review" if strong or moderate else "auto_v3_pilot",
            "difficulty_policy": "complete19_v3_size_controlled_signals",
        }
        tags_v3.append(item)
        if item["review_status"].endswith("needs_review"):
            review_queue.append(item)

    write_jsonl(ROOT / "group3" / "complete19_v3_size_controls.jsonl", size_controls)
    write_jsonl(ROOT / "group3" / "challenge_tags_complete19_v3.jsonl", tags_v3)
    write_jsonl(ROOT / "group3" / "challenge_tag_review_queue_complete19_v3.jsonl", review_queue)

    tag_by_chart = {row["chart_id"]: row for row in tags_v3}
    chart_joined = []
    for row in group1_chart_rows:
        tag = tag_by_chart[row["chart_id"]]
        chart_joined.append({**row, **tag})

    field_joined = []
    for row in group1_field_rows:
        tag = tag_by_chart[row["chart_id"]]
        field_joined.append({**row, **tag})

    write_jsonl(ROOT / "group3" / "group3_joined_chart_scores_complete19_v3.jsonl", chart_joined)
    write_jsonl(ROOT / "group3" / "group3_joined_field_scores_complete19_v3.jsonl", field_joined)

    signal_chart_rows = []
    for row in chart_joined:
        for signal in row.get("moderate_signals") or []:
            signal_chart_rows.append({**row, "signal_type": "moderate", "signal": signal})
        for signal in row.get("strong_signals") or []:
            signal_chart_rows.append({**row, "signal_type": "strong", "signal": signal})

    g3_tables = {
        "difficulty_level": aggregate_score(chart_joined, ["method", "difficulty_level"]),
        "moderate_signal": aggregate_score([r for r in signal_chart_rows if r["signal_type"] == "moderate"], ["method", "signal"]),
        "strong_signal": aggregate_score([r for r in signal_chart_rows if r["signal_type"] == "strong"], ["method", "signal"]),
        "signal_by_leg_count_bin": aggregate_score(signal_chart_rows, ["method", "signal", "leg_count_bin"]),
        "signal_by_present_field_count_bin": aggregate_score(signal_chart_rows, ["method", "signal", "present_field_count_bin"]),
        "difficulty_by_leg_count_bin": aggregate_score(chart_joined, ["method", "difficulty_level", "leg_count_bin"]),
        "difficulty_by_present_field_count_bin": aggregate_score(chart_joined, ["method", "difficulty_level", "present_field_count_bin"]),
    }
    for name, rows in g3_tables.items():
        write_csv(ROOT / "group3" / "reports" / f"complete19_v3_{name}_table.csv", rows)

    g3_audit = {
        "complete19_chart_count": len(complete_ids),
        "difficulty_level_counts": Counter(row["difficulty_level"] for row in tags_v3),
        "leg_count_bin_counts": Counter(row["leg_count_bin"] for row in tags_v3),
        "present_field_count_bin_counts": Counter(row["present_field_count_bin"] for row in tags_v3),
        "moderate_signal_counts": Counter(signal for row in tags_v3 for signal in row["moderate_signals"]),
        "strong_signal_counts": Counter(signal for row in tags_v3 for signal in row["strong_signals"]),
        "present_field_count_quantile_cutoffs": {"q1": q1, "q2": q2},
        "note": "leg_count and present_field_count are size controls, not direct hard labels.",
    }
    write_json(ROOT / "group3" / "group3_complete19_v3_audit.json", g3_audit)

    g2_report = [
        "# 实验组2 complete19 v3 报告",
        "",
        f"生成时间：{datetime.now().isoformat(timespec='seconds')}",
        "",
        "## v3 核心变化",
        "",
        "- `present` / evidence-reviewed 字段进入主线 evidence analysis。",
        "- `not_applicable` 字段进入附线 applicability boundary analysis。",
        "- `not_applicable` 不再混入 evidence_bucket 主表。",
        "- 424 编码语义字段以 `semantic_overlay` 保留，而不是覆盖 evidence_bucket。",
        "",
        "## 数量",
        "",
        f"- 完整可比 chart：{len(complete_ids)}",
        f"- score rows：{len(g2_joined)}",
        f"- positive present strict evidence rows：{len(positive)}",
        f"- positive present question-fallback rows：{len(positive_question_fallback)}",
        f"- size-control present rows：{len(size_control_present)}",
        f"- negative not_applicable rows：{len(negative)}",
        f"- diagnostic rows：{len(diagnostic)}",
        f"- unmatched present rows：{len(unmatched_present)}",
        f"- unmatched not_applicable rows：{len(unmatched_not_applicable)}",
        f"- evidence on not_applicable audit rows：{len(evidence_on_negative)}",
        "",
        "## Positive: method × evidence_bucket",
        "",
        table_md(g2_tables["positive_evidence_bucket"], ["method", "evidence_evidence_bucket", "correct", "total", "accuracy"], max_rows=80),
        "## Fallback: method × evidence_bucket",
        "",
        table_md(g2_tables["question_fallback_evidence_bucket"], ["method", "evidence_evidence_bucket", "correct", "total", "accuracy"], max_rows=80),
        "## Size Control: method × score_field",
        "",
        table_md(g2_tables["size_control_present_field"], ["method", "score_field", "correct", "total", "accuracy"], max_rows=80),
        "## Negative: method × negative_error_type",
        "",
        table_md(g2_tables["not_applicable_error_type"], ["method", "negative_error_type", "correct", "total", "accuracy"], max_rows=80),
        "## Negative: error share within method",
        "",
        table_md(g2_tables["not_applicable_error_share"], ["method", "negative_error_type", "count", "group_total", "share"], max_rows=120),
        "## 解释",
        "",
        "`not_applicable` 是字段适用性负类。它不表示航图上缺字，也不表示 424 数据缺失，而是表示该字段在当前航段语义下不应填写。v3 中只用它分析模型是否 overfill / over-assert，不把它当作普通 evidence source 字段。",
        "",
        "`leg_count` 是任务规模控制变量，不再进入 evidence-source 主表。`question-fallback` 是同一 chart、同一 question field 但航段编号未严格对齐的证据匹配，只作为 leg-alignment 待审查表，不作为严格主结论。",
    ]
    (ROOT / "group2" / "reports" / "group2_complete19_v3_report_zh.md").write_text("\n".join(g2_report), encoding="utf-8")

    g3_report = [
        "# 实验组3 complete19 v3 报告",
        "",
        f"生成时间：{datetime.now().isoformat(timespec='seconds')}",
        "",
        "## v3 核心变化",
        "",
        "- `leg_count` / `present_field_count` 作为规模控制变量，不直接判 hard。",
        "- 常见 missed approach 元素作为 weak descriptive tags，不直接判难。",
        "- 中等信号和强信号分开。",
        "- `difficulty_level` 由结构/证据信号决定，而不是由标签数量或航段数量直接决定。",
        "",
        "## 数量",
        "",
        f"- 完整可比 chart：{len(complete_ids)}",
        f"- difficulty level counts：{dict(g3_audit['difficulty_level_counts'])}",
        f"- leg_count_bin counts：{dict(g3_audit['leg_count_bin_counts'])}",
        f"- present_field_count_bin counts：{dict(g3_audit['present_field_count_bin_counts'])}",
        "",
        "## method × difficulty_level",
        "",
        table_md(g3_tables["difficulty_level"], ["method", "difficulty_level", "correct", "total", "row_count", "accuracy"], max_rows=80),
        "## strong signal counts",
        "",
        table_md([{"signal": k, "count": v} for k, v in sorted(g3_audit["strong_signal_counts"].items())], ["signal", "count"], max_rows=80),
        "## moderate signal counts",
        "",
        table_md([{"signal": k, "count": v} for k, v in sorted(g3_audit["moderate_signal_counts"].items())], ["signal", "count"], max_rows=80),
        "## 解释",
        "",
        "v3 把 `implicit_hold_time` 和 `plan_profile_only_holding` 视为中等证据信号，不再让常见的 holding 默认补全单独触发 hard。hard 主要由 `ca_df_sequence`、`cross_modal_required` 或 `insufficient_for_encoding_case` 触发。当前阶段只能验证定义，不形成 formal300 难例结论。",
    ]
    (ROOT / "group3" / "reports" / "group3_complete19_v3_report_zh.md").write_text("\n".join(g3_report), encoding="utf-8")

    joint_report = [
        "# 实验组2/3 complete19 v3 联合执行报告",
        "",
        f"生成时间：{datetime.now().isoformat(timespec='seconds')}",
        "",
        "## 已完成",
        "",
        "1. 固定 19 张完整可比 chart。",
        "2. 实验组2已拆分 positive / negative / diagnostic 字段。",
        "3. 实验组2已生成 positive evidence tables 和 not_applicable overfill tables。",
        "4. 实验组3已生成 size controls。",
        "5. 实验组3已重分类 weak / moderate / strong signals。",
        "6. 实验组3已生成 size-controlled difficulty tables。",
        "",
        "## 关键结果",
        "",
        f"- complete19 charts：{len(complete_ids)}",
        f"- group2 strict positive rows：{len(positive)}",
        f"- group2 question-fallback rows：{len(positive_question_fallback)}",
        f"- group2 size-control rows：{len(size_control_present)}",
        f"- group2 negative not_applicable rows：{len(negative)}",
        f"- group2 unmatched present rows：{len(unmatched_present)}",
        f"- group3 difficulty level counts：{dict(g3_audit['difficulty_level_counts'])}",
        "",
        "## 当前判断",
        "",
        "实验组2 v3 已把 evidence-source 主线、question-field fallback、size-control 字段、not_applicable 负类边界分析分开，避免把 leg_count 或航段未对齐字段混进严格证据主结论。",
        "",
        "实验组3 v3 已把任务规模变量和难度信号分开，并把常见 holding 默认补全降为中等信号。complete19 仍可能偏复杂，是否能产生足够 ordinary 样本需要用更大、覆盖更均衡的已标注集合验证。",
        "",
        "## 后续",
        "",
        "1. 审查 `group2_positive_question_fallback_complete19_v3.jsonl`，确认是否需要正式 leg-alignment 规则。",
        "2. 审查 `challenge_tag_review_queue_complete19_v3.jsonl`，确认 hard / moderate 划分是否符合论文问题。",
        "3. 等更多 submitted annotations 与实验组1 formal200 重合后，扩展 v3 到更大样本。",
    ]
    (ROOT / "reports" / "complete19_group2_group3_v3_report_zh.md").write_text("\n".join(joint_report), encoding="utf-8")

    summary = {
        "root": str(ROOT),
        "complete19_chart_count": len(complete_ids),
        "group2_positive_strict_rows": len(positive),
        "group2_positive_question_fallback_rows": len(positive_question_fallback),
        "group2_size_control_rows": len(size_control_present),
        "group2_negative_not_applicable_rows": len(negative),
        "group2_unmatched_present_rows": len(unmatched_present),
        "group2_report": str(ROOT / "group2" / "reports" / "group2_complete19_v3_report_zh.md"),
        "group3_difficulty_level_counts": dict(g3_audit["difficulty_level_counts"]),
        "group3_report": str(ROOT / "group3" / "reports" / "group3_complete19_v3_report_zh.md"),
        "joint_report": str(ROOT / "reports" / "complete19_group2_group3_v3_report_zh.md"),
    }
    write_json(ROOT / "reports" / "complete19_v3_run_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
