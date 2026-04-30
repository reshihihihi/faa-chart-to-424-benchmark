from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from aggregate_c2_qa_candidate import QA_PROMPT_DIR, aggregate_chart  # noqa: E402
from build_field_to_leg_links import build_links  # noqa: E402
from c3_questionnaire_to_canonical import questionnaire_to_canonical  # noqa: E402
from model_clients import call_model_json, create_model_client, model_api_manifest, save_model_response  # noqa: E402
from run_a1_a2_rules_pilot10 import RULE_SPEC, extract_rules  # noqa: E402
from run_b1prime_c4_pilot10 import build_field_candidates  # noqa: E402
from run_c2_qa_pilot10 import (  # noqa: E402
    QUESTION_SEQUENCE,
    call_qa_answer,
    qa_tool_schema,
    qa_validation_schema,
    summarize as summarize_c2,
)
from run_group1_pilot10_gpt54 import build_schema_retry_prompt, summarize_method  # noqa: E402
from run_pilot10_anthropic import (  # noqa: E402
    B1_PROMPT,
    SCHEMA_PATH,
    fill_prompt,
    score_canonical,
    sha256_file,
    validate_canonical,
    write_json,
    write_text,
)


METHODS = ["A1", "A2", "B1", "B1_prime", "B1_prime_link", "C1", "C2", "C3", "C4", "D_SFT"]
TEXT_METHODS = {"B1", "B1_prime", "B1_prime_link"}
IMAGE_JSON_METHODS = {"C1", "C3", "C4"}
PROMPTS = {
    "B1": ROOT / "prompts" / "paper_v2" / "b1_ocr_to_canonical_pilot10.zh_v1_candidate.md",
    "B1_prime": ROOT / "prompts" / "paper_v2" / "b1_prime_ocr_field_candidates_to_canonical_pilot10.zh_v0_candidate.md",
    "B1_prime_link": ROOT / "prompts" / "paper_v2" / "b1_prime_link_ocr_candidates_links_to_canonical.zh_v0_candidate.md",
    "C1": ROOT / "prompts" / "paper_v2" / "c1_image_to_canonical_pilot10.zh_v1_candidate.md",
    "C3": ROOT / "prompts" / "paper_v2" / "c3_questionnaire_pilot10.zh_v1_candidate.md",
    "C4": ROOT / "prompts" / "paper_v2" / "c4_image_ocr_to_canonical_pilot10.zh_v1_candidate.md",
}
FIELD_CANDIDATES_SCHEMA = ROOT / "schemas" / "field_candidates.schema.candidate.json"
FIELD_TO_LEG_SCHEMA = ROOT / "schemas" / "field_to_leg_links.schema.candidate.json"
C3_QUESTIONNAIRE_SCHEMA = ROOT / "schemas" / "c3_questionnaire.schema.candidate.json"
D_SFT_CONFIG = ROOT / "training" / "d_sft" / "configs" / "d_sft_training_config.frozen_20260428_r1.json"
D_SFT_CHECKPOINT_ARTIFACT_ID = "checkpoints/d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1/checkpoint-final"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def display_path(path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def display_external_checkpoint(path: Path | None) -> str | None:
    if path is None:
        return None
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        parts = list(path.parts)
        if "checkpoints" in parts:
            suffix = parts[parts.index("checkpoints") :]
        else:
            suffix = parts[-2:] if len(parts) >= 2 else [path.name]
        return "<external-artifact-root>/" + "/".join(str(part).replace("\\", "/") for part in suffix)


def repo_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def artifact_path(row: dict[str, Any], key: str) -> Path | None:
    artifact = row.get(key)
    if not isinstance(artifact, dict):
        return None
    path = artifact.get("path")
    if not path:
        return None
    return repo_path(str(path))


def validation_errors(obj: Any, validator: Draft202012Validator) -> list[str]:
    errors = sorted(validator.iter_errors(obj), key=lambda err: list(err.path))
    return [(".".join(str(part) for part in err.path) or "$") + f": {err.message}" for err in errors]


def row_for_prompt(row: dict[str, Any]) -> dict[str, Any]:
    image_path = artifact_path(row, "image")
    return {
        "pilot_sample_id": row["sample_id"],
        "sample_id": row["sample_id"],
        "chart_id": row["chart_id"],
        "airport": row["airport"],
        "proc_ident": row["proc_ident"],
        "chart_name": row["chart_name"],
        "image_path": display_path(image_path) if image_path else "",
    }


def load_targets(scoring_manifest: Path) -> dict[str, Path]:
    targets: dict[str, Path] = {}
    for row in read_jsonl(scoring_manifest):
        target = row.get("target")
        if not isinstance(target, dict) or not target.get("path"):
            continue
        targets[row["chart_id"]] = repo_path(str(target["path"]))
    return targets


def boundary_audit(run_dir: Path, methods: list[str]) -> dict[str, Any]:
    report: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": display_path(run_dir),
        "methods": {},
        "errors": [],
        "target_keys_forbidden_in_input_manifest": True,
    }
    forbidden_key_fragments = ["target", "score", "canonical_proxy_gt", "cifp", "answer_key"]
    scoring_targets = load_targets(run_dir / "scoring_manifest.jsonl")
    for method in methods:
        manifest = run_dir / method / "input_manifest.jsonl"
        rows = read_jsonl(manifest)
        method_errors: list[dict[str, Any]] = []
        for row in rows:
            for key in row:
                key_lower = key.lower()
                if any(fragment in key_lower for fragment in forbidden_key_fragments):
                    method_errors.append({"sample_id": row.get("sample_id"), "chart_id": row.get("chart_id"), "forbidden_key": key})
            for artifact_key in ["image", "OCR-1_full_text", "OCR-2_full_text"]:
                if artifact_key in row:
                    path = artifact_path(row, artifact_key)
                    if path is None or not path.exists():
                        method_errors.append({"sample_id": row.get("sample_id"), "chart_id": row.get("chart_id"), "missing_artifact": artifact_key})
        report["methods"][method] = {
            "rows": len(rows),
            "manifest": display_path(manifest),
            "manifest_sha256": sha256_file(manifest),
            "errors": method_errors,
        }
        report["errors"].extend({"method": method, **error} for error in method_errors)
    missing_targets = []
    for chart_id, target_path in scoring_targets.items():
        if not target_path.exists():
            missing_targets.append({"chart_id": chart_id, "target_path": display_path(target_path)})
    report["scoring_manifest"] = {
        "path": display_path(run_dir / "scoring_manifest.jsonl"),
        "sha256": sha256_file(run_dir / "scoring_manifest.jsonl"),
        "targets": len(scoring_targets),
        "missing_targets": missing_targets,
    }
    report["errors"].extend({"method": "SCORING", **item} for item in missing_targets)
    report["ready"] = len(report["errors"]) == 0
    write_json(run_dir / "reports" / "boundary_audit.json", report)
    return report


