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
from PIL import Image
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoProcessor, BitsAndBytesConfig, Qwen2VLForConditionalGeneration


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "training" / "d_sft" / "configs" / "d_sft_training_config.candidate.json"
DEFAULT_OUTPUT_ROOT = Path("E:/experiment3/d_sft")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def dependency_versions() -> dict[str, Any]:
    packages = ["torch", "transformers", "peft", "bitsandbytes", "Pillow", "jsonschema"]
    versions: dict[str, Any] = {"python": sys.version}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def extract_training_parts(row: dict[str, Any]) -> tuple[Path, str, str]:
    messages = row["messages"]
    user_content = messages[0]["content"]
    image_path = None
    prompt_text = None
    for item in user_content:
        if item["type"] == "image":
            image_path = Path(item["image"])
        elif item["type"] == "text":
            prompt_text = item["text"]
    assistant_text = messages[1]["content"]
    if image_path is None or prompt_text is None:
        raise ValueError(f"Missing image or prompt in sample {row.get('sample_id')}")
    if "```" in assistant_text:
        raise ValueError(f"Assistant label contains markdown code fence in {row.get('sample_id')}")
    json.loads(assistant_text)
    return image_path, prompt_text, assistant_text


def build_messages(image_path: Path, prompt_text: str, assistant_text: str | None = None) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": str(image_path)},
                {"type": "text", "text": prompt_text},
            ],
        }
    ]
    if assistant_text is not None:
        messages.append({"role": "assistant", "content": assistant_text})
    return messages


def tensor_to_device(value: Any, device: torch.device) -> Any:
    if torch.is_tensor(value):
        return value.to(device)
    return value


def make_batch(
    row: dict[str, Any],
    processor: Any,
    device: torch.device,
    max_seq_length: int,
    assistant_prefill: str,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    image_path, prompt_text, assistant_text = extract_training_parts(row)
    image = Image.open(image_path).convert("RGB")

    full_messages = build_messages(image_path, prompt_text, assistant_text)
    prompt_messages = build_messages(image_path, prompt_text)
    full_text = processor.apply_chat_template(full_messages, tokenize=False, add_generation_prompt=False)
    prompt_text_only = processor.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)
    if assistant_prefill:
        if not assistant_text.startswith(assistant_prefill):
            raise ValueError(f"Assistant label does not start with configured prefill for {row.get('sample_id')}")
        prompt_text_only += assistant_prefill

    full_inputs = processor(text=[full_text], images=[image], padding=True, return_tensors="pt")
    prompt_inputs = processor(text=[prompt_text_only], images=[image], padding=True, return_tensors="pt")
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
    full_inputs = {key: tensor_to_device(value, device) for key, value in full_inputs.items()}
    meta = {
        "sample_id": row.get("sample_id"),
        "image_path": str(image_path),
        "original_seq_length": original_length,
        "used_seq_length": min(original_length, max_seq_length),
        "prompt_length": prompt_len,
        "truncated": truncated,
    }
    return full_inputs, meta


