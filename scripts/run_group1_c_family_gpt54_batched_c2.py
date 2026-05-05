from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from aggregate_c2_qa_candidate import QUESTION_TO_CANONICAL, aggregate_chart  # noqa: E402
from c3_questionnaire_to_canonical import questionnaire_to_canonical  # noqa: E402
from model_clients import (  # noqa: E402
    OPENAI_BASE_URL_ENVS,
    call_model_json,
    create_model_client,
    model_api_manifest,
    save_model_response,
)
from run_c2_qa_pilot10 import (  # noqa: E402
    QUESTION_SEQUENCE,
    build_prompt as build_single_qa_prompt,
    build_retry_prompt as build_single_qa_retry_prompt,
    qa_relative_path,
    qa_tool_schema,
    qa_validation_schema,
    validate_answer,
)
from run_group1_formal_manifest import (  # noqa: E402
    C3_QUESTIONNAIRE_SCHEMA,
    PROMPTS,
    QA_PROMPT_DIR,
    SCHEMA_PATH,
    artifact_path,
    display_path,
    load_targets,
    read_jsonl,
    row_for_prompt,
    score_if_valid,
    validate_canonical,
    validation_errors,
    write_json,
    write_jsonl,
)
from run_group1_pilot10_gpt54 import build_schema_retry_prompt, summarize_method  # noqa: E402
from run_pilot10_anthropic import fill_prompt, sha256_file, write_text  # noqa: E402
from aggregate_c2_qa_candidate import summarize as summarize_c2  # noqa: E402


DEFAULT_SOURCE_RUN_DIR = ROOT / "formal_runs" / "group1" / "group1_formal_prepared_50_200_50_seed20260437_no_eval"
DEFAULT_RUN_DIR = (
    ROOT
    / "formal_runs"
    / "group1"
    / "group1_formal_eval_50_200_50_seed20260437_20260430_r1_gpt54_c_family_batched_c2"
)

METHOD_SPECS = {
    "C1_GPT54": {"source_method": "C1", "base_method": "C1", "kind": "image_json", "provider": "openai_compatible"},
    "C2_GPT54_batched_leg": {"source_method": "C2", "base_method": "C2", "kind": "c2_batched_leg", "provider": "openai_compatible"},
    "C2_CLAUDE_batched_leg": {"source_method": "C2", "base_method": "C2", "kind": "c2_batched_leg", "provider": "anthropic_compatible"},
    "C3_GPT54": {"source_method": "C3", "base_method": "C3", "kind": "image_json", "provider": "openai_compatible"},
    "C4_GPT54": {"source_method": "C4", "base_method": "C4", "kind": "image_json", "provider": "openai_compatible"},
}
METHOD_ALIASES = {
    "C1": "C1_GPT54",
    "C2": "C2_GPT54_batched_leg",
    "C2_CLAUDE": "C2_CLAUDE_batched_leg",
    "C3": "C3_GPT54",
    "C4": "C4_GPT54",
}
DEFAULT_METHODS = "C1_GPT54,C2_GPT54_batched_leg,C3_GPT54,C4_GPT54"


def parse_methods(value: str) -> list[str]:
    methods = []
    for item in value.split(","):
        name = item.strip()
        if not name:
            continue
        methods.append(METHOD_ALIASES.get(name, name))
    unknown = sorted(set(methods) - set(METHOD_SPECS))
    if unknown:
        raise ValueError(f"Unknown methods: {unknown}")
    return methods


def resolve_run_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def effective_openai_base_url(base_url: str | None) -> str | None:
    if base_url:
        return base_url
    if any(os.environ.get(name) for name in OPENAI_BASE_URL_ENVS):
        return None
    return os.environ.get("OPENAI_API_BASE")


