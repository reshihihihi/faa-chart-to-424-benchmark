#!/usr/bin/env python3
"""Run Experiment 6 V2 direct VLM verifier with Anthropic tool_use output."""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def stable_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_image_path(repo_root: Path, image_path: str) -> Path:
    path = Path(image_path)
    if path.is_absolute():
        return path
    return repo_root / path


def allowed_error_fields(candidate_record: Dict[str, Any]) -> List[str]:
    fields = ["missed_approach.leg_count", "missed_approach.legs.sequence"]
    for leg in candidate_record.get("missed_approach", {}).get("legs", []):
        leg_index = leg.get("leg_index")
        if not isinstance(leg_index, int):
            continue
        fields.extend(
            [
                f"missed_approach.legs[{leg_index}].path_terminator",
                f"missed_approach.legs[{leg_index}].fix_ident",
                f"missed_approach.legs[{leg_index}].altitude_constraint",
                f"missed_approach.legs[{leg_index}].turn",
                f"missed_approach.legs[{leg_index}].course_or_radial",
                f"missed_approach.legs[{leg_index}].hold_params",
                f"missed_approach.legs[{leg_index}].hold_params.value.leg_time_min",
            ]
        )
    return fields


def audit_decision_tool() -> Dict[str, Any]:
    return {
        "name": "audit_decision",
        "description": (
            "Return exactly one Experiment 6 audit decision. The tool input itself "
            "must be the final JSON object with top-level keys consistent and error_fields."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["consistent", "error_fields"],
            "properties": {
                "consistent": {"type": "boolean"},
                "error_fields": {"type": "array", "items": {"type": "string"}},
            },
        },
    }


def validate_decision(obj: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not isinstance(obj, dict):
        return None, "json_root_not_object"
    if set(obj) != {"consistent", "error_fields"}:
        return None, f"schema_key_error: expected ['consistent','error_fields'], got {sorted(obj)}"
    if not isinstance(obj.get("consistent"), bool):
        return None, "schema_type_error: consistent must be boolean"
    if not isinstance(obj.get("error_fields"), list) or not all(isinstance(x, str) for x in obj["error_fields"]):
        return None, "schema_type_error: error_fields must be string array"
    return {"consistent": obj["consistent"], "error_fields": obj["error_fields"]}, None


def image_block(image_path: Path) -> Dict[str, Any]:
    media_type = "image/png"
    if image_path.suffix.lower() in {".jpg", ".jpeg"}:
        media_type = "image/jpeg"
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.b64encode(image_path.read_bytes()).decode("ascii"),
        },
    }


def make_user_text(prompt: str, item: Dict[str, Any]) -> str:
    visible = {
        "verification_case_id": item["verification_case_id"],
        "chart_id": item["chart_id"],
        "sample_id": item["sample_id"],
        "candidate_record": item["candidate_record"],
    }
    return (
        prompt
        + "\n\nUse the audit_decision tool exactly once. Do not return markdown or prose."
        + "\n\nAllowed error_fields values\n"
        + json.dumps(allowed_error_fields(item["candidate_record"]), ensure_ascii=False, indent=2)
        + "\n\nCandidate 424-like record\n"
        + json.dumps(visible, ensure_ascii=False, indent=2, sort_keys=True)
    )


def create_client(base_url: str, api_key_env: str):
    import anthropic

    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    api_key = os.environ.get(api_key_env) if api_key_env else os.environ.get("ANTHROPIC_API_KEY")
    if not auth_token and not api_key:
        raise RuntimeError("Missing ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY.")
    kwargs: Dict[str, Any] = {}
    if auth_token:
        kwargs["auth_token"] = auth_token
    else:
        kwargs["api_key"] = api_key
    resolved_base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL")
    if resolved_base_url:
        kwargs["base_url"] = resolved_base_url
    return anthropic.Anthropic(**kwargs)


def extract_tool_decision(response: Any) -> Tuple[str, Optional[Dict[str, Any]], Optional[str], str]:
    tool_blocks = [
        block
        for block in response.content
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "audit_decision"
    ]
    if len(tool_blocks) != 1:
        return "", None, f"expected_one_tool_use_got_{len(tool_blocks)}", "anthropic_tool_use"
    tool_input = tool_blocks[0].input
    parsed, parse_error = validate_decision(tool_input)
    return json.dumps(tool_input, ensure_ascii=False, sort_keys=True), parsed, parse_error, "anthropic_tool_use"


