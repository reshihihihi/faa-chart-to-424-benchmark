from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any

from jsonschema import Draft202012Validator

from c3_questionnaire_to_canonical import questionnaire_to_canonical
from run_pilot10_anthropic import (
    B1_PROMPT,
    C3_PROMPT,
    DATA_DIR,
    OCR_PROMPT,
    ROOT,
    SCHEMA_PATH,
    call_model,
    fill_prompt,
    get_client,
    image_block,
    read_jsonl,
    resolve_package_path,
    save_raw_response,
    score_canonical,
    sha256_file,
    validate_canonical,
    write_json,
    write_text,
)


DEFAULT_RUN_ID = "pilot10_exp1_b1_c3_strict_json_20260427_r1"


def call_model_json_prefill(
    client: Any,
    *,
    model: str,
    prompt: str,
    image_path: Any,
    max_tokens: int,
    temperature: float,
) -> tuple[str, Any]:
    content: list[dict[str, Any]] = []
    if image_path is not None:
        content.append(image_block(image_path))
    content.append({"type": "text", "text": prompt})
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "user", "content": content},
            {"role": "assistant", "content": "{"},
        ],
    )
    text_parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
    return ("{" + "\n".join(text_parts).strip()).strip(), response


def extract_json_object(text: str, *, strict_only: bool = True) -> tuple[dict[str, Any], str]:
    stripped = text.strip()
    try:
        return json.loads(stripped), "strict_json"
    except json.JSONDecodeError as exc:
        if strict_only:
            raise ValueError("strict_json_parse_failed_bare_json_required") from exc

    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[0].strip().startswith("```") and lines[-1].strip() == "```":
            inner = "\n".join(lines[1:-1]).strip()
            try:
                return json.loads(inner), "single_fenced_json_block"
            except json.JSONDecodeError:
                pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = stripped[start : end + 1]
        return json.loads(candidate), "first_json_object"

    return json.loads(stripped), "strict_json"