def score_if_valid(
    *,
    method: str,
    pred: dict[str, Any],
    target_path: Path,
    run_dir: Path,
    chart_id: str,
) -> dict[str, Any]:
    target = json.loads(target_path.read_text(encoding="utf-8"))
    score = score_canonical(pred, target)
    write_json(run_dir / method / "scores" / f"{chart_id}.json", score)
    return {key: score[key] for key in ["correct", "total", "accuracy"]}


def run_rules_method(
    *,
    method: str,
    rows: list[dict[str, Any]],
    targets: dict[str, Path],
    validator: Draft202012Validator,
    run_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    ocr_key = "OCR-1_full_text" if method == "A1" else "OCR-2_full_text"
    for row in rows:
        prompt_row = row_for_prompt(row)
        chart_id = row["chart_id"]
        ocr_path = artifact_path(row, ocr_key)
        item: dict[str, Any] = {"method": method, "sample_id": row["sample_id"], "chart_id": chart_id, "score": None}
        if ocr_path is None or not ocr_path.exists():
            item["failure"] = f"missing_{ocr_key}"
            failures.append({"method": method, "sample_id": row["sample_id"], "chart_id": chart_id, "error": item["failure"]})
            results.append(item)
            continue
        prediction, diagnostics = extract_rules(prompt_row, ocr_path.read_text(encoding="utf-8"))
        write_json(run_dir / method / "canonical_json" / f"{chart_id}.json", prediction)
        write_json(run_dir / method / "rule_diagnostics" / f"{chart_id}.json", diagnostics)
        errors = validate_canonical(prediction, validator)
        write_json(run_dir / method / "validation" / f"{chart_id}.json", errors)
        item["validation_error_count"] = len(errors)
        item["validation_errors"] = errors
        if errors:
            failures.append({"method": method, "sample_id": row["sample_id"], "chart_id": chart_id, "error": "schema_validation_failed"})
        else:
            item["score"] = score_if_valid(method=method, pred=prediction, target_path=targets[chart_id], run_dir=run_dir, chart_id=chart_id)
        results.append(item)
    return results, failures


def run_json_method(
    *,
    method: str,
    rows: list[dict[str, Any]],
    targets: dict[str, Path],
    client: Any,
    provider: str,
    model: str,
    max_tokens: int,
    temperature: float,
    json_mode: bool,
    output_control: str,
    schema_retry_count: int,
    validator: Draft202012Validator,
    canonical_schema: dict[str, Any],
    field_validator: Draft202012Validator,
    link_validator: Draft202012Validator,
    c3_questionnaire_schema: dict[str, Any],
    run_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    prompt_template = PROMPTS[method].read_text(encoding="utf-8")
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    extraction_policy = {
        "openai_tool_call": "openai_tool_call_arguments",
        "anthropic_tool_use": "anthropic_tool_use_input",
    }.get(output_control, "strict_json")

    for row in rows:
        prompt_row = row_for_prompt(row)
        chart_id = row["chart_id"]
        sample_id = row["sample_id"]
        image_path = artifact_path(row, "image")
        ocr_text = ""
        if method in {"B1", "B1_prime", "B1_prime_link", "C4"}:
            ocr_path = artifact_path(row, "OCR-1_full_text")
            if ocr_path is None or not ocr_path.exists():
                failure = {"method": method, "sample_id": sample_id, "chart_id": chart_id, "error": "missing_OCR-1_full_text"}
                failures.append(failure)
                results.append({**failure, "validation_error_count": None, "score": None})
                continue
            ocr_text = ocr_path.read_text(encoding="utf-8")
        if method in {"C1", "C3", "C4"} and (image_path is None or not image_path.exists()):
            failure = {"method": method, "sample_id": sample_id, "chart_id": chart_id, "error": "missing_image"}
            failures.append(failure)
            results.append({**failure, "validation_error_count": None, "score": None})
            continue

        prompt = fill_prompt(prompt_template, prompt_row, ocr_text=ocr_text)
        field_errors: list[str] = []
        link_errors: list[str] = []
        if method in {"B1_prime", "B1_prime_link"}:
            field_candidates = build_field_candidates(ocr_text, chart_id)
            write_json(run_dir / method / "field_candidates" / f"{chart_id}.json", field_candidates)
            field_errors = validation_errors(field_candidates, field_validator)
            write_json(run_dir / method / "field_candidates_validation" / f"{chart_id}.json", field_errors)
            prompt = prompt.replace("{{field_candidates_json}}", json.dumps(field_candidates, ensure_ascii=False, indent=2))
        if method == "B1_prime_link":
            field_path = run_dir / method / "field_candidates" / f"{chart_id}.json"
            links = build_links(field_candidates, field_path)  # type: ignore[name-defined]
            write_json(run_dir / method / "field_to_leg_links" / f"{chart_id}.json", links)
            link_errors = validation_errors(links, link_validator)
            write_json(run_dir / method / "field_to_leg_links_validation" / f"{chart_id}.json", link_errors)
            prompt = prompt.replace("{{field_to_leg_links_json}}", json.dumps(links, ensure_ascii=False, indent=2))

        current_prompt = prompt
        max_attempts = 1 + schema_retry_count
        last_text = ""
        last_validation_errors: list[str] | None = None
        item: dict[str, Any] | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                tool_schema = c3_questionnaire_schema if method == "C3" else canonical_schema
                tool_name = "emit_questionnaire_json" if method == "C3" else "emit_canonical_json"
                text, response = call_model_json(
                    client,
                    provider=provider,
                    model=model,
                    prompt=current_prompt,
                    image_path=image_path if method in IMAGE_JSON_METHODS else None,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    json_mode=json_mode,
                    assistant_prefill_json=False,
                    output_control=output_control,
                    tool_schema=tool_schema,
                    tool_name=tool_name,
                )
                last_text = text
                write_text(run_dir / method / "raw_text" / f"{chart_id}.attempt_{attempt}.txt", text)
                save_model_response(run_dir / method / "raw_responses" / f"{chart_id}.attempt_{attempt}.json", response)
                parsed = json.loads(text.strip())
                if method == "C3":
                    write_json(run_dir / method / "questionnaire_json" / f"{chart_id}.attempt_{attempt}.json", parsed)
                    pred = questionnaire_to_canonical(parsed)
                else:
                    pred = parsed
                errors = validate_canonical(pred, validator)
                write_json(run_dir / method / "validation" / f"{chart_id}.attempt_{attempt}.json", errors)
                if not errors:
                    write_text(run_dir / method / "raw_text" / f"{chart_id}.txt", text)
                    save_model_response(run_dir / method / "raw_responses" / f"{chart_id}.json", response)
                    if method == "C3":
                        write_json(run_dir / method / "questionnaire_json" / f"{chart_id}.json", parsed)
                    write_json(run_dir / method / "canonical_json" / f"{chart_id}.json", pred)
                    write_json(run_dir / method / "validation" / f"{chart_id}.json", errors)
                    item = {
                        "method": method,
                        "sample_id": sample_id,
                        "chart_id": chart_id,
                        "json_extraction_policy": extraction_policy,
                        "validation_error_count": 0,
                        "validation_errors": [],
                        "attempt_count": attempt,
                        "schema_retry_count": attempt - 1,
                        "field_candidates_validation_error_count": len(field_errors) if method in {"B1_prime", "B1_prime_link"} else None,
                        "field_to_leg_links_validation_error_count": len(link_errors) if method == "B1_prime_link" else None,
                        "score": score_if_valid(method=method, pred=pred, target_path=targets[chart_id], run_dir=run_dir, chart_id=chart_id),
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
                    write_json(run_dir / method / "canonical_json" / f"{chart_id}.json", pred)
                    write_json(run_dir / method / "validation" / f"{chart_id}.json", errors)
                    item = {
                        "method": method,
                        "sample_id": sample_id,
                        "chart_id": chart_id,
                        "json_extraction_policy": extraction_policy,
                        "validation_error_count": len(errors),
                        "validation_errors": errors,
                        "attempt_count": attempt,
                        "schema_retry_count": attempt - 1,
                        "score": None,
                    }
                    failures.append({"method": method, "sample_id": sample_id, "chart_id": chart_id, "error": "schema_validation_failed"})
            except Exception as exc:  # noqa: BLE001
                err = repr(exc)
                write_text(run_dir / method / "parse_errors" / f"{chart_id}.attempt_{attempt}.txt", err)
                if attempt < max_attempts:
                    current_prompt = build_schema_retry_prompt(
                        original_prompt=prompt,
                        previous_output=last_text,
                        validation_errors=last_validation_errors,
                        parse_error=err,
                    )
                else:
                    item = {
                        "method": method,
                        "sample_id": sample_id,
                        "chart_id": chart_id,
                        "json_extraction_policy": extraction_policy,
                        "validation_error_count": None,
                        "validation_errors": last_validation_errors,
                        "attempt_count": attempt,
                        "schema_retry_count": attempt - 1,
                        "score": None,
                        "failure": err,
                    }
                    failures.append({"method": method, "sample_id": sample_id, "chart_id": chart_id, "error": err})
        if item is not None:
            results.append(item)
    return results, failures


def run_c2_method(
    *,
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
    run_dir: Path,
    max_qa_legs: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    qa_schemas = {qid: qa_tool_schema(canonical_schema, qid) for qid in ["q0_leg_count", *QUESTION_SEQUENCE]}
    qa_validation_schemas = {qid: qa_validation_schema(canonical_schema, qid) for qid in ["q0_leg_count", *QUESTION_SEQUENCE]}
    qa_validators = {qid: Draft202012Validator(schema) for qid, schema in qa_validation_schemas.items()}
    prompt_templates = {path.stem: path.read_text(encoding="utf-8") for path in sorted(QA_PROMPT_DIR.glob("*.txt"))}
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for row in rows:
        prompt_row = row_for_prompt(row)
        chart_id = row["chart_id"]
        image_path = artifact_path(row, "image")
        if image_path is None or not image_path.exists():
            failures.append({"method": "C2", "sample_id": row["sample_id"], "chart_id": chart_id, "error": "missing_image"})
            continue
        chart_diags: list[dict[str, Any]] = []
        q0_answer, q0_diag = call_qa_answer(
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
            max_tokens=max_tokens,
            temperature=temperature,
            output_control="anthropic_tool_use",
            schema_retry_count=schema_retry_count,
        )
        chart_diags.append(q0_diag)
        leg_count = q0_answer.get("value") if isinstance(q0_answer, dict) and q0_answer.get("status") == "present" else None
        if isinstance(leg_count, int) and leg_count > 0:
            if leg_count > max_qa_legs:
                failures.append({"method": "C2", "sample_id": row["sample_id"], "chart_id": chart_id, "error": f"q0_leg_count_exceeds_safety_cap:{leg_count}"})
                leg_count = max_qa_legs
            for leg_index in range(1, leg_count + 1):
                for qid in QUESTION_SEQUENCE:
                    _, diag = call_qa_answer(
                        client=client,
                        provider=provider,
                        model=model,
                        row=prompt_row,
                        image_path=image_path,
                        question_id=qid,
                        prompt_template=prompt_templates[qid],
                        leg_index=leg_index,
                        schema=qa_schemas[qid],
                        validator=qa_validators[qid],
                        run_dir=run_dir,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        output_control="anthropic_tool_use",
                        schema_retry_count=schema_retry_count,
                    )
                    chart_diags.append(diag)
        prediction, agg_diag = aggregate_chart(prompt_row, run_dir / "C2" / "qa_json" / chart_id)
        write_json(run_dir / "C2" / "canonical_json" / f"{chart_id}.json", prediction)
        write_json(run_dir / "C2" / "aggregation_diagnostics" / f"{chart_id}.json", agg_diag)
        write_json(run_dir / "C2" / "qa_call_diagnostics" / f"{chart_id}.json", chart_diags)
        errors = validate_canonical(prediction, validator)
        write_json(run_dir / "C2" / "validation" / f"{chart_id}.json", errors)
        item: dict[str, Any] = {
            "method": "C2",
            "sample_id": row["sample_id"],
            "chart_id": chart_id,
            "validation_error_count": len(errors),
            "validation_errors": errors,
            "qa_calls_total": len(chart_diags),
            "qa_calls_saved": sum(1 for diag in chart_diags if diag.get("saved_answer")),
            "qa_schema_retry_count_total": sum(diag.get("schema_retry_count") or 0 for diag in chart_diags),
            "score": None,
        }
        if errors:
            failures.append({"method": "C2", "sample_id": row["sample_id"], "chart_id": chart_id, "error": "schema_validation_failed"})
        else:
            item["score"] = score_if_valid(method="C2", pred=prediction, target_path=targets[chart_id], run_dir=run_dir, chart_id=chart_id)
        results.append(item)
    return results, failures


def run_d_sft_method(
    run_dir: Path,
    rows: list[dict[str, Any]],
    targets: dict[str, Path],
    limit: int | None,
    checkpoint: Path,
) -> dict[str, Any]:
    manifest_rows = []
    for row in rows[:limit] if limit is not None else rows:
        image_path = artifact_path(row, "image")
        if image_path is None:
            continue
        manifest_rows.append(
            {
                "sample_id": row["sample_id"],
                "chart_id": row["chart_id"],
                "image_path": str(image_path.resolve()),
                "target_path": str(targets[row["chart_id"]].resolve()),
            }
        )
    manifest = run_dir / "D_SFT" / "d_sft_formal_manifest.jsonl"
    write_jsonl(manifest, manifest_rows)
    d_run_id = run_dir.name + "_D_SFT"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "d_sft_infer_qwen2vl_lora.py"),
        "--config",
        str(D_SFT_CONFIG),
        "--checkpoint",
        str(checkpoint),
        "--manifest",
        str(manifest),
        "--schema",
        str(SCHEMA_PATH),
        "--output-root",
        str(run_dir / "D_SFT"),
        "--run-id",
        d_run_id,
        "--sample-role",
        "formal_smoke_evaluation_split" if "smoke" in run_dir.name else "formal300_evaluation_split",
    ]
    if limit is not None:
        cmd.extend(["--limit", str(limit)])
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    write_text(run_dir / "D_SFT" / "d_sft_command.txt", " ".join(cmd))
    write_text(run_dir / "D_SFT" / "d_sft_stdout.txt", proc.stdout)
    write_text(run_dir / "D_SFT" / "d_sft_stderr.txt", proc.stderr)
    summary_path = run_dir / "D_SFT" / "predictions" / d_run_id / "summary_report.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    else:
        summary = {
            "method_id": "D_SFT",
            "run_id": d_run_id,
            "returncode": proc.returncode,
            "failures": [{"stage": "subprocess", "error": proc.stderr[-2000:]}],
        }
    write_json(run_dir / "D_SFT" / "summary_report.json", summary)
    return summary


def write_run_manifest(run_dir: Path, methods: list[str], args: argparse.Namespace) -> None:
    prompt_hashes = {
        method: {"path": display_path(path), "sha256": sha256_file(path)}
        for method, path in PROMPTS.items()
        if method in methods
    }
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_dir.name,
        "run_dir": display_path(run_dir),
        "methods": methods,
        "formal_runner": {"path": "scripts/run_group1_formal_manifest.py", "sha256": sha256_file(ROOT / "scripts" / "run_group1_formal_manifest.py")},
        "input_policy": {
            "inference_reads_method_input_manifest_only": True,
            "scoring_reads_scoring_manifest_after_prediction": True,
            "target_used_for_prompt_or_parsing": False,
        },
        "models": {
            "text_llm": {"provider": "openai_compatible", "model": args.text_model, "temperature": args.temperature, "max_tokens": args.text_max_tokens},
            "vlm": {"provider": "anthropic_compatible", "model": args.vlm_model, "temperature": args.temperature, "max_tokens": args.vlm_max_tokens},
            "c2": {"provider": "anthropic_compatible", "model": args.vlm_model, "temperature": args.temperature, "max_tokens": args.c2_max_tokens},
            "d_sft": {
                "checkpoint": display_external_checkpoint(args.d_sft_checkpoint),
                "checkpoint_source": "--d-sft-checkpoint or D_SFT_CHECKPOINT environment variable",
                "checkpoint_artifact_id": D_SFT_CHECKPOINT_ARTIFACT_ID,
                "config": display_path(D_SFT_CONFIG),
            },
        },
        "api": {
            "openai_compatible": model_api_manifest(provider="openai_compatible", base_url=args.openai_base_url, api_key_env=args.openai_api_key_env, json_mode=True),
            "anthropic_compatible": model_api_manifest(provider="anthropic_compatible", base_url=args.anthropic_base_url, api_key_env=args.anthropic_api_key_env),
        },
        "schema": {"path": display_path(SCHEMA_PATH), "sha256": sha256_file(SCHEMA_PATH)},
        "field_candidates_schema": {"path": display_path(FIELD_CANDIDATES_SCHEMA), "sha256": sha256_file(FIELD_CANDIDATES_SCHEMA)},
        "field_to_leg_links_schema": {"path": display_path(FIELD_TO_LEG_SCHEMA), "sha256": sha256_file(FIELD_TO_LEG_SCHEMA)},
        "rule_spec": {"path": display_path(RULE_SPEC), "sha256": sha256_file(RULE_SPEC)},
        "prompts": prompt_hashes,
        "parser_policy": {
            "strict_json_only": True,
            "code_fence_stripping_allowed": False,
            "schema_retry_count_text": args.text_schema_retry_count,
            "schema_retry_count_vlm": args.vlm_schema_retry_count,
            "schema_retry_uses_target_or_scorer": False,
            "semantic_repair_allowed": False,
        },
    }
    write_json(run_dir / "formal_run_manifest.json", manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Group 1 formal/smoke manifests with target-isolated inference.")
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--dry-run-boundary-only", action="store_true")
    parser.add_argument("--text-model", default="gpt-5.4")
    parser.add_argument("--openai-base-url", default=None)
    parser.add_argument("--openai-api-key-env", default=None)
    parser.add_argument("--vlm-model", default="claude-sonnet-4-5-20250929")
    parser.add_argument("--anthropic-base-url", default=None)
    parser.add_argument("--anthropic-api-key-env", default=None)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--text-max-tokens", type=int, default=4096)
    parser.add_argument("--vlm-max-tokens", type=int, default=4096)
    parser.add_argument("--c2-max-tokens", type=int, default=1024)
    parser.add_argument("--text-schema-retry-count", type=int, default=1)
    parser.add_argument("--vlm-schema-retry-count", type=int, default=1)
    parser.add_argument("--c2-schema-retry-count", type=int, default=1)
    parser.add_argument("--max-qa-legs", type=int, default=12)
    parser.add_argument("--d-sft-limit", type=int, default=None)
    default_d_sft_checkpoint = os.environ.get("D_SFT_CHECKPOINT")
    parser.add_argument(
        "--d-sft-checkpoint",
        type=Path,
        default=Path(default_d_sft_checkpoint) if default_d_sft_checkpoint else None,
        help="External D-SFT adapter checkpoint path. Required when executing D_SFT; may also be set via D_SFT_CHECKPOINT.",
    )
    args = parser.parse_args()

    run_dir = args.run_dir if args.run_dir.is_absolute() else ROOT / args.run_dir
    methods = [item.strip() for item in args.methods.split(",") if item.strip()]
    unknown = sorted(set(methods) - set(METHODS))
    if unknown:
        raise ValueError(f"Unknown methods: {unknown}")

    audit = boundary_audit(run_dir, methods)
    if not audit["ready"]:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
        return 2
    write_run_manifest(run_dir, methods, args)
    if args.dry_run_boundary_only:
        print(json.dumps({"status": "boundary_ready", "run_dir": display_path(run_dir), "methods": methods}, ensure_ascii=False, indent=2))
        return 0
    if "D_SFT" in methods and args.d_sft_checkpoint is None:
        raise ValueError("D_SFT execution requires --d-sft-checkpoint or the D_SFT_CHECKPOINT environment variable.")

    canonical_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    canonical_validator = Draft202012Validator(canonical_schema)
    field_validator = Draft202012Validator(json.loads(FIELD_CANDIDATES_SCHEMA.read_text(encoding="utf-8")))
    link_validator = Draft202012Validator(json.loads(FIELD_TO_LEG_SCHEMA.read_text(encoding="utf-8")))
    c3_questionnaire_schema = json.loads(C3_QUESTIONNAIRE_SCHEMA.read_text(encoding="utf-8"))
    targets = load_targets(run_dir / "scoring_manifest.jsonl")

    all_results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    skipped_methods: list[dict[str, Any]] = []

    for method in methods:
        existing_method_summary = run_dir / method / "method_summary.json"
        if existing_method_summary.exists():
            print(f"Skipping {method}; existing method_summary.json found", flush=True)
            skipped_methods.append(
                {
                    "method": method,
                    "reason": "existing_method_summary",
                    "path": display_path(existing_method_summary),
                }
            )
            continue
        rows = read_jsonl(run_dir / method / "input_manifest.jsonl")
        print(f"Running {method} on {len(rows)} samples", flush=True)
        if method in {"A1", "A2"}:
            results, method_failures = run_rules_method(method=method, rows=rows, targets=targets, validator=canonical_validator, run_dir=run_dir)
        elif method in TEXT_METHODS:
            client = create_model_client(provider="openai_compatible", base_url=args.openai_base_url, api_key_env=args.openai_api_key_env)
            results, method_failures = run_json_method(
                method=method,
                rows=rows,
                targets=targets,
                client=client,
                provider="openai_compatible",
                model=args.text_model,
                max_tokens=args.text_max_tokens,
                temperature=args.temperature,
                json_mode=True,
                output_control="openai_tool_call",
                schema_retry_count=args.text_schema_retry_count,
                validator=canonical_validator,
                canonical_schema=canonical_schema,
                field_validator=field_validator,
                link_validator=link_validator,
                c3_questionnaire_schema=c3_questionnaire_schema,
                run_dir=run_dir,
            )
        elif method in {"C1", "C3", "C4"}:
            client = create_model_client(provider="anthropic_compatible", base_url=args.anthropic_base_url, api_key_env=args.anthropic_api_key_env)
            results, method_failures = run_json_method(
                method=method,
                rows=rows,
                targets=targets,
                client=client,
                provider="anthropic_compatible",
                model=args.vlm_model,
                max_tokens=args.vlm_max_tokens,
                temperature=args.temperature,
                json_mode=False,
                output_control="anthropic_tool_use",
                schema_retry_count=args.vlm_schema_retry_count,
                validator=canonical_validator,
                canonical_schema=canonical_schema,
                field_validator=field_validator,
                link_validator=link_validator,
                c3_questionnaire_schema=c3_questionnaire_schema,
                run_dir=run_dir,
            )
        elif method == "C2":
            client = create_model_client(provider="anthropic_compatible", base_url=args.anthropic_base_url, api_key_env=args.anthropic_api_key_env)
            results, method_failures = run_c2_method(
                rows=rows,
                targets=targets,
                client=client,
                provider="anthropic_compatible",
                model=args.vlm_model,
                max_tokens=args.c2_max_tokens,
                temperature=args.temperature,
                schema_retry_count=args.c2_schema_retry_count,
                validator=canonical_validator,
                canonical_schema=canonical_schema,
                run_dir=run_dir,
                max_qa_legs=args.max_qa_legs,
            )
        elif method == "D_SFT":
            summary = run_d_sft_method(run_dir, rows, targets, args.d_sft_limit, args.d_sft_checkpoint)
            results = summary.get("results", [])
            method_failures = summary.get("failures", [])
        else:
            raise AssertionError(method)
        all_results.extend(results)
        failures.extend(method_failures)
        if method == "C2":
            method_summary = summarize_c2(results)
        elif method == "D_SFT":
            method_summary = json.loads((run_dir / "D_SFT" / "summary_report.json").read_text(encoding="utf-8"))
        else:
            method_summary = summarize_method(method, results)
        write_json(run_dir / method / "method_summary.json", method_summary)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_dir.name,
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
        "readiness_interpretation": (
            "Input boundary, runner execution, artifact persistence, validation, and scoring completed. "
            "Parse/schema failures emitted by a method are counted as method failures, not as formal-run blockers."
        ),
        "formal_start_ready_if_smoke": True,
    }
    write_json(run_dir / "summary_report.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
