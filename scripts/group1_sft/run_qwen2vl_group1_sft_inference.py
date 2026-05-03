from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCORER_DIR = ROOT / "scripts" / "scorers"
sys.path.insert(0, str(SCORER_DIR))

JSON_OBJECT_PREFILL = "{"
CHART_TO_EVIDENCE_PREFILL = '{"chart_id":null,"evidence_items":[{'


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + ("\n" if value and not value.endswith("\n") else ""), encoding="utf-8")


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def repo_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def strict_json(text: str) -> dict[str, Any]:
    if "```" in text:
        raise ValueError("markdown_code_fence_not_allowed")
    parsed = json.loads(text.strip())
    if not isinstance(parsed, dict):
        raise ValueError("model_output_is_not_json_object")
    return parsed


def dependency_versions() -> dict[str, Any]:
    packages = ["torch", "transformers", "peft", "bitsandbytes", "Pillow", "jsonschema"]
    versions: dict[str, Any] = {"python": sys.version}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def image_path_from_row(row: dict[str, Any]) -> Path:
    image = row.get("image")
    if isinstance(image, dict) and image.get("path"):
        return repo_path(str(image["path"]))
    if row.get("image_path"):
        return repo_path(str(row["image_path"]))
    raise ValueError(f"Missing image path for {row.get('sample_id') or row.get('chart_id')}")


def load_schema_validator(schema_path: Path | None):
    if schema_path is None:
        return None
    from jsonschema import Draft202012Validator

    return Draft202012Validator(read_json(schema_path))


def validation_errors(obj: dict[str, Any], validator: Any | None) -> list[str]:
    if validator is None:
        return []
    errors = sorted(validator.iter_errors(obj), key=lambda err: list(err.path))
    return [(".".join(str(part) for part in err.path) or "$") + f": {err.message}" for err in errors]


def load_targets(scoring_manifest: Path | None) -> dict[str, Path]:
    if scoring_manifest is None:
        return {}
    targets: dict[str, Path] = {}
    for row in read_jsonl(scoring_manifest):
        target = row.get("target")
        if isinstance(target, dict) and target.get("path"):
            targets[row["chart_id"]] = repo_path(str(target["path"]))
    return targets


def load_scorer(policy_path: Path | None):
    if policy_path is None:
        return None, None
    from group1_canonical_field_scorer_v2 import load_policy, score_canonical

    return load_policy(policy_path), score_canonical


def load_model(args: argparse.Namespace):
    import torch
    from transformers import AutoProcessor, BitsAndBytesConfig, Qwen2VLForConditionalGeneration

    dtype = torch.float16 if args.compute_dtype == "float16" else torch.bfloat16
    quant_cfg = None
    if args.load_in_4bit:
        quant_cfg = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type=args.bnb_4bit_quant_type,
            bnb_4bit_compute_dtype=dtype,
            bnb_4bit_use_double_quant=args.bnb_4bit_use_double_quant,
        )
    processor_source = args.model_dir
    if args.adapter_checkpoint and (args.adapter_checkpoint / "preprocessor_config.json").exists():
        processor_source = args.adapter_checkpoint
    processor = AutoProcessor.from_pretrained(
        processor_source,
        local_files_only=args.local_files_only,
        min_pixels=args.min_pixels,
        max_pixels=args.max_pixels,
    )
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        args.model_dir,
        local_files_only=args.local_files_only,
        quantization_config=quant_cfg,
        device_map=args.device_map,
    )
    if args.adapter_checkpoint:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, args.adapter_checkpoint)
    model.eval()
    return model, processor


def build_messages(image_path: Path, prompt_text: str) -> list[dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": str(image_path)},
                {"type": "text", "text": prompt_text},
            ],
        }
    ]


