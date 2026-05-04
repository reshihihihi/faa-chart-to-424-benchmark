from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from PIL import Image
from transformers import AutoProcessor, BitsAndBytesConfig, Qwen2VLForConditionalGeneration


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATHS = ROOT / "training" / "group1_sft" / "configs" / "local_paths.local.json"

METHOD_CONFIG = {
    "D1_DEV50_ONLY": {
        "train_key": "d1_dev50_train_jsonl",
        "dev_key": "d1_dev50_dev_jsonl",
        "input_boundary": ["full_chart_image", "canonical_prompt"],
        "label_source": "development_only_field_reviews_canonical",
    },
    "D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL": {
        "train_key": "d1_evidence_boxes_train_jsonl",
        "dev_key": "d1_evidence_boxes_dev_jsonl",
        "initial_adapter_key": "d1_dev50_lora_or_checkpoint_dir",
        "input_boundary": ["full_chart_image", "evidence_boxes_then_canonical_prompt"],
        "label_source": "development_only_human_regions_plus_field_reviews",
    },
    "CHART_TO_EVIDENCE_SFT": {
        "train_key": "chart_to_evidence_train_jsonl",
        "dev_key": "chart_to_evidence_dev_jsonl",
        "input_boundary": ["full_chart_image", "chart_to_evidence_prompt"],
        "label_source": "human_confirmed_visible_evidence_regions_development_only",
    },
    "EVIDENCE_TO_SEMANTICS_SFT": {
        "train_key": "evidence_to_semantics_train_jsonl",
        "dev_key": "evidence_to_semantics_dev_jsonl",
        "input_boundary": ["human_confirmed_visible_evidence_record", "evidence_to_questionnaire_prompt"],
        "label_source": "human_reviewed_semantic_questionnaire_development_only",
    },
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dependency_versions() -> dict[str, Any]:
    packages = ["torch", "transformers", "peft", "bitsandbytes", "Pillow", "jsonschema"]
    versions: dict[str, Any] = {"python": sys.version}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_path(value: str, *, repo_root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return repo_root / path


def text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(part for part in parts if part)
    raise ValueError("Unsupported message content shape")


def image_from_content(content: Any) -> Path | None:
    if not isinstance(content, list):
        return None
    for item in content:
        if isinstance(item, dict) and item.get("type") == "image":
            image = item.get("image")
            if image:
                return Path(str(image))
    return None


def extract_training_parts(row: dict[str, Any], assistant_prefill: str) -> tuple[Path | None, str, str]:
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        raise ValueError(f"Missing training messages in sample {row.get('sample_id')}")
    user_message = messages[0]
    assistant_message = messages[1]
    user_content = user_message.get("content")
    image_path = image_from_content(user_content)
    prompt_text = text_from_content(user_content)
    assistant_text = str(assistant_message.get("content", ""))
    if "```" in assistant_text:
        raise ValueError(f"Assistant label contains markdown code fence in {row.get('sample_id')}")
    if assistant_prefill and not assistant_text.startswith(assistant_prefill):
        raise ValueError(f"Assistant label does not start with configured prefill in {row.get('sample_id')}")
    json.loads(assistant_text)
    return image_path, prompt_text, assistant_text


def build_messages(image_path: Path | None, prompt_text: str, assistant_text: str | None = None) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    if image_path is not None:
        content.append({"type": "image", "image": str(image_path)})
    content.append({"type": "text", "text": prompt_text})
    messages: list[dict[str, Any]] = [{"role": "user", "content": content}]
    if assistant_text is not None:
        messages.append({"role": "assistant", "content": assistant_text})
    return messages


def processor_call(processor: Any, text: str, image: Image.Image | None) -> dict[str, torch.Tensor]:
    kwargs: dict[str, Any] = {"text": [text], "padding": True, "return_tensors": "pt"}
    if image is not None:
        kwargs["images"] = [image]
    return processor(**kwargs)


def to_device(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {key: value.to(device) if torch.is_tensor(value) else value for key, value in batch.items()}


def make_batch(
    row: dict[str, Any],
    processor: Any,
    device: torch.device,
    max_seq_length: int,
    assistant_prefill: str,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    image_path, prompt_text, assistant_text = extract_training_parts(row, assistant_prefill)
    image = Image.open(image_path).convert("RGB") if image_path is not None else None

    full_messages = build_messages(image_path, prompt_text, assistant_text)
    prompt_messages = build_messages(image_path, prompt_text)
    full_text = processor.apply_chat_template(full_messages, tokenize=False, add_generation_prompt=False)
    prompt_only = processor.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)
    if assistant_prefill:
        prompt_only += assistant_prefill

    full_inputs = processor_call(processor, full_text, image)
    prompt_inputs = processor_call(processor, prompt_only, image)
    labels = full_inputs["input_ids"].clone()
    prompt_len = prompt_inputs["input_ids"].shape[1]
    labels[:, :prompt_len] = -100

    original_length = full_inputs["input_ids"].shape[1]
    truncated = original_length > max_seq_length
    if truncated:
        for key, value in list(full_inputs.items()):
            if torch.is_tensor(value) and value.ndim >= 2 and value.shape[1] == original_length:
                full_inputs[key] = value[:, :max_seq_length]
        labels = labels[:, :max_seq_length]
        if torch.all(labels == -100):
            raise ValueError(f"All labels were truncated away for {row.get('sample_id')}")

    full_inputs["labels"] = labels
    meta = {
        "sample_id": row.get("sample_id"),
        "chart_id": row.get("chart_id"),
        "has_image": image_path is not None,
        "image_path": str(image_path) if image_path is not None else None,
        "original_seq_length": original_length,
        "used_seq_length": min(original_length, max_seq_length),
        "prompt_length": prompt_len,
        "truncated": truncated,
    }
    if image is not None:
        image.close()
    return to_device(full_inputs, device), meta


def load_model_and_processor(args: argparse.Namespace, base_model_dir: Path) -> tuple[Any, Any]:
    dtype = torch.float16 if args.compute_dtype == "float16" else torch.bfloat16
    processor = AutoProcessor.from_pretrained(
        base_model_dir,
        local_files_only=args.local_files_only,
        min_pixels=args.min_pixels,
        max_pixels=args.max_pixels,
    )
    quant_cfg = None
    if args.load_in_4bit:
        quant_cfg = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type=args.bnb_4bit_quant_type,
            bnb_4bit_compute_dtype=dtype,
            bnb_4bit_use_double_quant=args.bnb_4bit_use_double_quant,
        )
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        base_model_dir,
        local_files_only=args.local_files_only,
        quantization_config=quant_cfg,
        device_map=args.device_map,
    )
    model.config.use_cache = False
    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()
    model = prepare_model_for_kbit_training(model)
    if args.initial_adapter_checkpoint:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, args.initial_adapter_checkpoint, is_trainable=True)
    else:
        peft_config = LoraConfig(
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=args.target_modules,
        )
        model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    return model, processor


