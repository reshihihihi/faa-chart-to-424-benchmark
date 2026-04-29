from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic
from jsonschema import Draft202012Validator

from c3_questionnaire_to_canonical import QUESTION_FIELDS, questionnaire_to_canonical


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "benchmark_exports" / "derived" / "v2" / "pilot10_external"
RUN_DIR = ROOT / "local_runs" / "pilot10_exp1_a1_b1_c3_v0"
PROMPT_DIR = ROOT / "prompts" / "paper_v2"
SCHEMA_PATH = ROOT / "schemas" / "missed_approach_leg.schema.json"

OCR_PROMPT = PROMPT_DIR / "ocr_full_chart_text.zh_v1_candidate.md"
B1_PROMPT = PROMPT_DIR / "b1_ocr_to_canonical_pilot10.zh_v1_candidate.md"
C3_PROMPT = PROMPT_DIR / "c3_questionnaire_pilot10.zh_v1_candidate.md"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def resolve_package_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    prefix = Path("benchmark_exports") / "derived" / "v2" / "pilot10_external"
    try:
        rel = path.relative_to(prefix)
        return DATA_DIR / rel
    except ValueError:
        return ROOT / path


def fill_prompt(template: str, row: dict[str, Any], *, ocr_text: str | None = None) -> str:
    replacements = {
        "{{chart_id}}": row["chart_id"],
        "{{airport}}": row["airport"],
        "{{approach_ident}}": row["proc_ident"],
        "{{chart_name}}": row["chart_name"],
        "{{ocr_text}}": ocr_text or "",
        "{{chart_image}}": str(resolve_package_path(row["image_path"])),
    }
    for key, value in replacements.items():
        template = template.replace(key, str(value))
    return template


def get_client() -> anthropic.Anthropic:
    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    base_url = os.environ.get("ANTHROPIC_BASE_URL")
    if not auth_token and not api_key:
        raise RuntimeError(
            "Missing ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY environment variable."
        )
    kwargs: dict[str, Any] = {}
    if auth_token:
        kwargs["auth_token"] = auth_token
    else:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url
    return anthropic.Anthropic(**kwargs)


def image_block(path: Path) -> dict[str, Any]:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": data,
        },
    }


def call_model(
    client: anthropic.Anthropic,
    *,
    model: str,
    prompt: str,
    image_path: Path | None,
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
        messages=[{"role": "user", "content": content}],
    )
    text_parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
    return "\n".join(text_parts).strip(), response


def parse_strict_json(text: str) -> dict[str, Any]:
    return json.loads(text)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + ("\n" if value and not value.endswith("\n") else ""), encoding="utf-8")


def _iter_answer_objects(obj: Any, path: str = ""):
    if isinstance(obj, dict):
        if "status" in obj and "value" in obj:
            yield path or "$", obj
        for key, value in obj.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield from _iter_answer_objects(value, child_path)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _iter_answer_objects(value, f"{path}[{index}]")


def validate_canonical_semantics(obj: dict[str, Any]) -> list[str]:
    if not isinstance(obj, dict) or "missed_approach" not in obj:
        return []

    messages: list[str] = []
    missed = obj.get("missed_approach", {})
    legs = missed.get("legs", []) if isinstance(missed, dict) else []
    leg_count = missed.get("leg_count", {}) if isinstance(missed, dict) else {}
    if isinstance(leg_count, dict) and leg_count.get("status") == "present" and leg_count.get("value") != len(legs):
        messages.append(
            "missed_approach.leg_count: present value must equal len(missed_approach.legs)"
        )

    if isinstance(legs, list):
        for expected_index, leg in enumerate(legs, start=1):
            if isinstance(leg, dict) and leg.get("leg_index") != expected_index:
                messages.append(
                    f"missed_approach.legs[{expected_index - 1}].leg_index: expected {expected_index}"
                )

    for path, answer in _iter_answer_objects(obj):
        status = answer.get("status")
        value = answer.get("value")
        if status != "present" and value is not None:
            messages.append(f"{path}: value must be null when status is {status!r}")
        if status == "present" and value is None:
            messages.append(f"{path}: value must be non-null when status is 'present'")
        if status == "present" and isinstance(value, str) and value.strip().lower() in {
            "unknown",
            "not_observable",
            "not applicable",
            "n/a",
        }:
            messages.append(f"{path}: present value must not contain a status word")
    return messages