def limited(rows: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    return rows[:limit] if limit is not None else rows


def method_rows(source_run_dir: Path, output_method: str, limit: int | None) -> list[dict[str, Any]]:
    source_method = METHOD_SPECS[output_method]["source_method"]
    rows = read_jsonl(source_run_dir / source_method / "input_manifest.jsonl")
    return limited(rows, limit)


def rewrite_input_rows(rows: list[dict[str, Any]], output_method: str) -> list[dict[str, Any]]:
    source_method = METHOD_SPECS[output_method]["source_method"]
    rewritten = []
    for row in rows:
        item = dict(row)
        item["source_method_id"] = source_method
        item["method_id"] = output_method
        item["model_substitution"] = (
            "claude_original_c2_to_claude_batched_c2"
            if output_method == "C2_CLAUDE_batched_leg"
            else "claude_c_family_to_gpt5.4"
        )
        if output_method == "C2_GPT54_batched_leg":
            item["c2_call_granularity"] = "q0_single_call_then_one_batched_call_per_leg_for_six_qa_fields"
            item["aggregator"] = "scripts/aggregate_c2_qa_candidate.py"
        if output_method == "C2_CLAUDE_batched_leg":
            item["c2_call_granularity"] = "q0_single_call_then_one_batched_call_per_leg_for_six_qa_fields"
            item["aggregator"] = "scripts/aggregate_c2_qa_candidate.py"
        rewritten.append(item)
    return rewritten


def prepare_run_dir(
    *,
    source_run_dir: Path,
    run_dir: Path,
    methods: list[str],
    rows_by_method: dict[str, list[dict[str, Any]]],
    args: argparse.Namespace,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(run_dir / "scoring_manifest.jsonl", read_jsonl(source_run_dir / "scoring_manifest.jsonl"))
    for method in methods:
        write_jsonl(run_dir / method / "input_manifest.jsonl", rewrite_input_rows(rows_by_method[method], method))

    run_plan = {
        "status": "prepared_for_gpt54_c_family_rerun",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_dir.name,
        "source_run_dir": display_path(source_run_dir),
        "methods": methods,
        "sample_count_per_method": {method: len(rows_by_method[method]) for method in methods},
        "base_model": args.model,
        "source_model_replaced": "Claude Sonnet 4.5 C-family methods",
        "c2_variant": {
            "name": "C2_GPT54_batched_leg",
            "kept": ["q0_leg_count gate", "fixed C2 QA fields", "deterministic aggregate_c2_qa_candidate.py"],
            "changed": "six per-leg QA prompts are batched into one model call per leg",
            "expected_call_reduction": "roughly q0 + legs calls instead of q0 + 6*legs calls",
        },
        "input_policy": {
            "inference_reads_method_input_manifest_only": True,
            "scoring_reads_scoring_manifest_after_prediction": True,
            "target_used_for_prompt_or_parsing": False,
        },
        "script": {
            "path": "scripts/run_group1_c_family_gpt54_batched_c2.py",
            "sha256": sha256_file(ROOT / "scripts" / "run_group1_c_family_gpt54_batched_c2.py"),
        },
    }
    write_json(run_dir / "run_plan.json", run_plan)


def collect_missing_artifacts(
    *,
    rows_by_method: dict[str, list[dict[str, Any]]],
    methods: list[str],
    targets: dict[str, Path],
) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    for method in methods:
        base_method = METHOD_SPECS[method]["base_method"]
        for row in rows_by_method[method]:
            chart_id = row["chart_id"]
            image_path = artifact_path(row, "image")
            if image_path is None or not image_path.exists():
                missing.append(
                    {
                        "method": method,
                        "sample_id": row.get("sample_id"),
                        "chart_id": chart_id,
                        "artifact": "image",
                        "path": display_path(image_path) if image_path else None,
                    }
                )
            if base_method == "C4":
                ocr_path = artifact_path(row, "OCR-1_full_text")
                if ocr_path is None or not ocr_path.exists():
                    missing.append(
                        {
                            "method": method,
                            "sample_id": row.get("sample_id"),
                            "chart_id": chart_id,
                            "artifact": "OCR-1_full_text",
                            "path": display_path(ocr_path) if ocr_path else None,
                        }
                    )
            target_path = targets.get(chart_id)
            if target_path is None or not target_path.exists():
                missing.append(
                    {
                        "method": method,
                        "sample_id": row.get("sample_id"),
                        "chart_id": chart_id,
                        "artifact": "target_for_scoring",
                        "path": display_path(target_path) if target_path else None,
                    }
                )
    return missing


def write_preflight_report(
    *,
    run_dir: Path,
    methods: list[str],
    rows_by_method: dict[str, list[dict[str, Any]]],
    missing: list[dict[str, Any]],
) -> dict[str, Any]:
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "ready": not missing,
        "methods": methods,
        "sample_count_per_method": {method: len(rows_by_method[method]) for method in methods},
        "missing_artifact_count": len(missing),
        "missing_artifacts_sample": missing[:50],
    }
    write_json(run_dir / "reports" / "preflight.json", report)
    return report


def completed_result_from_existing(
    *,
    output_method: str,
    source_method: str,
    row: dict[str, Any],
    run_dir: Path,
) -> dict[str, Any] | None:
    chart_id = row["chart_id"]
    validation_path = run_dir / output_method / "validation" / f"{chart_id}.json"
    score_path = run_dir / output_method / "scores" / f"{chart_id}.json"
    canonical_path = run_dir / output_method / "canonical_json" / f"{chart_id}.json"
    if not (canonical_path.exists() and validation_path.exists() and score_path.exists()):
        return None
    errors = json.loads(validation_path.read_text(encoding="utf-8"))
    if errors:
        return None
    score = json.loads(score_path.read_text(encoding="utf-8"))
    return {
        "method": output_method,
        "source_method": source_method,
        "sample_id": row["sample_id"],
        "chart_id": chart_id,
        "json_extraction_policy": "openai_tool_call_arguments_resumed",
        "validation_error_count": 0,
        "validation_errors": [],
        "attempt_count": 0,
        "schema_retry_count": 0,
        "resumed_from_existing_artifacts": True,
        "score": {key: score[key] for key in ["correct", "total", "accuracy"]},
    }


def batched_leg_tool_schema(canonical_schema: dict[str, Any]) -> dict[str, Any]:
    answers_schema = canonical_schema["$defs"]["leg"]["properties"]["answers"]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "C2 batched per-leg QA answer schema",
        "type": "object",
        "required": list(answers_schema["required"]),
        "additionalProperties": False,
        "properties": copy.deepcopy(answers_schema["properties"]),
        "$defs": copy.deepcopy(canonical_schema["$defs"]),
    }


