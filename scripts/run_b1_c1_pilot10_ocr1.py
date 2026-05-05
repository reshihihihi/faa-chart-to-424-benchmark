from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from run_pilot10_anthropic import (
    B1_PROMPT,
    DATA_DIR,
    ROOT,
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
from model_clients import call_model_json, create_model_client, model_api_manifest, save_model_response


DEFAULT_RUN_ID = "pilot10_group1_ocr1_b1_c1_gpt54_20260428_r1"
DEFAULT_OCR_TEXT_ROOT = ROOT / "ocr_artifacts" / "pilot10_external" / "ocr1_paddleocr_ppocrv5_20260428_r1" / "full_text"
C1_PROMPT = ROOT / "prompts" / "paper_v2" / "c1_image_to_canonical_pilot10.zh_v1_candidate.md"
RUN_OUTPUT_ROOT = ROOT / "predictions" / "pilot10_external"


def call_model_json_prefill(
    client: Any,
    *,
    provider: str,
    model: str,
    prompt: str,
    image_path: Path | None,
    max_tokens: int,
    temperature: float,
    json_mode: bool,
    assistant_prefill_json: bool,
) -> tuple[str, Any]:
    return call_model_json(
        client,
        provider=provider,
        model=model,
        prompt=prompt,
        image_path=image_path,
        max_tokens=max_tokens,
        temperature=temperature,
        json_mode=json_mode,
        assistant_prefill_json=assistant_prefill_json,
    )


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
    return {
        "samples_total": len(method_results),
        "schema_valid": sum(1 for item in method_results if item.get("validation_error_count") == 0),
        "samples_scored": len(scored),
        "json_extraction_policy_counts": policy_counts,
        "parser_repair_count_non_strict_json": sum(
            count for policy, count in policy_counts.items() if policy != "strict_json"
        ),
        "score": {
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total else None,
        },
        "results": method_results,
    }


def run_method(
    *,
    method: str,
    client: Any,
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
    provider: str,
    json_mode: bool,
    assistant_prefill_json: bool,
) -> tuple[dict[str, Any], dict[str, str] | None]:
    try:
        text, response = call_model_json_prefill(
            client,
            provider=provider,
            model=model,
            prompt=prompt,
            image_path=image_path,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=json_mode,
            assistant_prefill_json=assistant_prefill_json,
        )
        write_text(run_dir / method / "raw_text" / f"{chart_id}.txt", text)
        save_model_response(run_dir / method / "raw_responses" / f"{chart_id}.json", response)
        pred, extraction_policy = parse_strict_json(text)
        write_json(run_dir / method / "canonical_json" / f"{chart_id}.json", pred)
        validation_errors = validate_canonical(pred, validator)
        write_json(run_dir / method / "validation" / f"{chart_id}.json", validation_errors)
        item: dict[str, Any] = {
            "method": method,
            "sample_id": sample_id,
            "chart_id": chart_id,
            "json_extraction_policy": extraction_policy,
            "validation_error_count": len(validation_errors),
            "validation_errors": validation_errors,
            "score": None,
        }
        if validation_errors:
            return item, {"sample_id": sample_id, "chart_id": chart_id, "method": method, "error": "schema_validation_failed"}
        score = score_canonical(pred, target)
        write_json(run_dir / method / "scores" / f"{chart_id}.json", score)
        item["score"] = {key: score[key] for key in ["correct", "total", "accuracy"]}
        return item, None
    except Exception as exc:  # noqa: BLE001
        write_text(run_dir / method / "parse_errors" / f"{chart_id}.txt", repr(exc))
        item = {
            "method": method,
            "sample_id": sample_id,
            "chart_id": chart_id,
            "json_extraction_policy": None,
            "validation_error_count": None,
            "validation_errors": None,
            "score": None,
            "failure": repr(exc),
        }
        return item, {"sample_id": sample_id, "chart_id": chart_id, "method": method, "error": repr(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run corrected pilot10 B1 and C1 with ordinary OCR-1.")
    parser.add_argument("--provider", default="openai_compatible", choices=["openai_compatible", "anthropic_compatible"])
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key-env", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens-b1", type=int, default=4096)
    parser.add_argument("--max-tokens-c1", type=int, default=4096)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--ocr-text-root", type=Path, default=DEFAULT_OCR_TEXT_ROOT)
    parser.add_argument("--json-mode", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--assistant-prefill-json", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_dir = RUN_OUTPUT_ROOT / args.run_id
    if run_dir.exists() and not args.dry_run:
        raise RuntimeError(f"Run directory already exists: {run_dir}")

    manifest_path = DATA_DIR / "pilot10_manifest.jsonl"
    rows = read_jsonl(manifest_path)[: args.limit]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    run_manifest = {
        "run_id": args.run_id,
        "method_ids": ["B1", "C1"],
        "parameter_status": "temporary_pilot_use_only_not_final_freeze",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sample_manifest": manifest_path.relative_to(ROOT).as_posix(),
        "sample_role": "pilot10_external_excluded_from_formal_evaluation",
        "model": args.model,
        "temperature": args.temperature,
        "max_tokens": {
            "b1": args.max_tokens_b1,
            "c1": args.max_tokens_c1,
        },
        "api": model_api_manifest(
            provider=args.provider,
            base_url=args.base_url,
            api_key_env=args.api_key_env,
            json_mode=args.json_mode,
            assistant_prefill_json=args.assistant_prefill_json,
        ),
        "ocr": {
            "ocr_id": "OCR-1",
            "source": "ordinary_ocr_not_mllm_transcription",
            "full_text_root": args.ocr_text_root.relative_to(ROOT).as_posix(),
        },
        "schema": {
            "path": SCHEMA_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(SCHEMA_PATH),
        },
        "parser_policy": {
            "strict_json_only": True,
            "json_mode": args.json_mode,
            "assistant_prefill_json": args.assistant_prefill_json,
            "assistant_prefill_value": "{" if args.assistant_prefill_json else None,
            "semantic_repair": False,
            "code_fence_stripping_allowed": False,
        },
        "prompts": {
            "b1": {
                "path": B1_PROMPT.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(B1_PROMPT),
            },
            "c1": {
                "path": C1_PROMPT.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(C1_PROMPT),
            },
        },
        "scoring": {
            "target_used_only_after_validation": True,
            "target_source": "pilot10_external canonical_proxy_gt_file",
        },
        "samples": [row["pilot_sample_id"] for row in rows],
    }
    write_json(run_dir / "run_manifest.json", run_manifest)

    write_text(
        run_dir / "A1" / "NOT_RUN_A1.md",
        "A1 was not run because no frozen OCR+Rules runner is registered yet.",
    )
    write_text(
        run_dir / "A2" / "NOT_RUN_A2.md",
        "A2 was not run because no frozen OCR+Rules runner is registered yet.",
    )

    if args.dry_run:
        print(f"Dry run prepared {len(rows)} samples in {run_dir}.")
        return 0

    client = create_model_client(provider=args.provider, base_url=args.base_url, api_key_env=args.api_key_env)
    b1_template = B1_PROMPT.read_text(encoding="utf-8")
    c1_template = C1_PROMPT.read_text(encoding="utf-8")
    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for row in rows:
        sample_id = row["pilot_sample_id"]
        chart_id = row["chart_id"]
        image_path = resolve_package_path(row["image_path"])
        target_path = resolve_package_path(row["canonical_proxy_gt_file"])
        target = json.loads(target_path.read_text(encoding="utf-8"))
        ocr_text_path = args.ocr_text_root / f"{chart_id}.txt"
        print(f"Running B1/C1 {sample_id} {chart_id}", flush=True)

        if not ocr_text_path.exists():
            failures.append(
                {
                    "sample_id": sample_id,
                    "chart_id": chart_id,
                    "method": "B1",
                    "error": f"missing_ocr_text:{ocr_text_path.relative_to(ROOT).as_posix()}",
                }
            )
        else:
            ocr_text = ocr_text_path.read_text(encoding="utf-8")
            b1_prompt = fill_prompt(b1_template, row, ocr_text=ocr_text)
            item, failure = run_method(
                method="B1",
                client=client,
                model=args.model,
                prompt=b1_prompt,
                image_path=None,
                target=target,
                validator=validator,
                run_dir=run_dir,
                chart_id=chart_id,
                sample_id=sample_id,
                max_tokens=args.max_tokens_b1,
                temperature=args.temperature,
                provider=args.provider,
                json_mode=args.json_mode,
                assistant_prefill_json=args.assistant_prefill_json,
            )
            results.append(item)
            if failure:
                failures.append(failure)

        c1_prompt = fill_prompt(c1_template, row)
        item, failure = run_method(
            method="C1",
            client=client,
            model=args.model,
            prompt=c1_prompt,
            image_path=image_path,
            target=target,
            validator=validator,
            run_dir=run_dir,
            chart_id=chart_id,
            sample_id=sample_id,
            max_tokens=args.max_tokens_c1,
            temperature=args.temperature,
            provider=args.provider,
            json_mode=args.json_mode,
            assistant_prefill_json=args.assistant_prefill_json,
        )
        results.append(item)
        if failure:
            failures.append(failure)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id,
        "parameter_status": "temporary_pilot_use_only_not_final_freeze",
        "methods": {
            "B1": summarize_method("B1", results),
            "C1": summarize_method("C1", results),
        },
        "failures": failures,
    }
    write_json(run_dir / "summary_report.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