def load_model_and_processor(config: dict[str, Any]) -> tuple[Any, Any]:
    model_cfg = config["model"]
    image_cfg = config["image"]
    train_cfg = config["training"]
    dtype = torch.float16 if train_cfg.get("compute_dtype", "float16") == "float16" else torch.bfloat16
    processor = AutoProcessor.from_pretrained(
        model_cfg["base_model_id"],
        local_files_only=model_cfg.get("local_files_only", True),
        min_pixels=image_cfg["min_pixels"],
        max_pixels=image_cfg["max_pixels"],
    )
    quant_cfg = None
    if model_cfg.get("load_in_4bit", True):
        quant_cfg = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type=model_cfg.get("bnb_4bit_quant_type", "nf4"),
            bnb_4bit_compute_dtype=dtype,
            bnb_4bit_use_double_quant=model_cfg.get("bnb_4bit_use_double_quant", True),
        )
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        model_cfg["base_model_id"],
        local_files_only=model_cfg.get("local_files_only", True),
        quantization_config=quant_cfg,
        device_map=model_cfg.get("device_map", "auto"),
    )
    model.config.use_cache = False
    if train_cfg.get("gradient_checkpointing", True):
        model.gradient_checkpointing_enable()
    model = prepare_model_for_kbit_training(model)
    lora_cfg = config["lora"]
    peft_config = LoraConfig(
        r=lora_cfg["r"],
        lora_alpha=lora_cfg["lora_alpha"],
        lora_dropout=lora_cfg["lora_dropout"],
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=lora_cfg["target_modules"],
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


def train(config: dict[str, Any], *, dry_run: bool, run_id: str | None, output_root: Path) -> dict[str, Any]:
    set_seed(config["training"]["seed"])
    train_rows = read_jsonl(Path(config["data"]["train_jsonl"]), config["dry_run"]["train_samples"] if dry_run else None)
    dev_rows = read_jsonl(Path(config["data"]["dev_jsonl"]), config["dry_run"]["dev_samples"] if dry_run else None)
    if not train_rows:
        raise RuntimeError("No D-SFT training rows loaded.")
    if not dev_rows:
        raise RuntimeError("No D-SFT dev rows loaded.")

    run_kind = "dry_run" if dry_run else "formal_train"
    run_id = run_id or f"d_sft_{run_kind}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    run_dir = output_root / "checkpoints" / run_id
    log_dir = output_root / "logs" / run_id
    report_dir = output_root / "reports" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    log_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    model, processor = load_model_and_processor(config)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    max_seq_length = int(config["training"]["max_seq_length"])
    assistant_prefill = str(config.get("output_control", {}).get("assistant_prefill") or "")
    lr = float(config["training"]["learning_rate"])
    grad_accum = int(config["training"]["gradient_accumulation_steps"])
    epochs = int(config["dry_run"]["epochs"] if dry_run else config["training"]["epochs"])
    max_eval_samples = int(config["dry_run"]["dev_samples"] if dry_run else config["training"]["checkpoint_selection_dev_samples"])
    optimizer = torch.optim.AdamW(
        [param for param in model.parameters() if param.requires_grad],
        lr=lr,
        weight_decay=float(config["training"]["weight_decay"]),
    )

    losses: list[dict[str, Any]] = []
    sample_metas: list[dict[str, Any]] = []
    best_dev_loss = math.inf
    best_checkpoint = None
    global_step = 0
    optimizer_step = 0
    model.train()
    optimizer.zero_grad(set_to_none=True)

    for epoch in range(1, epochs + 1):
        random.shuffle(train_rows)
        for index, row in enumerate(train_rows, start=1):
            batch, meta = make_batch(row, processor, device, max_seq_length, assistant_prefill)
            out = model(**batch)
            loss = out.loss / grad_accum
            loss.backward()
            global_step += 1
            sample_metas.append(meta)
            losses.append(
                {
                    "epoch": epoch,
                    "sample_index": index,
                    "sample_id": meta["sample_id"],
                    "loss": float(out.loss.detach().cpu()),
                    "truncated": meta["truncated"],
                    "original_seq_length": meta["original_seq_length"],
                    "used_seq_length": meta["used_seq_length"],
                }
            )
            del batch, out, loss
            if global_step % grad_accum == 0 or index == len(train_rows):
                torch.nn.utils.clip_grad_norm_(
                    [param for param in model.parameters() if param.requires_grad],
                    float(config["training"]["max_grad_norm"]),
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
            max_seq_length=max_seq_length,
            max_eval_samples=max_eval_samples,
            assistant_prefill=assistant_prefill,
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
    write_json(log_dir / "training_losses.json", losses)
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "run_kind": run_kind,
        "method_id": "D_SFT",
        "input_boundary": {
            "training_forward_input": ["full_chart_image", "frozen_d_sft_prompt"],
            "assistant_label_source": "CIFP_to_canonical_proxy_label_train_dev_only",
            "forbidden_training_sources": [
                "formal300",
                "pilot10",
                "pilot100_external",
                "OCR_text",
                "field_candidates",
                "scorer_output",
                "other_method_predictions",
            ],
            "inference_input": ["full_chart_image", "frozen_d_sft_prompt"],
        },
        "config": config,
        "output_control": {
            "assistant_prefill": assistant_prefill,
            "purpose": "force generation to continue as a bare JSON object without parser repair",
        },
        "config_sha256": sha256_file(Path(config["_config_path"])) if config.get("_config_path") else None,
        "train_jsonl_sha256": sha256_file(Path(config["data"]["train_jsonl"])),
        "dev_jsonl_sha256": sha256_file(Path(config["data"]["dev_jsonl"])),
        "train_samples": len(train_rows),
        "dev_samples": len(dev_rows),
        "epochs": epochs,
        "global_steps": global_step,
        "optimizer_steps": optimizer_step,
        "truncated_train_samples": sum(1 for meta in sample_metas if meta["truncated"]),
        "max_train_seq_length_seen": max((meta["original_seq_length"] for meta in sample_metas), default=None),
        "best_dev_loss": None if best_dev_loss is math.inf else best_dev_loss,
        "best_checkpoint": best_checkpoint or str(final_dir.resolve()),
        "final_checkpoint": str(final_dir.resolve()),
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
    write_json(output_root / "reports" / f"{run_id}_training_report.json", report)
    del model, processor
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Train D-SFT Qwen2-VL LoRA with image-only inference boundary.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = read_json(args.config)
    config["_config_path"] = str(args.config.resolve())
    report = train(config, dry_run=args.dry_run, run_id=args.run_id, output_root=args.output_root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"D-SFT training failed: {exc!r}", file=sys.stderr)
        raise