def validate_batched_leg_answers(
    answer: Any,
    *,
    batch_validator: Draft202012Validator,
    qa_validators: dict[str, Draft202012Validator],
) -> list[str]:
    errors = validation_errors(answer, batch_validator)
    if not isinstance(answer, dict):
        return errors or ["batched_answer_is_not_object"]
    for question_id, canonical_field in QUESTION_TO_CANONICAL.items():
        field_answer = answer.get(canonical_field)
        for error in validate_answer(field_answer, question_id=question_id, validator=qa_validators[question_id]):
            errors.append(f"{canonical_field}: {error}")
    return errors


def build_batched_leg_prompt(
    row: dict[str, Any],
    prompt_templates: dict[str, str],
    leg_index: int,
) -> str:
    sections = []
    for question_id in QUESTION_SEQUENCE:
        canonical_field = QUESTION_TO_CANONICAL[question_id]
        question_text = prompt_templates[question_id].replace("<LEG_INDEX>", str(leg_index))
        sections.extend([f"## {canonical_field} ({question_id})", "", question_text, ""])

    return "\n".join(
        [
            "# C2 Batched-Leg Fixed QA Call",
            "",
            "Method boundary:",
            "full chart image -> VLM answers fixed QA fields for one leg -> deterministic aggregator -> canonical JSON.",
            "",
            "This GPT-5.4 rerun keeps the C2 q0 leg-count gate and deterministic aggregator,",
            "but batches the six fixed QA fields for the same leg into one model call.",
            "",
            "Allowed inputs for this call:",
            "- chart_id, airport, approach_ident, chart_name",
            "- full chart image",
            "- the fixed QA prompts below for this leg",
            "",
            "Forbidden inputs for this call:",
            "- OCR text or OCR bounding boxes",
            "- ROI labels or field candidates",
            "- gold missed-approach prose",
            "- canonical target or answer key",
            "- scorer outputs",
            "- CIFP or ARINC 424 records",
            "- human annotations or previous model outputs for this chart",
            "- web search or external aviation databases",
            "",
            "Metadata:",
            f"chart_id: {row['chart_id']}",
            f"airport: {row['airport']}",
            f"approach_ident: {row['proc_ident']}",
            f"chart_name: {row['chart_name']}",
            f"leg_index: {leg_index}",
            "",
            "Return exactly one JSON object with these six top-level keys:",
            "Q_terminator, Q1_fix_ident, Q2_altitude_constraint, Q3_turn, Q4_course_or_radial, Q5_hold_params.",
            "Each value must be the same status/value answer object required by the corresponding fixed QA prompt.",
            "If a status is not present, value must be null. Do not output markdown or prose.",
            "",
            *sections,
        ]
    )


def build_batched_leg_retry_prompt(
    *,
    original_prompt: str,
    previous_output: str,
    validation_errors: list[str],
) -> str:
    return "\n".join(
        [
            original_prompt,
            "",
            "## Schema-Only Retry",
            "",
            "Your previous batched per-leg answer failed JSON/schema/status-value validation.",
            "Return the same six-field JSON object for the same chart image, metadata, and leg index.",
            "Do not use targets, scorer output, CIFP, annotations, OCR, web search, or any new input.",
            "Do not output markdown or prose.",
            "",
            "Fixed hard rules:",
            "- The root object must have exactly the six required Q* keys.",
            "- Each Q* value must have exactly status and value.",
            "- If status is not present, value must be null.",
            "- If status is present, value must follow the corresponding question schema.",
            "- Degree fields must be 0.0 through 359.9; encode 360 as 359.9.",
            "",
            "VALIDATION_ERRORS:",
            "\n".join(validation_errors),
            "",
            "PREVIOUS_OUTPUT:",
            previous_output,
        ]
    )


