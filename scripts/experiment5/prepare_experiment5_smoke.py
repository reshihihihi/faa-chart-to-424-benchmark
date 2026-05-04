from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]

GROUP1_V2_ROOT = (
    REPO_ROOT
    / "formal_runs"
    / "group1"
    / "group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2"
)
TARGET_V2_DIR = (
    REPO_ROOT
    / "benchmark_exports"
    / "derived"
    / "v2"
    / "formal300"
    / "targets"
    / "scoring_equivalence_v2"
)
BASE_TARGET_DIR = REPO_ROOT / "benchmark_exports" / "derived" / "v2" / "formal300" / "targets"
EXPERIMENT5_DIR = (
    REPO_ROOT / "benchmark_exports" / "derived" / "v2" / "experiment5_diagnostic"
)
FORMAL_RUN_DIR = (
    REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_smoke_20260503_r1"
)


CORE_CHALLENGE_TAGS = {
    "has_ca_leg",
    "has_hm_leg",
    "ca_df_sequence",
    "multi_leg_complex",
    "has_holding",
    "has_navaid_radial",
    "has_direct_course",
}


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def formal200_rows() -> list[dict[str, Any]]:
    per_sample = GROUP1_V2_ROOT / "reports" / "D1_per_sample_v2.jsonl"
    if not per_sample.exists():
        raise FileNotFoundError(per_sample)
    rows = []
    for row in iter_jsonl(per_sample):
        rows.append(
            {
                "sample_id": row.get("sample_id"),
                "chart_id": row["chart_id"],
                "split": "formal200",
                "source_method_for_manifest": "D1_per_sample_v2",
            }
        )
    rows.sort(key=lambda item: item["chart_id"])
    if len(rows) != 200:
        raise RuntimeError(f"Expected 200 formal charts, found {len(rows)}")
    return rows


def answer_value(answers: dict[str, Any], field: str) -> Any:
    answer = answers.get(field, {})
    if not isinstance(answer, dict):
        return None
    if answer.get("status") != "present":
        return None
    return answer.get("value")


def target_tags(chart: dict[str, Any]) -> dict[str, Any]:
    missed = chart.get("missed_approach", {})
    legs = missed.get("legs", [])
    leg_count_answer = missed.get("leg_count", {})
    leg_count = leg_count_answer.get("value") if isinstance(leg_count_answer, dict) else None

    terminators: list[str] = []
    q4_types: list[str] = []
    tags: set[str] = set()
    field_family_counts: Counter[str] = Counter()

    for leg in legs:
        answers = leg.get("answers", {}) if isinstance(leg, dict) else {}
        terminator = answer_value(answers, "Q_terminator")
        if isinstance(terminator, str):
            terminators.append(terminator)
            field_family_counts["Q_terminator"] += 1
        if answer_value(answers, "Q1_fix_ident") is not None:
            field_family_counts["Q1_fix_ident"] += 1
        if answer_value(answers, "Q2_altitude_constraint") is not None:
            field_family_counts["Q2_altitude_constraint"] += 1
            tags.add("has_altitude_constraint")
        if answer_value(answers, "Q3_turn") is not None:
            field_family_counts["Q3_turn"] += 1
            tags.add("has_turn")
        q4 = answer_value(answers, "Q4_course_or_radial")
        if isinstance(q4, dict):
            field_family_counts["Q4_course_or_radial"] += 1
            tags.add("has_course_radial")
            q4_type = q4.get("type")
            if isinstance(q4_type, str):
                q4_types.append(q4_type)
                tags.add(f"has_q4_type_{q4_type}")
                if q4_type == "navaid_radial":
                    tags.add("has_navaid_radial")
                if q4_type == "course_deg":
                    tags.add("has_course_deg")
                if q4_type == "direct":
                    tags.add("has_direct_course")
        q5 = answer_value(answers, "Q5_hold_params")
        if isinstance(q5, dict):
            field_family_counts["Q5_hold_params"] += 1
            tags.add("has_holding")
            if q5.get("leg_time_min") is not None:
                tags.add("has_hold_time")
            if q5.get("leg_distance_nm") is not None:
                tags.add("has_hold_distance")

    if "CA" in terminators:
        tags.add("has_ca_leg")
    if "DF" in terminators:
        tags.add("has_df_leg")
    if "HM" in terminators:
        tags.add("has_hm_leg")
        tags.add("has_holding")
    if any(a == "CA" and b == "DF" for a, b in zip(terminators, terminators[1:])):
        tags.add("ca_df_sequence")
    if leg_count is not None and leg_count >= 4:
        tags.add("multi_leg_complex")
    if terminators:
        tags.add("terminator_present")

    core_challenge_hit_count = sum(1 for tag in CORE_CHALLENGE_TAGS if tag in tags)
    challenge_level = 0
    if core_challenge_hit_count == 1:
        challenge_level = 1
    elif 2 <= core_challenge_hit_count <= 3:
        challenge_level = 2
    elif core_challenge_hit_count >= 4:
        challenge_level = 3

    return {
        "challenge_tags": sorted(tags),
        "challenge_level": challenge_level,
        "core_challenge_hit_count": core_challenge_hit_count,
        "leg_count": leg_count,
        "terminators": terminators,
        "q4_types": sorted(set(q4_types)),
        "field_family_counts": dict(sorted(field_family_counts.items())),
    }