def infer_one(
    *,
    model: Any,
    processor: Any,
    image_path: Path,
    prompt_text: str,
    max_new_tokens: int,
    assistant_prefill: str,
) -> str:
    import torch
    from PIL import Image

    image = Image.open(image_path).convert("RGB")
    messages = build_messages(image_path, prompt_text)
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


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(args.input_manifest, args.limit)
    prompt_text = args.prompt.read_text(encoding="utf-8").strip()
    run_id = args.run_id or f"{args.method}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    run_dir = args.output_root / "predictions" / run_id
    if run_dir.exists() and not args.overwrite:
        raise RuntimeError(f"Prediction run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=args.overwrite)
    validator = load_schema_validator(args.json_schema)
    model, processor = load_model(args)
    assistant_prefill = args.assistant_prefill
    if assistant_prefill is None:
        assistant_prefill = CHART_TO_EVIDENCE_PREFILL if args.method == "CHART_TO_EVIDENCE_SFT" else JSON_OBJECT_PREFILL

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []
    valid_predictions: list[dict[str, Any]] = []
    for row in rows:
        sample_id = row.get("sample_id")
        chart_id = row["chart_id"]
        image_path = image_path_from_row(row)
        item: dict[str, Any] = {
            "method": args.method,
            "sample_id": sample_id,
            "chart_id": chart_id,
            "image_path": str(image_path),
            "score": None,
            "validation_error_count": None,
        }
        try:
            text = infer_one(
                model=model,
                processor=processor,
                image_path=image_path,
                prompt_text=prompt_text,
                max_new_tokens=args.max_new_tokens,
                assistant_prefill=assistant_prefill,
            )
            write_text(run_dir / "raw_text" / f"{chart_id}.txt", text)
            parsed = strict_json(text)
            write_json(run_dir / "parsed_json" / f"{chart_id}.json", parsed)
            errors = validation_errors(parsed, validator)
            write_json(run_dir / "validation" / f"{chart_id}.json", errors)
            item["validation_error_count"] = len(errors)
            item["validation_errors"] = errors
            if errors:
                failures.append({"sample_id": sample_id, "chart_id": chart_id, "stage": "schema_validation", "error": errors[0]})
            else:
                valid_predictions.append({"sample_id": sample_id, "chart_id": chart_id, "parsed": parsed, "item": item})
        except Exception as exc:  # noqa: BLE001
            err = repr(exc)
            write_text(run_dir / "errors" / f"{chart_id}.txt", err)
            item["failure"] = err
            failures.append({"sample_id": sample_id, "chart_id": chart_id, "stage": "inference_or_parse", "error": err})
        results.append(item)

    if args.scoring_manifest:
        targets = load_targets(args.scoring_manifest)
        policies, score_canonical = load_scorer(args.comparison_policy)
        for prediction in valid_predictions:
            chart_id = prediction["chart_id"]
            if chart_id in targets and policies is not None and score_canonical is not None:
                target = read_json(targets[chart_id])
                score = score_canonical(prediction["parsed"], target, chart_id=chart_id, policies=policies)
                write_json(run_dir / "scores" / f"{chart_id}.json", score)
                item = prediction["item"]
                item["score"] = {key: score[key] for key in ["correct", "total", "accuracy"]}
                score_rows.append({"sample_id": prediction["sample_id"], "chart_id": chart_id, **item["score"]})

    correct = sum(row["correct"] for row in score_rows)
    total = sum(row["total"] for row in score_rows)
    summary = {
        "schema": "group1_sft_qwen2vl_inference_summary_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "method_id": args.method,
        "input_manifest": str(args.input_manifest),
        "model_dir": str(args.model_dir),
        "adapter_checkpoint": str(args.adapter_checkpoint) if args.adapter_checkpoint else None,
        "prompt": str(args.prompt),
        "json_schema": str(args.json_schema) if args.json_schema else None,
        "scoring_manifest": str(args.scoring_manifest) if args.scoring_manifest else None,
        "comparison_policy": str(args.comparison_policy) if args.scoring_manifest else None,
        "parser_policy": {
            "strict_json_only": True,
            "code_fence_stripping_allowed": False,
            "semantic_repair_allowed": False,
            "assistant_prefill": assistant_prefill,
        },
        "input_boundary": {
            "target_used_for_prompt_or_parsing": False,
            "scoring_manifest_used_after_prediction_only": bool(args.scoring_manifest),
            "forbidden_inference_inputs": [
                "target_json",
                "raw_424_record",
                "score_file",
                "other_method_prediction",
                "human_answer",
            ],
        },
        "samples_total": len(rows),
        "samples_scored": len(score_rows),
        "failures": failures,
        "failure_count": len(failures),
        "score": {"correct": correct, "total": total, "accuracy": correct / total if total else None},
        "results": results,
        "dependency_versions": dependency_versions(),
    }
    write_json(run_dir / "summary_report.json", summary)
    write_json(args.output_root / "summary_report.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Qwen2-VL inference for Group 1 SFT extension methods.")
    parser.add_argument("--method", required=True, choices=["D_BASE_SAME_BACKBONE", "D1", "CHART_TO_EVIDENCE_SFT"])
    parser.add_argument("--input-manifest", required=True, type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--adapter-checkpoint", type=Path, default=None)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--json-schema", type=Path, default=None)
    parser.add_argument("--scoring-manifest", type=Path, default=None)
    parser.add_argument("--comparison-policy", type=Path, default=ROOT / "benchmark_exports" / "derived" / "v2" / "formal300" / "targets" / "scoring_equivalence_v2" / "comparison_policy_v2.jsonl")
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--assistant-prefill", default=None)
    parser.add_argument("--max-new-tokens", type=int, default=1536)
    parser.add_argument("--min-pixels", type=int, default=3136)
    parser.add_argument("--max-pixels", type=int, default=501760)
    parser.add_argument("--compute-dtype", choices=["float16", "bfloat16"], default="float16")
    parser.add_argument("--load-in-4bit", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--bnb-4bit-quant-type", default="nf4")
    parser.add_argument("--bnb-4bit-use-double-quant", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--local-files-only", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    summary = run(args)
    print(
        json.dumps(
            {
                "run_id": summary["run_id"],
                "method_id": summary["method_id"],
                "samples_total": summary["samples_total"],
                "samples_scored": summary["samples_scored"],
                "failure_count": summary["failure_count"],
                "score": summary["score"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not summary["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
