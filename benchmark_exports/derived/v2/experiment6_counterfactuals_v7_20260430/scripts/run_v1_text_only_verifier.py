#!/usr/bin/env python3
"""Run Experiment 6 V1 text-only verifier via an OpenAI-compatible API."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
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
            ]
        )
    return fields


def extract_json(raw: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    raw = raw.strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"json_parse_error: {exc}"
    if not isinstance(obj, dict):
        return None, "json_root_not_object"
    if set(obj) != {"consistent", "error_fields"}:
        return None, f"schema_key_error: expected ['consistent','error_fields'], got {sorted(obj)}"
    if not isinstance(obj.get("consistent"), bool):
        return None, "schema_type_error: consistent must be boolean"
    if not isinstance(obj.get("error_fields"), list) or not all(isinstance(x, str) for x in obj["error_fields"]):
        return None, "schema_type_error: error_fields must be string array"
    return {"consistent": obj["consistent"], "error_fields": obj["error_fields"]}, None


def make_messages(prompt: str, item: Dict[str, Any]) -> List[Dict[str, str]]:
    ocr_text = item.get("ocr_text", "")
    if not ocr_text and isinstance(item.get("ocr_text_lines"), list):
        ocr_text = "\n".join(str(line) for line in item["ocr_text_lines"])
    visible = {
        "verification_case_id": item["verification_case_id"],
        "chart_id": item["chart_id"],
        "sample_id": item["sample_id"],
        "text_source": item.get("text_source"),
        "ocr_id": item.get("ocr_id"),
        "ocr_engine": item.get("ocr_engine"),
        "ocr_version": item.get("ocr_version"),
        "ocr_text": ocr_text,
        "allowed_error_fields": allowed_error_fields(item["candidate_record"]),
        "candidate_record": item["candidate_record"],
    }
    return [
        {
            "role": "system",
            "content": "Return only valid bare JSON with keys consistent and error_fields. No markdown.",
        },
        {
            "role": "user",
            "content": prompt + "\n\nText-only verification input follows\n" + json.dumps(visible, ensure_ascii=False, indent=2, sort_keys=True),
        },
    ]


def call_chat_completion(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    timeout_sec: int,
    max_tokens: int,
    temperature: float,
) -> Dict[str, Any]:
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=data,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        return json.loads(response.read().decode("utf-8"))


def run_one(item: Dict[str, Any], prompt: str, prompt_hash: str, args: argparse.Namespace) -> Dict[str, Any]:
    messages = make_messages(prompt, item)
    started = time.time()
    raw_output = ""
    parsed: Optional[Dict[str, Any]] = None
    parse_error: Optional[str] = None
    api_error: Optional[str] = None
    attempts = 0

    for attempt in range(1, args.api_retries + 2):
        attempts = attempt
        try:
            response = call_chat_completion(
                base_url=args.base_url,
                api_key=args.api_key or "",
                model=args.model,
                messages=messages,
                timeout_sec=args.timeout_sec,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
            raw_output = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed, parse_error = extract_json(raw_output)
            api_error = None
            break
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as exc:
            api_error = f"{type(exc).__name__}: {exc}"
            if attempt <= args.api_retries:
                time.sleep(min(2 * attempt, 10))
                continue

    return {
        "verification_case_id": item["verification_case_id"],
        "chart_id": item["chart_id"],
        "sample_id": item["sample_id"],
        "method": "V1_text_only",
        "model": args.model,
        "base_url": args.base_url,
        "prompt_hash": prompt_hash,
        "input_hash": stable_hash(item),
        "raw_output": raw_output,
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
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_COMPAT_BASE_URL", "http://127.0.0.1:8080/v1"))
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout-sec", type=int, default=120)
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
        "method": "V1_text_only",
        "model": args.model,
        "base_url": args.base_url,
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
