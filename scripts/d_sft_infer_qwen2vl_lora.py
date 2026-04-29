from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from jsonschema import Draft202012Validator
from peft import PeftModel
from PIL import Image
from transformers import AutoProcessor, BitsAndBytesConfig, Qwen2VLForConditionalGeneration


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from c3_questionnaire_to_canonical import QUESTION_FIELDS  # noqa: E402


DEFAULT_CONFIG = ROOT / "training" / "d_sft" / "configs" / "d_sft_training_config.candidate.json"
DEFAULT_OUTPUT_ROOT = Path("E:/experiment3/d_sft")
DEFAULT_PILOT100 = (
    Path("E:/experiment3/try_B1_B1'")
    / "data"
    / "pilot100_external"
    / "pilot100_external_manifest.jsonl"
)
DEFAULT_SCHEMA = ROOT / "schemas" / "missed_approach_leg.schema.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + ("\n" if value and not value.endswith("\n") else ""), encoding="utf-8")


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows = []
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


def strict_json(text: str) -> dict[str, Any]:
    if "```" in text:
        raise ValueError("markdown_code_fence_not_allowed")
    return json.loads(text.strip())


def dependency_versions() -> dict[str, Any]:
    packages = ["torch", "transformers", "peft", "bitsandbytes", "Pillow", "jsonschema"]
    versions: dict[str, Any] = {"python": sys.version}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def validate_canonical(obj: dict[str, Any], validator: Draft202012Validator) -> list[str]:
    errors = sorted(validator.iter_errors(obj), key=lambda err: list(err.path))
    messages = []
    for err in errors:
        loc = ".".join(str(p) for p in err.path) or "$"
        messages.append(f"{loc}: {err.message}")
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

    pred_legs = {leg.get("leg_index"): leg for leg in pred.get("missed_approach", {}).get("legs", [])}
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
    messages = image_prompt_messages(image_path, prompt_text)
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
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


def resolve_target(row: dict[str, Any]) -> Path:
    return Path(row.get("canonical_proxy_gt_file") or row.get("target_path"))


def run_inference(
    *,
    config: dict[str, Any],
    checkpoint: Path,
    manifest: Path,
    schema_path: Path,
    output_root: Path,
    run_id: str,
    limit: int | None,
    sample_role: str,
) -> dict[str, Any]:
    rows = read_jsonl(manifest, limit)
    prompt_path = Path(config["data"]["prompt_path"])
    prompt_text = prompt_path.read_text(encoding="utf-8").strip()
    assistant_prefill = str(config.get("output_control", {}).get("assistant_prefill") or "")
    schema = read_json(schema_path)
    validator = Draft202012Validator(schema)
    run_dir = output_root / "predictions" / run_id
    if run_dir.exists():
        raise RuntimeError(f"Prediction run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)

    model, processor = load_model(config, checkpoint)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for row in rows:
        sample_id = row.get("pilot_sample_id") or row.get("sample_id")
        chart_id = row["chart_id"]
        image_path = Path(row["image_path"])
        target_path = resolve_target(row)
        item: dict[str, Any] = {
            "method": "D_SFT",
            "sample_id": sample_id,
            "chart_id": chart_id,
            "image_path": str(image_path.resolve()),
            "target_used_only_after_prediction": True,
            "json_extraction_policy": "strict_json_only",
            "validation_error_count": None,
            "score": None,
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
            pred = strict_json(text)
            write_json(run_dir / "canonical_json" / f"{chart_id}.json", pred)
            validation_errors = validate_canonical(pred, validator)
            write_json(run_dir / "validation" / f"{chart_id}.json", validation_errors)
            item["validation_error_count"] = len(validation_errors)
            item["validation_errors"] = validation_errors
            if validation_errors:
                failures.append(
                    {
                        "sample_id": sample_id,
                        "chart_id": chart_id,
                        "stage": "schema_validation",
                        "error": validation_errors[0],
                    }
                )
            else:
                target = read_json(target_path)
                score = score_canonical(pred, target)
                write_json(run_dir / "scores" / f"{chart_id}.json", score)
                item["score"] = {key: score[key] for key in ["correct", "total", "accuracy"]}
        except Exception as exc:
            write_text(run_dir / "parse_or_infer_errors" / f"{chart_id}.txt", repr(exc))
            item["failure"] = repr(exc)
            failures.append({"sample_id": sample_id, "chart_id": chart_id, "stage": "inference_or_parse", "error": repr(exc)})
        results.append(item)

    scored = [item["score"] for item in results if item.get("score")]
    correct = sum(item["correct"] for item in scored)
    total = sum(item["total"] for item in scored)
    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "method_id": "D_SFT",
        "checkpoint": str(checkpoint.resolve()),
        "checkpoint_role": "selected_by_d_sft_dev_only",
        "sample_manifest": str(manifest.resolve()),
        "sample_role": sample_role,
        "input_boundary": {
            "inference_input": ["full_chart_image", "frozen_d_sft_prompt"],
            "forbidden_inference_inputs": [
                "OCR_text",
                "field_candidates",
                "CIFP_raw_record",
                "target_JSON",
                "score_file",
                "human_answer",
                "other_method_prediction",
            ],
            "target_used_only_after_prediction_for_scoring": True,
        },
        "prompt": {"path": str(prompt_path.resolve()), "sha256": sha256_file(prompt_path)},
        "schema": {"path": str(schema_path.resolve()), "sha256": sha256_file(schema_path)},
        "parser_policy": {
            "strict_json_only": True,
            "code_fence_stripping_allowed": False,
            "semantic_repair_allowed": False,
            "retry_policy": "no_selective_retry; this script performs no retry",
            "assistant_prefill": assistant_prefill,
        },
        "samples_total": len(rows),
        "schema_valid": sum(1 for item in results if item.get("validation_error_count") == 0),
        "samples_scored": len(scored),
        "parse_or_schema_failures": len(failures),
        "score": {"correct": correct, "total": total, "accuracy": correct / total if total else None},
        "results": results,
        "failures": failures,
        "dependency_versions": dependency_versions(),
    }
    write_json(run_dir / "summary_report.json", summary)
    write_json(output_root / "reports" / f"{run_id}_summary_report.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run D-SFT image-only inference on pilot100_external.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_PILOT100)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sample-role", default="pilot100_external_heldout_feasibility_only_not_formal300")
    args = parser.parse_args()

    config = read_json(args.config)
    run_id = args.run_id or f"d_sft_pilot100_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    summary = run_inference(
        config=config,
        checkpoint=args.checkpoint,
        manifest=args.manifest,
        schema_path=args.schema,
        output_root=args.output_root,
        run_id=run_id,
        limit=args.limit,
        sample_role=args.sample_role,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not summary["failures"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"D-SFT inference failed: {exc!r}", file=sys.stderr)
        raise