def choose_smoke20(tag_rows: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    by_chart = {row["chart_id"]: row for row in tag_rows}
    by_tag: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in tag_rows:
        for tag in row["challenge_tags"]:
            by_tag[tag].append(row)
    for rows in by_tag.values():
        rows.sort(key=lambda r: (r["challenge_level"], r["chart_id"]))

    selected: list[str] = []
    selection_reasons: dict[str, list[str]] = defaultdict(list)

    def add(chart_id: str, reason: str) -> None:
        if chart_id not in selected:
            selected.append(chart_id)
        selection_reasons[chart_id].append(reason)

    priority_tags = [
        "has_ca_leg",
        "has_df_leg",
        "has_hm_leg",
        "ca_df_sequence",
        "multi_leg_complex",
        "has_holding",
        "has_navaid_radial",
        "has_course_deg",
        "has_direct_course",
        "has_altitude_constraint",
        "has_turn",
        "has_hold_time",
        "has_hold_distance",
    ]
    for tag in priority_tags:
        candidates = by_tag.get(tag, [])
        if candidates:
            best = sorted(
                candidates,
                key=lambda r: (-r["core_challenge_hit_count"], r["chart_id"]),
            )[0]
            add(best["chart_id"], f"cover_target_tag:{tag}")

    combo_candidates = sorted(
        tag_rows,
        key=lambda r: (-r["core_challenge_hit_count"], -r["challenge_level"], r["chart_id"]),
    )
    for row in combo_candidates:
        if len(selected) >= 14:
            break
        add(row["chart_id"], "cover_high_tag_combination")

    core_like = [
        row
        for row in tag_rows
        if not {"has_ca_leg", "has_hm_leg", "ca_df_sequence", "multi_leg_complex"} & set(row["challenge_tags"])
    ]
    for row in sorted(core_like, key=lambda r: (r["core_challenge_hit_count"], r["chart_id"])):
        if len(selected) >= 18:
            break
        add(row["chart_id"], "stratified_core_or_low_challenge_control")

    for row in sorted(tag_rows, key=lambda r: (r["chart_id"])):
        if len(selected) >= 20:
            break
        add(row["chart_id"], "deterministic_fill_to_20")

    selected = selected[:20]
    selected_rows = [by_chart[chart_id] for chart_id in selected]
    coverage = Counter(tag for row in selected_rows for tag in row["challenge_tags"])
    metadata = {
        "selection_policy": "deterministic target-derived coverage; no model scores or method errors used",
        "selected_count": len(selected),
        "selection_reasons": dict(selection_reasons),
        "tag_coverage": dict(sorted(coverage.items())),
    }
    return selected, metadata


def build_inventory() -> dict[str, Any]:
    paths = {
        "group1_v2_root": GROUP1_V2_ROOT,
        "target_v2": TARGET_V2_DIR / "canonical_proxy_gt_chart_display_v2.json",
        "field_targets_v2": TARGET_V2_DIR / "field_targets_chart_display_v2.jsonl",
        "comparison_policy_v2": TARGET_V2_DIR / "comparison_policy_v2.jsonl",
        "schema": REPO_ROOT / "schemas" / "missed_approach_leg.schema.json",
        "scorer_v2": REPO_ROOT / "scripts" / "scorers" / "group1_canonical_field_scorer_v2.py",
        "scorer_strict": REPO_ROOT / "scripts" / "scorers" / "group1_canonical_field_scorer.py",
        "evidence_provenance": BASE_TARGET_DIR / "evidence_provenance.jsonl",
        "d1_per_sample_v2": GROUP1_V2_ROOT / "reports" / "D1_per_sample_v2.jsonl",
        "old_vs_new_score_delta": GROUP1_V2_ROOT / "reports" / "old_vs_new_score_delta.csv",
        "d1_summary_v2": GROUP1_V2_ROOT / "reports" / "D1_summary_v2.json",
        "c4_summary_v2": GROUP1_V2_ROOT / "reports" / "C4_summary_v2.json",
        "b1_summary_v2": GROUP1_V2_ROOT / "reports" / "B1_summary_v2.json",
    }
    inventory = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": ".",
        "base_commit": git_head(),
        "paths": {},
    }
    for name, path in paths.items():
        inventory["paths"][name] = {
            "path": rel(path),
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() and path.is_file() else None,
            "sha256": sha256_file(path),
        }
    return inventory