@torch.no_grad()
def evaluate(
    *,
    model: Any,
    processor: Any,
    rows: list[dict[str, Any]],
    device: torch.device,
    max_seq_length: int,
    max_eval_samples: int,
    assistant_prefill: str,
) -> dict[str, Any]:
    model.eval()
    losses: list[float] = []
    metas: list[dict[str, Any]] = []
    for row in rows[:max_eval_samples]:
        batch, meta = make_batch(row, processor, device, max_seq_length, assistant_prefill)
        out = model(**batch)
        losses.append(float(out.loss.detach().cpu()))
        metas.append(meta)
        del batch, out
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    model.train()
    return {
        "samples": len(losses),
        "loss_mean": sum(losses) / len(losses) if losses else None,
        "losses": losses,
        "truncated_count": sum(1 for meta in metas if meta["truncated"]),
        "max_seq_length_seen": max((meta["original_seq_length"] for meta in metas), default=None),
    }


def train(args: argparse.Namespace) -> dict[str, Any]:
    method_cfg = METHOD_CONFIG[args.method]
    paths = read_json(args.paths)
    repo_root = resolve_path(paths.get("repo_root", str(ROOT)), repo_root=ROOT)
    base_model_dir = resolve_path(paths["base_vlm_model_dir"], repo_root=repo_root)
    train_jsonl = resolve_path(paths[method_cfg["train_key"]], repo_root=repo_root)
    dev_jsonl = resolve_path(paths[method_cfg["dev_key"]], repo_root=repo_root)
    initial_adapter_checkpoint = (
        resolve_path(str(args.initial_adapter_checkpoint), repo_root=repo_root)
        if args.initial_adapter_checkpoint
        else None
    )
    if initial_adapter_checkpoint is None and method_cfg.get("initial_adapter_key"):
        initial_adapter_checkpoint = resolve_path(paths[method_cfg["initial_adapter_key"]], repo_root=repo_root)
    if initial_adapter_checkpoint is not None and not initial_adapter_checkpoint.exists():
        raise RuntimeError(f"Initial adapter checkpoint does not exist: {initial_adapter_checkpoint}")
    args.initial_adapter_checkpoint = initial_adapter_checkpoint
    local_root = resolve_path(paths.get("local_root", str(paths["output_root"])), repo_root=repo_root)
    checkpoint_root = args.checkpoint_root or (local_root / "checkpoints" / args.method)
    reports_root = args.reports_root or (local_root / "reports")

    set_seed(args.seed)
    train_rows = read_jsonl(train_jsonl, args.train_limit)
    dev_rows = read_jsonl(dev_jsonl, args.dev_limit)
    if not train_rows:
        raise RuntimeError(f"No training rows loaded for {args.method}.")
    if not dev_rows:
        raise RuntimeError(f"No dev rows loaded for {args.method}.")

    run_id = args.run_id or f"{args.method.lower()}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    run_dir = checkpoint_root / run_id
    report_dir = reports_root / run_id
    if run_dir.exists() and not args.overwrite:
        raise RuntimeError(f"Checkpoint run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=args.overwrite)
    report_dir.mkdir(parents=True, exist_ok=True)

    model, processor = load_model_and_processor(args, base_model_dir)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    optimizer = torch.optim.AdamW(
        [param for param in model.parameters() if param.requires_grad],
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
    )

    losses: list[dict[str, Any]] = []
    sample_metas: list[dict[str, Any]] = []
    best_dev_loss = math.inf
    best_checkpoint = None
    global_step = 0
    optimizer_step = 0
    model.train()
    optimizer.zero_grad(set_to_none=True)

    for epoch in range(1, args.epochs + 1):
        random.shuffle(train_rows)
        for index, row in enumerate(train_rows, start=1):
            batch, meta = make_batch(row, processor, device, args.max_seq_length, args.assistant_prefill)
            out = model(**batch)
            loss = out.loss / args.gradient_accumulation_steps
            loss.backward()
            global_step += 1
            sample_metas.append(meta)
            losses.append(
                {
                    "epoch": epoch,
                    "sample_index": index,
                    "sample_id": meta["sample_id"],
                    "chart_id": meta["chart_id"],
                    "loss": float(out.loss.detach().cpu()),
                    "truncated": meta["truncated"],
                    "original_seq_length": meta["original_seq_length"],
                    "used_seq_length": meta["used_seq_length"],
                }
            )
            del batch, out, loss
            if global_step % args.gradient_accumulation_steps == 0 or index == len(train_rows):
                torch.nn.utils.clip_grad_norm_(
                    [param for param in model.parameters() if param.requires_grad],
                    args.max_grad_norm,
                )
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                optimizer_step += 1
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        eval_report = evaluate(
            model=model,
            processor=processor,
            rows=dev_rows,
            device=device,
            max_seq_length=args.max_seq_length,
            max_eval_samples=args.checkpoint_selection_dev_samples,
            assistant_prefill=args.assistant_prefill,
        )
        checkpoint_dir = run_dir / f"checkpoint-epoch{epoch:02d}"
        model.save_pretrained(checkpoint_dir)
        processor.save_pretrained(checkpoint_dir)
        if eval_report["loss_mean"] is not None and eval_report["loss_mean"] < best_dev_loss:
            best_dev_loss = eval_report["loss_mean"]
            best_checkpoint = str(checkpoint_dir.resolve())
        write_json(report_dir / f"dev_eval_epoch{epoch:02d}.json", eval_report)

    final_dir = run_dir / "checkpoint-final"
    model.save_pretrained(final_dir)
    processor.save_pretrained(final_dir)
    write_json(report_dir / "training_losses.json", losses)
    report = {
        "schema": "group1_sft_lora_training_report_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "method_id": args.method,
        "run_id": run_id,
        "base_model_dir": str(base_model_dir),
        "initial_adapter_checkpoint": str(initial_adapter_checkpoint) if initial_adapter_checkpoint else None,
        "initial_adapter_checkpoint_exists": initial_adapter_checkpoint.exists() if initial_adapter_checkpoint else None,
        "train_jsonl": {"path": str(train_jsonl), "rows": len(train_rows), "sha256": sha256_file(train_jsonl)},
        "dev_jsonl": {"path": str(dev_jsonl), "rows": len(dev_rows), "sha256": sha256_file(dev_jsonl)},
        "input_boundary": {
            "training_forward_input": method_cfg["input_boundary"],
            "assistant_label_source": method_cfg["label_source"],
            "forbidden_training_sources": [
                "evaluation_200_labels",
                "probe_50_labels",
                "scorer_output",
                "other_method_predictions",
                "raw_424_record",
                "raw_cifp_record",
            ],
        },
        "output_control": {
            "assistant_prefill": args.assistant_prefill,
            "parser_repair_allowed": False,
        },
        "epochs": args.epochs,
        "global_steps": global_step,
        "optimizer_steps": optimizer_step,
        "truncated_train_samples": sum(1 for meta in sample_metas if meta["truncated"]),
        "max_train_seq_length_seen": max((meta["original_seq_length"] for meta in sample_metas), default=None),
        "best_dev_loss": None if best_dev_loss is math.inf else best_dev_loss,
        "best_checkpoint": best_checkpoint or str(final_dir.resolve()),
        "final_checkpoint": str(final_dir.resolve()),
        "lora": {
            "r": args.lora_r,
            "lora_alpha": args.lora_alpha,
            "lora_dropout": args.lora_dropout,
            "target_modules": args.target_modules,
        },
        "training": {
            "seed": args.seed,
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "gradient_accumulation_steps": args.gradient_accumulation_steps,
            "max_grad_norm": args.max_grad_norm,
            "max_seq_length": args.max_seq_length,
            "compute_dtype": args.compute_dtype,
            "load_in_4bit": args.load_in_4bit,
        },
        "cuda": {
            "available": torch.cuda.is_available(),
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "max_memory_allocated_gb": round(torch.cuda.max_memory_allocated() / 1024**3, 4)
            if torch.cuda.is_available()
            else None,
        },
        "dependency_versions": dependency_versions(),
    }
    write_json(report_dir / "training_report.json", report)
    write_json(reports_root / f"{run_id}_training_report.json", report)
    del model, processor
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Train Group 1 SFT Qwen2-VL LoRA adapters.")
    parser.add_argument("--method", required=True, choices=sorted(METHOD_CONFIG))
    parser.add_argument("--paths", type=Path, default=DEFAULT_PATHS)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--checkpoint-root", type=Path, default=None)
    parser.add_argument("--reports-root", type=Path, default=None)
    parser.add_argument("--initial-adapter-checkpoint", type=Path, default=None)
    parser.add_argument("--train-limit", type=int, default=None)
    parser.add_argument("--dev-limit", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=260503)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--weight-decay", type=float, default=0.0)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--max-seq-length", type=int, default=4096)
    parser.add_argument("--checkpoint-selection-dev-samples", type=int, default=10)
    parser.add_argument("--assistant-prefill", default="{")
    parser.add_argument("--min-pixels", type=int, default=3136)
    parser.add_argument("--max-pixels", type=int, default=501760)
    parser.add_argument("--compute-dtype", choices=["float16", "bfloat16"], default="float16")
    parser.add_argument("--load-in-4bit", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--bnb-4bit-quant-type", default="nf4")
    parser.add_argument("--bnb-4bit-use-double-quant", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--local-files-only", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--gradient-checkpointing", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--lora-r", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument(
        "--target-modules",
        nargs="+",
        default=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    report = train(args)
    print(
        json.dumps(
            {
                "method_id": report["method_id"],
                "run_id": report["run_id"],
                "train_rows": report["train_jsonl"]["rows"],
                "dev_rows": report["dev_jsonl"]["rows"],
                "best_dev_loss": report["best_dev_loss"],
                "final_checkpoint": report["final_checkpoint"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
