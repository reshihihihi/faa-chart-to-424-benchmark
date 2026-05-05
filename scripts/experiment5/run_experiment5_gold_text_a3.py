from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_a1_a2_rules_pilot10 import (  # noqa: E402
    answer,
    blank_leg,
    canonical_empty,
    clean_ident,
    extract_rules,
    first_altitude,
    hold_params,
    navaid_radial,
    normalize_text,
    schema_degree,
)
from run_pilot10_anthropic import sha256_file  # noqa: E402
from scorers.group1_canonical_field_scorer import score_canonical as score_canonical_strict  # noqa: E402
from scorers.group1_canonical_field_scorer_v2 import (  # noqa: E402
    load_policy,
    score_canonical as score_canonical_v2,
    validate_canonical,
)


DEFAULT_RUN_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_gold_text_20260503_r1"
EXPERIMENT5_DIR = REPO_ROOT / "benchmark_exports" / "derived" / "v2" / "experiment5_diagnostic"
GOLD_TEXT_PATH = EXPERIMENT5_DIR / "gold_ma_text_smoke20_template.jsonl"
SAMPLE_MANIFEST = (
    REPO_ROOT
    / "benchmark_exports"
    / "derived"
    / "v2"
    / "formal300"
    / "split_candidates"
    / "split_50_200_50_seed20260437"
    / "sample_manifest_50_200_50_seed20260437.jsonl"
)
TARGET_V2 = (
    REPO_ROOT
    / "benchmark_exports"
    / "derived"
    / "v2"
    / "formal300"
    / "targets"
    / "scoring_equivalence_v2"
    / "canonical_proxy_gt_chart_display_v2.json"
)
POLICY_V2 = (
    REPO_ROOT
    / "benchmark_exports"
    / "derived"
    / "v2"
    / "formal300"
    / "targets"
    / "scoring_equivalence_v2"
    / "comparison_policy_v2.jsonl"
)
SCHEMA_PATH = REPO_ROOT / "schemas" / "missed_approach_leg.schema.json"
RULE_REGISTRY = EXPERIMENT5_DIR / "rule_registry.yaml"

METHOD = "A3_GoldText_Rules"
FORBIDDEN_METHOD_INPUT_KEYS = [
    "target",
    "score",
    "canonical_answer",
    "canonical_leg_index",
    "Q_terminator",
    "leg_type",
    "field_review_v2",
]


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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + ("\n" if value and not value.endswith("\n") else ""), encoding="utf-8")


