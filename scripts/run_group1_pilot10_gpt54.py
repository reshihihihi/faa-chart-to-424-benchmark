from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from c3_questionnaire_to_canonical import questionnaire_to_canonical
from model_clients import call_model_json, create_model_client, model_api_manifest, save_model_response
from run_b1prime_c4_pilot10 import build_field_candidates
from run_pilot10_anthropic import (
    B1_PROMPT,
    DATA_DIR,
    ROOT as HELPERS_ROOT,
    SCHEMA_PATH,
    fill_prompt,
    read_jsonl,
    resolve_package_path,
    score_canonical,
    sha256_file,
    validate_canonical,
    write_json,
    write_text,
)


assert ROOT == HELPERS_ROOT

DEFAULT_RUN_ID = "pilot10_group1_gpt54_ordinary_ocr_20260428_r1"
RUN_OUTPUT_ROOT = ROOT / "predictions" / "pilot10_external"
DEFAULT_OCR1_TEXT_ROOT = (
    ROOT / "ocr_artifacts" / "pilot10_external" / "ocr1_paddleocr_ppocrv5_20260428_r1" / "full_text"
)
DEFAULT_OCR2_TEXT_ROOT = (
    ROOT / "ocr_artifacts" / "pilot10_external" / "ocr2_tesseract5_20260428_r1" / "full_text"
)

B1_PRIME_PROMPT = ROOT / "prompts" / "paper_v2" / "b1_prime_ocr_field_candidates_to_canonical_pilot10.zh_v0_candidate.md"
C1_PROMPT = ROOT / "prompts" / "paper_v2" / "c1_image_to_canonical_pilot10.zh_v1_candidate.md"
C3_PROMPT = ROOT / "prompts" / "paper_v2" / "c3_questionnaire_pilot10.zh_v1_candidate.md"
C4_PROMPT = ROOT / "prompts" / "paper_v2" / "c4_image_ocr_to_canonical_pilot10.zh_v1_candidate.md"
FIELD_CANDIDATES_SCHEMA = ROOT / "schemas" / "field_candidates.schema.candidate.json"
C3_QUESTIONNAIRE_SCHEMA = ROOT / "schemas" / "c3_questionnaire.schema.candidate.json"
C3_PARSER = ROOT / "scripts" / "c3_questionnaire_to_canonical.py"


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


def ocr_manifest_artifacts(ocr_text_root: Path) -> dict[str, Any]:
    artifact_root = ocr_text_root.parent
    return {
        "artifact_root": display_path(artifact_root),
        "run_manifest": file_artifact(artifact_root / "run_manifest.json"),
        "manifest_jsonl": file_artifact(artifact_root / "manifest.jsonl"),
    }


def build_input_artifacts_for_method(
    rows: list[dict[str, Any]],
    *,
    method: str,
    ocr1_text_root: Path,
) -> list[dict[str, Any]]:
    artifacts = []
    for row in rows:
        chart_id = row["chart_id"]
        item: dict[str, Any] = {
            "sample_id": row["pilot_sample_id"],
            "chart_id": chart_id,
        }
        if method in {"C1", "C3", "C4"}:
            item["image"] = file_artifact(resolve_package_path(row["image_path"]))
        if method in {"B1", "B1_prime", "C4"}:
            item["OCR-1_full_text"] = file_artifact(ocr1_text_root / f"{chart_id}.txt")
        artifacts.append(item)
    return artifacts


def build_input_artifacts_by_method(
    rows: list[dict[str, Any]],
    *,
    methods: list[str],
    ocr1_text_root: Path,
) -> dict[str, list[dict[str, Any]]]:
    return {
        method: build_input_artifacts_for_method(rows, method=method, ocr1_text_root=ocr1_text_root)
        for method in methods
    }


