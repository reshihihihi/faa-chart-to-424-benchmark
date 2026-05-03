from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_a1_a2_rules_pilot10 import clean_ident, first_altitude, normalize_text, schema_degree  # noqa: E402
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

METHODS = {"B2a_GoldText_LLM", "B2b_GoldText_FieldCandidates_LLM"}
DEFAULT_BASE_URL = "http://127.0.0.1:8080/v1"
FORBIDDEN_METHOD_INPUT_KEYS = {
    "target",
    "score",
    "canonical_answer",
    "canonical_leg_index",
    "Q_terminator",
    "leg_type",
    "field_review_v2",
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
    path.write_text(value + ("\n" if value and not value.endswith("\n") else ""), encoding="utf-8")


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def rel(path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def load_sample_meta() -> dict[str, dict[str, Any]]:
    return {row["chart_id"]: row for row in read_jsonl(SAMPLE_MANIFEST)}


def model_api_url(base_url: str, endpoint: str) -> str:
    return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"


def post_json(url: str, payload: dict[str, Any], *, timeout: int) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer local-proxy",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc


def get_json(url: str, *, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Authorization": "Bearer local-proxy"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc


def call_chat_tool(
    *,
    base_url: str,
    model: str,
    prompt: str,
    schema: dict[str, Any],
    max_tokens: int,
    temperature: float,
    timeout: int,
) -> tuple[str, dict[str, Any]]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "emit_canonical_json",
                    "description": "Emit one canonical missed-approach JSON object that follows the registered schema.",
                    "parameters": schema,
                    "strict": True,
                },
            }
        ],
        "tool_choice": {"type": "function", "function": {"name": "emit_canonical_json"}},
    }
    response = post_json(model_api_url(base_url, "chat/completions"), payload, timeout=timeout)
    choices = response.get("choices") or []
    if not choices:
        raise RuntimeError("Model response contained no choices.")
    message = choices[0].get("message") or {}
    tool_calls = message.get("tool_calls") or []
    if len(tool_calls) != 1:
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip(), response
        raise RuntimeError(f"Expected exactly one tool call, got {len(tool_calls)}.")
    function = tool_calls[0].get("function") or {}
    if function.get("name") != "emit_canonical_json":
        raise RuntimeError(f"Unexpected tool call name: {function.get('name')}")
    return str(function.get("arguments") or "").strip(), response


def add_candidate(
    candidates: dict[str, list[dict[str, Any]]],
    array_name: str,
    *,
    value: Any,
    field_type: str,
    source_snippet: str,
    start: int | None,
    end: int | None,
    rule_id: str,
    confidence: float,
    notes: str,
) -> None:
    candidates[array_name].append(
        {
            "value": value,
            "field_type": field_type,
            "source": "gold_ma_prose_text",
            "source_section": "gold_missed_approach_text",
            "source_snippet": source_snippet,
            "source_start_char": start,
            "source_end_char": end,
            "rule_id": rule_id,
            "confidence": confidence,
            "notes": notes,
        }
    )