def validate_canonical(obj: dict[str, Any], validator: Draft202012Validator) -> list[str]:
    errors = sorted(validator.iter_errors(obj), key=lambda err: list(err.path))
    messages = []
    for err in errors:
        loc = ".".join(str(p) for p in err.path) or "$"
        messages.append(f"{loc}: {err.message}")
    messages.extend(validate_canonical_semantics(obj))
    return messages


def score_answer(pred: Any, target: Any) -> bool:
    return pred == target


def score_canonical(pred: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    rows = []
    total = 0
    correct = 0

    pred_leg_count = pred.get("missed_approach", {}).get("leg_count")
    target_leg_count = target.get("missed_approach", {}).get("leg_count")
    ok = score_answer(pred_leg_count, target_leg_count)
    rows.append({"field": "leg_count", "correct": ok, "pred": pred_leg_count, "target": target_leg_count})
    total += 1
    correct += int(ok)

    pred_legs = {
        leg.get("leg_index"): leg for leg in pred.get("missed_approach", {}).get("legs", [])
    }
    target_legs = target.get("missed_approach", {}).get("legs", [])
    for target_leg in target_legs:
        idx = target_leg["leg_index"]
        pred_leg = pred_legs.get(idx, {})
        pred_answers = pred_leg.get("answers", {})
        target_answers = target_leg.get("answers", {})
        for field in QUESTION_FIELDS:
            pred_answer = pred_answers.get(field)
            target_answer = target_answers.get(field)
            ok = score_answer(pred_answer, target_answer)
            rows.append(
                {
                    "field": f"leg_{idx}.{field}",
                    "correct": ok,
                    "pred": pred_answer,
                    "target": target_answer,
                }
            )
            total += 1
            correct += int(ok)

    return {
        "correct": correct,
        "total": total,
        "accuracy": correct / total if total else None,
        "rows": rows,
    }


def save_raw_response(path: Path, response: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(response, "model_dump_json"):
        path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
    else:
        path.write_text(str(response), encoding="utf-8")


def ensure_a1_not_run() -> None:
    message = """# A1 Not Run

A1 requires a frozen OCR+Rules runner. This pilot package does not currently contain a
frozen A1 rules implementation. A1 is intentionally not executed by
`scripts/run_pilot10_anthropic.py` to avoid inventing an unfrozen baseline.
"""
    write_text(RUN_DIR / "A1" / "NOT_RUN_A1.md", message.rstrip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pilot10 OCR, B1, and C3 via Anthropic-compatible API.")
    parser.add_argument("--model", default=os.environ.get("ANTHROPIC_MODEL", "default"))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens-ocr", type=int, default=4096)
    parser.add_argument("--max-tokens-b1", type=int, default=4096)
    parser.add_argument("--max-tokens-c3", type=int, default=4096)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ensure_a1_not_run()

    manifest_path = DATA_DIR / "pilot10_manifest.jsonl"
    rows = read_jsonl(manifest_path)[: args.limit]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    run_manifest = {
        "run_id": "pilot10_exp1_a1_b1_c3_v0",
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
            },
            "c3": {
                "path": str(C3_PROMPT.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(C3_PROMPT),
            },
        },
        "parser": {
            "c3_questionnaire_to_canonical": "scripts/c3_questionnaire_to_canonical.py",
            "semantic_repair": False,
        },
        "strict_json_parse": True,
        "samples": [row["pilot_sample_id"] for row in rows],
    }
    write_json(RUN_DIR / "run_manifest.json", run_manifest)

    if args.dry_run:
        print(f"Dry run prepared {len(rows)} samples.")
        return 0

    client = get_client()
    ocr_template = OCR_PROMPT.read_text(encoding="utf-8")
    b1_template = B1_PROMPT.read_text(encoding="utf-8")
    c3_template = C3_PROMPT.read_text(encoding="utf-8")

    overall_scores: dict[str, list[dict[str, Any]]] = {"B1": [], "C3": []}
    failures: list[dict[str, str]] = []

    for row in rows:
        sample_id = row["pilot_sample_id"]
        chart_id = row["chart_id"]
        image_path = resolve_package_path(row["image_path"])
        target_path = resolve_package_path(row["canonical_proxy_gt_file"])
        target = json.loads(target_path.read_text(encoding="utf-8"))

        print(f"Running {sample_id} {chart_id}")

        ocr_text_path = RUN_DIR / "OCR" / "full_chart_text" / f"{chart_id}.txt"
        if args.skip_existing and ocr_text_path.exists():
            ocr_text = ocr_text_path.read_text(encoding="utf-8")
        else:
            prompt = fill_prompt(ocr_template, row)
            try:
                ocr_text, ocr_response = call_model(
                    client,
                    model=args.model,
                    prompt=prompt,
                    image_path=image_path,
                    max_tokens=args.max_tokens_ocr,
                    temperature=args.temperature,
                )
                write_text(ocr_text_path, ocr_text)
                save_raw_response(RUN_DIR / "OCR" / "raw_responses" / f"{chart_id}.json", ocr_response)
            except Exception as exc:
                failures.append({"sample_id": sample_id, "method": "OCR", "error": repr(exc)})
                continue

        b1_out = RUN_DIR / "B1" / "canonical_json" / f"{chart_id}.json"
        if not (args.skip_existing and b1_out.exists()):
            prompt = fill_prompt(b1_template, row, ocr_text=ocr_text)
            try:
                b1_text, b1_response = call_model(
                    client,
                    model=args.model,
                    prompt=prompt,
                    image_path=None,
                    max_tokens=args.max_tokens_b1,
                    temperature=args.temperature,
                )
                write_text(RUN_DIR / "B1" / "raw_text" / f"{chart_id}.txt", b1_text)
                save_raw_response(RUN_DIR / "B1" / "raw_responses" / f"{chart_id}.json", b1_response)
                b1_json = parse_strict_json(b1_text)
                write_json(b1_out, b1_json)
                validation_errors = validate_canonical(b1_json, validator)
                write_json(RUN_DIR / "B1" / "validation" / f"{chart_id}.json", validation_errors)
                if not validation_errors:
                    score = score_canonical(b1_json, target)
                    write_json(RUN_DIR / "B1" / "scores" / f"{chart_id}.json", score)
                    overall_scores["B1"].append({"chart_id": chart_id, **{k: score[k] for k in ["correct", "total", "accuracy"]}})
                else:
                    failures.append({"sample_id": sample_id, "method": "B1", "error": "schema_validation_failed"})
            except Exception as exc:
                write_text(RUN_DIR / "B1" / "parse_errors" / f"{chart_id}.txt", repr(exc))
                failures.append({"sample_id": sample_id, "method": "B1", "error": repr(exc)})

        c3_questionnaire_path = RUN_DIR / "C3" / "questionnaire_json" / f"{chart_id}.json"
        c3_canonical_path = RUN_DIR / "C3" / "canonical_json" / f"{chart_id}.json"
        if not (args.skip_existing and c3_questionnaire_path.exists()):
            prompt = fill_prompt(c3_template, row)
            try:
                c3_text, c3_response = call_model(
                    client,
                    model=args.model,
                    prompt=prompt,
                    image_path=image_path,
                    max_tokens=args.max_tokens_c3,
                    temperature=args.temperature,
                )
                write_text(RUN_DIR / "C3" / "raw_text" / f"{chart_id}.txt", c3_text)
                save_raw_response(RUN_DIR / "C3" / "raw_responses" / f"{chart_id}.json", c3_response)
                questionnaire = parse_strict_json(c3_text)
                write_json(c3_questionnaire_path, questionnaire)
                canonical = questionnaire_to_canonical(questionnaire)
                write_json(c3_canonical_path, canonical)
                validation_errors = validate_canonical(canonical, validator)
                write_json(RUN_DIR / "C3" / "validation" / f"{chart_id}.json", validation_errors)
                if not validation_errors:
                    score = score_canonical(canonical, target)
                    write_json(RUN_DIR / "C3" / "scores" / f"{chart_id}.json", score)
                    overall_scores["C3"].append({"chart_id": chart_id, **{k: score[k] for k in ["correct", "total", "accuracy"]}})
                else:
                    failures.append({"sample_id": sample_id, "method": "C3", "error": "schema_validation_failed"})
            except Exception as exc:
                write_text(RUN_DIR / "C3" / "parse_errors" / f"{chart_id}.txt", repr(exc))
                failures.append({"sample_id": sample_id, "method": "C3", "error": repr(exc)})

    summary: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scores": {},
        "failures": failures,
    }
    for method, items in overall_scores.items():
        correct = sum(item["correct"] for item in items)
        total = sum(item["total"] for item in items)
        summary["scores"][method] = {
            "samples_scored": len(items),
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total else None,
            "per_sample": items,
        }
    write_json(RUN_DIR / "summary_report.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