METHOD_BOUNDARIES = {
    "B1": {
        "allowed_inputs": ["chart_id", "airport", "approach_ident", "chart_name", "OCR-1 full-chart text"],
        "forbidden_inputs": [
            "chart image pixels at the LLM stage",
            "OCR bbox",
            "ROI labels",
            "field_candidates",
            "field_to_leg_candidates",
            "canonical_target_or_answer_key",
            "scorer_output",
            "CIFP_or_ARINC_424_records",
            "human_annotations",
            "previous_model_outputs_for_same_chart",
            "web_search",
        ],
    },
    "C1": {
        "allowed_inputs": ["chart_id", "airport", "approach_ident", "chart_name", "full-chart image"],
        "forbidden_inputs": [
            "OCR text",
            "OCR bbox",
            "ROI labels",
            "field_candidates",
            "field_to_leg_candidates",
            "canonical_target_or_answer_key",
            "scorer_output",
            "CIFP_or_ARINC_424_records",
            "human_annotations",
            "previous_model_outputs_for_same_chart",
            "web_search",
        ],
    },
    "C3": {
        "allowed_inputs": ["chart_id", "airport", "approach_ident", "chart_name", "full-chart image"],
        "forbidden_inputs": [
            "OCR text",
            "OCR bbox",
            "ROI labels",
            "field_candidates",
            "field_to_leg_candidates",
            "canonical_target_or_answer_key",
            "scorer_output",
            "CIFP_or_ARINC_424_records",
            "human_annotations",
            "previous_model_outputs_for_same_chart",
            "web_search",
        ],
    },
    "C4": {
        "allowed_inputs": ["chart_id", "airport", "approach_ident", "chart_name", "full-chart image", "OCR-1 full-chart text"],
        "forbidden_inputs": [
            "OCR text from another source or view",
            "OCR bbox",
            "ROI labels",
            "field_candidates",
            "field_to_leg_candidates",
            "canonical_target_or_answer_key",
            "scorer_output",
            "CIFP_or_ARINC_424_records",
            "human_annotations",
            "previous_model_outputs_for_same_chart",
            "web_search",
        ],
    },
}


def parse_strict_json(text: str) -> tuple[dict[str, Any], str]:
    return json.loads(text.strip()), "strict_json"