def run_one(item: Dict[str, Any], prompt: str, prompt_hash: str, args: argparse.Namespace) -> Dict[str, Any]:
    started = time.time()
    parsed: Optional[Dict[str, Any]] = None
    parse_error: Optional[str] = None
    api_error: Optional[str] = None
    raw_output = ""
    output_mode = "anthropic_tool_use"
    attempts = 0
    try:
        client = create_client(args.base_url, args.api_key_env)
        image_path = resolve_image_path(Path(args.repo_root).resolve(), item["image_path"])
        messages = [
            {
                "role": "user",
                "content": [
                    image_block(image_path),
                    {"type": "text", "text": make_user_text(prompt, item)},
                ],
            }
        ]
    except Exception as exc:
        api_error = f"input_or_client_error: {type(exc).__name__}: {exc}"
        messages = []
        client = None

    if api_error is None:
        for attempt in range(1, args.api_retries + 2):
            attempts = attempt
            try:
                response = client.messages.create(
                    model=args.model,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                    messages=messages,
                    tools=[audit_decision_tool()],
                    tool_choice={"type": "tool", "name": "audit_decision"},
                )
                raw_output, parsed, parse_error, output_mode = extract_tool_decision(response)
                api_error = None
                break
            except Exception as exc:  # provider/proxy exceptions are diverse
                api_error = f"{type(exc).__name__}: {exc}"
                if attempt <= args.api_retries:
                    time.sleep(min(3 * attempt, 12))
                    continue

    return {
        "verification_case_id": item["verification_case_id"],
        "chart_id": item["chart_id"],
        "sample_id": item["sample_id"],
        "method": args.method_id,
        "model": args.model,
        "base_url": args.base_url or os.environ.get("ANTHROPIC_BASE_URL"),
        "prompt_hash": prompt_hash,
        "input_hash": stable_hash(item),
        "raw_output": raw_output,
        "output_mode": output_mode,
        "parsed_output": parsed,
        "parse_ok": parsed is not None,
        "parse_error": parse_error,
        "api_error": api_error,
        "api_attempts": attempts,
        "elapsed_sec": round(time.time() - started, 3),
    }


def load_done(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {row["verification_case_id"] for row in read_jsonl(path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-jsonl", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--out-jsonl", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--model", default="claude-sonnet-4-5-20250929")
    parser.add_argument("--method-id", default="V2_direct_vlm_anthropic_tooluse")
    parser.add_argument("--base-url", default=os.environ.get("ANTHROPIC_BASE_URL", ""))
    parser.add_argument("--api-key-env", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--api-retries", type=int, default=1)
    args = parser.parse_args()

    prompt = Path(args.prompt).read_text(encoding="utf-8")
    prompt_hash = sha256_text(prompt)
    rows = list(read_jsonl(Path(args.input_jsonl)))
    if args.limit:
        rows = rows[: args.limit]

    out_path = Path(args.out_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(out_path)
    todo = [row for row in rows if row["verification_case_id"] not in done]

    started = time.time()
    completed_now = 0
    with out_path.open("a", encoding="utf-8", newline="\n") as f:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_map = {executor.submit(run_one, item, prompt, prompt_hash, args): item["verification_case_id"] for item in todo}
            for future in concurrent.futures.as_completed(future_map):
                result = future.result()
                f.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
                f.flush()
                completed_now += 1
                if completed_now == 1 or completed_now % 5 == 0:
                    print(f"completed {len(done) + completed_now}/{len(rows)}")

    selected_ids = {row["verification_case_id"] for row in rows}
    selected_outputs = [row for row in read_jsonl(out_path) if row["verification_case_id"] in selected_ids]
    summary = {
        "method": args.method_id,
        "model": args.model,
        "base_url": args.base_url or os.environ.get("ANTHROPIC_BASE_URL"),
        "prompt": args.prompt,
        "prompt_hash": prompt_hash,
        "input_jsonl": args.input_jsonl,
        "out_jsonl": args.out_jsonl,
        "requested_records": len(rows),
        "previously_done": len(done),
        "completed_now": completed_now,
        "total_outputs_for_request": len(selected_outputs),
        "parse_ok": sum(1 for row in selected_outputs if row.get("parse_ok")),
        "parse_fail": sum(1 for row in selected_outputs if not row.get("parse_ok")),
        "api_error": sum(1 for row in selected_outputs if row.get("api_error")),
        "elapsed_sec": round(time.time() - started, 3),
    }
    summary_path = Path(args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["api_error"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