def call_single_qa_answer(
    *,
    output_method: str,
    client: Any,
    provider: str,
    model: str,
    row: dict[str, Any],
    image_path: Path,
    question_id: str,
    prompt_template: str,
    leg_index: int | None,
    schema: dict[str, Any],
    validator: Draft202012Validator,
    run_dir: Path,
    max_tokens: int,
    temperature: float,
    schema_retry_count: int,
    output_control: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    chart_id = row["chart_id"]
    rel_path = qa_relative_path(question_id, leg_index)
    base_prompt = build_single_qa_prompt(row, question_id, prompt_template, leg_index)
    current_prompt = base_prompt
    max_attempts = 1 + schema_retry_count
    diagnostic: dict[str, Any] = {
        "question_id": question_id,
        "leg_index": leg_index,
        "attempt_count": 0,
        "schema_retry_count": 0,
        "validation_errors": [],
        "saved_answer": False,
    }
    last_text = ""
    for attempt in range(1, max_attempts + 1):
        diagnostic["attempt_count"] = attempt
        try:
            text, response = call_model_json(
                client,
                provider=provider,
                model=model,
                prompt=current_prompt,
                image_path=image_path,
                max_tokens=max_tokens,
                temperature=temperature,
                json_mode=False,
                assistant_prefill_json=False,
                output_control=output_control,
                tool_schema=schema,
                tool_name="emit_qa_answer",
            )
            last_text = text
            write_text(run_dir / output_method / "raw_text" / chart_id / rel_path.with_suffix(f".attempt_{attempt}.txt"), text)
            save_model_response(run_dir / output_method / "raw_responses" / chart_id / rel_path.with_suffix(f".attempt_{attempt}.json"), response)
            answer = json.loads(text)
            errors = validate_answer(answer, question_id=question_id, validator=validator)
            write_json(run_dir / output_method / "qa_validation" / chart_id / rel_path.with_suffix(f".attempt_{attempt}.json"), errors)
            if not errors:
                write_json(run_dir / output_method / "qa_json" / chart_id / rel_path, answer)
                write_text(run_dir / output_method / "raw_text" / chart_id / rel_path.with_suffix(".txt"), text)
                save_model_response(run_dir / output_method / "raw_responses" / chart_id / rel_path.with_suffix(".json"), response)
                write_json(run_dir / output_method / "qa_validation" / chart_id / rel_path, errors)
                diagnostic["schema_retry_count"] = attempt - 1
                diagnostic["saved_answer"] = True
                return answer, diagnostic
            diagnostic["validation_errors"] = errors
            if attempt < max_attempts:
                current_prompt = build_single_qa_retry_prompt(
                    original_prompt=base_prompt,
                    previous_output=text,
                    validation_errors=errors,
                )
        except Exception as exc:  # noqa: BLE001
            diagnostic["validation_errors"] = [repr(exc)]
            write_text(run_dir / output_method / "qa_errors" / chart_id / rel_path.with_suffix(f".attempt_{attempt}.txt"), repr(exc))
            if attempt < max_attempts:
                current_prompt = build_single_qa_retry_prompt(
                    original_prompt=base_prompt,
                    previous_output=last_text,
                    validation_errors=[repr(exc)],
                )
    diagnostic["schema_retry_count"] = max_attempts - 1
    write_json(run_dir / output_method / "qa_invalid" / chart_id / rel_path, {"last_output": last_text, "diagnostic": diagnostic})
    return None, diagnostic


def call_batched_leg_answers(
    *,
    output_method: str,
    client: Any,
    provider: str,
    model: str,
    row: dict[str, Any],
    image_path: Path,
    leg_index: int,
    prompt_templates: dict[str, str],
    schema: dict[str, Any],
    batch_validator: Draft202012Validator,
    qa_validators: dict[str, Draft202012Validator],
    run_dir: Path,
    max_tokens: int,
    temperature: float,
    schema_retry_count: int,
    output_control: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    chart_id = row["chart_id"]
    rel_path = Path(f"leg_{leg_index:03d}") / "batched_leg_answers.json"
    base_prompt = build_batched_leg_prompt(row, prompt_templates, leg_index)
    current_prompt = base_prompt
    max_attempts = 1 + schema_retry_count
    diagnostic: dict[str, Any] = {
        "question_id": "batched_leg_answers",
        "batched_question_ids": list(QUESTION_SEQUENCE),
        "leg_index": leg_index,
        "attempt_count": 0,
        "schema_retry_count": 0,
        "validation_errors": [],
        "saved_answer": False,
        "saved_field_count": 0,
    }
    last_text = ""
    for attempt in range(1, max_attempts + 1):
        diagnostic["attempt_count"] = attempt
        try:
            text, response = call_model_json(
                client,
                provider=provider,
                model=model,
                prompt=current_prompt,
                image_path=image_path,
                max_tokens=max_tokens,
                temperature=temperature,
                json_mode=False,
                assistant_prefill_json=False,
                output_control=output_control,
                tool_schema=schema,
                tool_name="emit_batched_leg_qa",
            )
            last_text = text
            write_text(run_dir / output_method / "raw_text" / chart_id / rel_path.with_suffix(f".attempt_{attempt}.txt"), text)
            save_model_response(run_dir / output_method / "raw_responses" / chart_id / rel_path.with_suffix(f".attempt_{attempt}.json"), response)
            answer = json.loads(text)
            errors = validate_batched_leg_answers(
                answer,
                batch_validator=batch_validator,
                qa_validators=qa_validators,
            )
            write_json(run_dir / output_method / "qa_validation" / chart_id / rel_path.with_suffix(f".attempt_{attempt}.json"), errors)
            if not errors:
                write_json(run_dir / output_method / "qa_json_batched" / chart_id / rel_path, answer)
                write_json(run_dir / output_method / "qa_validation" / chart_id / rel_path, errors)
                for question_id, canonical_field in QUESTION_TO_CANONICAL.items():
                    field_rel_path = qa_relative_path(question_id, leg_index)
                    write_json(run_dir / output_method / "qa_json" / chart_id / field_rel_path, answer[canonical_field])
                    write_json(run_dir / output_method / "qa_validation" / chart_id / field_rel_path, [])
                write_text(run_dir / output_method / "raw_text" / chart_id / rel_path.with_suffix(".txt"), text)
                save_model_response(run_dir / output_method / "raw_responses" / chart_id / rel_path.with_suffix(".json"), response)
                diagnostic["schema_retry_count"] = attempt - 1
                diagnostic["saved_answer"] = True
                diagnostic["saved_field_count"] = len(QUESTION_SEQUENCE)
                return answer, diagnostic
            diagnostic["validation_errors"] = errors
            if attempt < max_attempts:
                current_prompt = build_batched_leg_retry_prompt(
                    original_prompt=base_prompt,
                    previous_output=text,
                    validation_errors=errors,
                )
        except Exception as exc:  # noqa: BLE001
            diagnostic["validation_errors"] = [repr(exc)]
            write_text(run_dir / output_method / "qa_errors" / chart_id / rel_path.with_suffix(f".attempt_{attempt}.txt"), repr(exc))
            if attempt < max_attempts:
                current_prompt = build_batched_leg_retry_prompt(
                    original_prompt=base_prompt,
                    previous_output=last_text,
                    validation_errors=[repr(exc)],
                )
    diagnostic["schema_retry_count"] = max_attempts - 1
    write_json(run_dir / output_method / "qa_invalid" / chart_id / rel_path, {"last_output": last_text, "diagnostic": diagnostic})
    return None, diagnostic


def run_image_json_variant(
    *,
    output_method: str,
    base_method: str,
    rows: list[dict[str, Any]],
    targets: dict[str, Path],
    client: Any,
    provider: str,
    model: str,
    max_tokens: int,
    temperature: float,
    schema_retry_count: int,
    validator: Draft202012Validator,
    canonical_schema: dict[str, Any],
    c3_questionnaire_schema: dict[str, Any],
    run_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    prompt_template = PROMPTS[base_method].read_text(encoding="utf-8")
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for row in rows:
        prompt_row = row_for_prompt(row)
        chart_id = row["chart_id"]
        sample_id = row["sample_id"]
        resumed = completed_result_from_existing(
            output_method=output_method,
            source_method=base_method,
            row=row,
            run_dir=run_dir,
        )
        if resumed is not None:
            results.append(resumed)
            continue
        image_path = artifact_path(row, "image")
        ocr_text = ""
        if base_method == "C4":
            ocr_path = artifact_path(row, "OCR-1_full_text")
            if ocr_path is None or not ocr_path.exists():
                failure = {"method": output_method, "sample_id": sample_id, "chart_id": chart_id, "error": "missing_OCR-1_full_text"}
                failures.append(failure)
                results.append({**failure, "validation_error_count": None, "score": None})
                continue
            ocr_text = ocr_path.read_text(encoding="utf-8")
        if image_path is None or not image_path.exists():
            failure = {"method": output_method, "sample_id": sample_id, "chart_id": chart_id, "error": "missing_image"}
            failures.append(failure)
            results.append({**failure, "validation_error_count": None, "score": None})
            continue

        prompt = fill_prompt(prompt_template, prompt_row, ocr_text=ocr_text)
        current_prompt = prompt
        max_attempts = 1 + schema_retry_count
        last_text = ""
        last_validation_errors: list[str] | None = None
        item: dict[str, Any] | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                tool_schema = c3_questionnaire_schema if base_method == "C3" else canonical_schema
                tool_name = "emit_questionnaire_json" if base_method == "C3" else "emit_canonical_json"
                text, response = call_model_json(
                    client,
                    provider=provider,
                    model=model,
                    prompt=current_prompt,
                    image_path=image_path,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    json_mode=False,
                    assistant_prefill_json=False,
                    output_control="openai_tool_call",
                    tool_schema=tool_schema,
                    tool_name=tool_name,
                )
                last_text = text
                write_text(run_dir / output_method / "raw_text" / f"{chart_id}.attempt_{attempt}.txt", text)
                save_model_response(run_dir / output_method / "raw_responses" / f"{chart_id}.attempt_{attempt}.json", response)
                parsed = json.loads(text.strip())
                if base_method == "C3":
                    write_json(run_dir / output_method / "questionnaire_json" / f"{chart_id}.attempt_{attempt}.json", parsed)
                    pred = questionnaire_to_canonical(parsed)
                else:
                    pred = parsed
                errors = validate_canonical(pred, validator)
                write_json(run_dir / output_method / "validation" / f"{chart_id}.attempt_{attempt}.json", errors)
                if not errors:
                    write_text(run_dir / output_method / "raw_text" / f"{chart_id}.txt", text)
                    save_model_response(run_dir / output_method / "raw_responses" / f"{chart_id}.json", response)
                    if base_method == "C3":
                        write_json(run_dir / output_method / "questionnaire_json" / f"{chart_id}.json", parsed)
                    write_json(run_dir / output_method / "canonical_json" / f"{chart_id}.json", pred)
                    write_json(run_dir / output_method / "validation" / f"{chart_id}.json", errors)
                    item = {
                        "method": output_method,
                        "source_method": base_method,
                        "sample_id": sample_id,
                        "chart_id": chart_id,
                        "json_extraction_policy": "openai_tool_call_arguments",
                        "validation_error_count": 0,
                        "validation_errors": [],
                        "attempt_count": attempt,
                        "schema_retry_count": attempt - 1,
                        "score": score_if_valid(method=output_method, pred=pred, target_path=targets[chart_id], run_dir=run_dir, chart_id=chart_id),
                    }
                    break
                last_validation_errors = errors
                if attempt < max_attempts:
                    current_prompt = build_schema_retry_prompt(
                        original_prompt=prompt,
                        previous_output=text,
                        validation_errors=errors,
                        parse_error=None,
                    )
                else:
                    write_json(run_dir / output_method / "canonical_json" / f"{chart_id}.json", pred)
                    write_json(run_dir / output_method / "validation" / f"{chart_id}.json", errors)
                    item = {
                        "method": output_method,
                        "source_method": base_method,
                        "sample_id": sample_id,
                        "chart_id": chart_id,
                        "json_extraction_policy": "openai_tool_call_arguments",
                        "validation_error_count": len(errors),
                        "validation_errors": errors,
                        "attempt_count": attempt,
                        "schema_retry_count": attempt - 1,
                        "score": None,
                    }
                    failures.append({"method": output_method, "sample_id": sample_id, "chart_id": chart_id, "error": "schema_validation_failed"})
            except Exception as exc:  # noqa: BLE001
                err = repr(exc)
                write_text(run_dir / output_method / "parse_errors" / f"{chart_id}.attempt_{attempt}.txt", err)
                if attempt < max_attempts:
                    current_prompt = build_schema_retry_prompt(
                        original_prompt=prompt,
                        previous_output=last_text,
                        validation_errors=last_validation_errors,
                        parse_error=err,
                    )
                else:
                    item = {
                        "method": output_method,
                        "source_method": base_method,
                        "sample_id": sample_id,
                        "chart_id": chart_id,
                        "json_extraction_policy": "openai_tool_call_arguments",
                        "validation_error_count": None,
                        "validation_errors": last_validation_errors,
                        "attempt_count": attempt,
                        "schema_retry_count": attempt - 1,
                        "score": None,
                        "failure": err,
                    }
                    failures.append({"method": output_method, "sample_id": sample_id, "chart_id": chart_id, "error": err})
        if item is not None:
            results.append(item)
    return results, failures


def run_c2_batched_leg_variant(
    *,
    output_method: str,
    rows: list[dict[str, Any]],
    targets: dict[str, Path],
    client: Any,
    provider: str,
    model: str,
    q0_max_tokens: int,
    batched_max_tokens: int,
    temperature: float,
    schema_retry_count: int,
    validator: Draft202012Validator,
    canonical_schema: dict[str, Any],
    run_dir: Path,
    max_qa_legs: int,
    output_control: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    qa_schemas = {qid: qa_tool_schema(canonical_schema, qid) for qid in ["q0_leg_count", *QUESTION_SEQUENCE]}
    qa_validation_schemas = {qid: qa_validation_schema(canonical_schema, qid) for qid in ["q0_leg_count", *QUESTION_SEQUENCE]}
    qa_validators = {qid: Draft202012Validator(schema) for qid, schema in qa_validation_schemas.items()}
    batch_schema = batched_leg_tool_schema(canonical_schema)
    batch_validator = Draft202012Validator(batch_schema)
    prompt_templates = {path.stem: path.read_text(encoding="utf-8") for path in sorted(QA_PROMPT_DIR.glob("*.txt"))}

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for row in rows:
        prompt_row = row_for_prompt(row)
        chart_id = row["chart_id"]
        resumed = completed_result_from_existing(
            output_method=output_method,
            source_method="C2",
            row=row,
            run_dir=run_dir,
        )
        if resumed is not None:
            resumed.pop("json_extraction_policy", None)
            resumed.update(
                {
                    "qa_calls_total": 0,
                    "qa_calls_saved": 0,
                    "qa_fields_saved": 0,
                    "qa_schema_retry_count_total": 0,
                    "resumed_from_existing_artifacts": True,
                }
            )
            results.append(resumed)
            continue
        image_path = artifact_path(row, "image")
        if image_path is None or not image_path.exists():
            failure = {"method": output_method, "sample_id": row["sample_id"], "chart_id": chart_id, "error": "missing_image"}
            failures.append(failure)
            results.append({**failure, "validation_error_count": None, "score": None})
            continue

        chart_diags: list[dict[str, Any]] = []
        q0_answer, q0_diag = call_single_qa_answer(
            output_method=output_method,
            client=client,
            provider=provider,
            model=model,
            row=prompt_row,
            image_path=image_path,
            question_id="q0_leg_count",
            prompt_template=prompt_templates["q0_leg_count"],
            leg_index=None,
            schema=qa_schemas["q0_leg_count"],
            validator=qa_validators["q0_leg_count"],
            run_dir=run_dir,
            max_tokens=q0_max_tokens,
            temperature=temperature,
            schema_retry_count=schema_retry_count,
            output_control=output_control,
        )
        chart_diags.append(q0_diag)
        leg_count = q0_answer.get("value") if isinstance(q0_answer, dict) and q0_answer.get("status") == "present" else None
        if isinstance(leg_count, int) and leg_count > 0:
            if leg_count > max_qa_legs:
                failures.append({"method": output_method, "sample_id": row["sample_id"], "chart_id": chart_id, "error": f"q0_leg_count_exceeds_safety_cap:{leg_count}"})
                leg_count = max_qa_legs
            for leg_index in range(1, leg_count + 1):
                _, diag = call_batched_leg_answers(
                    output_method=output_method,
                    client=client,
                    provider=provider,
                    model=model,
                    row=prompt_row,
                    image_path=image_path,
                    leg_index=leg_index,
                    prompt_templates=prompt_templates,
                    schema=batch_schema,
                    batch_validator=batch_validator,
                    qa_validators=qa_validators,
                    run_dir=run_dir,
                    max_tokens=batched_max_tokens,
                    temperature=temperature,
                    schema_retry_count=schema_retry_count,
                    output_control=output_control,
                )
                chart_diags.append(diag)

        prediction, agg_diag = aggregate_chart(prompt_row, run_dir / output_method / "qa_json" / chart_id)
        write_json(run_dir / output_method / "canonical_json" / f"{chart_id}.json", prediction)
        write_json(run_dir / output_method / "aggregation_diagnostics" / f"{chart_id}.json", agg_diag)
        write_json(run_dir / output_method / "qa_call_diagnostics" / f"{chart_id}.json", chart_diags)
        errors = validate_canonical(prediction, validator)
        write_json(run_dir / output_method / "validation" / f"{chart_id}.json", errors)
        item: dict[str, Any] = {
            "method": output_method,
            "source_method": "C2",
            "sample_id": row["sample_id"],
            "chart_id": chart_id,
            "validation_error_count": len(errors),
            "validation_errors": errors,
            "qa_calls_total": len(chart_diags),
            "qa_calls_saved": sum(1 for diag in chart_diags if diag.get("saved_answer")),
            "qa_fields_saved": sum((diag.get("saved_field_count") or 1) for diag in chart_diags if diag.get("saved_answer")),
            "qa_schema_retry_count_total": sum(diag.get("schema_retry_count") or 0 for diag in chart_diags),
            "score": None,
        }
        if errors:
            failures.append({"method": output_method, "sample_id": row["sample_id"], "chart_id": chart_id, "error": "schema_validation_failed"})
        else:
            item["score"] = score_if_valid(method=output_method, pred=prediction, target_path=targets[chart_id], run_dir=run_dir, chart_id=chart_id)
        results.append(item)
    return results, failures


def write_run_manifest(
    *,
    run_dir: Path,
    source_run_dir: Path,
    methods: list[str],
    args: argparse.Namespace,
    openai_base_url: str | None,
) -> None:
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_dir.name,
        "source_run_dir": display_path(source_run_dir),
        "methods": methods,
        "models": {
            "openai_compatible": {"name": args.model, "temperature": args.temperature},
            "anthropic_compatible": {"name": args.anthropic_model, "temperature": args.temperature},
        },
        "api": {
            "openai_compatible": model_api_manifest(
                provider="openai_compatible",
                base_url=openai_base_url,
                api_key_env=args.openai_api_key_env,
                json_mode=False,
                assistant_prefill_json=False,
            ),
            "anthropic_compatible": model_api_manifest(
                provider="anthropic_compatible",
                base_url=args.anthropic_base_url,
                api_key_env=args.anthropic_api_key_env,
                json_mode=False,
                assistant_prefill_json=False,
            ),
        },
        "output_control": {
            "C1_GPT54": "openai_tool_call",
            "C2_GPT54_batched_leg": "openai_tool_call",
            "C2_CLAUDE_batched_leg": "anthropic_tool_use",
            "C3_GPT54": "openai_tool_call",
            "C4_GPT54": "openai_tool_call",
        },
        "c2_batched_leg_policy": {
            "q0_leg_count_first": True,
            "leg_count_source_for_followup_questions": "C2_q0_model_answer_only",
            "per_leg_model_call_outputs_six_fixed_qa_answers": True,
            "max_qa_legs_safety_cap": args.max_qa_legs,
            "schema_retry_count": args.c2_schema_retry_count,
            "target_leg_count_used_for_followup_questions": False,
            "ocr_text_used": False,
            "field_candidates_used": False,
            "deterministic_aggregator": "scripts/aggregate_c2_qa_candidate.py",
        },
        "schema": {"path": display_path(SCHEMA_PATH), "sha256": sha256_file(SCHEMA_PATH)},
        "c3_questionnaire_schema": {"path": display_path(C3_QUESTIONNAIRE_SCHEMA), "sha256": sha256_file(C3_QUESTIONNAIRE_SCHEMA)},
        "prompts": {
            method: {"path": display_path(PROMPTS[METHOD_SPECS[method]["base_method"]]), "sha256": sha256_file(PROMPTS[METHOD_SPECS[method]["base_method"]])}
            for method in methods
            if METHOD_SPECS[method]["kind"] == "image_json"
        },
        "qa_prompt_bundle": {
            "path": display_path(QA_PROMPT_DIR),
            "files": {path.name: sha256_file(path) for path in sorted(QA_PROMPT_DIR.glob("*.txt"))},
        },
        "input_policy": {
            "target_used_for_prompt_or_parsing": False,
            "scorer_used_only_after_schema_validation": True,
            "web_search_used": False,
        },
    }
    write_json(run_dir / "formal_run_manifest.json", manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rerun Group 1 C-family methods with GPT-5.4; C2 uses batched per-leg QA.")
    parser.add_argument("--source-run-dir", type=Path, default=DEFAULT_SOURCE_RUN_DIR)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--methods", default=DEFAULT_METHODS, help="Comma list. Accepts C1,C2,C3,C4 aliases.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--openai-base-url", default=None)
    parser.add_argument("--openai-api-key-env", default=None)
    parser.add_argument("--anthropic-model", default=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"))
    parser.add_argument("--anthropic-base-url", default=None)
    parser.add_argument("--anthropic-api-key-env", default=None)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--vlm-max-tokens", type=int, default=4096)
    parser.add_argument("--c2-q0-max-tokens", type=int, default=1024)
    parser.add_argument("--c2-batched-max-tokens", type=int, default=3072)
    parser.add_argument("--vlm-schema-retry-count", type=int, default=1)
    parser.add_argument("--c2-schema-retry-count", type=int, default=1)
    parser.add_argument("--max-qa-legs", type=int, default=12)
    args = parser.parse_args()

    source_run_dir = resolve_run_path(args.source_run_dir)
    run_dir = resolve_run_path(args.run_dir)
    methods = parse_methods(args.methods)
    if run_dir.exists() and not args.resume:
        raise RuntimeError(f"Run directory already exists: {run_dir}. Use --resume or choose a new --run-dir.")

    rows_by_method = {method: method_rows(source_run_dir, method, args.limit) for method in methods}
    targets = load_targets(source_run_dir / "scoring_manifest.jsonl")
    prepare_run_dir(source_run_dir=source_run_dir, run_dir=run_dir, methods=methods, rows_by_method=rows_by_method, args=args)
    missing = collect_missing_artifacts(rows_by_method=rows_by_method, methods=methods, targets=targets)
    preflight = write_preflight_report(run_dir=run_dir, methods=methods, rows_by_method=rows_by_method, missing=missing)
    if args.preflight_only or missing:
        print(json.dumps(preflight, ensure_ascii=False, indent=2))
        return 0 if not missing else 2

    openai_base_url = effective_openai_base_url(args.openai_base_url)
    write_run_manifest(run_dir=run_dir, source_run_dir=source_run_dir, methods=methods, args=args, openai_base_url=openai_base_url)

    canonical_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    canonical_validator = Draft202012Validator(canonical_schema)
    c3_questionnaire_schema = json.loads(C3_QUESTIONNAIRE_SCHEMA.read_text(encoding="utf-8"))
    targets = load_targets(run_dir / "scoring_manifest.jsonl")
    openai_client: Any | None = None
    anthropic_client: Any | None = None

    all_results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    skipped_methods: list[dict[str, Any]] = []
    for method in methods:
        existing_method_summary = run_dir / method / "method_summary.json"
        if existing_method_summary.exists():
            print(f"Skipping {method}; existing method_summary.json found", flush=True)
            skipped_methods.append({"method": method, "reason": "existing_method_summary", "path": display_path(existing_method_summary)})
            continue
        print(f"Running {method} on {len(rows_by_method[method])} samples", flush=True)
        spec = METHOD_SPECS[method]
        provider = spec["provider"]
        if provider == "openai_compatible":
            if openai_client is None:
                openai_client = create_model_client(provider="openai_compatible", base_url=openai_base_url, api_key_env=args.openai_api_key_env)
            client = openai_client
            model = args.model
            output_control = "openai_tool_call"
        elif provider == "anthropic_compatible":
            if anthropic_client is None:
                anthropic_client = create_model_client(
                    provider="anthropic_compatible",
                    base_url=args.anthropic_base_url,
                    api_key_env=args.anthropic_api_key_env,
                )
            client = anthropic_client
            model = args.anthropic_model
            output_control = "anthropic_tool_use"
        else:
            raise ValueError(f"Unsupported method provider: {provider}")
        if spec["kind"] == "image_json":
            if provider != "openai_compatible":
                raise ValueError(f"image_json variants in this runner require openai_compatible, got {provider}")
            results, method_failures = run_image_json_variant(
                output_method=method,
                base_method=spec["base_method"],
                rows=rows_by_method[method],
                targets=targets,
                client=client,
                provider=provider,
                model=model,
                max_tokens=args.vlm_max_tokens,
                temperature=args.temperature,
                schema_retry_count=args.vlm_schema_retry_count,
                validator=canonical_validator,
                canonical_schema=canonical_schema,
                c3_questionnaire_schema=c3_questionnaire_schema,
                run_dir=run_dir,
            )
            method_summary = summarize_method(method, results)
        elif spec["kind"] == "c2_batched_leg":
            results, method_failures = run_c2_batched_leg_variant(
                output_method=method,
                rows=rows_by_method[method],
                targets=targets,
                client=client,
                provider=provider,
                model=model,
                q0_max_tokens=args.c2_q0_max_tokens,
                batched_max_tokens=args.c2_batched_max_tokens,
                temperature=args.temperature,
                schema_retry_count=args.c2_schema_retry_count,
                validator=canonical_validator,
                canonical_schema=canonical_schema,
                run_dir=run_dir,
                max_qa_legs=args.max_qa_legs,
                output_control=output_control,
            )
            method_summary = summarize_c2(results)
        else:
            raise AssertionError(spec["kind"])
        all_results.extend(results)
        failures.extend(method_failures)
        write_json(run_dir / method / "method_summary.json", method_summary)

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_dir.name,
        "source_run_dir": display_path(source_run_dir),
        "methods": {
            method: json.loads((run_dir / method / "method_summary.json").read_text(encoding="utf-8"))
            for method in methods
            if (run_dir / method / "method_summary.json").exists()
        },
        "method_failure_count": len(failures),
        "method_failures": failures,
        "skipped_methods": skipped_methods,
        "hard_blocker_count": 0,
        "hard_blockers": [],
    }
    write_json(run_dir / "summary_report.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