def summarize_method(method: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    method_results = [item for item in results if item["method"] == method]
    scored = [item["score"] for item in method_results if item.get("score")]
    correct = sum(item["correct"] for item in scored)
    total = sum(item["total"] for item in scored)
    policy_counts: dict[str, int] = {}
    for item in method_results:
        policy = item.get("json_extraction_policy") or "failed"
        policy_counts[policy] = policy_counts.get(policy, 0) + 1
    parser_repair_policies = {"code_fence_stripped", "first_json_object_extracted"}
    return {
        "samples_total": len(method_results),
        "schema_valid": sum(1 for item in method_results if item.get("validation_error_count") == 0),
        "samples_scored": len(scored),
        "json_extraction_policy_counts": policy_counts,
        "parser_repair_count_non_strict_json": sum(
            count for policy, count in policy_counts.items() if policy in parser_repair_policies
        ),
        "schema_retry_count_total": sum(item.get("schema_retry_count") or 0 for item in method_results),
        "score": {
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total else None,
        },
        "results": method_results,
    }


def save_not_run_notes(run_dir: Path) -> None:
    write_text(
        run_dir / "A1" / "NOT_RUN.md",
        "\n".join(
            [
                "# A1 Not Run",
                "",
                "Reason: A1 is handled by scripts/run_a1_a2_rules_pilot10.py, not by this LLM/VLM runner.",
                "Available input: OCR-1 PaddleOCR PP-OCRv5 pilot10 artifacts.",
                "Policy: use the candidate A1/A2 rules runner only when explicitly running A1/A2.",
            ]
        ),
    )
    write_text(
        run_dir / "A2" / "NOT_RUN.md",
        "\n".join(
            [
                "# A2 Not Run",
                "",
                "Reason: A2 is handled by scripts/run_a1_a2_rules_pilot10.py, not by this LLM/VLM runner.",
                "Available input: OCR-2 Tesseract 5.x pilot10 artifacts.",
                "Policy: A2 must use the same candidate/frozen rules as A1.",
            ]
        ),
    )
    write_text(
        run_dir / "C2" / "NOT_RUN.md",
        "\n".join(
            [
                "# C2 Not Run",
                "",
                "Reason: this runner does not execute the multi-call C2 QA pipeline.",
                "Available assets: prompts/path_c_qa_v2/ and scripts/aggregate_c2_qa_candidate.py.",
                "Policy: C2 requires a fixed QA runner, raw QA output layout, and rerun policy before formal running.",
            ]
        ),
    )
    write_text(
        run_dir / "D_SFT" / "EXCLUDED_BY_USER_SCOPE.md",
        "D-SFT is excluded from this pilot because the current user scope is Experiment Group 1 without D-SFT.",
    )


def build_schema_retry_prompt(
    *,
    original_prompt: str,
    previous_output: str,
    validation_errors: list[str] | None,
    parse_error: str | None,
) -> str:
    issue_lines = []
    if parse_error:
        issue_lines.append(f"JSON parse error: {parse_error}")
    for error in validation_errors or []:
        issue_lines.append(f"Schema validation error: {error}")
    issue_text = "\n".join(issue_lines) if issue_lines else "The previous output failed validation."
    return "\n".join(
        [
            original_prompt,
            "",
            "## Schema-Only Retry",
            "",
            "Your previous output failed the registered JSON/parser/schema checks below.",
            "Return a corrected object using the same allowed inputs and the same task.",
            "Do not use targets, scorer output, CIFP, annotations, external databases, or any new input.",
            "Do not add explanations.",
            "Do not wrap the output in markdown.",
            "Keep the same extraction task; only correct JSON syntax and schema-shape/status-value violations.",
            "",
            "Fixed schema hard rules:",
            "- status must be one of present, not_applicable, not_observable, unknown.",
            "- If status is not present, value must be null.",
            "- Q1_fix_ident.value must be a real ident, not a facility-type word.",
            "- Facility labels can be ident plus type, such as ORL VORTAC; use ORL as the ident when supported, never VORTAC.",
            "- Never output VOR, VORTAC, DME, NDB, FIX, WAYPOINT, NAVAID, HOLDING, AIRPORT, RUNWAY, LOCALIZER, LOC, or ILS as Q1_fix_ident.value.",
            "- All degree fields must be in the closed-open schema range 0.0 through 359.9. If the chart/OCR shows 360 degrees, encode it as 359.9, never 360.",
            "",
            "VALIDATION_ISSUES:",
            issue_text,
            "",
            "PREVIOUS_OUTPUT:",
            previous_output,
        ]
    )


def run_one_json_method(
    *,
    method: str,
    client: Any,
    provider: str,
    model: str,
    prompt: str,
    image_path: Path | None,
    target: dict[str, Any],
    validator: Draft202012Validator,
    run_dir: Path,
    chart_id: str,
    sample_id: str,
    max_tokens: int,
    temperature: float,
    json_mode: bool,
    assistant_prefill_json: bool,
    output_control: str,
    tool_schema: dict[str, Any] | None,
    tool_name: str,
    schema_retry_count: int,
    questionnaire_output: bool = False,
) -> tuple[dict[str, Any], dict[str, str] | None]:
    current_prompt = prompt
    last_text = ""
    last_error: str | None = None
    last_validation_errors: list[str] | None = None
    extraction_policy = {
        "openai_tool_call": "openai_tool_call_arguments",
        "anthropic_tool_use": "anthropic_tool_use_input",
    }.get(output_control, "strict_json")
    max_attempts = 1 + schema_retry_count

    for attempt in range(1, max_attempts + 1):
        try:
            text, response = call_model_json(
                client,
                provider=provider,
                model=model,
                prompt=current_prompt,
                image_path=image_path,
                max_tokens=max_tokens,
                temperature=temperature,
                json_mode=json_mode,
                assistant_prefill_json=assistant_prefill_json,
                output_control=output_control,
                tool_schema=tool_schema,
                tool_name=tool_name,
            )
            last_text = text
            write_text(run_dir / method / "raw_text" / f"{chart_id}.attempt_{attempt}.txt", text)
            save_model_response(run_dir / method / "raw_responses" / f"{chart_id}.attempt_{attempt}.json", response)

            parsed, _ = parse_strict_json(text)
            if questionnaire_output:
                write_json(run_dir / method / "questionnaire_json" / f"{chart_id}.attempt_{attempt}.json", parsed)
                pred = questionnaire_to_canonical(parsed)
            else:
                pred = parsed

            validation_errors = validate_canonical(pred, validator)
            write_json(run_dir / method / "validation" / f"{chart_id}.attempt_{attempt}.json", validation_errors)

            if not validation_errors:
                write_text(run_dir / method / "raw_text" / f"{chart_id}.txt", text)
                save_model_response(run_dir / method / "raw_responses" / f"{chart_id}.json", response)
                if questionnaire_output:
                    write_json(run_dir / method / "questionnaire_json" / f"{chart_id}.json", parsed)
                write_json(run_dir / method / "canonical_json" / f"{chart_id}.json", pred)
                write_json(run_dir / method / "validation" / f"{chart_id}.json", validation_errors)
                score = score_canonical(pred, target)
                write_json(run_dir / method / "scores" / f"{chart_id}.json", score)
                return {
                    "method": method,
                    "sample_id": sample_id,
                    "chart_id": chart_id,
                    "json_extraction_policy": extraction_policy,
                    "validation_error_count": 0,
                    "validation_errors": [],
                    "attempt_count": attempt,
                    "schema_retry_count": attempt - 1,
                    "score": {key: score[key] for key in ["correct", "total", "accuracy"]},
                }, None

            last_validation_errors = validation_errors
            last_error = "schema_validation_failed"
            if attempt < max_attempts:
                current_prompt = build_schema_retry_prompt(
                    original_prompt=prompt,
                    previous_output=text,
                    validation_errors=validation_errors,
                    parse_error=None,
                )
                continue
            write_text(run_dir / method / "raw_text" / f"{chart_id}.txt", text)
            if questionnaire_output:
                write_json(run_dir / method / "questionnaire_json" / f"{chart_id}.json", parsed)
            write_json(run_dir / method / "canonical_json" / f"{chart_id}.json", pred)
            write_json(run_dir / method / "validation" / f"{chart_id}.json", validation_errors)
            item = {
                "method": method,
                "sample_id": sample_id,
                "chart_id": chart_id,
                "json_extraction_policy": extraction_policy,
                "validation_error_count": len(validation_errors),
                "validation_errors": validation_errors,
                "attempt_count": attempt,
                "schema_retry_count": attempt - 1,
                "score": None,
            }
            return item, {"sample_id": sample_id, "chart_id": chart_id, "method": method, "error": last_error}
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
            write_text(run_dir / method / "parse_errors" / f"{chart_id}.attempt_{attempt}.txt", last_error)
            if attempt < max_attempts:
                current_prompt = build_schema_retry_prompt(
                    original_prompt=prompt,
                    previous_output=last_text,
                    validation_errors=last_validation_errors,
                    parse_error=last_error,
                )
                continue

    write_text(run_dir / method / "parse_errors" / f"{chart_id}.txt", last_error or "unknown_failure")
    item = {
        "method": method,
        "sample_id": sample_id,
        "chart_id": chart_id,
        "json_extraction_policy": extraction_policy,
        "validation_error_count": None,
        "validation_errors": last_validation_errors,
        "attempt_count": max_attempts,
        "schema_retry_count": schema_retry_count,
        "score": None,
        "failure": last_error,
    }
    return item, {"sample_id": sample_id, "chart_id": chart_id, "method": method, "error": last_error or "unknown_failure"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Experiment Group 1 pilot10 runnable subset with gpt-5.4.")
    parser.add_argument("--provider", default="openai_compatible", choices=["openai_compatible", "anthropic_compatible"])
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key-env", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--sample-manifest", type=Path, default=DATA_DIR / "pilot10_manifest.jsonl")
    parser.add_argument("--output-root", type=Path, default=RUN_OUTPUT_ROOT)
    parser.add_argument("--sample-role", default="pilot10_external_excluded_from_formal_evaluation")
    parser.add_argument("--ocr1-text-root", type=Path, default=DEFAULT_OCR1_TEXT_ROOT)
    parser.add_argument("--ocr2-text-root", type=Path, default=DEFAULT_OCR2_TEXT_ROOT)
    parser.add_argument("--json-mode", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--assistant-prefill-json", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument(
        "--output-control",
        default="raw_json",
        choices=["raw_json", "openai_tool_call", "anthropic_tool_use"],
        help="raw_json uses normal text JSON parsing; tool modes force one schema-bound tool call/use.",
    )
    parser.add_argument(
        "--schema-retry-count",
        type=int,
        default=0,
        help="Number of fixed schema-only retry attempts after parse/schema failure. Uses no targets or scores.",
    )
    parser.add_argument(
        "--methods",
        default="B1,B1_prime,C1,C3,C4",
        help="Comma-separated subset from B1,B1_prime,C1,C3,C4.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    methods = [item.strip() for item in args.methods.split(",") if item.strip()]
    allowed_methods = {"B1", "B1_prime", "C1", "C3", "C4"}
    unknown_methods = sorted(set(methods) - allowed_methods)
    if unknown_methods:
        raise ValueError(f"Unsupported runnable methods for this script: {unknown_methods}")

    run_dir = args.output_root / args.run_id
    if run_dir.exists() and not args.dry_run:
        raise RuntimeError(f"Run directory already exists: {run_dir}")

    manifest_path = args.sample_manifest
    rows = read_jsonl(manifest_path)[: args.limit]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    field_schema = json.loads(FIELD_CANDIDATES_SCHEMA.read_text(encoding="utf-8"))
    field_validator = Draft202012Validator(field_schema)
    c3_questionnaire_schema = json.loads(C3_QUESTIONNAIRE_SCHEMA.read_text(encoding="utf-8"))

    prompt_paths = {
        "B1": B1_PROMPT,
        "B1_prime": B1_PRIME_PROMPT,
        "C1": C1_PROMPT,
        "C3": C3_PROMPT,
        "C4": C4_PROMPT,
    }
    not_run_methods = {
        "A1": "not_run_in_this_llm_vlm_runner_candidate_rules_runner_available",
        "A2": "not_run_in_this_llm_vlm_runner_candidate_rules_runner_available",
        "C2": "not_run_in_this_single_call_runner_candidate_qa_bundle_and_aggregator_available",
        "D_SFT": "excluded_by_user_scope",
    }
    for image_method in ["C1", "C3", "C4"]:
        if image_method not in methods:
            not_run_methods[image_method] = "not_run_current_gpt54_openai_oauth_proxy_does_not_support_local_image_input"

    tooling_by_method: dict[str, dict[str, Any]] = {}
    if args.output_control in {"openai_tool_call", "anthropic_tool_use"}:
        for method in methods:
            if method == "C3":
                tool_schema_path = C3_QUESTIONNAIRE_SCHEMA
                tool_name = "emit_questionnaire_json"
            else:
                tool_schema_path = SCHEMA_PATH
                tool_name = "emit_canonical_json"
            tooling_by_method[method] = {
                "tool_name": tool_name,
                "tool_parameters_schema_path": tool_schema_path.relative_to(ROOT).as_posix(),
                "tool_parameters_schema_sha256": sha256_file(tool_schema_path),
            }

    run_manifest = {
        "run_id": args.run_id,
        "experiment_group": "group1_full_chart_main_extraction",
        "group1_methods_in_scope_without_d_sft": ["A1", "A2", "B1", "B1_prime", "C1", "C2", "C3", "C4"],
        "executed_methods": methods,
        "not_run_methods": not_run_methods,
        "excluded_not_group1": ["B2a", "B2b", "B3", "B4"],
        "parameter_status": "temporary_pilot_use_only_not_final_freeze",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sample_manifest": display_path(manifest_path),
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
            json_mode=args.json_mode,
            assistant_prefill_json=args.assistant_prefill_json,
        ),
        "ocr_sources": {
            "OCR-1": {
                "role": "ordinary full-chart OCR for B1/B1_prime/C4",
                "full_text_root": display_path(args.ocr1_text_root),
                "source_policy": "ordinary_ocr_not_mllm_transcription",
                "artifact_manifest": ocr_manifest_artifacts(args.ocr1_text_root),
            },
            "OCR-2": {
                "role": "available for A2 only; not used by executed LLM/VLM subset",
                "full_text_root": display_path(args.ocr2_text_root),
                "artifact_manifest": ocr_manifest_artifacts(args.ocr2_text_root),
            },
        },
        "schema": {
            "path": SCHEMA_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(SCHEMA_PATH),
        },
        "method_boundaries": {
            method: METHOD_BOUNDARIES[method]
            for method in methods
            if method in METHOD_BOUNDARIES
        },
        "input_artifacts_by_method": build_input_artifacts_by_method(
            rows,
            methods=methods,
            ocr1_text_root=args.ocr1_text_root,
        ),
        "field_candidates_schema": {
            "path": FIELD_CANDIDATES_SCHEMA.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(FIELD_CANDIDATES_SCHEMA),
            "status": "candidate_not_frozen",
        },
        "parser_policy": {
            "strict_json_only": True,
            "json_mode": args.json_mode,
            "assistant_prefill_json": args.assistant_prefill_json,
            "assistant_prefill_value": "{" if args.assistant_prefill_json else None,
            "output_control": args.output_control,
            "openai_tool_call_schema_bound": args.output_control == "openai_tool_call",
            "anthropic_tool_use_schema_bound": args.output_control == "anthropic_tool_use",
            "tooling_by_method": tooling_by_method,
            "schema_retry_count": args.schema_retry_count,
            "schema_retry_uses_target_or_scorer": False,
            "semantic_repair": False,
            "canonical_semantic_validation": True,
            "code_fence_stripping_allowed": False,
            "anthropic_tool_use_single_parameter_wrapper_unwrapped": args.output_control == "anthropic_tool_use",
            "target_used_for_parsing": False,
            "c3_questionnaire_to_canonical": {
                "path": C3_PARSER.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(C3_PARSER),
            },
            "c3_questionnaire_schema": {
                "path": C3_QUESTIONNAIRE_SCHEMA.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(C3_QUESTIONNAIRE_SCHEMA),
            },
        },
        "prompts": {
            method: {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(path),
                "status": "candidate_not_formal_frozen",
            }
            for method, path in prompt_paths.items()
        },
        "scoring": {
            "target_used_only_after_validation": True,
            "target_source": "pilot10_external canonical_proxy_gt_file",
        },
        "samples": [row["pilot_sample_id"] for row in rows],
    }
    write_json(run_dir / "run_manifest.json", run_manifest)
    save_not_run_notes(run_dir)

    if args.dry_run:
        print(f"Dry run prepared {len(rows)} samples in {run_dir}.")
        return 0

    client = create_model_client(provider=args.provider, base_url=args.base_url, api_key_env=args.api_key_env)
    prompt_templates = {method: path.read_text(encoding="utf-8") for method, path in prompt_paths.items()}
    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for row in rows:
        sample_id = row["pilot_sample_id"]
        chart_id = row["chart_id"]
        image_path = resolve_package_path(row["image_path"])
        target_path = resolve_package_path(row["canonical_proxy_gt_file"])
        target = json.loads(target_path.read_text(encoding="utf-8"))
        ocr1_text_path = args.ocr1_text_root / f"{chart_id}.txt"
        print(f"Running group1 runnable subset {sample_id} {chart_id}", flush=True)

        ocr_text: str | None = None
        if any(method in methods for method in ["B1", "B1_prime", "C4"]):
            if not ocr1_text_path.exists():
                failures.append(
                    {
                        "sample_id": sample_id,
                        "chart_id": chart_id,
                        "method": "OCR-1",
                        "error": f"missing_ocr1_text:{display_path(ocr1_text_path)}",
                    }
                )
            else:
                ocr_text = ocr1_text_path.read_text(encoding="utf-8")

        if "B1" in methods and ocr_text is not None:
            item, failure = run_one_json_method(
                method="B1",
                client=client,
                provider=args.provider,
                model=args.model,
                prompt=fill_prompt(prompt_templates["B1"], row, ocr_text=ocr_text),
                image_path=None,
                target=target,
                validator=validator,
                run_dir=run_dir,
                chart_id=chart_id,
                sample_id=sample_id,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                json_mode=args.json_mode,
                assistant_prefill_json=args.assistant_prefill_json,
                output_control=args.output_control,
                tool_schema=schema,
                tool_name="emit_canonical_json",
                schema_retry_count=args.schema_retry_count,
            )
            results.append(item)
            if failure:
                failures.append(failure)

        if "B1_prime" in methods and ocr_text is not None:
            field_candidates = build_field_candidates(ocr_text, chart_id)
            write_json(run_dir / "B1_prime" / "field_candidates" / f"{chart_id}.json", field_candidates)
            field_errors = validate_canonical(field_candidates, field_validator)
            write_json(run_dir / "B1_prime" / "field_candidates_validation" / f"{chart_id}.json", field_errors)
            prompt = fill_prompt(prompt_templates["B1_prime"], row, ocr_text=ocr_text).replace(
                "{{field_candidates_json}}",
                json.dumps(field_candidates, ensure_ascii=False, indent=2),
            )
            item, failure = run_one_json_method(
                method="B1_prime",
                client=client,
                provider=args.provider,
                model=args.model,
                prompt=prompt,
                image_path=None,
                target=target,
                validator=validator,
                run_dir=run_dir,
                chart_id=chart_id,
                sample_id=sample_id,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                json_mode=args.json_mode,
                assistant_prefill_json=args.assistant_prefill_json,
                output_control=args.output_control,
                tool_schema=schema,
                tool_name="emit_canonical_json",
                schema_retry_count=args.schema_retry_count,
            )
            item["field_candidates_validation_error_count"] = len(field_errors)
            results.append(item)
            if field_errors:
                failures.append(
                    {
                        "sample_id": sample_id,
                        "chart_id": chart_id,
                        "method": "B1_prime_field_candidates",
                        "error": "field_candidates_schema_validation_failed",
                    }
                )
            if failure:
                failures.append(failure)

        if "C1" in methods:
            item, failure = run_one_json_method(
                method="C1",
                client=client,
                provider=args.provider,
                model=args.model,
                prompt=fill_prompt(prompt_templates["C1"], row),
                image_path=image_path,
                target=target,
                validator=validator,
                run_dir=run_dir,
                chart_id=chart_id,
                sample_id=sample_id,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                json_mode=args.json_mode,
                assistant_prefill_json=args.assistant_prefill_json,
                output_control=args.output_control,
                tool_schema=schema,
                tool_name="emit_canonical_json",
                schema_retry_count=args.schema_retry_count,
            )
            results.append(item)
            if failure:
                failures.append(failure)

        if "C3" in methods:
            item, failure = run_one_json_method(
                method="C3",
                client=client,
                provider=args.provider,
                model=args.model,
                prompt=fill_prompt(prompt_templates["C3"], row),
                image_path=image_path,
                target=target,
                validator=validator,
                run_dir=run_dir,
                chart_id=chart_id,
                sample_id=sample_id,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                json_mode=args.json_mode,
                assistant_prefill_json=args.assistant_prefill_json,
                output_control=args.output_control,
                tool_schema=c3_questionnaire_schema
                if args.output_control in {"openai_tool_call", "anthropic_tool_use"}
                else None,
                tool_name="emit_questionnaire_json",
                schema_retry_count=args.schema_retry_count,
                questionnaire_output=True,
            )
            results.append(item)
            if failure:
                failures.append(failure)

        if "C4" in methods and ocr_text is not None:
            item, failure = run_one_json_method(
                method="C4",
                client=client,
                provider=args.provider,
                model=args.model,
                prompt=fill_prompt(prompt_templates["C4"], row, ocr_text=ocr_text),
                image_path=image_path,
                target=target,
                validator=validator,
                run_dir=run_dir,
                chart_id=chart_id,
                sample_id=sample_id,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                json_mode=args.json_mode,
                assistant_prefill_json=args.assistant_prefill_json,
                output_control=args.output_control,
                tool_schema=schema,
                tool_name="emit_canonical_json",
                schema_retry_count=args.schema_retry_count,
            )
            results.append(item)
            if failure:
                failures.append(failure)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id,
        "parameter_status": "temporary_pilot_use_only_not_final_freeze",
        "methods": {method: summarize_method(method, results) for method in methods},
        "not_run_methods": run_manifest["not_run_methods"],
        "failures": failures,
    }
    write_json(run_dir / "summary_report.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