def rel(path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def load_sample_meta() -> dict[str, dict[str, Any]]:
    return {row["chart_id"]: row for row in read_jsonl(SAMPLE_MANIFEST)}


def direct_fix(text: str) -> str | None:
    match = re.search(r"\bDIRECT\s+([A-Z0-9]{2,5})\b", text)
    return clean_ident(match.group(1) if match else None)


def track_to_fix_matches(text: str) -> list[tuple[float, str]]:
    patterns = [
        r"\b(?:ON\s+)?(?:TRACK|TRK|COURSE|CRS|HEADING|HDG)\s+([0-3]?[0-9]{2})\s*(?:DEG|DEGREES|°|º|˚)?\s+TO\s+([A-Z0-9]{2,5})\b",
        r"\b([0-3]?[0-9]{2})\s*(?:DEG|DEGREES|°|º|˚)?\s*(?:TRACK|TRK|COURSE|CRS|HEADING|HDG)\s+TO\s+([A-Z0-9]{2,5})\b",
    ]
    matches: list[tuple[float, str]] = []
    seen: set[tuple[float, str]] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            degree = schema_degree(match.group(1))
            ident = clean_ident(match.group(2))
            if degree is None or not ident:
                continue
            key = (degree, ident)
            if key not in seen:
                matches.append(key)
                seen.add(key)
    return matches


def radial_to_fix_match(text: str) -> tuple[dict[str, Any], str] | None:
    radial = navaid_radial(text)
    if not radial:
        return None
    radial_token = f"R-{int(radial['radial_deg']):03d}"
    after_radial = text.split(radial_token, 1)[-1]
    match = re.search(r"\bTO\s+([A-Z0-9]{2,5})\b", after_radial)
    ident = clean_ident(match.group(1) if match else None)
    if not ident:
        return None
    return radial, ident


def turn_value(text: str) -> str | None:
    if re.search(r"\bLEFT\s+TURN\b|\bCLIMBING\s+LEFT\s+TURN\b|\bLT\s+TURN\b", text):
        return "LEFT"
    if re.search(r"\bRIGHT\s+TURN\b|\bCLIMBING\s+RIGHT\s+TURN\b|\bRT\s+TURN\b", text):
        return "RIGHT"
    return None


def hold_fix(text: str, fallback_fix: str | None) -> str | None:
    patterns = [
        r"\bTO\s+([A-Z0-9]{2,5})\s+(?:AND\s+)?HOLD\b",
        r"\b([A-Z0-9]{2,5})\s+(?:AND\s+)?HOLD\b",
        r"\bHOLD(?:ING)?\s+(?:AT|ON)\s+([A-Z0-9]{2,5})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        ident = clean_ident(match.group(1) if match else None)
        if ident:
            return ident
    return fallback_fix


def append_ca_leg(
    legs: list[dict[str, Any]],
    altitude: int | None,
    turn: str | None,
    diagnostics: list[dict[str, Any]],
) -> None:
    leg = blank_leg(len(legs) + 1)
    answers = leg["answers"]
    answers["Q_terminator"] = answer("present", "CA")
    answers["Q1_fix_ident"] = answer("not_applicable")
    if altitude is not None:
        answers["Q2_altitude_constraint"] = answer(
            "present",
            {"desc": "AT_OR_ABOVE", "altitude_ft": altitude, "altitude_2_ft": None},
        )
    answers["Q4_course_or_radial"] = answer("not_applicable")
    answers["Q5_hold_params"] = answer("not_applicable")
    if turn is not None:
        answers["Q3_turn"] = answer("present", turn)
    legs.append(leg)
    diagnostics.append(
        {
            "leg_index": leg["leg_index"],
            "rule_id": "R_B4_CLIMB_ALTITUDE_TO_CA",
            "altitude": altitude,
            "turn": turn,
        }
    )


def append_df_leg(legs: list[dict[str, Any]], fix: str, diagnostics: list[dict[str, Any]]) -> None:
    leg = blank_leg(len(legs) + 1)
    answers = leg["answers"]
    answers["Q_terminator"] = answer("present", "DF")
    answers["Q1_fix_ident"] = answer("present", fix)
    answers["Q2_altitude_constraint"] = answer("not_applicable")
    answers["Q3_turn"] = answer("not_applicable")
    answers["Q4_course_or_radial"] = answer("present", {"type": "direct"})
    answers["Q5_hold_params"] = answer("not_applicable")
    legs.append(leg)
    diagnostics.append({"leg_index": leg["leg_index"], "rule_id": "R_B4_DIRECT_TO_DF", "fix": fix})


def append_tf_leg(
    legs: list[dict[str, Any]],
    degree: float,
    fix: str,
    diagnostics: list[dict[str, Any]],
) -> None:
    leg = blank_leg(len(legs) + 1)
    answers = leg["answers"]
    answers["Q_terminator"] = answer("present", "TF")
    answers["Q1_fix_ident"] = answer("present", fix)
    answers["Q2_altitude_constraint"] = answer("not_applicable")
    answers["Q3_turn"] = answer("not_applicable")
    answers["Q4_course_or_radial"] = answer("present", {"type": "course_deg", "course_deg": degree})
    answers["Q5_hold_params"] = answer("not_applicable")
    legs.append(leg)
    diagnostics.append(
        {
            "leg_index": leg["leg_index"],
            "rule_id": "R_B4_COURSE_OR_RADIAL",
            "subrule": "track_to_fix_to_TF",
            "fix": fix,
            "course_deg": degree,
        }
    )


def append_cf_leg(
    legs: list[dict[str, Any]],
    radial: dict[str, Any],
    fix: str,
    diagnostics: list[dict[str, Any]],
) -> None:
    leg = blank_leg(len(legs) + 1)
    answers = leg["answers"]
    answers["Q_terminator"] = answer("present", "CF")
    answers["Q1_fix_ident"] = answer("present", fix)
    answers["Q2_altitude_constraint"] = answer("not_applicable")
    answers["Q3_turn"] = answer("not_applicable")
    answers["Q4_course_or_radial"] = answer("present", radial)
    answers["Q5_hold_params"] = answer("not_applicable")
    legs.append(leg)
    diagnostics.append(
        {
            "leg_index": leg["leg_index"],
            "rule_id": "R_B4_COURSE_OR_RADIAL",
            "subrule": "radial_to_fix_to_CF",
            "fix": fix,
            "radial": radial,
        }
    )


def append_hm_leg(
    legs: list[dict[str, Any]],
    fix: str | None,
    text: str,
    diagnostics: list[dict[str, Any]],
) -> None:
    leg = blank_leg(len(legs) + 1)
    answers = leg["answers"]
    answers["Q_terminator"] = answer("present", "HM")
    answers["Q1_fix_ident"] = answer("present", fix) if fix else answer("unknown")
    answers["Q2_altitude_constraint"] = answer("not_applicable")
    answers["Q3_turn"] = answer("not_applicable")
    answers["Q4_course_or_radial"] = answer("not_applicable")
    answers["Q5_hold_params"] = answer("present", hold_params(text))
    legs.append(leg)
    diagnostics.append({"leg_index": leg["leg_index"], "rule_id": "R_B4_HOLD_TO_HM", "fix": fix})


def build_gold_text_prediction(sample: dict[str, Any], gold_ma_prose: str) -> tuple[dict[str, Any], dict[str, Any]]:
    row = {
        "chart_id": sample["chart_id"],
        "airport": sample["airport"],
        "proc_ident": sample["proc_ident"],
        "chart_name": sample["chart_name"],
    }
    prediction = canonical_empty(row)
    normalized = normalize_text(gold_ma_prose)
    legs: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []

    altitude = first_altitude(normalized)
    turn = turn_value(normalized)
    d_fix = direct_fix(normalized)
    radial_match = radial_to_fix_match(normalized)
    tracks = track_to_fix_matches(normalized)
    has_hold = bool(re.search(r"\bHOLD(?:ING)?\b", normalized))

    if altitude is not None:
        append_ca_leg(
            legs,
            altitude,
            turn if not d_fix and not tracks and radial_match is None else None,
            evidence,
        )
    if d_fix:
        append_df_leg(legs, d_fix, evidence)
    radial_fix = None
    if radial_match:
        radial, radial_fix = radial_match
        append_cf_leg(legs, radial, radial_fix, evidence)
    for degree, fix in tracks:
        append_tf_leg(legs, degree, fix, evidence)
    if has_hold:
        fallback_fix = tracks[-1][1] if tracks else radial_fix or d_fix
        append_hm_leg(legs, hold_fix(normalized, fallback_fix), normalized, evidence)

    fallback_used = False
    fallback_diagnostics = None
    if not legs:
        prediction, fallback_diagnostics = extract_rules(row, gold_ma_prose)
        fallback_used = True
    else:
        prediction["missed_approach"]["leg_count"] = answer("present", len(legs))
        prediction["missed_approach"]["legs"] = legs

    diagnostics = {
        "runner": "experiment5_a3_gold_ma_prose_rules_v1",
        "method": METHOD,
        "rule_registry": rel(RULE_REGISTRY),
        "rule_registry_sha256": sha256_file(RULE_REGISTRY),
        "rule_registry_status": "candidate_for_smoke_diagnostic_not_formal_reviewed",
        "allowed_method_input": "adjudicated gold_ma_prose only",
        "uses_gold_ma_text": True,
        "uses_field_candidates": False,
        "uses_target_or_score": False,
        "uses_cifp_or_arinc_424": False,
        "normalization": "uppercase_whitespace_dash_punctuation_only",
        "gold_ma_prose_normalized": normalized,
        "detected": {
            "altitude": altitude,
            "turn": turn,
            "direct_fix": d_fix,
            "radial_to_fix": radial_match,
            "tracks_to_fix": tracks,
            "has_hold": has_hold,
        },
        "rule_evidence": evidence,
        "fallback_legacy_extract_rules_used": fallback_used,
        "fallback_legacy_diagnostics": fallback_diagnostics,
        "abstain_policy": "unknown_or_not_applicable_when_allowed_gold_text_is_insufficient",
    }
    return prediction, diagnostics


def score_and_write(
    *,
    chart_id: str,
    pred: dict[str, Any],
    target: dict[str, Any],
    policies: dict[tuple[str, str], dict[str, Any]],
    run_dir: Path,
) -> dict[str, Any]:
    score_v2 = score_canonical_v2(pred, target, chart_id=chart_id, policies=policies)
    score_strict = score_canonical_strict(pred, target)
    write_json(run_dir / METHOD / "scores_v2" / f"{chart_id}.json", score_v2)
    write_json(run_dir / METHOD / "scores_strict" / f"{chart_id}.json", score_strict)
    return {
        "correct": score_v2["correct"],
        "total": score_v2["total"],
        "accuracy": score_v2["accuracy"],
        "scoring_mode": "chart_display_aware_v2",
        "v2": {key: score_v2[key] for key in ["correct", "total", "accuracy"]},
        "strict": {key: score_strict[key] for key in ["correct", "total", "accuracy"]},
        "v2_minus_strict_correct": score_v2["correct"] - score_strict["correct"],
        "v2_minus_strict_accuracy": (
            score_v2["accuracy"] - score_strict["accuracy"]
            if score_v2["accuracy"] is not None and score_strict["accuracy"] is not None
            else None
        ),
    }


def field_family(field: str) -> str:
    if field == "leg_count":
        return field
    if "." in field:
        return field.rsplit(".", 1)[-1]
    return field


def summarize_results(results: list[dict[str, Any]], run_dir: Path) -> dict[str, Any]:
    scored = [row["score"] for row in results if row.get("score")]
    correct = sum(row["v2"]["correct"] for row in scored)
    total = sum(row["v2"]["total"] for row in scored)
    strict_correct = sum(row["strict"]["correct"] for row in scored)
    strict_total = sum(row["strict"]["total"] for row in scored)

    families: dict[str, dict[str, Any]] = defaultdict(lambda: {"correct": 0, "total": 0})
    for row in results:
        chart_id = row["chart_id"]
        score_path = run_dir / METHOD / "scores_v2" / f"{chart_id}.json"
        if not score_path.exists():
            continue
        score = json.loads(score_path.read_text(encoding="utf-8"))
        for score_row in score.get("rows", []):
            family = field_family(score_row["field"])
            families[family]["total"] += 1
            families[family]["correct"] += int(bool(score_row.get("correct")))

    family_rows = []
    for family, counts in sorted(families.items()):
        total_family = counts["total"]
        correct_family = counts["correct"]
        family_rows.append(
            {
                "field": family,
                "correct": correct_family,
                "total": total_family,
                "accuracy": correct_family / total_family if total_family else None,
            }
        )

    return {
        "method": METHOD,
        "samples_total": len(results),
        "schema_valid": sum(1 for row in results if row.get("validation_error_count") == 0),
        "samples_scored": len(scored),
        "score_v2": {
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total else None,
        },
        "score_strict": {
            "correct": strict_correct,
            "total": strict_total,
            "accuracy": strict_correct / strict_total if strict_total else None,
        },
        "v2_minus_strict_correct": correct - strict_correct,
        "v2_minus_strict_accuracy": (
            (correct / total) - (strict_correct / strict_total) if total and strict_total else None
        ),
        "field_family": family_rows,
    }


def scan_gold_inputs_for_forbidden_keys(gold_rows: list[dict[str, Any]]) -> dict[str, Any]:
    method_input_hits: dict[str, list[str]] = {key: [] for key in FORBIDDEN_METHOD_INPUT_KEYS}
    source_row_hits: dict[str, list[str]] = {key: [] for key in FORBIDDEN_METHOD_INPUT_KEYS}
    method_input_payloads = []
    for row in gold_rows:
        payload = {
            "chart_id": row.get("chart_id"),
            "gold_ma_prose": row.get("gold_ma_prose"),
            "source": row.get("source"),
            "review_status": row.get("review_status"),
            "checked_scopes": row.get("checked_scopes"),
        }
        method_input_payloads.append(payload)
        for key in FORBIDDEN_METHOD_INPUT_KEYS:
            if key in payload:
                method_input_hits[key].append(str(row.get("chart_id")))
            if key in row:
                source_row_hits[key].append(str(row.get("chart_id")))
    nonempty_method_hits = {
        key: sorted(set(chart_ids)) for key, chart_ids in method_input_hits.items() if chart_ids
    }
    nonempty_source_hits = {
        key: sorted(set(chart_ids)) for key, chart_ids in source_row_hits.items() if chart_ids
    }
    return {
        "scanned_method_input_payload_count": len(method_input_payloads),
        "forbidden_key_hits": nonempty_method_hits,
        "source_gold_row_forbidden_key_hits": nonempty_source_hits,
        "hard_leakage_detected": bool(nonempty_method_hits),
    }


def render_report(summary: dict[str, Any], no_leakage: dict[str, Any], b2_status: dict[str, Any]) -> str:
    score = summary["score_v2"]
    strict = summary["score_strict"]
    lines = [
        "# 实验组5 A3 gold text smoke 运行报告",
        "",
        f"- run_id: `{summary['run_id']}`",
        f"- 方法: `{METHOD}`",
        f"- 样本数: {summary['samples_total']}",
        "- 输入: adjudicated `gold_ma_prose` only",
        "- 规则注册表状态: `candidate_for_smoke_diagnostic_not_formal_reviewed`",
        "- target/score 使用: 只在 prediction 写盘后评分使用，不进入方法输入",
        "",
        "## A3 结果",
        "",
        "| 方法 | schema-valid | v2 正确/总数 | v2 accuracy | strict accuracy |",
        "|---|---:|---:|---:|---:|",
        (
            f"| `{METHOD}` | {summary['schema_valid']}/{summary['samples_total']} | "
            f"{score['correct']}/{score['total']} | {score['accuracy']:.2%} | {strict['accuracy']:.2%} |"
        ),
        "",
        "## 字段族表现",
        "",
        "| 字段 | 正确/总数 | accuracy |",
        "|---|---:|---:|",
    ]
    for row in summary["field_family"]:
        lines.append(f"| `{row['field']}` | {row['correct']}/{row['total']} | {row['accuracy']:.2%} |")
    lines.extend(
        [
            "",
            "## No-leakage 审查",
            "",
            f"- target_used_for_prediction: `{no_leakage['target_used_for_prediction']}`",
            f"- score_used_for_prediction: `{no_leakage['score_used_for_prediction']}`",
            f"- cifp_or_arinc_424_used_for_prediction: `{no_leakage['cifp_or_arinc_424_used_for_prediction']}`",
            f"- field_review_v2_used_for_prediction: `{no_leakage['field_review_v2_used_for_prediction']}`",
            f"- hard_leakage_detected: `{no_leakage['hard_leakage_detected']}`",
            f"- forbidden_key_hits: `{json.dumps(no_leakage['forbidden_key_hits'], ensure_ascii=False)}`",
            "",
            "## B2 当前状态",
            "",
            f"- B2a/B2b: `{b2_status['status']}`",
            f"- 原因: {b2_status['reason']}",
            "",
            "## 解释边界",
            "",
            "- 这是 smoke20 诊断结果，不是 formal200 结论。",
            "- A3 消除了 MA prose OCR 错误，但仍不提供图形区 gold observable，也不提供 target 字段答案。",
            "- rule_registry 尚未完成正式审查，因此该结果可以用于诊断下一步，不宜直接作为论文 formal claim。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Experiment 5 A3 gold MA prose deterministic rules.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--gold-text", type=Path, default=GOLD_TEXT_PATH)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.run_dir.exists() and not args.force:
        raise RuntimeError(f"Run directory already exists: {args.run_dir}; pass --force to update it.")

    gold_rows = read_jsonl(args.gold_text)[: args.limit]
    chart_ids = [row["chart_id"] for row in gold_rows]
    missing_gold = [row["chart_id"] for row in gold_rows if not str(row.get("gold_ma_prose") or "").strip()]
    if missing_gold:
        raise RuntimeError(f"Missing gold_ma_prose for chart_ids: {missing_gold}")

    samples = load_sample_meta()
    targets = json.loads(TARGET_V2.read_text(encoding="utf-8"))
    policies = load_policy(POLICY_V2)
    canonical_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(canonical_schema)

    missing_samples = sorted(set(chart_ids) - set(samples))
    missing_targets = sorted(set(chart_ids) - set(targets))
    if missing_samples or missing_targets:
        raise RuntimeError(f"Missing samples={missing_samples}, missing_targets={missing_targets}")

    run_manifest = {
        "run_id": args.run_dir.name,
        "experiment_group": 5,
        "method": METHOD,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_scope": "experiment5_smoke20_gold_ma_prose",
        "limit": args.limit,
        "chart_ids": chart_ids,
        "gold_text_path": rel(args.gold_text),
        "gold_text_sha256": sha256_file(args.gold_text),
        "sample_manifest": rel(SAMPLE_MANIFEST),
        "sample_manifest_sha256": sha256_file(SAMPLE_MANIFEST),
        "target_v2": rel(TARGET_V2),
        "target_v2_sha256": sha256_file(TARGET_V2),
        "policy_v2": rel(POLICY_V2),
        "policy_v2_sha256": sha256_file(POLICY_V2),
        "schema": rel(SCHEMA_PATH),
        "schema_sha256": sha256_file(SCHEMA_PATH),
        "rule_registry": rel(RULE_REGISTRY),
        "rule_registry_sha256": sha256_file(RULE_REGISTRY),
        "rule_registry_status": "candidate_for_smoke_diagnostic_not_formal_reviewed",
        "method_boundary": {
            "allowed_inputs": [
                "chart_id",
                "airport",
                "approach_ident",
                "chart_name",
                "adjudicated gold_ma_prose",
                "canonical JSON schema contract",
                "candidate rule registry",
            ],
            "forbidden_inputs": FORBIDDEN_METHOD_INPUT_KEYS
            + [
                "canonical JSON target",
                "scorer output",
                "CIFP or ARINC 424 records",
                "field review records",
                "gold observable facts",
                "previous model or rule outputs for same chart",
                "web search",
            ],
        },
        "target_used_for_prediction": False,
        "score_used_for_prediction": False,
        "cifp_or_arinc_424_used_for_prediction": False,
        "gold_observable_used_for_prediction": False,
        "gold_ma_text_used_for_prediction": True,
        "field_candidates_used_for_prediction": False,
        "field_review_v2_used_for_prediction": False,
    }
    write_json(args.run_dir / "run_manifest_a3_gold_text.json", run_manifest)

    all_results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    input_manifest: list[dict[str, Any]] = []
    for gold_row in gold_rows:
        chart_id = gold_row["chart_id"]
        sample = samples[chart_id]
        gold_text = str(gold_row["gold_ma_prose"]).strip()
        input_path = args.run_dir / METHOD / "inputs" / "gold_ma_text" / f"{chart_id}.txt"
        write_text(input_path, gold_text)
        input_manifest.append(
            {
                "chart_id": chart_id,
                "gold_ma_text_path": rel(input_path),
                "gold_ma_text_sha256": sha256_file(input_path),
                "source": gold_row.get("source"),
                "review_status": gold_row.get("review_status"),
                "checked_scopes": gold_row.get("checked_scopes"),
            }
        )

        pred, diagnostics = build_gold_text_prediction(sample, gold_text)
        write_json(args.run_dir / METHOD / "canonical_json" / f"{chart_id}.json", pred)
        write_json(args.run_dir / METHOD / "rule_diagnostics" / f"{chart_id}.json", diagnostics)
        errors = validate_canonical(pred, validator)
        write_json(args.run_dir / METHOD / "validation" / f"{chart_id}.json", errors)
        item: dict[str, Any] = {
            "method": METHOD,
            "chart_id": chart_id,
            "sample_id": sample["sample_id"],
            "uses_gold_ma_text": True,
            "uses_field_candidates": False,
            "validation_error_count": len(errors),
            "validation_errors": errors,
            "score": None,
        }
        if errors:
            failures.append({"method": METHOD, "chart_id": chart_id, "error": "schema_validation_failed"})
        else:
            item["score"] = score_and_write(
                chart_id=chart_id,
                pred=pred,
                target=targets[chart_id],
                policies=policies,
                run_dir=args.run_dir,
            )
        all_results.append(item)

    write_jsonl(args.run_dir / "reports" / "a3_gold_text_results.jsonl", all_results)
    write_jsonl(args.run_dir / "reports" / "a3_gold_text_failures.jsonl", failures)
    write_jsonl(args.run_dir / "manifests" / "a3_gold_text_method_inputs.jsonl", input_manifest)

    summary = summarize_results(all_results, args.run_dir)
    summary.update(
        {
            "run_id": args.run_dir.name,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "chart_ids": chart_ids,
            "failure_count": len(failures),
            "failures": failures,
        }
    )
    write_json(args.run_dir / "reports" / "a3_gold_text_summary.json", summary)

    scan = scan_gold_inputs_for_forbidden_keys(gold_rows)
    no_leakage = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": METHOD,
        "target_used_for_prediction": False,
        "score_used_for_prediction": False,
        "cifp_or_arinc_424_used_for_prediction": False,
        "gold_observable_used_for_prediction": False,
        "gold_ma_text_used_for_prediction": True,
        "field_candidates_used_for_prediction": False,
        "field_review_v2_used_for_prediction": False,
        "forbidden_key_hits": scan["forbidden_key_hits"],
        "source_gold_row_forbidden_key_hits": scan["source_gold_row_forbidden_key_hits"],
        "hard_leakage_detected": scan["hard_leakage_detected"],
        "note": "A3 intentionally uses gold_ma_prose; target and score are loaded only after predictions are written for evaluation.",
    }
    write_json(args.run_dir / "reports" / "a3_gold_text_no_leakage_report.json", no_leakage)

    b2_status = {
        "status": "not_run_pending_model_server",
        "reason": (
            "B2a/B2b require an OpenAI-compatible model server. "
            f"No successful model-server call is recorded by {Path(__file__).name}; run B2 only after service readiness is confirmed."
        ),
        "default_expected_base_url": os.environ.get("OPENAI_BASE_URL")
        or os.environ.get("CODEX_PROXY_BASE_URL")
        or "http://127.0.0.1:8080/v1",
    }
    write_json(args.run_dir / "reports" / "b2_gold_text_status.json", b2_status)
    write_text(args.run_dir / "reports" / "experiment5_a3_gold_text_execution_report_zh.md", render_report(summary, no_leakage, b2_status))

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failures and not no_leakage["hard_leakage_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
