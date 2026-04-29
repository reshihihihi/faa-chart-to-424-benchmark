from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from aggregate_c2_qa_candidate import AGGREGATOR_SPEC, QA_PROMPT_DIR, QUESTION_TO_CANONICAL, aggregate_chart
from model_clients import call_model_json, create_model_client, model_api_manifest, save_model_response
from run_pilot10_anthropic import (
    DATA_DIR,
    SCHEMA_PATH,
    read_jsonl,
    resolve_package_path,
    score_canonical,
    sha256_file,
    validate_canonical,
    write_json,
    write_text,
)


RUN_OUTPUT_ROOT = ROOT / "predictions" / "pilot10_external"
DEFAULT_RUN_ID = "pilot10_group1_c2_claude_tooluse_qa_ordinary_ocr_20260428_r1"
QUESTION_SEQUENCE = [
    "q_terminator",
    "q1_fix_ident",
    "q2_altitude_constraint",
    "q3_turn",
    "q4_course_or_radial",
    "q5_hold_params",
]
QUESTION_DEF = {
    "q0_leg_count": "answer_int",
    "q_terminator": "answer_terminator",
    "q1_fix_ident": "answer_fix_ident",
    "q2_altitude_constraint": "answer_altitude_constraint",
    "q3_turn": "answer_turn",
    "q4_course_or_radial": "answer_course_or_radial",
    "q5_hold_params": "answer_hold_params",
}
QUESTION_STATUS_ENUM = {
    "q0_leg_count": ["present", "not_observable", "unknown"],
    "q_terminator": ["present", "not_observable", "unknown"],
    "q1_fix_ident": ["present", "not_applicable", "not_observable", "unknown"],
    "q2_altitude_constraint": ["present", "not_applicable", "not_observable", "unknown"],
    "q3_turn": ["present", "not_applicable", "not_observable", "unknown"],
    "q4_course_or_radial": ["present", "not_applicable", "not_observable", "unknown"],
    "q5_hold_params": ["present", "not_applicable", "not_observable", "unknown"],
}
FACILITY_TYPE_WORDS = {
    "VOR",
    "VORTAC",
    "DME",
    "NDB",
    "FIX",
    "WAYPOINT",
    "NAVAID",
    "HOLDING",
    "AIRPORT",
    "RUNWAY",
    "LOCALIZER",
    "LOC",
    "ILS",
}


def display_path(path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def file_artifact(path: Path) -> dict[str, Any]:
    return {
        "path": display_path(path),
        "exists": path.exists(),
        "sha256": sha256_file(path) if path.exists() else None,
    }


def build_input_artifacts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "sample_id": row["pilot_sample_id"],
            "chart_id": row["chart_id"],
            "image": file_artifact(resolve_package_path(row["image_path"])),
        }
        for row in rows
    ]


def qa_tool_schema(canonical_schema: dict[str, Any], question_id: str) -> dict[str, Any]:
    if question_id == "q4_course_or_radial":
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "C2 QA tool schema for q4_course_or_radial",
            "type": "object",
            "required": ["status", "value"],
            "additionalProperties": False,
            "properties": {
                "status": {"type": "string", "enum": QUESTION_STATUS_ENUM[question_id]},
                "value": {
                    "anyOf": [
                        {"type": "null"},
                        {
                            "type": "object",
                            "required": ["type"],
                            "additionalProperties": False,
                            "properties": {
                                "type": {"type": "string", "enum": ["course_deg", "navaid_radial", "direct"]},
                                "course_deg": {"type": "number", "minimum": 0, "maximum": 359.9},
                                "navaid": {"type": "string", "minLength": 1, "maxLength": 5},
                                "radial_deg": {"type": "number", "minimum": 0, "maximum": 359.9},
                                "direction": {"type": "string", "enum": ["outbound", "inbound"]},
                            },
                        },
                    ],
                },
            },
        }

    schema = copy.deepcopy(canonical_schema["$defs"][QUESTION_DEF[question_id]])
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = f"C2 QA answer schema for {question_id}"
    schema["properties"]["status"] = {"type": "string", "enum": QUESTION_STATUS_ENUM[question_id]}
    return schema