def summarize_method(method: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    method_results = [item for item in results if item["method"] == method]
    scored = [item["score"] for item in method_results if item.get("score")]
    correct = sum(item["correct"] for item in scored)
    total = sum(item["total"] for item in scored)
    policy_counts: dict[str, int] = {}
    for item in method_results:
        policy = item.get("json_extraction_policy") or "failed"
        policy_counts[policy] = policy_counts.get(policy, 0) + 1
    non_strict_count = sum(count for policy, count in policy_counts.items() if policy != "strict_json")

    return {
        "samples_total": len(method_results),
        "schema_valid": sum(1 for item in method_results if item.get("validation_error_count") == 0),
        "samples_scored": len(scored),
        "json_extraction_policy_counts": policy_counts,
        "parser_repair_count_non_strict_json": non_strict_count,
        "score": {
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total else None,
        },
        "results": method_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run B1 and C3 on pilot10 with current temporary parameters."
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens-ocr", type=int, default=4096)
    parser.add_argument("--max-tokens-b1", type=int, default=4096)
    parser.add_argument("--max-tokens-c3", type=int, default=4096)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument(
        "--assistant-prefill-json",
        action="store_true",
        help='Use an assistant prefill of "{" for B1/C3 JSON outputs to prevent markdown fences.',
    )
    parser.add_argument(
        "--allow-non-strict-json",
        action="store_true",
        help="Allow pilot-only extraction from markdown fences or first JSON object. Formal-style runs should not set this.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_dir = ROOT / "local_runs" / args.run_id
    if run_dir.exists() and not args.dry_run:
        raise RuntimeError(f"Run directory already exists: {run_dir}")

    manifest_path = DATA_DIR / "pilot10_manifest.jsonl"
    rows = read_jsonl(manifest_path)[: args.limit]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    run_manifest = {
        "run_id": args.run_id,
        "method_ids": ["B1", "C3"],
        "parameter_status": "temporary_pilot_use_only_not_final_freeze",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sample_manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "model": args.model,
        "temperature": args.temperature,
        "max_tokens": {
            "ocr": args.max_tokens_ocr,
            "b1": args.max_tokens_b1,
            "c3": args.max_tokens_c3,
        },
        "api": {
            "provider": "anthropic_compatible",
            "base_url_env": "ANTHROPIC_BASE_URL",
            "auth_env": "ANTHROPIC_AUTH_TOKEN",
            "token_value_recorded": False,
        },
        "prompts": {
            "ocr": {
                "path": str(OCR_PROMPT.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(OCR_PROMPT),
            },
            "b1": {
                "path": str(B1_PROMPT.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(B1_PROMPT),
                "method_changed": False,
            },
            "c3": {
                "path": str(C3_PROMPT.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(C3_PROMPT),
                "method_changed": False,
            },
        },
        "parser": {
            "semantic_repair": False,
            "target_used_for_parsing": False,
            "strict_json_only": not args.allow_non_strict_json,
            "assistant_prefill_json": args.assistant_prefill_json,
            "assistant_prefill_value": "{" if args.assistant_prefill_json else None,
            "format_violation_policy": "markdown_code_fence_or_extra_text_is_parse_failure"
            if not args.allow_non_strict_json
            else "pilot_only_non_strict_json_extraction_allowed",
            "allowed_json_extraction_policy": ["strict_json"]
            if not args.allow_non_strict_json
            else [
                "strict_json",
                "single_fenced_json_block",
                "first_json_object",
            ],
            "c3_questionnaire_to_canonical": {
                "path": "scripts/c3_questionnaire_to_canonical.py",
                "sha256": sha256_file(ROOT / "scripts" / "c3_questionnaire_to_canonical.py"),
            },
        },
        "scoring": {
            "target_used_only_after_validation": True,
            "target_source": "pilot10_external canonical_proxy_gt_file",
        },
        "samples": [row["pilot_sample_id"] for row in rows],
    }
    write_json(run_dir / "run_manifest.json", run_manifest)

    if args.dry_run:
        print(f"Dry run prepared {len(rows)} samples in {run_dir}.")
        return 0

    client = get_client()
    ocr_template = OCR_PROMPT.read_text(encoding="utf-8")
    b1_template = B1_PROMPT.read_text(encoding="utf-8")
    c3_template = C3_PROMPT.read_text(encoding="utf-8")

    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for row in rows:
        sample_id = row["pilot_sample_id"]
        chart_id = row["chart_id"]
        image_path = resolve_package_path(row["image_path"])
        target_path = resolve_package_path(row["canonical_proxy_gt_file"])
        target = json.loads(target_path.read_text(encoding="utf-8"))

        print(f"Running OCR/B1/C3 {sample_id} {chart_id}", flush=True)

        try:
            ocr_prompt = fill_prompt(ocr_template, row)
            ocr_text, ocr_response = call_model(
                client,
                model=args.model,
                prompt=ocr_prompt,
                image_path=image_path,
                max_tokens=args.max_tokens_ocr,
                temperature=args.temperature,
            )
            write_text(run_dir / "OCR" / "full_chart_text" / f"{chart_id}.txt", ocr_text)
            save_raw_response(run_dir / "OCR" / "raw_responses" / f"{chart_id}.json", ocr_response)
        except Exception as exc:
            write_text(run_dir / "OCR" / "errors" / f"{chart_id}.txt", repr(exc))
            failures.append({"sample_id": sample_id, "chart_id": chart_id, "method": "OCR", "error": repr(exc)})
            continue

        try:
            b1_prompt = fill_prompt(b1_template, row, ocr_text=ocr_text)
            b1_call = call_model_json_prefill if args.assistant_prefill_json else call_model
            b1_text, b1_response = b1_call(
                client,
                model=args.model,
                prompt=b1_prompt,
                image_path=None,
                max_tokens=args.max_tokens_b1,
                temperature=args.temperature,
            )
            write_text(run_dir / "B1" / "raw_text" / f"{chart_id}.txt", b1_text)
            save_raw_response(run_dir / "B1" / "raw_responses" / f"{chart_id}.json", b1_response)
            b1_json, extraction_policy = extract_json_object(
                b1_text, strict_only=not args.allow_non_strict_json
            )
            write_json(run_dir / "B1" / "canonical_json" / f"{chart_id}.json", b1_json)
            validation_errors = validate_canonical(b1_json, validator)
            write_json(run_dir / "B1" / "validation" / f"{chart_id}.json", validation_errors)
            item: dict[str, Any] = {
                "method": "B1",
                "sample_id": sample_id,
                "chart_id": chart_id,
                "json_extraction_policy": extraction_policy,
                "validation_error_count": len(validation_errors),
                "validation_errors": validation_errors,
                "score": None,
            }
            if not validation_errors:
                score = score_canonical(b1_json, target)
                write_json(run_dir / "B1" / "scores" / f"{chart_id}.json", score)
                item["score"] = {k: score[k] for k in ["correct", "total", "accuracy"]}
            else:
                failures.append(
                    {"sample_id": sample_id, "chart_id": chart_id, "method": "B1", "error": "schema_validation_failed"}
                )
            results.append(item)
        except Exception as exc:
            write_text(run_dir / "B1" / "parse_errors" / f"{chart_id}.txt", repr(exc))
            failures.append({"sample_id": sample_id, "chart_id": chart_id, "method": "B1", "error": repr(exc)})
            results.append(
                {
                    "method": "B1",
                    "sample_id": sample_id,
                    "chart_id": chart_id,
                    "json_extraction_policy": None,
                    "validation_error_count": None,
                    "validation_errors": None,
                    "score": None,
                    "failure": repr(exc),
                }
            )

        try:
            c3_prompt = fill_prompt(c3_template, row)
            c3_call = call_model_json_prefill if args.assistant_prefill_json else call_model
            c3_text, c3_response = c3_call(
                client,
                model=args.model,
                prompt=c3_prompt,
                image_path=image_path,
                max_tokens=args.max_tokens_c3,
                temperature=args.temperature,
            )
            write_text(run_dir / "C3" / "raw_text" / f"{chart_id}.txt", c3_text)
            save_raw_response(run_dir / "C3" / "raw_responses" / f"{chart_id}.json", c3_response)
            questionnaire, extraction_policy = extract_json_object(
                c3_text, strict_only=not args.allow_non_strict_json
            )
            write_json(run_dir / "C3" / "questionnaire_json" / f"{chart_id}.json", questionnaire)
            canonical = questionnaire_to_canonical(questionnaire)
            write_json(run_dir / "C3" / "canonical_json" / f"{chart_id}.json", canonical)
            validation_errors = validate_canonical(canonical, validator)
            write_json(run_dir / "C3" / "validation" / f"{chart_id}.json", validation_errors)
            item = {
                "method": "C3",
                "sample_id": sample_id,
                "chart_id": chart_id,
                "json_extraction_policy": extraction_policy,
                "validation_error_count": len(validation_errors),
                "validation_errors": validation_errors,
                "score": None,
            }
            if not validation_errors:
                score = score_canonical(canonical, target)
                write_json(run_dir / "C3" / "scores" / f"{chart_id}.json", score)
                item["score"] = {k: score[k] for k in ["correct", "total", "accuracy"]}
            else:
                failures.append(
                    {"sample_id": sample_id, "chart_id": chart_id, "method": "C3", "error": "schema_validation_failed"}
                )
            results.append(item)
        except Exception as exc:
            write_text(run_dir / "C3" / "parse_errors" / f"{chart_id}.txt", repr(exc))
            failures.append({"sample_id": sample_id, "chart_id": chart_id, "method": "C3", "error": repr(exc)})
            results.append(
                {
                    "method": "C3",
                    "sample_id": sample_id,
                    "chart_id": chart_id,
                    "json_extraction_policy": None,
                    "validation_error_count": None,
                    "validation_errors": None,
                    "score": None,
                    "failure": repr(exc),
                }
            )

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id,
        "parameter_status": "temporary_pilot_use_only_not_final_freeze",
        "methods": {
            "B1": summarize_method("B1", results),
            "C3": summarize_method("C3", results),
        },
        "failures": failures,
    }
    write_json(run_dir / "summary_report.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
