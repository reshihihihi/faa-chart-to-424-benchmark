from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from peft import PeftModel
from PIL import Image
from transformers import AutoProcessor, BitsAndBytesConfig, Qwen2VLForConditionalGeneration


QUESTION_FIELDS = [
    "Q_terminator",
    "Q1_fix_ident",
    "Q2_altitude_constraint",
    "Q3_turn",
    "Q4_course_or_radial",
    "Q5_hold_params",
]

ALLOWED_STATUSES = {"present", "not_applicable", "not_observable"}
DEFAULT_CONFIG = Path("E:/experiment3/d_sft/configs/d1_50_final_v2_qwen2vl_lora_20260506_r1.local.json")
DEFAULT_OUTPUT_ROOT = Path("E:/experiment3/d_sft")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + ("\n" if value and not value.endswith("\n") else ""), encoding="utf-8")


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dependency_versions() -> dict[str, Any]:
    packages = ["torch", "transformers", "peft", "bitsandbytes", "Pillow"]
    versions: dict[str, Any] = {"python": sys.version}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
        if not isinstance(obj, dict):
            raise ValueError("decoded JSON is not an object")
        return obj
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start < 0:
        raise json.JSONDecodeError("No JSON object found", text, 0)
    depth = 0
    in_string = False
    escape = False
    for pos in range(start, len(text)):
        char = text[pos]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                obj = json.loads(text[start : pos + 1])
                if not isinstance(obj, dict):
                    raise ValueError("decoded JSON is not an object")
                return obj
    raise json.JSONDecodeError("No complete JSON object found", text, start)


def iter_answer_objects(obj: Any, path: str = ""):
    if isinstance(obj, dict):
        if "status" in obj and "value" in obj:
            yield path or "$", obj
        for key, value in obj.items():
            child = f"{path}.{key}" if path else str(key)
            yield from iter_answer_objects(value, child)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from iter_answer_objects(value, f"{path}[{index}]")


def validate_final_v2_semantics(obj: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    missed = obj.get("missed_approach")
    if not isinstance(missed, dict):
        return ["missed_approach missing or not an object"]
    leg_count = missed.get("leg_count")
    legs = missed.get("legs")
    if not isinstance(legs, list):
        messages.append("missed_approach.legs missing or not an array")
        legs = []
    if isinstance(leg_count, dict) and leg_count.get("status") == "present" and leg_count.get("value") != len(legs):
        messages.append("missed_approach.leg_count present value must equal len(legs)")
    for expected_index, leg in enumerate(legs, start=1):
        if not isinstance(leg, dict):
            messages.append(f"missed_approach.legs[{expected_index - 1}] not an object")
            continue
        if leg.get("leg_index") != expected_index:
            messages.append(f"missed_approach.legs[{expected_index - 1}].leg_index expected {expected_index}")
        answers = leg.get("answers")
        if not isinstance(answers, dict):
            messages.append(f"missed_approach.legs[{expected_index - 1}].answers missing or not an object")
            continue
        for field in QUESTION_FIELDS:
            if field not in answers:
                messages.append(f"missed_approach.legs[{expected_index - 1}].answers.{field} missing")
    for path, answer in iter_answer_objects(obj):
        status = answer.get("status")
        value = answer.get("value")
        if status not in ALLOWED_STATUSES:
            messages.append(f"{path}: status {status!r} not allowed in final-v2")
        if status == "present" and value is None:
            messages.append(f"{path}: present value must be non-null")
        if status != "present" and value is not None:
            messages.append(f"{path}: value must be null when status is {status!r}")
    return messages


def load_model(config: dict[str, Any], checkpoint: Path) -> tuple[Any, Any]:
    model_cfg = config["model"]
    train_cfg = config["training"]
    image_cfg = config["image"]
    dtype = torch.float16 if train_cfg.get("compute_dtype", "float16") == "float16" else torch.bfloat16
    quant_cfg = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type=model_cfg.get("bnb_4bit_quant_type", "nf4"),
        bnb_4bit_compute_dtype=dtype,
        bnb_4bit_use_double_quant=model_cfg.get("bnb_4bit_use_double_quant", True),
    )
    processor_source = checkpoint if (checkpoint / "preprocessor_config.json").exists() else model_cfg["base_model_id"]
    processor = AutoProcessor.from_pretrained(
        processor_source,
        local_files_only=model_cfg.get("local_files_only", True),
        min_pixels=image_cfg["min_pixels"],
        max_pixels=image_cfg["max_pixels"],
    )
    base_model = Qwen2VLForConditionalGeneration.from_pretrained(
        model_cfg["base_model_id"],
        local_files_only=model_cfg.get("local_files_only", True),
        quantization_config=quant_cfg,
        device_map=model_cfg.get("device_map", "auto"),
    )
    model = PeftModel.from_pretrained(base_model, checkpoint)
    model.eval()
    return model, processor