def qa_validation_schema(canonical_schema: dict[str, Any], question_id: str) -> dict[str, Any]:
    schema = copy.deepcopy(canonical_schema["$defs"][QUESTION_DEF[question_id]])
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = f"C2 QA strict validation schema for {question_id}"
    schema["properties"]["status"] = {"type": "string", "enum": QUESTION_STATUS_ENUM[question_id]}
    return schema


def validate_answer(
    answer: Any,
    *,
    question_id: str,
    validator: Draft202012Validator,
) -> list[str]:
    errors = [error.message for error in sorted(validator.iter_errors(answer), key=lambda item: item.path)]
    if not isinstance(answer, dict):
        return errors or ["answer_is_not_object"]

    status = answer.get("status")
    value = answer.get("value")
    if status != "present" and value is not None:
        errors.append("status_value_violation: non-present status requires value null")
    if status == "present" and value is None:
        errors.append("status_value_violation: present status requires non-null value")
    if question_id == "q1_fix_ident" and status == "present" and isinstance(value, str):
        if value.upper() in FACILITY_TYPE_WORDS:
            errors.append(f"facility_type_not_fix_ident: {value}")
    return errors


def qa_relative_path(question_id: str, leg_index: int | None = None) -> Path:
    if question_id == "q0_leg_count":
        return Path("q0_leg_count.json")
    if leg_index is None:
        raise ValueError(f"leg_index required for {question_id}")
    return Path(f"leg_{leg_index:03d}") / f"{question_id}.json"


def build_prompt(row: dict[str, Any], question_id: str, template: str, leg_index: int | None) -> str:
    question_text = template
    if leg_index is not None:
        question_text = question_text.replace("<LEG_INDEX>", str(leg_index))
    return "\n".join(
        [
            "# C2 Fixed QA Call",
            "",
            "Method boundary:",
            "full chart image -> VLM answers one fixed QA prompt -> deterministic aggregator -> canonical JSON.",
            "",
            "Allowed inputs for this call:",
            "- chart_id, airport, approach_ident, chart_name",
            "- full chart image",
            "- this fixed QA prompt",
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
            f"question_id: {question_id}",
            f"leg_index: {leg_index if leg_index is not None else 'none'}",
            "",
            question_text,
        ]
    )


def build_retry_prompt(
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
            "Your previous answer failed JSON/schema/status-value validation.",
            "Return the same single answer object for the same question using the same chart image and metadata.",
            "Do not use targets, scorer output, CIFP, annotations, OCR, web search, or any new input.",
            "Do not output markdown or prose.",
            "",
            "Fixed hard rules:",
            "- The answer must have exactly status and value.",
            "- If status is not present, value must be null.",
            "- If status is present, value must follow the question schema.",
            "- If value is an object, emit it as a nested JSON object, never as a quoted/stringified JSON object.",
            "- For q1_fix_ident, never output VOR, VORTAC, DME, NDB, FIX, WAYPOINT, NAVAID, HOLDING, AIRPORT, RUNWAY, LOCALIZER, LOC, or ILS as value.",
            "- For q4_course_or_radial and q5_hold_params, every degree field must be 0.0 through 359.9. If the chart shows 360 degrees, encode it as 359.9, never 360.",
            "",
            "VALIDATION_ERRORS:",
            "\n".join(validation_errors),
            "",
            "PREVIOUS_OUTPUT:",
            previous_output,
        ]
    )


