from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from scorers.group1_canonical_field_scorer import score_canonical as score_canonical_strict  # noqa: E402
from scorers.group1_canonical_field_scorer_v2 import (  # noqa: E402
    load_policy,
    score_canonical as score_canonical_v2,
    validate_canonical,
)


DEFAULT_RUN_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_dev50_20260503_r1"
DEFAULT_BASE_URL = "http://127.0.0.1:8080/v1"
SCHEMA_PATH = REPO_ROOT / "schemas" / "missed_approach_leg.schema.json"
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
ADMIN_GOLD_ANSWER = DEFAULT_RUN_DIR / "admin_artifacts" / "admin_gold_answer_dev50.jsonl"
ADMIN_FIELD_REVIEW = DEFAULT_RUN_DIR / "admin_artifacts" / "admin_field_review_dev50.jsonl"
GOLD_OBSERVABLE_ACCEPT_PENDING = DEFAULT_RUN_DIR / "inputs" / "gold_observable_dev50_accept_pending.jsonl"

QUESTION_FIELDS = [
    "Q_terminator",
    "Q1_fix_ident",
    "Q2_altitude_constraint",
    "Q3_turn",
    "Q4_course_or_radial",
    "Q5_hold_params",
]
METHODS = {"G0_Direct", "G1_Rules", "G3_LLM_Rules"}
ANSWER_SIDE_KEYS = {
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
    payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + ("\n" if value and not value.endswith("\n") else ""), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def answer(status: str, value: Any = None) -> dict[str, Any]:
    return {"status": status, "value": value}


def blank_prediction(chart_id: str, procedure: dict[str, Any], leg_count: int) -> dict[str, Any]:
    return {
        "chart_id": chart_id,
        "procedure": {
            "airport": procedure.get("airport"),
            "approach_ident": procedure.get("approach_ident"),
            "chart_name": procedure.get("chart_name"),
        },
        "missed_approach": {
            "leg_count": answer("present", leg_count) if leg_count > 0 else answer("unknown"),
            "legs": [
                {
                    "leg_index": idx,
                    "answers": {field: answer("unknown") for field in QUESTION_FIELDS},
                }
                for idx in range(1, leg_count + 1)
            ],
        },
    }


def build_oracle_prediction(
    *,
    method: str,
    chart_id: str,
    procedure: dict[str, Any],
    reviews: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if method == "G0_Direct":
        allowed_support_modes = {"direct_visible"}
    elif method == "G1_Rules":
        allowed_support_modes = {"direct_visible", "rule_default_completion"}
    else:
        raise ValueError(method)

    selected = [
        row
        for row in reviews
        if row.get("support_mode") in allowed_support_modes
        and row.get("field_name") in QUESTION_FIELDS
        and isinstance(row.get("canonical_leg_index"), int)
    ]
    leg_count = max((row["canonical_leg_index"] for row in selected), default=0)
    pred = blank_prediction(chart_id, procedure, leg_count)
    by_index = {leg["leg_index"]: leg for leg in pred["missed_approach"]["legs"]}
    applied: list[dict[str, Any]] = []
    for row in selected:
        leg = by_index.get(row["canonical_leg_index"])
        if not leg:
            continue
        field = row["field_name"]
        leg["answers"][field] = row.get("canonical_answer") or answer("unknown")
        applied.append(
            {
                "field_key": row.get("field_key"),
                "support_mode": row.get("support_mode"),
                "evidence_region_ids": row.get("evidence_region_ids") or [],
            }
        )
    diagnostics = {
        "method": method,
        "input_type": "admin_field_review_oracle_relation",
        "allowed_support_modes": sorted(allowed_support_modes),
        "selected_field_review_count": len(selected),
        "applied_field_count": len(applied),
        "uses_canonical_answer": True,
        "uses_canonical_leg_index": True,
        "purpose": (
            "Oracle diagnostic replay of audited direct-visible fields"
            if method == "G0_Direct"
            else "Oracle diagnostic replay of audited direct-visible plus rule-default-completion fields"
        ),
        "applied_fields": applied,
    }
    return pred, diagnostics


def model_api_url(base_url: str, endpoint: str) -> str:
    return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"


def get_json(url: str, *, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Authorization": "Bearer local-proxy"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc


def post_json(url: str, payload: dict[str, Any], *, timeout: int) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Authorization": "Bearer local-proxy"},
        method="POST",
    )
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
        raise RuntimeError(f"Expected exactly one tool call, got {len(tool_calls)}.")
    function = tool_calls[0].get("function") or {}
    return str(function.get("arguments") or "").strip(), response


def prompt_for_g3(chart_id: str, procedure: dict[str, Any], observable: dict[str, Any]) -> str:
    method_input = {
        "chart_id": chart_id,
        "procedure": procedure,
        "observable_facts": observable.get("observable_facts") or [],
    }
    return (
        "You convert audited chart-observable facts into the canonical missed-approach JSON schema.\n"
        "Use only the facts below and the rules stated in this prompt.\n"
        "Do not assume any value that is not supported by the facts; use unknown or not_applicable when uncertain.\n\n"
        "Rules:\n"
        "- FIX_TEXT facts provide visible fix identifiers.\n"
        "- ALTITUDE_TEXT facts provide visible altitude constraints.\n"
        "- HEADING_TEXT facts provide visible course_deg values.\n"
        "- RADIAL_TEXT/NAVAID_TEXT/OUTBOUND_INBOUND_MARK facts provide navaid_radial values.\n"
        "- CLIMB_ARROW and path segment facts indicate visible missed-approach path evidence but do not by themselves give a terminator.\n"
        "- A hold should only be emitted when the facts support a holding fix or visible hold-related evidence.\n"
        "- If leg ordering or terminator type is not justified, keep the answer unknown rather than inventing it.\n"
        "- Every answer object must contain exactly status and value.\n\n"
        "Method input JSON:\n"
        f"{json.dumps(method_input, ensure_ascii=False, indent=2)}"
    )


def retry_prompt_for_g3(
    original_prompt: str,
    previous_output: str,
    validation_errors: list[str] | None,
    parse_error: str | None,
) -> str:
    return (
        f"{original_prompt}\n\n"
        "Schema retry: the previous output failed local canonical validation.\n"
        "Keep the same allowed inputs. Correct only the schema/contract problems needed to pass validation.\n"
        "Important contract reminders:\n"
        "- If status is unknown, not_applicable, or not_observable, value must be null.\n"
        "- Q4_course_or_radial present values must include type and be exactly one of course_deg, navaid_radial, or direct.\n"
        "- If leg_count.status is present, leg_count.value must equal len(legs).\n\n"
        f"Parse error:\n{parse_error or 'None'}\n\n"
        f"Validation errors:\n{json.dumps(validation_errors or [], ensure_ascii=False, indent=2)}\n\n"
        f"Previous output:\n{previous_output}\n\n"
        "Emit a corrected object through the registered tool/schema."
    )


def scan_key_names(value: Any, forbidden: set[str]) -> dict[str, Any]:
    hits: list[dict[str, str]] = []

    def visit(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            for key, item in obj.items():
                if key in forbidden:
                    hits.append({"path": path or "$", "key": key})
                visit(item, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                visit(item, f"{path}[{index}]")

    visit(value, "")
    return {"hit_count": len(hits), "hits": hits[:50], "truncated": len(hits) > 50}


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
    write_json(run_dir / method / "scores_v2_admin_gold" / f"{chart_id}.json", score_v2)
    write_json(run_dir / method / "scores_strict_admin_gold" / f"{chart_id}.json", score_strict)
    return {
        "v2": {key: score_v2[key] for key in ["correct", "total", "accuracy"]},
        "strict": {key: score_strict[key] for key in ["correct", "total", "accuracy"]},
    }


def load_existing_result(
    *,
    method: str,
    chart_id: str,
    run_dir: Path,
    score_dir: str,
) -> dict[str, Any] | None:
    validation = read_json(run_dir / method / "validation" / f"{chart_id}.json")
    score_v2 = read_json(run_dir / method / score_dir / f"{chart_id}.json")
    score_strict = read_json(run_dir / method / "scores_strict_admin_gold" / f"{chart_id}.json")
    if validation is None or score_v2 is None or score_strict is None:
        return None
    if validation:
        return None
    row = {
        "method": method,
        "chart_id": chart_id,
        "validation_error_count": 0,
        "validation_errors": [],
        "score": {
            "v2": {key: score_v2[key] for key in ["correct", "total", "accuracy"]},
            "strict": {key: score_strict[key] for key in ["correct", "total", "accuracy"]},
        },
        "reused_existing_output": True,
    }
    input_payload = read_json(run_dir / method / "inputs" / f"{chart_id}.json")
    if input_payload is not None:
        row["method_input_forbidden_scan"] = scan_key_names(input_payload, ANSWER_SIDE_KEYS)
    return row


def run_g3_one(
    *,
    args: argparse.Namespace,
    chart_id: str,
    procedure: dict[str, Any],
    observable: dict[str, Any],
    target: dict[str, Any],
    policies: dict[tuple[str, str], dict[str, Any]],
    schema: dict[str, Any],
    validator: Draft202012Validator,
) -> dict[str, Any]:
    method = "G3_LLM_Rules"
    prompt = prompt_for_g3(chart_id, procedure, observable)
    input_payload = {
        "chart_id": chart_id,
        "procedure": procedure,
        "observable_path": rel(args.gold_observable),
        "observable_facts": observable.get("observable_facts") or [],
        "rule_prompt": "embedded_in_prompt",
    }
    write_json(args.run_dir / method / "inputs" / f"{chart_id}.json", input_payload)
    write_text(args.run_dir / method / "prompts" / f"{chart_id}.txt", prompt)
    current_prompt = prompt
    last_text = ""
    last_errors: list[str] | None = None
    total_elapsed = 0.0
    for attempt in range(1, args.schema_retry_count + 2):
        started = time.time()
        try:
            text, response = call_chat_tool(
                base_url=args.base_url,
                model=args.model,
                prompt=current_prompt,
                schema=schema,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                timeout=args.request_timeout,
            )
            total_elapsed += time.time() - started
            last_text = text
            write_text(args.run_dir / method / "raw_text" / f"{chart_id}.attempt_{attempt}.txt", text)
            write_json(args.run_dir / method / "raw_responses" / f"{chart_id}.attempt_{attempt}.json", response)
            pred = json.loads(text)
            errors = validate_canonical(pred, validator)
            write_json(args.run_dir / method / "validation" / f"{chart_id}.attempt_{attempt}.json", errors)
            if not errors:
                write_text(args.run_dir / method / "raw_text" / f"{chart_id}.txt", text)
                write_json(args.run_dir / method / "raw_responses" / f"{chart_id}.json", response)
                write_json(args.run_dir / method / "validation" / f"{chart_id}.json", errors)
                write_json(args.run_dir / method / "canonical_json" / f"{chart_id}.json", pred)
                score = score_and_write(
                    method=method,
                    chart_id=chart_id,
                    pred=pred,
                    target=target,
                    policies=policies,
                    run_dir=args.run_dir,
                )
                return {
                    "method": method,
                    "chart_id": chart_id,
                    "elapsed_sec": total_elapsed,
                    "attempt_count": attempt,
                    "schema_retry_count": attempt - 1,
                    "validation_error_count": 0,
                    "validation_errors": [],
                    "score": score,
                    "method_input_forbidden_scan": scan_key_names(input_payload, ANSWER_SIDE_KEYS),
                }
            last_errors = errors
            if attempt <= args.schema_retry_count:
                current_prompt = retry_prompt_for_g3(prompt, text, errors, None)
                continue
            write_text(args.run_dir / method / "raw_text" / f"{chart_id}.txt", text)
            write_json(args.run_dir / method / "raw_responses" / f"{chart_id}.json", response)
            write_json(args.run_dir / method / "validation" / f"{chart_id}.json", errors)
            write_json(args.run_dir / method / "canonical_json" / f"{chart_id}.json", pred)
            return {
                "method": method,
                "chart_id": chart_id,
                "elapsed_sec": total_elapsed,
                "attempt_count": attempt,
                "schema_retry_count": attempt - 1,
                "validation_error_count": len(errors),
                "validation_errors": errors,
                "score": None,
                "method_input_forbidden_scan": scan_key_names(input_payload, ANSWER_SIDE_KEYS),
            }
        except Exception as exc:  # noqa: BLE001
            total_elapsed += time.time() - started
            err = repr(exc)
            write_text(args.run_dir / method / "errors" / f"{chart_id}.attempt_{attempt}.txt", err)
            if attempt <= args.schema_retry_count:
                current_prompt = retry_prompt_for_g3(prompt, last_text, last_errors, err)
                continue
            write_json(args.run_dir / method / "validation" / f"{chart_id}.json", [err])
            return {
                "method": method,
                "chart_id": chart_id,
                "elapsed_sec": total_elapsed,
                "attempt_count": attempt,
                "schema_retry_count": attempt - 1,
                "validation_error_count": 1,
                "validation_errors": [err],
                "score": None,
                "method_input_forbidden_scan": scan_key_names(input_payload, ANSWER_SIDE_KEYS),
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
        v2_correct = sum(row["v2"]["correct"] for row in scored)
        v2_total = sum(row["v2"]["total"] for row in scored)
        strict_correct = sum(row["strict"]["correct"] for row in scored)
        strict_total = sum(row["strict"]["total"] for row in scored)
        families: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
        for row in rows:
            score_path = run_dir / method / "scores_v2_admin_gold" / f"{row['chart_id']}.json"
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
            "score_v2": {
                "correct": v2_correct,
                "total": v2_total,
                "accuracy": v2_correct / v2_total if v2_total else None,
            },
            "score_strict": {
                "correct": strict_correct,
                "total": strict_total,
                "accuracy": strict_correct / strict_total if strict_total else None,
            },
            "schema_retry_total": sum(row.get("schema_retry_count") or 0 for row in rows),
            "field_family": [
                {
                    "field": family,
                    "correct": value["correct"],
                    "total": value["total"],
                    "accuracy": value["correct"] / value["total"] if value["total"] else None,
                }
                for family, value in sorted(families.items())
            ],
        }
    return summaries


def format_percent(value: float | None) -> str:
    return "NA" if value is None else f"{value:.2%}"


def render_report(summary: dict[str, Any], no_leakage: dict[str, Any]) -> str:
    lines = [
        "# 实验组5 dev50 G 系列运行报告",
        "",
        f"- run_id: `{summary['run_id']}`",
        f"- admin gold answer: `{summary['admin_gold_answer']}`",
        f"- gold observable: `{summary['gold_observable']}`",
        f"- model: `{summary.get('model')}`",
        "",
        "## 结果",
        "",
        "| 方法 | schema-valid | retry | v2 正确/总数 | v2 accuracy | strict accuracy |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for method, item in summary["summaries"].items():
        lines.append(
            f"| `{method}` | {item['schema_valid']}/{item['samples_total']} | "
            f"{item.get('schema_retry_total', 0)} | "
            f"{item['score_v2']['correct']}/{item['score_v2']['total']} | "
            f"{format_percent(item['score_v2']['accuracy'])} | {format_percent(item['score_strict']['accuracy'])} |"
        )
    lines.extend(
        [
            "",
            "## 输入边界",
            "",
            "- `G0_Direct` 使用后台 `field_reviews` 中 `support_mode=direct_visible` 的人工审核字段关系，属于 direct-visible oracle replay。",
            "- `G1_Rules` 使用后台 `direct_visible + rule_default_completion` 的人工审核字段关系，属于 rules-completion oracle replay。",
            "- `G3_LLM_Rules` 只使用去答案字段后的 `gold_observable` 和 prompt 里的规则说明。",
            "- 评分统一使用 `admin_gold_answer_dev50.jsonl`。",
            "",
            "## 审查",
            "",
            f"- G3 method input forbidden key hits: `{no_leakage['g3_method_input_forbidden_key_hits']}`",
            f"- G0/G1 answer-side oracle usage recorded: `{no_leakage['g0_g1_oracle_answer_usage_recorded']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Experiment 5 dev50 G-series methods from admin artifacts.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--admin-gold-answer", type=Path, default=ADMIN_GOLD_ANSWER)
    parser.add_argument("--admin-field-review", type=Path, default=ADMIN_FIELD_REVIEW)
    parser.add_argument("--gold-observable", type=Path, default=GOLD_OBSERVABLE_ACCEPT_PENDING)
    parser.add_argument("--methods", default="G0_Direct,G1_Rules,G3_LLM_Rules")
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--request-timeout", type=int, default=240)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--schema-retry-count", type=int, default=1)
    parser.add_argument(
        "--resume-existing",
        action="store_true",
        help="Reuse completed per-chart outputs that already have validation and score files.",
    )
    args = parser.parse_args()

    methods = [item.strip() for item in args.methods.split(",") if item.strip()]
    unknown = sorted(set(methods) - METHODS)
    if unknown:
        raise ValueError(f"Unknown methods: {unknown}")

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    policies = load_policy(POLICY_V2)
    gold_rows = read_jsonl(args.admin_gold_answer)
    targets = {row["chart_id"]: row["annotation_pr28_json"] for row in gold_rows}
    field_reviews_by_chart: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(args.admin_field_review):
        field_reviews_by_chart[row["chart_id"]].append(row)
    observables = {row["chart_id"]: row for row in read_jsonl(args.gold_observable)}
    chart_ids = [row["chart_id"] for row in gold_rows]

    if "G3_LLM_Rules" in methods:
        model_list = get_json(model_api_url(args.base_url, "models"), timeout=10)
        available = [item.get("id") for item in model_list.get("data", []) if isinstance(item, dict)]
        if args.model not in available:
            raise RuntimeError(f"Model {args.model!r} not exposed by {args.base_url}; available={available}")

    run_manifest = {
        "run_id": args.run_dir.name,
        "methods": methods,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "admin_gold_answer": rel(args.admin_gold_answer),
        "admin_gold_answer_sha256": sha256_file(args.admin_gold_answer),
        "admin_field_review": rel(args.admin_field_review),
        "admin_field_review_sha256": sha256_file(args.admin_field_review),
        "gold_observable": rel(args.gold_observable),
        "gold_observable_sha256": sha256_file(args.gold_observable),
        "schema": rel(SCHEMA_PATH),
        "policy_v2": rel(POLICY_V2),
        "model": args.model if "G3_LLM_Rules" in methods else None,
        "base_url": args.base_url if "G3_LLM_Rules" in methods else None,
        "max_workers": args.max_workers if "G3_LLM_Rules" in methods else None,
        "schema_retry_count": args.schema_retry_count if "G3_LLM_Rules" in methods else None,
    }
    write_json(args.run_dir / "run_manifest_g_admin.json", run_manifest)

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for method in [item for item in methods if item in {"G0_Direct", "G1_Rules"}]:
        for chart_id in chart_ids:
            target = targets[chart_id]
            existing = load_existing_result(
                method=method,
                chart_id=chart_id,
                run_dir=args.run_dir,
                score_dir="scores_v2_admin_gold",
            )
            if args.resume_existing and existing is not None:
                results.append(existing)
                print(f"{method} {chart_id} reused", flush=True)
            else:
                pred, diagnostics = build_oracle_prediction(
                    method=method,
                    chart_id=chart_id,
                    procedure=target["procedure"],
                    reviews=field_reviews_by_chart[chart_id],
                )
                errors = validate_canonical(pred, validator)
                write_json(args.run_dir / method / "canonical_json" / f"{chart_id}.json", pred)
                write_json(args.run_dir / method / "diagnostics" / f"{chart_id}.json", diagnostics)
                write_json(args.run_dir / method / "validation" / f"{chart_id}.json", errors)
                score = None
                if errors:
                    failures.append({"method": method, "chart_id": chart_id, "error": errors})
                else:
                    score = score_and_write(
                        method=method,
                        chart_id=chart_id,
                        pred=pred,
                        target=target,
                        policies=policies,
                        run_dir=args.run_dir,
                    )
                results.append(
                    {
                        "method": method,
                        "chart_id": chart_id,
                        "validation_error_count": len(errors),
                        "validation_errors": errors,
                        "score": score,
                    }
                )
                print(f"{method} {chart_id}", flush=True)

    if "G3_LLM_Rules" in methods:
        futures = {}
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            for chart_id in chart_ids:
                existing = load_existing_result(
                    method="G3_LLM_Rules",
                    chart_id=chart_id,
                    run_dir=args.run_dir,
                    score_dir="scores_v2_admin_gold",
                )
                if args.resume_existing and existing is not None:
                    results.append(existing)
                    print(f"G3_LLM_Rules {chart_id} reused", flush=True)
                    continue
                futures[
                    executor.submit(
                        run_g3_one,
                        args=args,
                        chart_id=chart_id,
                        procedure=targets[chart_id]["procedure"],
                        observable=observables[chart_id],
                        target=targets[chart_id],
                        policies=policies,
                        schema=schema,
                        validator=validator,
                    )
                ] = chart_id
            for future in as_completed(futures):
                chart_id = futures[future]
                try:
                    row = future.result()
                    results.append(row)
                    if row.get("validation_error_count"):
                        failures.append(
                            {
                                "method": "G3_LLM_Rules",
                                "chart_id": chart_id,
                                "error": row.get("validation_errors"),
                            }
                        )
                    print(f"G3_LLM_Rules {chart_id}", flush=True)
                except Exception as exc:  # noqa: BLE001
                    failures.append({"method": "G3_LLM_Rules", "chart_id": chart_id, "error": repr(exc)})
                    print(f"G3_LLM_Rules {chart_id} failed: {repr(exc)}", flush=True)

    write_jsonl(args.run_dir / "reports" / "g_admin_results.jsonl", results)
    write_jsonl(args.run_dir / "reports" / "g_admin_failures.jsonl", failures)
    no_leakage = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "g0_g1_oracle_answer_usage_recorded": any(method in methods for method in ["G0_Direct", "G1_Rules"]),
        "g0_g1_note": "G0/G1 intentionally replay audited admin field-review relations; this is oracle diagnostic, not a blind predictor.",
        "g3_uses_admin_gold_answer_for_prediction": False,
        "g3_uses_field_review_for_prediction": False,
        "g3_method_input_forbidden_key_hits": sum(
            (row.get("method_input_forbidden_scan") or {}).get("hit_count", 0)
            for row in results
            if row.get("method") == "G3_LLM_Rules"
        ),
    }
    write_json(args.run_dir / "reports" / "g_admin_no_leakage_report.json", no_leakage)
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_dir.name,
        "methods": methods,
        "chart_ids": chart_ids,
        "admin_gold_answer": rel(args.admin_gold_answer),
        "admin_field_review": rel(args.admin_field_review),
        "gold_observable": rel(args.gold_observable),
        "model": args.model if "G3_LLM_Rules" in methods else None,
        "base_url": args.base_url if "G3_LLM_Rules" in methods else None,
        "summaries": summarize(results, args.run_dir),
        "failure_count": len(failures),
        "failures": failures,
    }
    write_json(args.run_dir / "reports" / "g_admin_summary.json", summary)
    write_text(args.run_dir / "reports" / "experiment5_g_admin_execution_report_zh.md", render_report(summary, no_leakage))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