def git_head() -> str | None:
    head = REPO_ROOT / ".git"
    try:
        import subprocess

        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Experiment 5 inventory and smoke20 manifests.")
    parser.add_argument("--out-dir", default=EXPERIMENT5_DIR, type=Path)
    parser.add_argument("--run-dir", default=FORMAL_RUN_DIR, type=Path)
    args = parser.parse_args()

    out_dir = args.out_dir
    run_dir = args.run_dir
    manifest_dir = run_dir / "manifests"
    report_dir = run_dir / "reports"

    inventory = build_inventory()
    target_path = TARGET_V2_DIR / "canonical_proxy_gt_chart_display_v2.json"
    targets = load_json(target_path)
    formal_rows = formal200_rows()

    tag_rows = []
    for row in formal_rows:
        chart_id = row["chart_id"]
        tags = target_tags(targets[chart_id])
        tag_rows.append(
            {
                **row,
                **tags,
                "tag_source": "target_derived",
                "review_status": "auto",
            }
        )

    selected, smoke_meta = choose_smoke20(tag_rows)
    target_lookup = {row["chart_id"]: row for row in tag_rows}
    smoke_rows = [
        {
            **target_lookup[chart_id],
            "smoke_subset": "experiment5_smoke20_20260503_r1",
            "selection_reasons": smoke_meta["selection_reasons"].get(chart_id, []),
        }
        for chart_id in selected
    ]

    common_paths = {
        "target_v2_path": rel(target_path),
        "field_targets_v2_path": rel(TARGET_V2_DIR / "field_targets_chart_display_v2.jsonl"),
        "comparison_policy_v2_path": rel(TARGET_V2_DIR / "comparison_policy_v2.jsonl"),
        "schema_path": rel(REPO_ROOT / "schemas" / "missed_approach_leg.schema.json"),
        "scorer_v2_path": rel(REPO_ROOT / "scripts" / "scorers" / "group1_canonical_field_scorer_v2.py"),
        "strict_scorer_path": rel(REPO_ROOT / "scripts" / "scorers" / "group1_canonical_field_scorer.py"),
    }
    experiment_manifest = [{**row, **common_paths, "in_smoke20": row["chart_id"] in selected} for row in tag_rows]
    smoke_manifest = [{**row, **common_paths} for row in smoke_rows]

    write_json(out_dir / "artifact_inventory.json", inventory)
    write_jsonl(out_dir / "target_derived_tags.jsonl", tag_rows)
    write_jsonl(out_dir / "experiment5_input_manifest.jsonl", experiment_manifest)
    write_jsonl(out_dir / "smoke20_manifest.jsonl", smoke_manifest)
    write_json(manifest_dir / "smoke20_selection_summary.json", smoke_meta)
    write_jsonl(manifest_dir / "smoke20_manifest.jsonl", smoke_manifest)

    gold_text_template = [
        {
            "chart_id": row["chart_id"],
            "gold_ma_prose": "TBD_HUMAN_CORRECTED_MISSED_APPROACH_TEXT",
            "source": "human_corrected_from_chart",
            "checked_scopes": ["MISSED_APPROACH_TEXT"],
            "review_status": "todo",
            "reviewer": "TBD",
            "notes": "Do not copy target fields, Q_terminator, score, or canonical JSON here.",
        }
        for row in smoke_rows
    ]
    observable_template = [
        {
            "chart_id": row["chart_id"],
            "observable_id": f"{row['chart_id']}__obs_001",
            "observable_group_id": "ma_step_001",
            "source_regions": [],
            "evidence_region_ids": [],
            "checked_scopes": [
                "MISSED_APPROACH_TEXT",
                "PLAN_VIEW",
                "MISSED_APPROACH_DETAIL_AREA",
            ],
            "facts": {
                "visible_fix": None,
                "visible_altitude": None,
                "visible_turn_direction": None,
                "visible_course_or_radial": None,
                "holding_pattern_depicted": None,
                "holding_fix": None,
                "holding_inbound_course_deg": None,
                "hold_leg_time_explicit": None,
                "hold_leg_distance_explicit": None,
            },
            "review_status": "todo",
            "notes": "Observable facts only. Do not write Q_terminator, target leg index, expected value, score, or final canonical JSON.",
        }
        for row in smoke_rows
    ]
    write_jsonl(out_dir / "gold_ma_text_smoke20_template.jsonl", gold_text_template)
    write_jsonl(out_dir / "gold_observable_smoke20_template.jsonl", observable_template)

    tag_counter = Counter(tag for row in tag_rows for tag in row["challenge_tags"])
    smoke_tag_counter = Counter(tag for row in smoke_rows for tag in row["challenge_tags"])
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "formal200_count": len(tag_rows),
        "smoke20_count": len(smoke_rows),
        "formal200_tag_counts": dict(sorted(tag_counter.items())),
        "smoke20_tag_counts": dict(sorted(smoke_tag_counter.items())),
        "smoke20_chart_ids": selected,
        "next_required_inputs": [
            "gold_ma_text.jsonl or completed gold_ma_text_smoke20_template.jsonl",
            "roi_manifest_for_experiment5.jsonl",
            "roi_ocr_manifest.jsonl",
            "rule_registry.yaml",
            "gold_observable_evidence.jsonl or completed gold_observable_smoke20_template.jsonl",
        ],
    }
    write_json(report_dir / "experiment5_artifact_inventory.json", {"inventory": inventory, "summary": summary})
    report_md = [
        "# 实验组5 artifact inventory 与 smoke20 选择报告",
        "",
        f"- base commit: `{inventory['base_commit']}`",
        f"- formal200 样本数: {len(tag_rows)}",
        f"- smoke20 样本数: {len(smoke_rows)}",
        "- smoke20 选择原则: deterministic target-derived coverage; 不使用模型分数或错误来选样本",
        "",
        "## smoke20 chart_id",
        "",
    ]
    report_md.extend(f"- `{chart_id}`: {', '.join(smoke_meta['selection_reasons'].get(chart_id, []))}" for chart_id in selected)
    report_md.extend(
        [
            "",
            "## smoke20 tag 覆盖",
            "",
            "| tag | count |",
            "|---|---:|",
        ]
    )
    report_md.extend(f"| `{tag}` | {count} |" for tag, count in sorted(smoke_tag_counter.items()))
    report_md.extend(
        [
            "",
            "## 仍需补齐",
            "",
            "- `gold_ma_text.jsonl` 或完成 smoke20 gold text 模板。",
            "- `roi_manifest_for_experiment5.jsonl`。",
            "- `roi_ocr_manifest.jsonl`。",
            "- `rule_registry.yaml`。",
            "- `gold_observable_evidence.jsonl` 或完成 smoke20 observable 模板。",
        ]
    )
    (report_dir / "experiment5_artifact_inventory_zh.md").parent.mkdir(parents=True, exist_ok=True)
    (report_dir / "experiment5_artifact_inventory_zh.md").write_text(
        "\n".join(report_md) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
