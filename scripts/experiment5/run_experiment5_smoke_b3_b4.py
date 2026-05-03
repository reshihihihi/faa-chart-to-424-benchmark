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

from model_clients import call_model_json, create_model_client, model_api_manifest, save_model_response  # noqa: E402
from run_a1_a2_rules_pilot10 import (  # noqa: E402
    answer,
    blank_leg,
    canonical_empty,
    clean_ident,
    first_altitude,
    hold_params,
    navaid_radial,
    normalize_text,
    schema_degree,
)
from run_group1_pilot10_gpt54 import build_schema_retry_prompt  # noqa: E402
from run_pilot10_anthropic import sha256_file  # noqa: E402
from scorers.group1_canonical_field_scorer import score_canonical as score_canonical_strict  # noqa: E402
from scorers.group1_canonical_field_scorer_v2 import (  # noqa: E402
    load_policy,
    score_canonical as score_canonical_v2,
    validate_canonical,
)


RUN_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_smoke_20260503_r2"
EXPERIMENT5_DIR = REPO_ROOT / "benchmark_exports" / "derived" / "v2" / "experiment5_diagnostic"
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
PROMPT_PATH = REPO_ROOT / "prompts" / "paper_v2" / "experiment5_roi_ocr_candidates_to_canonical.zh_v1_region_priority.md"
INPUT_MANIFEST = EXPERIMENT5_DIR / "roi_ocr_candidate_input_manifest_smoke20.jsonl"
RULE_REGISTRY = EXPERIMENT5_DIR / "rule_registry.yaml"

METHOD_TO_PROFILE = {
    "B3_T": "T",
    "B3_PD": "PD",
    "B3_TPD": "TPD",
    "B4_TPD": "TPD",
}
METHOD_DESCRIPTION = {
    "B3_T": "MISSED_APPROACH_TEXT ROI OCR + region-aware ROI field_candidates + LLM -> canonical JSON",
    "B3_PD": "PLAN_VIEW + MISSED_APPROACH_DETAIL_AREA ROI OCR + region-aware ROI field_candidates + LLM -> canonical JSON",
    "B3_TPD": "MISSED_APPROACH_TEXT + PLAN_VIEW + MISSED_APPROACH_DETAIL_AREA ROI OCR + region-aware ROI field_candidates + LLM -> canonical JSON",
    "B4_TPD": "MISSED_APPROACH_TEXT + PLAN_VIEW + MISSED_APPROACH_DETAIL_AREA ROI OCR + region-aware ROI field_candidates + deterministic rules -> canonical JSON",
}
PROFILE_DESCRIPTION = {
    "T": "Only MISSED_APPROACH_TEXT source-view OCR is provided.",
    "PD": "Only PLAN_VIEW and MISSED_APPROACH_DETAIL_AREA source-view OCR are provided; MISSED_APPROACH_TEXT is withheld.",
    "TPD": "MISSED_APPROACH_TEXT, PLAN_VIEW, and MISSED_APPROACH_DETAIL_AREA source-view OCR are provided with region labels.",
}


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
    path.write_text(value, encoding="utf-8")


