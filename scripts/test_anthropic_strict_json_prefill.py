from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from c3_questionnaire_to_canonical import questionnaire_to_canonical
from run_pilot10_anthropic import (
    B1_PROMPT,
    C3_PROMPT,
    DATA_DIR,
    ROOT,
    SCHEMA_PATH,
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


DEFAULT_RUN_ID = "strict_json_prefill_probe_20260427_r1"


def call_model_prefill(
    client: Any,
    *,
    model: str,
    prompt: str,
    image_path: Path | None,
    max_tokens: int,
    temperature: float,
    assistant_prefill: str,
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
            {"role": "assistant", "content": assistant_prefill},
        ],
    )
    text_parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
    continuation = "\n".join(text_parts).strip()
    return (assistant_prefill + continuation).strip(), response


def inspect_json_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    parsed_ok = False
    parse_error = None
    try:
        json.loads(stripped)
        parsed_ok = True
    except json.JSONDecodeError as exc:
        parse_error = str(exc)
    return {
        "length": len(text),
        "strict_json": parsed_ok,
        "parse_error": parse_error,
        "first_20": stripped[:20],
        "last_20": stripped[-20:],
        "starts_with_left_brace": stripped.startswith("{"),
        "ends_with_right_brace": stripped.endswith("}"),
        "contains_code_fence": "```" in text,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Anthropic assistant prefill for bare JSON output.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--sample-index", type=int, default=0)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument(
        "--ocr-text-run-id",
        default="pilot10_exp1_b1_c3_strict_json_20260427_r1",
        help="Run id containing already generated OCR text for B1.",
    )
    args = parser.parse_args()

    run_dir = ROOT / "local_runs" / args.run_id
    if run_dir.exists():
        raise RuntimeError(f"Run directory already exists: {run_dir}")

    rows = read_jsonl(DATA_DIR / "pilot10_manifest.jsonl")
    row = rows[args.sample_index]
    chart_id = row["chart_id"]
    sample_id = row["pilot_sample_id"]
    image_path = resolve_package_path(row["image_path"])
    target_path = resolve_package_path(row["canonical_proxy_gt_file"])
    target = json.loads(target_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))

    ocr_text_path = ROOT / "local_runs" / args.ocr_text_run_id / "OCR" / "full_chart_text" / f"{chart_id}.txt"
    if not ocr_text_path.exists():
        raise FileNotFoundError(f"Missing OCR text: {ocr_text_path}")
    ocr_text = ocr_text_path.read_text(encoding="utf-8")

    client = get_client()
    summary: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id,
        "purpose": "strict_json_format_control_probe",
        "strategy": "anthropic_messages_assistant_prefill_left_brace",
        "model": args.model,
        "temperature": args.temperature,
        "sample_id": sample_id,
        "chart_id": chart_id,
        "prompts": {
            "b1": {
                "path": str(B1_PROMPT.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(B1_PROMPT),
            },
            "c3": {
                "path": str(C3_PROMPT.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(C3_PROMPT),
            },
        },
        "ocr_text_source": str(ocr_text_path.relative_to(ROOT)).replace("\\", "/"),
        "tests": {},
    }
    write_json(run_dir / "run_manifest.json", summary)

    b1_prompt = fill_prompt(B1_PROMPT.read_text(encoding="utf-8"), row, ocr_text=ocr_text)
    b1_text, b1_response = call_model_prefill(
        client,
        model=args.model,
        prompt=b1_prompt,
        image_path=None,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        assistant_prefill="{",
    )
    write_text(run_dir / "B1" / "raw_text" / f"{chart_id}.txt", b1_text)
    save_raw_response(run_dir / "B1" / "raw_responses" / f"{chart_id}.json", b1_response)
    b1_inspection = inspect_json_text(b1_text)
    summary["tests"]["B1"] = b1_inspection
    if b1_inspection["strict_json"]:
        b1_json = json.loads(b1_text.strip())
        write_json(run_dir / "B1" / "canonical_json" / f"{chart_id}.json", b1_json)
        validation_errors = validate_canonical(b1_json, validator)
        write_json(run_dir / "B1" / "validation" / f"{chart_id}.json", validation_errors)
        summary["tests"]["B1"]["validation_error_count"] = len(validation_errors)
        if not validation_errors:
            score = score_canonical(b1_json, target)
            write_json(run_dir / "B1" / "scores" / f"{chart_id}.json", score)
            summary["tests"]["B1"]["score"] = {key: score[key] for key in ["correct", "total", "accuracy"]}

    c3_prompt = fill_prompt(C3_PROMPT.read_text(encoding="utf-8"), row)
    c3_text, c3_response = call_model_prefill(
        client,
        model=args.model,
        prompt=c3_prompt,
        image_path=image_path,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        assistant_prefill="{",
    )
    write_text(run_dir / "C3" / "raw_text" / f"{chart_id}.txt", c3_text)
    save_raw_response(run_dir / "C3" / "raw_responses" / f"{chart_id}.json", c3_response)
    c3_inspection = inspect_json_text(c3_text)
    summary["tests"]["C3"] = c3_inspection
    if c3_inspection["strict_json"]:
        questionnaire = json.loads(c3_text.strip())
        write_json(run_dir / "C3" / "questionnaire_json" / f"{chart_id}.json", questionnaire)
        canonical = questionnaire_to_canonical(questionnaire)
        write_json(run_dir / "C3" / "canonical_json" / f"{chart_id}.json", canonical)
        validation_errors = validate_canonical(canonical, validator)
        write_json(run_dir / "C3" / "validation" / f"{chart_id}.json", validation_errors)
        summary["tests"]["C3"]["validation_error_count"] = len(validation_errors)
        if not validation_errors:
            score = score_canonical(canonical, target)
            write_json(run_dir / "C3" / "scores" / f"{chart_id}.json", score)
            summary["tests"]["C3"]["score"] = {key: score[key] for key in ["correct", "total", "accuracy"]}

    write_json(run_dir / "summary_report.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["tests"]["B1"]["strict_json"] and summary["tests"]["C3"]["strict_json"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