def make_instruction_body(text: str) -> str:
    return re.sub(r"^\s*MISSED\s+(?:APPROACH|APCH)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()


def build_gold_text_field_candidates(chart_id: str, gold_ma_prose: str) -> dict[str, Any]:
    normalized = normalize_text(gold_ma_prose)
    arrays = {
        "fix_candidates": [],
        "altitude_candidates": [],
        "turn_candidates": [],
        "course_candidates": [],
        "hold_candidates": [],
        "instruction_snippets": [],
        "track_to_fix_snippets": [],
        "route_sequence_snippets": [],
        "direct_phrase_snippets": [],
        "climb_phrase_snippets": [],
    }

    instruction = make_instruction_body(gold_ma_prose)
    add_candidate(
        arrays,
        "instruction_snippets",
        value=instruction,
        field_type="missed_approach_instruction",
        source_snippet=gold_ma_prose,
        start=0,
        end=len(gold_ma_prose),
        rule_id="gold_ma_instruction_span_regex_v1",
        confidence=0.99,
        notes="automatic_candidate_from_adjudicated_gold_ma_prose_no_target_or_leg_binding",
    )

    for match in re.finditer(r"\bDIRECT\s+([A-Z0-9]{2,5})\b", normalized):
        ident = clean_ident(match.group(1))
        if ident:
            add_candidate(
                arrays,
                "fix_candidates",
                value=ident,
                field_type="fix_ident",
                source_snippet=match.group(0),
                start=match.start(1),
                end=match.end(1),
                rule_id="gold_ma_direct_fix_regex_v1",
                confidence=0.95,
                notes="direct_phrase_context",
            )
            add_candidate(
                arrays,
                "direct_phrase_snippets",
                value=match.group(0),
                field_type="direct_phrase",
                source_snippet=match.group(0),
                start=match.start(),
                end=match.end(),
                rule_id="gold_ma_direct_phrase_regex_v1",
                confidence=0.95,
                notes="direct_phrase_context",
            )

    altitude = first_altitude(normalized)
    if altitude is not None:
        match = re.search(rf"\b{altitude}\b", normalized)
        add_candidate(
            arrays,
            "altitude_candidates",
            value=altitude,
            field_type="altitude_ft",
            source_snippet=match.group(0) if match else str(altitude),
            start=match.start() if match else None,
            end=match.end() if match else None,
            rule_id="gold_ma_altitude_ft_regex_v1",
            confidence=0.95,
            notes="climb_to_altitude_context",
        )

    for match in re.finditer(r"\bCLIMB(?:ING)?\b(?:[^.;]*)", normalized):
        add_candidate(
            arrays,
            "climb_phrase_snippets",
            value=match.group(0).strip(),
            field_type="climb_phrase",
            source_snippet=match.group(0).strip(),
            start=match.start(),
            end=match.end(),
            rule_id="gold_ma_climb_phrase_regex_v1",
            confidence=0.9,
            notes="climb_phrase_context",
        )

    for direction in ["LEFT", "RIGHT"]:
        for match in re.finditer(rf"\b{direction}\s+TURN\b|\bCLIMBING\s+{direction}\s+TURN\b", normalized):
            add_candidate(
                arrays,
                "turn_candidates",
                value=direction,
                field_type="turn_direction",
                source_snippet=match.group(0),
                start=match.start(),
                end=match.end(),
                rule_id="gold_ma_turn_regex_v1",
                confidence=0.95,
                notes="turn_phrase_context",
            )

    track_patterns = [
        r"\b(?:ON\s+)?(?:TRACK|TRK|COURSE|CRS|HEADING|HDG)\s+([0-3]?[0-9]{2})\s*(?:DEG|DEGREES|°|º|˚)?\s+TO\s+([A-Z0-9]{2,5})\b",
        r"\b(?:VIA\s+)?([0-3]?[0-9]{2})\s*(?:DEG|DEGREES|°|º|˚)?\s*(?:TRACK|TRK|COURSE|CRS|HEADING|HDG)\s+TO\s+([A-Z0-9]{2,5})\b",
    ]
    seen_track: set[tuple[float, str]] = set()
    for pattern in track_patterns:
        for match in re.finditer(pattern, normalized):
            degree = schema_degree(match.group(1))
            ident = clean_ident(match.group(2))
            if degree is None or not ident:
                continue
            key = (degree, ident)
            if key in seen_track:
                continue
            seen_track.add(key)
            add_candidate(
                arrays,
                "course_candidates",
                value=degree,
                field_type="course_deg",
                source_snippet=match.group(0),
                start=match.start(1),
                end=match.end(1),
                rule_id="gold_ma_track_course_regex_v1",
                confidence=0.9,
                notes="track_to_fix_context",
            )
            add_candidate(
                arrays,
                "fix_candidates",
                value=ident,
                field_type="fix_ident",
                source_snippet=match.group(0),
                start=match.start(2),
                end=match.end(2),
                rule_id="gold_ma_track_to_fix_regex_v1",
                confidence=0.9,
                notes="track_to_fix_context",
            )
            add_candidate(
                arrays,
                "track_to_fix_snippets",
                value=match.group(0),
                field_type="track_to_fix",
                source_snippet=match.group(0),
                start=match.start(),
                end=match.end(),
                rule_id="gold_ma_track_to_fix_snippet_regex_v1",
                confidence=0.9,
                notes="track_to_fix_context",
            )

    for match in re.finditer(r"\b([A-Z0-9]{2,5})\s+(?:VOR|VORTAC|NDB|DME)?\s*R-?\s*([0-3]\d{2})\b", normalized):
        navaid = clean_ident(match.group(1))
        degree = schema_degree(match.group(2))
        if navaid and degree is not None:
            add_candidate(
                arrays,
                "course_candidates",
                value={"type": "navaid_radial", "navaid": navaid, "radial_deg": degree, "direction": "outbound"},
                field_type="navaid_radial",
                source_snippet=match.group(0),
                start=match.start(),
                end=match.end(),
                rule_id="gold_ma_navaid_radial_regex_v1",
                confidence=0.9,
                notes="navaid_radial_context",
            )

    for match in re.finditer(r"\bHOLD(?:ING)?\b", normalized):
        add_candidate(
            arrays,
            "hold_candidates",
            value=gold_ma_prose,
            field_type="hold_phrase",
            source_snippet=gold_ma_prose,
            start=match.start(),
            end=match.end(),
            rule_id="gold_ma_hold_phrase_regex_v1",
            confidence=0.95,
            notes="hold_phrase_context_no_leg_binding",
        )

    return {
        "schema_version": "experiment5_gold_ma_prose_field_candidates_schema_v1",
        "chart_id": chart_id,
        "candidate_source": "experiment5_gold_ma_prose_regex_candidates_v1",
        "source_contract": {
            "source": "adjudicated_gold_ma_prose",
            "allows_canonical_target": False,
            "allows_gold_observable_evidence": False,
            "allows_field_review_v2": False,
            "allows_cifp_or_arinc_424": False,
        },
        "leakage_policy": {
            "uses_canonical_target": False,
            "uses_expected_value": False,
            "uses_gold_field_to_leg_mapping": False,
            "uses_human_evidence_provenance": False,
            "uses_gold_observable_evidence": False,
            "uses_cifp_or_arinc_424": False,
            "uses_scorer_output": False,
            "uses_field_review_v2": False,
        },
        "field_candidates": arrays,
    }


def prompt_for(
    *,
    method: str,
    sample: dict[str, Any],
    gold_ma_prose: str,
    field_candidates: dict[str, Any] | None,
) -> str:
    candidate_policy = (
        "No field_candidates are provided. Use only the gold missed-approach prose."
        if field_candidates is None
        else (
            "Automatic field_candidates are provided. They were generated only from the same gold missed-approach "
            "prose. They are weak evidence, not leg mappings, not target fields, and not an answer key."
        )
    )
    candidates_text = "{}" if field_candidates is None else json.dumps(field_candidates, ensure_ascii=False, indent=2)
    return f"""# Experiment 5 B2 Gold Text Diagnostic Prompt

## Method Boundary

You are running `{method}` for Experiment 5.

This is a diagnostic method. It tests whether an LLM can recover canonical missed-approach JSON when OCR errors in the missed-approach prose have been removed.

## Allowed Inputs

- chart_id
- airport
- approach_ident
- chart_name
- adjudicated gold missed-approach prose
- automatic field_candidates generated from the same gold prose, only for B2b
- the canonical output contract

## Forbidden Inputs

Do not use or assume access to:

- full chart image pixels
- ROI OCR outside the gold prose shown below
- field_review_v2
- canonical target or answer key
- score or scorer output
- canonical_answer
- canonical_leg_index
- Q_terminator labels supplied as input
- leg_type
- CIFP or ARINC 424 records
- gold observable evidence
- historical model outputs for the same chart
- web search or external aviation databases

Candidate policy: {candidate_policy}

## Task

Extract the missed approach procedure and emit one canonical JSON object. If a field is ambiguous or not supported by the allowed input, set that answer to unknown/null or not_applicable/null as appropriate. Do not guess only to fill the schema.

Copy metadata exactly:

- chart_id: {sample["chart_id"]}
- airport: {sample["airport"]}
- approach_ident: {sample["proc_ident"]}
- chart_name: {sample["chart_name"]}

## Output Contract

Top-level object must contain exactly chart_id, procedure, and missed_approach.

procedure must contain exactly airport, approach_ident, and chart_name.

missed_approach must contain leg_count and legs.

Each leg must contain leg_index and answers. leg_index starts at 1 and increases by 1 without gaps. If leg_count.status is present, leg_count.value must equal len(legs).

answers must contain exactly:

- Q_terminator
- Q1_fix_ident
- Q2_altitude_constraint
- Q3_turn
- Q4_course_or_radial
- Q5_hold_params

Each answer object must contain exactly status and value. Allowed status values are present, not_applicable, not_observable, unknown. If status is not present, value must be null.

Q_terminator value, when present, must be one of:
CA, CF, CI, CR, DF, FA, FM, HA, HF, HM, IF, RF, TF, VA, VD, VI, VM, VR, AF, CD, FC, FD, VC, PI

Q1_fix_ident value, when present, must be an ident string with at most 5 characters.

Q2_altitude_constraint value, when present, must look like:
{{"desc":"AT_OR_ABOVE","altitude_ft":3000,"altitude_2_ft":null}}

Q3_turn value, when present, must be LEFT or RIGHT.

Q4_course_or_radial value, when present, must be exactly one of:
{{"type":"course_deg","course_deg":70.0}}
{{"type":"navaid_radial","navaid":"ABC","radial_deg":123.0,"direction":"outbound"}}
{{"type":"direct"}}

Q5_hold_params value, when present, must look like:
{{"inbound_course_deg":70.0,"leg_time_min":1.0,"leg_distance_nm":null,"turn":"RIGHT"}}

For non-hold legs, Q5_hold_params should be not_applicable. For hold legs, Q3_turn should usually be not_applicable because hold turn belongs in Q5_hold_params.

All degree values must be 0.0 through 359.9. If the chart displays 360, encode it as 359.9.

## Input

GOLD_MISSED_APPROACH_PROSE:
{gold_ma_prose}

FIELD_CANDIDATES_JSON:
{candidates_text}

Return exactly one object through the registered tool/schema. Do not output Markdown or explanation.
"""


def retry_prompt(original_prompt: str, previous_output: str, validation_errors: list[str] | None, parse_error: str | None) -> str:
    return f"""{original_prompt}

## Schema Retry

Your previous output failed validation or parsing.

Parse error:
{parse_error or "None"}

Validation errors:
{json.dumps(validation_errors or [], ensure_ascii=False, indent=2)}

Previous output:
{previous_output}

Emit a corrected object through the registered tool/schema.
"""


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


def load_existing_sample_result(
    *,
    args: argparse.Namespace,
    method: str,
    chart_id: str,
    sample: dict[str, Any],
    idx: int,
    total_for_method: int,
    input_payload: dict[str, Any],
    prompt: str,
    manifest: dict[str, Any],
) -> dict[str, Any] | None:
    input_path = args.run_dir / method / "inputs" / f"{chart_id}.json"
    prompt_path = args.run_dir / method / "prompts" / f"{chart_id}.txt"
    validation_path = args.run_dir / method / "validation" / f"{chart_id}.json"
    score_v2_path = args.run_dir / method / "scores_v2" / f"{chart_id}.json"
    score_strict_path = args.run_dir / method / "scores_strict" / f"{chart_id}.json"

    if read_json(input_path) != input_payload:
        return None
    if read_text(prompt_path) != prompt + ("\n" if prompt and not prompt.endswith("\n") else ""):
        return None

    validation = read_json(validation_path)
    score_v2 = read_json(score_v2_path)
    score_strict = read_json(score_strict_path)
    if validation is None or score_v2 is None or score_strict is None:
        return None
    if validation:
        return None

    return {
        "method": method,
        "idx": idx,
        "total_for_method": total_for_method,
        "chart_id": chart_id,
        "item": {
            "method": method,
            "chart_id": chart_id,
            "sample_id": sample["sample_id"],
            "attempt_count": None,
            "schema_retry_count": 0,
            "elapsed_sec": 0.0,
            "uses_gold_ma_text": True,
            "uses_field_candidates": input_payload.get("field_candidates") is not None,
            "field_candidates_source": "automatic_regex_from_gold_ma_prose_no_target"
            if input_payload.get("field_candidates") is not None
            else None,
            "validation_error_count": 0,
            "validation_errors": [],
            "score": {
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
            },
            "reused_existing_output": True,
        },
        "failures": [],
        "input_payload": input_payload,
        "manifest": manifest,
    }


def field_family(field: str) -> str:
    if field == "leg_count":
        return field
    if "." in field:
        return field.rsplit(".", 1)[-1]
    return field


def summarize(results: list[dict[str, Any]], run_dir: Path) -> dict[str, Any]:
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
        families: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
        for row in rows:
            score_path = run_dir / method / "scores_v2" / f"{row['chart_id']}.json"
            if not score_path.exists():
                continue
            score = json.loads(score_path.read_text(encoding="utf-8"))
            for score_row in score.get("rows", []):
                family = field_family(score_row["field"])
                families[family]["total"] += 1
                families[family]["correct"] += int(bool(score_row.get("correct")))
        summaries[method] = {
            "samples_total": len(rows),
            "schema_valid": sum(1 for row in rows if row.get("validation_error_count") == 0),
            "samples_scored": len(scored),
            "score_v2": {"correct": correct, "total": total, "accuracy": correct / total if total else None},
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
            "field_family": [
                {
                    "field": family,
                    "correct": counts["correct"],
                    "total": counts["total"],
                    "accuracy": counts["correct"] / counts["total"] if counts["total"] else None,
                }
                for family, counts in sorted(families.items())
            ],
        }
    return summaries


def render_report(summary: dict[str, Any], no_leakage: dict[str, Any]) -> str:
    lines = [
        "# 实验组5 B2 gold text smoke 运行报告",
        "",
        f"- run_id: `{summary['run_id']}`",
        f"- 模型: `{summary['model']}`",
        f"- base_url: `{summary['base_url']}`",
        f"- 方法: {', '.join(f'`{m}`' for m in summary['methods'])}",
        f"- 样本数: {len(summary['chart_ids'])}",
        "- target/score 使用: 只在 prediction 写盘后评分使用，不进入方法输入",
        "",
        "## B2 结果",
        "",
        "| 方法 | schema-valid | retry | v2 正确/总数 | v2 accuracy | strict accuracy |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for method in summary["methods"]:
        item = summary["summaries"].get(method, {})
        score = item.get("score_v2", {})
        strict = item.get("score_strict", {})
        accuracy = score.get("accuracy")
        strict_accuracy = strict.get("accuracy")
        lines.append(
            f"| `{method}` | {item.get('schema_valid', 0)}/{item.get('samples_total', 0)} | "
            f"{item.get('schema_retry_total', 0)} | {score.get('correct', 0)}/{score.get('total', 0)} | "
            f"{format_percent(accuracy)} | "
            f"{format_percent(strict_accuracy)} |"
        )
    lines.extend(["", "## 字段族表现", ""])
    for method in summary["methods"]:
        lines.extend([f"### `{method}`", "", "| 字段 | 正确/总数 | accuracy |", "|---|---:|---:|"])
        for row in summary["summaries"].get(method, {}).get("field_family", []):
            lines.append(f"| `{row['field']}` | {row['correct']}/{row['total']} | {row['accuracy']:.2%} |")
        lines.append("")
    lines.extend(
        [
            "## No-leakage 审查",
            "",
            f"- hard_leakage_detected: `{no_leakage['hard_leakage_detected']}`",
            f"- forbidden_key_hits: `{json.dumps(no_leakage['forbidden_key_hits'], ensure_ascii=False)}`",
            f"- target_used_for_prediction: `{no_leakage['target_used_for_prediction']}`",
            f"- score_used_for_prediction: `{no_leakage['score_used_for_prediction']}`",
            f"- field_review_v2_used_for_prediction: `{no_leakage['field_review_v2_used_for_prediction']}`",
            "",
            "## 解释边界",
            "",
            "- 这是 smoke20 诊断结果，不是 formal200 结论。",
            "- B2a 只使用 gold MA prose；B2b 使用 gold MA prose 和从同一 prose 自动生成的候选。",
            "- 未使用 field_review_v2、canonical target、score、CIFP/ARINC 424 或 gold observable 作为方法输入。",
        ]
    )
    return "\n".join(lines) + "\n"


def format_percent(value: float | None) -> str:
    return "NA" if value is None else f"{value:.2%}"


def scan_method_inputs(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    hits: dict[str, list[str]] = {key: [] for key in FORBIDDEN_METHOD_INPUT_KEYS}
    for payload in payloads:
        chart_id = str(payload.get("chart_id"))
        for key in FORBIDDEN_METHOD_INPUT_KEYS:
            if key in payload:
                hits[key].append(chart_id)
            field_candidates = payload.get("field_candidates")
            if isinstance(field_candidates, dict) and key in field_candidates:
                hits[key].append(chart_id)
    nonempty = {key: sorted(set(value)) for key, value in hits.items() if value}
    return {"forbidden_key_hits": nonempty, "hard_leakage_detected": bool(nonempty)}


def run_one_sample(
    *,
    args: argparse.Namespace,
    method: str,
    idx: int,
    total_for_method: int,
    gold_row: dict[str, Any],
    samples: dict[str, dict[str, Any]],
    targets: dict[str, Any],
    policies: dict[str, Any],
    canonical_schema: dict[str, Any],
    validator: Draft202012Validator,
) -> dict[str, Any]:
    chart_id = gold_row["chart_id"]
    sample = samples[chart_id]
    gold_ma_prose = str(gold_row["gold_ma_prose"]).strip()
    if not gold_ma_prose:
        return {
            "method": method,
            "idx": idx,
            "total_for_method": total_for_method,
            "chart_id": chart_id,
            "item": None,
            "failures": [{"method": method, "chart_id": chart_id, "error": "missing_gold_ma_prose"}],
            "input_payload": None,
            "manifest": None,
        }

    field_candidates = (
        build_gold_text_field_candidates(chart_id, gold_ma_prose)
        if method == "B2b_GoldText_FieldCandidates_LLM"
        else None
    )
    input_payload = {
        "chart_id": chart_id,
        "airport": sample["airport"],
        "approach_ident": sample["proc_ident"],
        "chart_name": sample["chart_name"],
        "gold_ma_prose": gold_ma_prose,
        "field_candidates": field_candidates,
    }
    prompt = prompt_for(
        method=method,
        sample=sample,
        gold_ma_prose=gold_ma_prose,
        field_candidates=field_candidates,
    )
    manifest = {
        "method": method,
        "chart_id": chart_id,
        "input_payload_path": rel(args.run_dir / method / "inputs" / f"{chart_id}.json"),
        "prompt_path": rel(args.run_dir / method / "prompts" / f"{chart_id}.txt"),
        "uses_gold_ma_text": True,
        "uses_field_candidates": field_candidates is not None,
        "field_candidates_source": "automatic_regex_from_gold_ma_prose_no_target" if field_candidates is not None else None,
    }

    if args.resume_existing:
        existing = load_existing_sample_result(
            args=args,
            method=method,
            chart_id=chart_id,
            sample=sample,
            idx=idx,
            total_for_method=total_for_method,
            input_payload=input_payload,
            prompt=prompt,
            manifest=manifest,
        )
        if existing is not None:
            return existing

    write_json(args.run_dir / method / "inputs" / f"{chart_id}.json", input_payload)
    if field_candidates is not None:
        write_json(args.run_dir / method / "field_candidates" / f"{chart_id}.json", field_candidates)
    write_text(args.run_dir / method / "prompts" / f"{chart_id}.txt", prompt)

    item: dict[str, Any] | None = None
    local_failures: list[dict[str, Any]] = []
    last_text = ""
    last_errors: list[str] | None = None
    current_prompt = prompt
    for attempt in range(1, args.schema_retry_count + 2):
        started = time.time()
        try:
            text, response = call_chat_tool(
                base_url=args.base_url,
                model=args.model,
                prompt=current_prompt,
                schema=canonical_schema,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                timeout=args.request_timeout,
            )
            elapsed = time.time() - started
            last_text = text
            write_text(args.run_dir / method / "raw_text" / f"{chart_id}.attempt_{attempt}.txt", text)
            write_json(args.run_dir / method / "raw_responses" / f"{chart_id}.attempt_{attempt}.json", response)
            pred = json.loads(text)
            errors = validate_canonical(pred, validator)
            write_json(args.run_dir / method / "validation" / f"{chart_id}.attempt_{attempt}.json", errors)
            if not errors:
                write_json(args.run_dir / method / "canonical_json" / f"{chart_id}.json", pred)
                write_json(args.run_dir / method / "validation" / f"{chart_id}.json", errors)
                write_text(args.run_dir / method / "raw_text" / f"{chart_id}.txt", text)
                write_json(args.run_dir / method / "raw_responses" / f"{chart_id}.json", response)
                item = {
                    "method": method,
                    "chart_id": chart_id,
                    "sample_id": sample["sample_id"],
                    "attempt_count": attempt,
                    "schema_retry_count": attempt - 1,
                    "elapsed_sec": elapsed,
                    "uses_gold_ma_text": True,
                    "uses_field_candidates": field_candidates is not None,
                    "field_candidates_source": "automatic_regex_from_gold_ma_prose_no_target"
                    if field_candidates is not None
                    else None,
                    "validation_error_count": 0,
                    "validation_errors": [],
                    "score": score_and_write(
                        method=method,
                        chart_id=chart_id,
                        pred=pred,
                        target=targets[chart_id],
                        policies=policies,
                        run_dir=args.run_dir,
                    ),
                }
                break
            last_errors = errors
            if attempt <= args.schema_retry_count:
                current_prompt = retry_prompt(prompt, text, errors, None)
            else:
                write_json(args.run_dir / method / "canonical_json" / f"{chart_id}.json", pred)
                write_json(args.run_dir / method / "validation" / f"{chart_id}.json", errors)
                item = {
                    "method": method,
                    "chart_id": chart_id,
                    "sample_id": sample["sample_id"],
                    "attempt_count": attempt,
                    "schema_retry_count": attempt - 1,
                    "uses_gold_ma_text": True,
                    "uses_field_candidates": field_candidates is not None,
                    "validation_error_count": len(errors),
                    "validation_errors": errors,
                    "score": None,
                }
                local_failures.append({"method": method, "chart_id": chart_id, "error": "schema_validation_failed"})
        except Exception as exc:  # noqa: BLE001
            err = repr(exc)
            write_text(args.run_dir / method / "errors" / f"{chart_id}.attempt_{attempt}.txt", err)
            if attempt <= args.schema_retry_count:
                current_prompt = retry_prompt(prompt, last_text, last_errors, err)
            else:
                item = {
                    "method": method,
                    "chart_id": chart_id,
                    "sample_id": sample["sample_id"],
                    "attempt_count": attempt,
                    "schema_retry_count": attempt - 1,
                    "uses_gold_ma_text": True,
                    "uses_field_candidates": field_candidates is not None,
                    "validation_error_count": None,
                    "validation_errors": last_errors,
                    "score": None,
                    "failure": err,
                }
                local_failures.append({"method": method, "chart_id": chart_id, "error": err})
    return {
        "method": method,
        "idx": idx,
        "total_for_method": total_for_method,
        "chart_id": chart_id,
        "item": item,
        "failures": local_failures,
        "input_payload": input_payload,
        "manifest": manifest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Experiment 5 B2 gold text LLM diagnostics through openai-oauth.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--gold-text", type=Path, default=GOLD_TEXT_PATH)
    parser.add_argument("--methods", default="B2a_GoldText_LLM,B2b_GoldText_FieldCandidates_LLM")
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--schema-retry-count", type=int, default=1)
    parser.add_argument("--request-timeout", type=int, default=180)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    methods = [method.strip() for method in args.methods.split(",") if method.strip()]
    unknown = sorted(set(methods) - METHODS)
    if unknown:
        raise ValueError(f"Unsupported methods: {unknown}")

    model_list = get_json(model_api_url(args.base_url, "models"), timeout=args.request_timeout)
    available_models = [item.get("id") for item in model_list.get("data", []) if isinstance(item, dict)]
    if args.model not in available_models:
        raise RuntimeError(f"Model {args.model!r} is not exposed by {args.base_url}; available={available_models}")

    gold_rows = read_jsonl(args.gold_text)[: args.limit]
    samples = load_sample_meta()
    targets = json.loads(TARGET_V2.read_text(encoding="utf-8"))
    policies = load_policy(POLICY_V2)
    canonical_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(canonical_schema)
    chart_ids = [row["chart_id"] for row in gold_rows]

    run_manifest = {
        "run_id": args.run_dir.name,
        "experiment_group": 5,
        "methods": methods,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_scope": "experiment5_smoke20_gold_ma_prose",
        "limit": args.limit,
        "chart_ids": chart_ids,
        "model": args.model,
        "base_url": args.base_url,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "schema_retry_count": args.schema_retry_count,
        "max_workers": args.max_workers,
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
        "model_api": {
            "provider": "openai_compatible_via_openai_oauth",
            "base_url": args.base_url,
            "token_value_recorded": False,
        },
        "target_used_for_prediction": False,
        "score_used_for_prediction": False,
        "cifp_or_arinc_424_used_for_prediction": False,
        "gold_observable_used_for_prediction": False,
        "gold_ma_text_used_for_prediction": True,
        "field_review_v2_used_for_prediction": False,
        "b2b_field_candidates_source": "automatic_regex_from_gold_ma_prose_no_target" if "B2b_GoldText_FieldCandidates_LLM" in methods else None,
    }
    write_json(args.run_dir / "run_manifest_b2_gold_text.json", run_manifest)

    all_results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    method_input_payloads: list[dict[str, Any]] = []
    method_input_manifest: list[dict[str, Any]] = []

    tasks = [(method, idx, gold_row) for method in methods for idx, gold_row in enumerate(gold_rows, start=1)]

    def record_result(result: dict[str, Any]) -> None:
        if result.get("item") is not None:
            all_results.append(result["item"])
        failures.extend(result.get("failures") or [])
        if result.get("input_payload") is not None:
            method_input_payloads.append(result["input_payload"])
        if result.get("manifest") is not None:
            method_input_manifest.append(result["manifest"])
        suffix = " reused" if (result.get("item") or {}).get("reused_existing_output") else ""
        print(
            f"{result['method']} {result['idx']}/{result['total_for_method']} {result['chart_id']}{suffix}",
            flush=True,
        )

    if args.max_workers <= 1:
        for method, idx, gold_row in tasks:
            record_result(
                run_one_sample(
                    args=args,
                    method=method,
                    idx=idx,
                    total_for_method=len(gold_rows),
                    gold_row=gold_row,
                    samples=samples,
                    targets=targets,
                    policies=policies,
                    canonical_schema=canonical_schema,
                    validator=validator,
                )
            )
    else:
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            future_map = {
                executor.submit(
                    run_one_sample,
                    args=args,
                    method=method,
                    idx=idx,
                    total_for_method=len(gold_rows),
                    gold_row=gold_row,
                    samples=samples,
                    targets=targets,
                    policies=policies,
                    canonical_schema=canonical_schema,
                    validator=validator,
                ): (method, idx, gold_row["chart_id"])
                for method, idx, gold_row in tasks
            }
            for future in as_completed(future_map):
                method, idx, chart_id = future_map[future]
                try:
                    record_result(future.result())
                except Exception as exc:  # noqa: BLE001
                    err = repr(exc)
                    failures.append({"method": method, "chart_id": chart_id, "error": err})
                    print(f"{method} {idx}/{len(gold_rows)} {chart_id} failed: {err}", flush=True)

    write_jsonl(args.run_dir / "reports" / "b2_gold_text_results.jsonl", all_results)
    write_jsonl(args.run_dir / "reports" / "b2_gold_text_failures.jsonl", failures)
    write_jsonl(args.run_dir / "manifests" / "b2_gold_text_method_inputs.jsonl", method_input_manifest)

    no_leakage_scan = scan_method_inputs(method_input_payloads)
    no_leakage = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "methods": methods,
        "target_used_for_prediction": False,
        "score_used_for_prediction": False,
        "cifp_or_arinc_424_used_for_prediction": False,
        "gold_observable_used_for_prediction": False,
        "gold_ma_text_used_for_prediction": True,
        "field_review_v2_used_for_prediction": False,
        "forbidden_key_hits": no_leakage_scan["forbidden_key_hits"],
        "hard_leakage_detected": no_leakage_scan["hard_leakage_detected"],
        "note": "B2 intentionally uses gold_ma_prose; B2b field candidates are automatic regex candidates from the same gold prose.",
    }
    write_json(args.run_dir / "reports" / "b2_gold_text_no_leakage_report.json", no_leakage)

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_dir.name,
        "methods": methods,
        "chart_ids": chart_ids,
        "model": args.model,
        "base_url": args.base_url,
        "max_workers": args.max_workers,
        "summaries": summarize(all_results, args.run_dir),
        "failure_count": len(failures),
        "failures": failures,
    }
    write_json(args.run_dir / "reports" / "b2_gold_text_summary.json", summary)
    write_text(args.run_dir / "reports" / "experiment5_b2_gold_text_execution_report_zh.md", render_report(summary, no_leakage))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failures and not no_leakage["hard_leakage_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