def rel(path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def load_sample_meta() -> dict[str, dict[str, Any]]:
    return {row["chart_id"]: row for row in read_jsonl(SAMPLE_MANIFEST)}


def load_candidate_inputs() -> dict[tuple[str, str], dict[str, Any]]:
    return {(row["chart_id"], row["region_profile"]): row for row in read_jsonl(INPUT_MANIFEST)}


def prompt_for(
    *,
    method: str,
    profile: str,
    sample: dict[str, Any],
    roi_text: str,
    field_candidates: dict[str, Any],
) -> str:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    replacements = {
        "{{method_id}}": method,
        "{{region_profile}}": profile,
        "{{region_description}}": PROFILE_DESCRIPTION[profile],
        "{{chart_id}}": sample["chart_id"],
        "{{airport}}": sample["airport"],
        "{{approach_ident}}": sample["proc_ident"],
        "{{chart_name}}": sample["chart_name"],
        "{{roi_ocr_text}}": roi_text,
        "{{field_candidates_json}}": json.dumps(field_candidates, ensure_ascii=False, indent=2),
    }
    for key, value in replacements.items():
        prompt = prompt.replace(key, str(value))
    return prompt


def score_and_write(
    *,
    method: str,
    chart_id: str,
    pred: dict[str, Any],
    target: dict[str, Any],
    policies: dict[tuple[str, str], dict[str, Any]],
    run_dir: Path,
) -> dict[str, Any]:
    score_v2 = score_canonical_v2(pred, target, chart_id=chart_id, policies=policies)
    score_strict = score_canonical_strict(pred, target)
    write_json(run_dir / method / "scores_v2" / f"{chart_id}.json", score_v2)
    write_json(run_dir / method / "scores_strict" / f"{chart_id}.json", score_strict)
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


def split_region_text(roi_text: str) -> dict[str, str]:
    pattern = re.compile(r"^\[(MISSED_APPROACH_TEXT|PLAN_VIEW|MISSED_APPROACH_DETAIL_AREA)\]\s*$", re.MULTILINE)
    matches = list(pattern.finditer(roi_text))
    regions: dict[str, str] = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(roi_text)
        regions[match.group(1)] = roi_text[start:end].strip()
    return regions


def candidates_by_region(field_candidates: dict[str, Any], source_region: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key, items in field_candidates.get("field_candidates", {}).items():
        for item in items:
            if item.get("source_region") == source_region:
                fixed = dict(item)
                fixed["candidate_array"] = key
                out.append(fixed)
    return out


def instruction_text_from_candidates(field_candidates: dict[str, Any], roi_text: str) -> tuple[str, list[dict[str, Any]]]:
    ma_text = split_region_text(roi_text).get("MISSED_APPROACH_TEXT", "")
    ma_candidates = [
        item
        for item in field_candidates.get("field_candidates", {}).get("instruction_snippets", [])
        if item.get("source_region") == "MISSED_APPROACH_TEXT"
    ]
    if ma_candidates:
        text = "\n".join(str(item.get("value") or item.get("source_snippet") or "") for item in ma_candidates)
        if "MISSED APPROACH" not in text.upper():
            text = f"MISSED APPROACH: {text}"
        return text, ma_candidates
    return ma_text, []


def first_candidate_value(
    field_candidates: dict[str, Any],
    candidate_array: str,
    *,
    source_region: str = "MISSED_APPROACH_TEXT",
) -> Any:
    for item in field_candidates.get("field_candidates", {}).get(candidate_array, []):
        if item.get("source_region") == source_region:
            return item.get("value")
    return None


def direct_fix(text: str, field_candidates: dict[str, Any]) -> str | None:
    match = re.search(r"\bDIRECT\s+([A-Z0-9]{2,5})\b", text)
    if match:
        ident = clean_ident(match.group(1))
        if ident:
            return ident
    value = first_candidate_value(field_candidates, "direct_phrase_snippets")
    if isinstance(value, str):
        match = re.search(r"\bDIRECT\s+([A-Z0-9]{2,5})\b", normalize_text(value))
        if match:
            return clean_ident(match.group(1))
    return None


def hold_fix(text: str, fallback_fix: str | None, field_candidates: dict[str, Any]) -> str | None:
    for pattern in [
        r"\bTO\s+([A-Z0-9]{2,5})\s+(?:AND\s+)?HOLD\b",
        r"\b([A-Z0-9]{2,5})\s+(?:AND\s+)?HOLD\b",
        r"\bHOLD(?:ING)?\s+(?:AT|ON)\s+([A-Z0-9]{2,5})\b",
    ]:
        match = re.search(pattern, text)
        ident = clean_ident(match.group(1) if match else None)
        if ident:
            return ident
    value = first_candidate_value(field_candidates, "hold_candidates")
    if isinstance(value, str):
        for pattern in [r"\bTO\s+([A-Z0-9]{2,5})\s+(?:AND\s+)?HOLD\b", r"\b([A-Z0-9]{2,5})\s+(?:AND\s+)?HOLD\b"]:
            match = re.search(pattern, normalize_text(value))
            ident = clean_ident(match.group(1) if match else None)
            if ident:
                return ident
    return fallback_fix


def track_to_fix_matches(text: str) -> list[tuple[float, str]]:
    matches: list[tuple[float, str]] = []
    for match in re.finditer(
        r"\b(?:ON\s+)?(?:TRACK|TRK|COURSE|CRS|HEADING|HDG)\s+([0-3]?[0-9]{2})\s*(?:DEG|DEGREES|°|º|˚)?\s+TO\s+([A-Z0-9]{2,5})\b",
        text,
    ):
        degree = schema_degree(match.group(1))
        ident = clean_ident(match.group(2))
        if degree is not None and ident:
            matches.append((degree, ident))
    return matches


def radial_to_fix_match(text: str) -> tuple[dict[str, Any], str] | None:
    radial = navaid_radial(text)
    if not radial:
        return None
    after_radial = text.split(f"R-{int(radial['radial_deg']):03d}", 1)[-1]
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


def append_ca_leg(legs: list[dict[str, Any]], altitude: int | None, turn: str | None, diagnostics: list[dict[str, Any]]) -> None:
    leg = blank_leg(len(legs) + 1)
    answers = leg["answers"]
    answers["Q_terminator"] = answer("present", "CA")
    answers["Q1_fix_ident"] = answer("not_applicable")
    if altitude is not None:
        answers["Q2_altitude_constraint"] = answer(
            "present",
            {"desc": "AT_OR_ABOVE", "altitude_ft": altitude, "altitude_2_ft": None},
        )
    if turn is not None:
        answers["Q3_turn"] = answer("present", turn)
    answers["Q4_course_or_radial"] = answer("not_applicable")
    answers["Q5_hold_params"] = answer("not_applicable")
    legs.append(leg)
    diagnostics.append({"leg_index": leg["leg_index"], "rule_id": "R_B4_CLIMB_ALTITUDE_TO_CA", "altitude": altitude, "turn": turn})


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


def append_tf_leg(legs: list[dict[str, Any]], degree: float, fix: str, diagnostics: list[dict[str, Any]]) -> None:
    leg = blank_leg(len(legs) + 1)
    answers = leg["answers"]
    answers["Q_terminator"] = answer("present", "TF")
    answers["Q1_fix_ident"] = answer("present", fix)
    answers["Q2_altitude_constraint"] = answer("not_applicable")
    answers["Q3_turn"] = answer("not_applicable")
    answers["Q4_course_or_radial"] = answer("present", {"type": "course_deg", "course_deg": degree})
    answers["Q5_hold_params"] = answer("not_applicable")
    legs.append(leg)
    diagnostics.append({"leg_index": leg["leg_index"], "rule_id": "R_B4_TRACK_TO_FIX_TO_TF", "fix": fix, "course_deg": degree})


def append_cf_leg(legs: list[dict[str, Any]], radial: dict[str, Any], fix: str, diagnostics: list[dict[str, Any]]) -> None:
    leg = blank_leg(len(legs) + 1)
    answers = leg["answers"]
    answers["Q_terminator"] = answer("present", "CF")
    answers["Q1_fix_ident"] = answer("present", fix)
    answers["Q2_altitude_constraint"] = answer("not_applicable")
    answers["Q3_turn"] = answer("not_applicable")
    answers["Q4_course_or_radial"] = answer("present", radial)
    answers["Q5_hold_params"] = answer("not_applicable")
    legs.append(leg)
    diagnostics.append({"leg_index": leg["leg_index"], "rule_id": "R_B4_COURSE_OR_RADIAL", "fix": fix, "radial": radial})


def append_hm_leg(legs: list[dict[str, Any]], fix: str | None, text: str, diagnostics: list[dict[str, Any]]) -> None:
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


def build_b4_candidate_prediction(sample: dict[str, Any], text: str, field_candidates: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    row = {
        "chart_id": sample["chart_id"],
        "airport": sample["airport"],
        "proc_ident": sample["proc_ident"],
        "chart_name": sample["chart_name"],
    }
    prediction = canonical_empty(row)
    normalized = normalize_text(text)
    legs: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []

    altitude = first_altitude(normalized)
    turn = turn_value(normalized)
    d_fix = direct_fix(normalized, field_candidates)
    tracks = track_to_fix_matches(normalized)
    radial_match = radial_to_fix_match(normalized)
    has_hold = bool(re.search(r"\bHOLD(?:ING)?\b", normalized))

    if altitude is not None:
        append_ca_leg(legs, altitude, turn if not d_fix and not tracks and radial_match is None else None, evidence)
    if d_fix:
        append_df_leg(legs, d_fix, evidence)
    if radial_match:
        radial, fix = radial_match
        append_cf_leg(legs, radial, fix, evidence)
    for degree, fix in tracks:
        append_tf_leg(legs, degree, fix, evidence)
    if has_hold:
        h_fix = hold_fix(normalized, tracks[-1][1] if tracks else d_fix, field_candidates)
        append_hm_leg(legs, h_fix, normalized, evidence)

    if not legs:
        fallback_pred, fallback_diag = extract_rules(row, text)
        return fallback_pred, [{"rule_id": "R_B4_FALLBACK_LEGACY_EXTRACT_RULES", "legacy_diagnostics": fallback_diag}]

    prediction["missed_approach"]["leg_count"] = answer("present", len(legs))
    prediction["missed_approach"]["legs"] = legs
    return prediction, evidence


def run_candidate_rules(
    *,
    sample: dict[str, Any],
    roi_text: str,
    field_candidates: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    prompt_row = {
        "chart_id": sample["chart_id"],
        "airport": sample["airport"],
        "proc_ident": sample["proc_ident"],
        "chart_name": sample["chart_name"],
    }
    rule_input_text, primary_candidates = instruction_text_from_candidates(field_candidates, roi_text)
    pred, rule_evidence = build_b4_candidate_prediction(sample, rule_input_text, field_candidates)
    diagnostics = {
        "rule_registry": rel(RULE_REGISTRY),
        "rule_registry_sha256": sha256_file(RULE_REGISTRY),
        "runner": "experiment5_b4_region_aware_candidate_rules_v1",
        "uses_field_candidates": True,
        "uses_target_or_score": False,
        "primary_rule_ids": [
            "R_B4_PRIMARY_MA_TEXT_INSTRUCTION",
            "R_B4_CLIMB_ALTITUDE_TO_CA",
            "R_B4_DIRECT_TO_DF",
            "R_B4_HOLD_TO_HM",
            "R_B4_COURSE_OR_RADIAL",
        ],
        "candidate_counts_by_region": {
            region: len(candidates_by_region(field_candidates, region))
            for region in ["MISSED_APPROACH_TEXT", "PLAN_VIEW", "MISSED_APPROACH_DETAIL_AREA"]
        },
        "primary_instruction_candidate_count": len(primary_candidates),
        "primary_instruction_candidates": primary_candidates,
        "rule_input_text": rule_input_text,
        "rule_evidence": rule_evidence,
        "abstain_policy": "unknown_or_not_applicable_when_allowed_evidence_is_insufficient",
        "support_region_policy": "P/D candidates may support only when tied to MA_TEXT; this v1 runner keeps MA_TEXT as primary.",
    }
    return pred, diagnostics


def run_rules(
    *,
    rows: list[str],
    samples: dict[str, dict[str, Any]],
    candidate_inputs: dict[tuple[str, str], dict[str, Any]],
    targets: dict[str, Any],
    policies: dict[tuple[str, str], dict[str, Any]],
    validator: Draft202012Validator,
    run_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    method = "B4_TPD"
    out_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for chart_id in rows:
        sample = samples[chart_id]
        input_row = candidate_inputs[(chart_id, "TPD")]
        roi_text = Path(input_row["roi_ocr_input_text_path"]).read_text(encoding="utf-8")
        field_candidates = json.loads(Path(input_row["field_candidates_path"]).read_text(encoding="utf-8"))
        pred, diagnostics = run_candidate_rules(sample=sample, roi_text=roi_text, field_candidates=field_candidates)
        write_json(run_dir / method / "canonical_json" / f"{chart_id}.json", pred)
        write_json(run_dir / method / "rule_diagnostics" / f"{chart_id}.json", diagnostics)
        errors = validate_canonical(pred, validator)
        write_json(run_dir / method / "validation" / f"{chart_id}.json", errors)
        item: dict[str, Any] = {
            "method": method,
            "chart_id": chart_id,
            "sample_id": sample["sample_id"],
            "region_profile": "TPD",
            "uses_field_candidates": True,
            "validation_error_count": len(errors),
            "validation_errors": errors,
            "score": None,
        }
        if errors:
            failures.append({"method": method, "chart_id": chart_id, "error": "schema_validation_failed"})
        else:
            item["score"] = score_and_write(
                method=method,
                chart_id=chart_id,
                pred=pred,
                target=targets[chart_id],
                policies=policies,
                run_dir=run_dir,
            )
        out_rows.append(item)
    return out_rows, failures


def run_llm_method(
    *,
    method: str,
    rows: list[str],
    samples: dict[str, dict[str, Any]],
    candidate_inputs: dict[tuple[str, str], dict[str, Any]],
    targets: dict[str, Any],
    policies: dict[tuple[str, str], dict[str, Any]],
    validator: Draft202012Validator,
    canonical_schema: dict[str, Any],
    run_dir: Path,
    client: Any,
    provider: str,
    model: str,
    max_tokens: int,
    temperature: float,
    schema_retry_count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    profile = METHOD_TO_PROFILE[method]
    out_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for chart_id in rows:
        sample = samples[chart_id]
        input_row = candidate_inputs[(chart_id, profile)]
        roi_text = Path(input_row["roi_ocr_input_text_path"]).read_text(encoding="utf-8")
        field_candidates = json.loads(Path(input_row["field_candidates_path"]).read_text(encoding="utf-8"))
        prompt = prompt_for(
            method=method,
            profile=profile,
            sample=sample,
            roi_text=roi_text,
            field_candidates=field_candidates,
        )
        write_text(run_dir / method / "prompts" / f"{chart_id}.txt", prompt)
        current_prompt = prompt
        item: dict[str, Any] | None = None
        last_text = ""
        last_errors: list[str] | None = None
        for attempt in range(1, schema_retry_count + 2):
            try:
                text, response = call_model_json(
                    client,
                    provider=provider,
                    model=model,
                    prompt=current_prompt,
                    image_path=None,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    json_mode=False,
                    assistant_prefill_json=False,
                    output_control="openai_tool_call",
                    tool_schema=canonical_schema,
                    tool_name="emit_canonical_json",
                )
                last_text = text
                write_text(run_dir / method / "raw_text" / f"{chart_id}.attempt_{attempt}.txt", text)
                save_model_response(run_dir / method / "raw_responses" / f"{chart_id}.attempt_{attempt}.json", response)
                pred = json.loads(text)
                errors = validate_canonical(pred, validator)
                write_json(run_dir / method / "validation" / f"{chart_id}.attempt_{attempt}.json", errors)
                if not errors:
                    write_text(run_dir / method / "raw_text" / f"{chart_id}.txt", text)
                    save_model_response(run_dir / method / "raw_responses" / f"{chart_id}.json", response)
                    write_json(run_dir / method / "canonical_json" / f"{chart_id}.json", pred)
                    write_json(run_dir / method / "validation" / f"{chart_id}.json", errors)
                    item = {
                        "method": method,
                        "chart_id": chart_id,
                        "sample_id": sample["sample_id"],
                        "region_profile": profile,
                        "attempt_count": attempt,
                        "schema_retry_count": attempt - 1,
                        "uses_field_candidates": True,
                        "field_candidates_path": rel(Path(input_row["field_candidates_path"])),
                        "field_candidates_sha256": input_row.get("field_candidates_sha256"),
                        "roi_ocr_input_text_path": rel(Path(input_row["roi_ocr_input_text_path"])),
                        "roi_ocr_input_text_sha256": input_row.get("roi_ocr_input_text_sha256"),
                        "validation_error_count": 0,
                        "validation_errors": [],
                        "score": score_and_write(
                            method=method,
                            chart_id=chart_id,
                            pred=pred,
                            target=targets[chart_id],
                            policies=policies,
                            run_dir=run_dir,
                        ),
                    }
                    break
                last_errors = errors
                if attempt <= schema_retry_count:
                    current_prompt = build_schema_retry_prompt(
                        original_prompt=prompt,
                        previous_output=text,
                        validation_errors=errors,
                        parse_error=None,
                    )
                else:
                    write_json(run_dir / method / "canonical_json" / f"{chart_id}.json", pred)
                    write_json(run_dir / method / "validation" / f"{chart_id}.json", errors)
                    item = {
                        "method": method,
                        "chart_id": chart_id,
                        "sample_id": sample["sample_id"],
                        "region_profile": profile,
                        "attempt_count": attempt,
                        "schema_retry_count": attempt - 1,
                        "uses_field_candidates": True,
                        "field_candidates_path": rel(Path(input_row["field_candidates_path"])),
                        "field_candidates_sha256": input_row.get("field_candidates_sha256"),
                        "roi_ocr_input_text_path": rel(Path(input_row["roi_ocr_input_text_path"])),
                        "roi_ocr_input_text_sha256": input_row.get("roi_ocr_input_text_sha256"),
                        "validation_error_count": len(errors),
                        "validation_errors": errors,
                        "score": None,
                    }
                    failures.append({"method": method, "chart_id": chart_id, "error": "schema_validation_failed"})
            except Exception as exc:  # noqa: BLE001
                err = repr(exc)
                write_text(run_dir / method / "errors" / f"{chart_id}.attempt_{attempt}.txt", err)
                if attempt <= schema_retry_count:
                    current_prompt = build_schema_retry_prompt(
                        original_prompt=prompt,
                        previous_output=last_text,
                        validation_errors=last_errors,
                        parse_error=err,
                    )
                else:
                    item = {
                        "method": method,
                        "chart_id": chart_id,
                        "sample_id": sample["sample_id"],
                        "region_profile": profile,
                        "attempt_count": attempt,
                        "schema_retry_count": attempt - 1,
                        "uses_field_candidates": True,
                        "field_candidates_path": rel(Path(input_row["field_candidates_path"])),
                        "field_candidates_sha256": input_row.get("field_candidates_sha256"),
                        "roi_ocr_input_text_path": rel(Path(input_row["roi_ocr_input_text_path"])),
                        "roi_ocr_input_text_sha256": input_row.get("roi_ocr_input_text_sha256"),
                        "validation_error_count": None,
                        "validation_errors": last_errors,
                        "score": None,
                        "failure": err,
                    }
                    failures.append({"method": method, "chart_id": chart_id, "error": err})
        if item is not None:
            out_rows.append(item)
    return out_rows, failures


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_method: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        by_method[row["method"]].append(row)
    summaries: dict[str, Any] = {}
    for method, rows in sorted(by_method.items()):
        scored = [row["score"] for row in rows if row.get("score")]
        correct = sum(row["v2"]["correct"] for row in scored)
        total = sum(row["v2"]["total"] for row in scored)
        strict_correct = sum(row["strict"]["correct"] for row in scored)
        strict_total = sum(row["strict"]["total"] for row in scored)
        summaries[method] = {
            "samples_total": len(rows),
            "schema_valid": sum(1 for row in rows if row.get("validation_error_count") == 0),
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
            "schema_retry_total": sum(row.get("schema_retry_count") or 0 for row in rows),
            "uses_field_candidates": any(row.get("uses_field_candidates") for row in rows),
        }
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Experiment 5 smoke B3/B4 diagnostic methods.")
    parser.add_argument("--run-dir", type=Path, default=RUN_DIR)
    parser.add_argument("--methods", default="B3_T,B3_TPD,B4_TPD")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--text-model", default="gpt-5.4")
    parser.add_argument("--openai-base-url", default=None)
    parser.add_argument("--openai-api-key-env", default=None)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--schema-retry-count", type=int, default=1)
    args = parser.parse_args()

    methods = [item.strip() for item in args.methods.split(",") if item.strip()]
    unknown = sorted(set(methods) - set(METHOD_TO_PROFILE))
    if unknown:
        raise ValueError(f"Unsupported methods: {unknown}")

    candidate_inputs = load_candidate_inputs()
    chart_ids = sorted({chart_id for chart_id, _profile in candidate_inputs})[: args.limit]
    samples = load_sample_meta()
    targets = json.loads(TARGET_V2.read_text(encoding="utf-8"))
    policies = load_policy(POLICY_V2)
    canonical_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(canonical_schema)

    provider = "openai_compatible"
    client = None
    if any(method in {"B3_T", "B3_PD", "B3_TPD"} for method in methods):
        client = create_model_client(
            provider=provider,
            base_url=args.openai_base_url,
            api_key_env=args.openai_api_key_env,
        )

    run_manifest = {
        "run_id": args.run_dir.name,
        "experiment_group": 5,
        "methods": methods,
        "method_descriptions": METHOD_DESCRIPTION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_scope": "experiment5_smoke20_prefix_limit_for_flow_check",
        "limit": args.limit,
        "chart_ids": chart_ids,
        "input_manifest": rel(INPUT_MANIFEST),
        "input_manifest_sha256": sha256_file(INPUT_MANIFEST),
        "sample_manifest": rel(SAMPLE_MANIFEST),
        "sample_manifest_sha256": sha256_file(SAMPLE_MANIFEST),
        "target_v2": rel(TARGET_V2),
        "target_v2_sha256": sha256_file(TARGET_V2),
        "policy_v2": rel(POLICY_V2),
        "policy_v2_sha256": sha256_file(POLICY_V2),
        "schema": rel(SCHEMA_PATH),
        "schema_sha256": sha256_file(SCHEMA_PATH),
        "prompt": rel(PROMPT_PATH),
        "prompt_sha256": sha256_file(PROMPT_PATH),
        "rule_registry": rel(RULE_REGISTRY),
        "rule_registry_sha256": sha256_file(RULE_REGISTRY),
        "model_api": model_api_manifest(
            provider=provider,
            base_url=args.openai_base_url,
            api_key_env=args.openai_api_key_env,
            json_mode=False,
            assistant_prefill_json=False,
        ),
        "text_model": args.text_model,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "schema_retry_count": args.schema_retry_count,
        "target_used_for_prediction": False,
        "score_used_for_prediction": False,
        "cifp_or_arinc_424_used_for_prediction": False,
        "gold_observable_used_for_prediction": False,
        "gold_ma_text_used_for_prediction": False,
        "b4_uses_field_candidates": "B4_TPD" in methods,
        "b3_pd_withholds_missed_approach_text": "B3_PD" in methods,
        "env_openai_base_url": os.environ.get("OPENAI_BASE_URL") or os.environ.get("CODEX_PROXY_BASE_URL"),
    }
    write_json(args.run_dir / "run_manifest_b3_b4_smoke.json", run_manifest)

    all_results: list[dict[str, Any]] = []
    all_failures: list[dict[str, Any]] = []
    if "B4_TPD" in methods:
        results, failures = run_rules(
            rows=chart_ids,
            samples=samples,
            candidate_inputs=candidate_inputs,
            targets=targets,
            policies=policies,
            validator=validator,
            run_dir=args.run_dir,
        )
        all_results.extend(results)
        all_failures.extend(failures)

    for method in methods:
        if method not in {"B3_T", "B3_PD", "B3_TPD"}:
            continue
        if client is None:
            raise RuntimeError("Model client was not initialized.")
        results, failures = run_llm_method(
            method=method,
            rows=chart_ids,
            samples=samples,
            candidate_inputs=candidate_inputs,
            targets=targets,
            policies=policies,
            validator=validator,
            canonical_schema=canonical_schema,
            run_dir=args.run_dir,
            client=client,
            provider=provider,
            model=args.text_model,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            schema_retry_count=args.schema_retry_count,
        )
        all_results.extend(results)
        all_failures.extend(failures)

    write_jsonl(args.run_dir / "reports" / "b3_b4_smoke_results.jsonl", all_results)
    write_jsonl(args.run_dir / "reports" / "b3_b4_smoke_failures.jsonl", all_failures)
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "methods": methods,
        "chart_ids": chart_ids,
        "summaries": summarize(all_results),
        "failure_count": len(all_failures),
        "failures": all_failures,
    }
    write_json(args.run_dir / "reports" / "b3_b4_smoke_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not all_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