def call_qa_answer(
    *,
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
    output_control: str,
    schema_retry_count: int,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    chart_id = row["chart_id"]
    rel_path = qa_relative_path(question_id, leg_index)
    base_prompt = build_prompt(row, question_id, prompt_template, leg_index)
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
            write_text(run_dir / "C2" / "raw_text" / chart_id / rel_path.with_suffix(f".attempt_{attempt}.txt"), text)
            save_model_response(run_dir / "C2" / "raw_responses" / chart_id / rel_path.with_suffix(f".attempt_{attempt}.json"), response)
            answer = json.loads(text)
            errors = validate_answer(answer, question_id=question_id, validator=validator)
            write_json(run_dir / "C2" / "qa_validation" / chart_id / rel_path.with_suffix(f".attempt_{attempt}.json"), errors)
            if not errors:
                write_json(run_dir / "C2" / "qa_json" / chart_id / rel_path, answer)
                write_text(run_dir / "C2" / "raw_text" / chart_id / rel_path.with_suffix(".txt"), text)
                save_model_response(run_dir / "C2" / "raw_responses" / chart_id / rel_path.with_suffix(".json"), response)
                write_json(run_dir / "C2" / "qa_validation" / chart_id / rel_path, errors)
                diagnostic["schema_retry_count"] = attempt - 1
                diagnostic["validation_errors"] = []
                diagnostic["saved_answer"] = True
                return answer, diagnostic
            diagnostic["validation_errors"] = errors
            if attempt < max_attempts:
                current_prompt = build_retry_prompt(
                    original_prompt=base_prompt,
                    previous_output=text,
                    validation_errors=errors,
                )
        except Exception as exc:  # noqa: BLE001
            diagnostic["validation_errors"] = [repr(exc)]
            write_text(
                run_dir / "C2" / "qa_errors" / chart_id / rel_path.with_suffix(f".attempt_{attempt}.txt"),
                repr(exc),
            )
            if attempt < max_attempts:
                current_prompt = build_retry_prompt(
                    original_prompt=base_prompt,
                    previous_output=last_text,
                    validation_errors=[repr(exc)],
                )

    diagnostic["schema_retry_count"] = max_attempts - 1
    write_json(run_dir / "C2" / "qa_invalid" / chart_id / rel_path, {"last_output": last_text, "diagnostic": diagnostic})
    return None, diagnostic


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [item["score"] for item in results if item.get("score")]
    correct = sum(item["correct"] for item in scored)
    total = sum(item["total"] for item in scored)
    return {
        "samples_total": len(results),
        "schema_valid": sum(1 for item in results if item.get("validation_error_count") == 0),
        "samples_scored": len(scored),
        "score": {"correct": correct, "total": total, "accuracy": correct / total if total else None},
        "qa_calls_total": sum(item.get("qa_calls_total", 0) for item in results),
        "qa_calls_saved": sum(item.get("qa_calls_saved", 0) for item in results),
        "qa_schema_retry_count_total": sum(item.get("qa_schema_retry_count_total", 0) for item in results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Group 1 C2 fixed-QA pilot10 with VLM tool-use output control.")
    parser.add_argument("--provider", default="anthropic_compatible", choices=["anthropic_compatible"])
    parser.add_argument("--model", default="claude-sonnet-4-5-20250929")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key-env", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--sample-manifest", type=Path, default=DATA_DIR / "pilot10_manifest.jsonl")
    parser.add_argument("--output-root", type=Path, default=RUN_OUTPUT_ROOT)
    parser.add_argument("--sample-role", default="pilot10_external_excluded_from_formal_evaluation")
    parser.add_argument("--output-control", default="anthropic_tool_use", choices=["anthropic_tool_use"])
    parser.add_argument("--schema-retry-count", type=int, default=1)
    parser.add_argument("--max-qa-legs", type=int, default=12)
    args = parser.parse_args()

    run_dir = args.output_root / args.run_id
    if run_dir.exists():
        raise RuntimeError(f"Run directory already exists: {run_dir}")

    rows = read_jsonl(args.sample_manifest)[: args.limit]
    canonical_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    canonical_validator = Draft202012Validator(canonical_schema)
    qa_schemas = {question_id: qa_tool_schema(canonical_schema, question_id) for question_id in ["q0_leg_count", *QUESTION_SEQUENCE]}
    qa_validation_schemas = {
        question_id: qa_validation_schema(canonical_schema, question_id)
        for question_id in ["q0_leg_count", *QUESTION_SEQUENCE]
    }
    qa_validators = {question_id: Draft202012Validator(schema) for question_id, schema in qa_validation_schemas.items()}
    prompt_templates = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted(QA_PROMPT_DIR.glob("*.txt"))
    }

    run_manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id,
        "experiment_group": "group1_full_chart_main_extraction",
        "method": "C2",
        "parameter_status": "temporary_pilot_use_only_not_final_freeze",
        "sample_manifest": display_path(args.sample_manifest),
        "sample_role": args.sample_role,
        "model": {
            "provider": args.provider,
            "name": args.model,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "status": "candidate_not_formal_frozen",
        },
        "api": model_api_manifest(
            provider=args.provider,
            base_url=args.base_url,
            api_key_env=args.api_key_env,
            json_mode=False,
            assistant_prefill_json=False,
        ),
        "method_boundary": {
            "allowed_inputs": ["chart_id", "airport", "approach_ident", "chart_name", "full_chart_image", "fixed_QA_prompt_bundle"],
            "forbidden_inputs": [
                "ocr_text",
                "ocr_bbox",
                "roi",
                "automatic_field_candidates",
                "field_to_leg_candidates",
                "gold_missed_approach_prose",
                "canonical_target",
                "scorer_output",
                "CIFP_or_ARINC_424_records",
                "human_annotations",
                "previous_model_outputs_for_same_chart",
                "web_search",
            ],
        },
        "qa_runner_policy": {
            "q0_leg_count_first": True,
            "leg_count_source_for_followup_questions": "C2_q0_model_answer_only",
            "max_qa_legs_safety_cap": args.max_qa_legs,
            "per_question_schema_retry_count": args.schema_retry_count,
            "schema_retry_uses_target_or_scorer": False,
            "malformed_or_invalid_qa_answer_policy": "do_not_save_primary_qa_json; aggregator treats missing as unknown",
            "one_question_per_model_call": True,
            "target_leg_count_used_for_followup_questions": False,
            "ocr_text_used": False,
            "field_candidates_used": False,
        },
        "qa_artifact_layout": {
            "primary_answers": "C2/qa_json/<chart_id>/q0_leg_count.json and C2/qa_json/<chart_id>/leg_###/<question_id>.json",
            "raw_text": "C2/raw_text/<chart_id>/...",
            "raw_responses": "C2/raw_responses/<chart_id>/...",
            "invalid_attempts": "C2/qa_invalid/<chart_id>/...",
            "aggregation_diagnostics": "C2/aggregation_diagnostics/<chart_id>.json",
        },
        "input_artifacts": build_input_artifacts(rows),
        "output_control": {
            "type": args.output_control,
            "tool_name": "emit_qa_answer",
            "tool_schema_note": "q4_course_or_radial uses a proxy-compatible object-valued tool schema; local QA validation still uses the strict canonical answer schema.",
            "per_question_tool_schema": {
                question_id: {
                    "schema_title": qa_schemas[question_id]["title"],
                    "canonical_answer_def": QUESTION_DEF[question_id],
                    "status_enum": QUESTION_STATUS_ENUM[question_id],
                }
                for question_id in qa_schemas
            },
            "parser_repair_allowed": False,
            "canonical_semantic_validation": True,
            "anthropic_tool_use_single_parameter_wrapper_unwrapped": True,
        },
        "schema": {"path": display_path(SCHEMA_PATH), "sha256": sha256_file(SCHEMA_PATH)},
        "qa_prompt_bundle": {
            "path": display_path(QA_PROMPT_DIR),
            "files": {
                path.name: sha256_file(path)
                for path in sorted(QA_PROMPT_DIR.glob("*.txt"))
            },
            "status": "candidate_not_formal_frozen",
        },
        "aggregator": {
            "script_path": "scripts/aggregate_c2_qa_candidate.py",
            "script_sha256": sha256_file(ROOT / "scripts" / "aggregate_c2_qa_candidate.py"),
            "spec_path": display_path(AGGREGATOR_SPEC),
            "spec_sha256": sha256_file(AGGREGATOR_SPEC),
            "target_used_for_aggregation": False,
            "scorer_used_for_aggregation": False,
        },
        "scoring": {"target_used_only_after_validation": True},
        "samples": [row["pilot_sample_id"] for row in rows],
    }
    write_json(run_dir / "run_manifest.json", run_manifest)

    client = create_model_client(provider=args.provider, base_url=args.base_url, api_key_env=args.api_key_env)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for row in rows:
        chart_id = row["chart_id"]
        image_path = resolve_package_path(row["image_path"])
        print(f"Running C2 QA {row['pilot_sample_id']} {chart_id}", flush=True)
        chart_diagnostics: list[dict[str, Any]] = []

        q0_answer, q0_diag = call_qa_answer(
            client=client,
            provider=args.provider,
            model=args.model,
            row=row,
            image_path=image_path,
            question_id="q0_leg_count",
            prompt_template=prompt_templates["q0_leg_count"],
            leg_index=None,
            schema=qa_schemas["q0_leg_count"],
            validator=qa_validators["q0_leg_count"],
            run_dir=run_dir,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            output_control=args.output_control,
            schema_retry_count=args.schema_retry_count,
        )
        chart_diagnostics.append(q0_diag)
        leg_count = q0_answer.get("value") if isinstance(q0_answer, dict) and q0_answer.get("status") == "present" else None
        if isinstance(leg_count, int) and leg_count > 0:
            if leg_count > args.max_qa_legs:
                failures.append({"chart_id": chart_id, "method": "C2", "error": f"q0_leg_count_exceeds_safety_cap:{leg_count}"})
                leg_count = args.max_qa_legs
            for leg_index in range(1, leg_count + 1):
                for question_id in QUESTION_SEQUENCE:
                    _, diag = call_qa_answer(
                        client=client,
                        provider=args.provider,
                        model=args.model,
                        row=row,
                        image_path=image_path,
                        question_id=question_id,
                        prompt_template=prompt_templates[question_id],
                        leg_index=leg_index,
                        schema=qa_schemas[question_id],
                        validator=qa_validators[question_id],
                        run_dir=run_dir,
                        max_tokens=args.max_tokens,
                        temperature=args.temperature,
                        output_control=args.output_control,
                        schema_retry_count=args.schema_retry_count,
                    )
                    chart_diagnostics.append(diag)

        prediction, aggregation_diagnostics = aggregate_chart(row, run_dir / "C2" / "qa_json" / chart_id)
        write_json(run_dir / "C2" / "canonical_json" / f"{chart_id}.json", prediction)
        write_json(run_dir / "C2" / "aggregation_diagnostics" / f"{chart_id}.json", aggregation_diagnostics)
        write_json(run_dir / "C2" / "qa_call_diagnostics" / f"{chart_id}.json", chart_diagnostics)
        validation_errors = validate_canonical(prediction, canonical_validator)
        write_json(run_dir / "C2" / "validation" / f"{chart_id}.json", validation_errors)

        item: dict[str, Any] = {
            "method": "C2",
            "sample_id": row["pilot_sample_id"],
            "chart_id": chart_id,
            "validation_error_count": len(validation_errors),
            "validation_errors": validation_errors,
            "qa_calls_total": len(chart_diagnostics),
            "qa_calls_saved": sum(1 for diag in chart_diagnostics if diag.get("saved_answer")),
            "qa_schema_retry_count_total": sum(diag.get("schema_retry_count") or 0 for diag in chart_diagnostics),
            "score": None,
        }
        if validation_errors:
            failures.append({"chart_id": chart_id, "method": "C2", "error": "schema_validation_failed"})
        else:
            target_path = resolve_package_path(row["canonical_proxy_gt_file"])
            target = json.loads(target_path.read_text(encoding="utf-8"))
            score = score_canonical(prediction, target)
            write_json(run_dir / "C2" / "scores" / f"{chart_id}.json", score)
            item["score"] = {key: score[key] for key in ["correct", "total", "accuracy"]}
        results.append(item)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id,
        "method": "C2",
        "summary": summarize(results),
        "failures": failures,
    }
    write_json(run_dir / "summary_report.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