def image_prompt_messages(image_path: Path, prompt_text: str) -> list[dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": str(image_path)},
                {"type": "text", "text": prompt_text},
            ],
        }
    ]


@torch.no_grad()
def infer_one(
    *,
    model: Any,
    processor: Any,
    image_path: Path,
    prompt_text: str,
    max_new_tokens: int,
    assistant_prefill: str,
) -> str:
    image = Image.open(image_path).convert("RGB")
    text = processor.apply_chat_template(image_prompt_messages(image_path, prompt_text), tokenize=False, add_generation_prompt=True)
    text = text + assistant_prefill
    inputs = processor(text=[text], images=[image], padding=True, return_tensors="pt")
    device = next(model.parameters()).device
    inputs = {key: value.to(device) if torch.is_tensor(value) else value for key, value in inputs.items()}
    generated = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        pad_token_id=processor.tokenizer.pad_token_id,
        eos_token_id=processor.tokenizer.eos_token_id,
    )
    trimmed = generated[:, inputs["input_ids"].shape[1] :]
    generated_text = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
    return (assistant_prefill + generated_text).strip()


def run(args: argparse.Namespace) -> dict[str, Any]:
    config = read_json(args.config)
    prompt_path = Path(config["data"]["prompt_path"])
    prompt_text = prompt_path.read_text(encoding="utf-8").strip()
    assistant_prefill = str(config.get("output_control", {}).get("assistant_prefill") or "")
    rows = read_jsonl(args.manifest, args.limit)
    run_dir = args.output_root / "predictions" / args.run_id
    if run_dir.exists():
        raise RuntimeError(f"Prediction run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    model, processor = load_model(config, args.checkpoint)

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for row in rows:
        chart_id = row["chart_id"]
        image_path = Path(row["image_path"])
        item: dict[str, Any] = {
            "sample_id": row.get("sample_id"),
            "chart_id": chart_id,
            "image_path": str(image_path),
            "target_used": False,
        }
        try:
            text = infer_one(
                model=model,
                processor=processor,
                image_path=image_path,
                prompt_text=prompt_text,
                max_new_tokens=int(config["inference"]["max_new_tokens"]),
                assistant_prefill=assistant_prefill,
            )
            write_text(run_dir / "raw_text" / f"{chart_id}.txt", text)
            pred = extract_json_object(text)
            write_json(run_dir / "canonical_json" / f"{chart_id}.json", pred)
            validation_errors = validate_final_v2_semantics(pred)
            write_json(run_dir / "validation" / f"{chart_id}.json", validation_errors)
            item["parse_ok"] = True
            item["final_v2_validation_error_count"] = len(validation_errors)
            item["final_v2_validation_errors"] = validation_errors
            if validation_errors:
                failures.append(
                    {
                        "sample_id": row.get("sample_id"),
                        "chart_id": chart_id,
                        "stage": "final_v2_validation",
                        "error": validation_errors[0],
                    }
                )
        except Exception as exc:  # noqa: BLE001 - recorded as method failure.
            write_text(run_dir / "parse_or_infer_errors" / f"{chart_id}.txt", repr(exc))
            item["parse_ok"] = False
            item["failure"] = repr(exc)
            failures.append({"sample_id": row.get("sample_id"), "chart_id": chart_id, "stage": "inference_or_parse", "error": repr(exc)})
        results.append(item)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id,
        "method_id": "D1-50_FINAL_V2",
        "checkpoint": str(args.checkpoint.resolve()),
        "manifest": str(args.manifest.resolve()),
        "sample_role": args.sample_role,
        "input_boundary": {
            "inference_input": ["full_chart_image", "final_v2_d_prompt"],
            "forbidden_inference_inputs": [
                "target_JSON",
                "score_file",
                "raw_CIFP",
                "human_answer",
                "other_method_prediction",
                "comparison_policy",
            ],
            "target_used": False,
        },
        "prompt": {"path": str(prompt_path.resolve()), "sha256": sha256_file(prompt_path)},
        "config": {"path": str(args.config.resolve()), "sha256": sha256_file(args.config)},
        "checkpoint_adapter_sha256": sha256_file(args.checkpoint / "adapter_model.safetensors"),
        "parser_policy": {
            "extract_first_complete_json_object": True,
            "semantic_repair_allowed": False,
            "assistant_prefill": assistant_prefill,
        },
        "samples_total": len(rows),
        "parse_ok": sum(1 for item in results if item.get("parse_ok")),
        "final_v2_valid": sum(1 for item in results if item.get("final_v2_validation_error_count") == 0),
        "parse_or_final_v2_failures": len(failures),
        "results": results,
        "failures": failures,
        "dependency_versions": dependency_versions(),
    }
    write_json(run_dir / "summary_report.json", summary)
    write_json(args.output_root / "reports" / f"{args.run_id}_summary_report.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pure final-v2 D-SFT inference without reading targets or scores.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sample-role", default="formal300_evaluation")
    args = parser.parse_args()
    summary = run(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
