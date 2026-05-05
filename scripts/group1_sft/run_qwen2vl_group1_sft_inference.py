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
JOINT_EVIDENCE_CANONICAL_METHODS = {"D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL"}


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


def iter_json_object_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    stack = 0
    start: int | None = None
    in_string = False
    escaped = False
    for i, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if stack == 0:
                start = i
            stack += 1
        elif char == "}" and stack > 0:
            stack -= 1
            if stack == 0 and start is not None:
                spans.append((start, i + 1))
                start = None
    return spans


def parse_last_schema_valid_json_object(
    text: str,
    *,
    validator: Any | None,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    spans = iter_json_object_spans(text)
    candidates: list[tuple[int, dict[str, Any], list[str]]] = []
    schema_valid_candidates: list[tuple[int, dict[str, Any]]] = []
    for index, (start, end) in enumerate(spans):
        try:
            parsed = json.loads(text[start:end])
        except Exception:
            continue
        if not isinstance(parsed, dict):
            continue
        errors = validation_errors(parsed, validator)
        candidates.append((index, parsed, errors))
        if not errors:
            schema_valid_candidates.append((index, parsed))
    if schema_valid_candidates:
        index, parsed = schema_valid_candidates[-1]
        return parsed, {
            "json_object_candidate_extraction_applied": True,
            "json_object_candidate_count": len(spans),
            "json_object_candidate_selected_index": index,
            "json_object_candidate_selection_rule": "last_schema_valid_complete_object",
        }
    if not candidates:
        return None
    index, parsed, errors = candidates[-1]
    return parsed, {
        "json_object_candidate_extraction_applied": True,
        "json_object_candidate_count": len(spans),
        "json_object_candidate_selected_index": index,
        "json_object_candidate_selection_rule": "last_parseable_complete_object_no_schema_valid_candidate",
        "json_object_candidate_schema_errors": errors[:5],
    }


def delimiter_balance_outside_strings(text: str) -> dict[str, int]:
    balances = {"curly": 0, "square": 0}
    in_string = False
    escaped = False
    for char in text:
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            balances["curly"] += 1
        elif char == "}":
            balances["curly"] -= 1
        elif char == "[":
            balances["square"] += 1
        elif char == "]":
            balances["square"] -= 1
    return balances


def parse_model_output(
    text: str,
    *,
    method: str,
    allow_single_missing_final_object_brace: bool,
    allow_json_object_candidate_extraction: bool,
    validator: Any | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    parse_event: dict[str, Any] = {
        "strict_json_parse_ok": False,
        "single_missing_final_object_brace_applied": False,
        "json_object_candidate_extraction_applied": False,
        "semantic_repair_applied": False,
    }
    try:
        parsed = strict_json(text)
        parse_event["strict_json_parse_ok"] = True
        return parsed, parse_event
    except Exception as strict_exc:  # noqa: BLE001
        parse_event["strict_json_error"] = repr(strict_exc)
        if allow_json_object_candidate_extraction and "```" not in text:
            candidate = parse_last_schema_valid_json_object(text, validator=validator)
            if candidate is not None:
                parsed, extraction_event = candidate
                parse_event.update(extraction_event)
                return parsed, parse_event
        if (
            not allow_single_missing_final_object_brace
            or method not in JOINT_EVIDENCE_CANONICAL_METHODS
            or "```" in text
        ):
            raise

    stripped = text.strip()
    balances = delimiter_balance_outside_strings(stripped)
    parse_event["delimiter_balance_before_closure"] = balances
    if balances != {"curly": 1, "square": 0}:
        raise ValueError(
            "single_missing_final_object_brace_not_applicable: "
            f"curly_balance={balances['curly']} square_balance={balances['square']}"
        )
    if not stripped.startswith("{") or not stripped.endswith("}"):
        raise ValueError("single_missing_final_object_brace_not_applicable: output_boundary_mismatch")

    parsed = json.loads(stripped + "}")
    if not isinstance(parsed, dict):
        raise ValueError("model_output_is_not_json_object")
    schema_errors = validation_errors(parsed, validator)
    if schema_errors:
        raise ValueError("single_missing_final_object_brace_candidate_schema_invalid: " + schema_errors[0])
    parse_event["single_missing_final_object_brace_applied"] = True
    parse_event["mechanical_closure_added"] = "}"
    return parsed, parse_event


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


def canonical_prediction_for_scoring(parsed: dict[str, Any], method: str, *, expect_wrapper: bool) -> dict[str, Any]:
    if method in JOINT_EVIDENCE_CANONICAL_METHODS and expect_wrapper:
        canonical = parsed.get("canonical_prediction")
        if not isinstance(canonical, dict):
            raise ValueError("canonical_prediction_is_missing_or_not_object")
        return canonical
    return parsed


def evidence_box_count(parsed: dict[str, Any], method: str, *, expect_wrapper: bool) -> int | None:
    if method not in JOINT_EVIDENCE_CANONICAL_METHODS or not expect_wrapper:
        return None
    boxes = parsed.get("evidence_boxes")
    return len(boxes) if isinstance(boxes, list) else None


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
    repetition_penalty: float,
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
        repetition_penalty=repetition_penalty,
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
    expect_wrapper = args.output_mode == "wrapper" or (
        args.output_mode == "auto" and args.method in JOINT_EVIDENCE_CANONICAL_METHODS
    )
    validator = load_schema_validator(args.json_schema)
    canonical_validator = (
        load_schema_validator(args.canonical_json_schema) if expect_wrapper else None
    )
    model, processor = load_model(args)
    assistant_prefill = args.assistant_prefill
    if assistant_prefill is None:
        assistant_prefill = CHART_TO_EVIDENCE_PREFILL if args.method == "CHART_TO_EVIDENCE_SFT" else JSON_OBJECT_PREFILL

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []
    valid_predictions: list[dict[str, Any]] = []
    parser_events: list[dict[str, Any]] = []
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
                repetition_penalty=args.repetition_penalty,
            )
            write_text(run_dir / "raw_text" / f"{chart_id}.txt", text)
            parsed, parser_event = parse_model_output(
                text,
                method=args.method,
                allow_single_missing_final_object_brace=args.allow_single_missing_final_object_brace,
                allow_json_object_candidate_extraction=args.allow_json_object_candidate_extraction,
                validator=validator,
            )
            parser_event["sample_id"] = sample_id
            parser_event["chart_id"] = chart_id
            parser_events.append(parser_event)
            write_json(run_dir / "parser_logs" / f"{chart_id}.json", parser_event)
            item["parser"] = {
                "strict_json_parse_ok": parser_event["strict_json_parse_ok"],
                "single_missing_final_object_brace_applied": parser_event[
                    "single_missing_final_object_brace_applied"
                ],
                "json_object_candidate_extraction_applied": parser_event[
                    "json_object_candidate_extraction_applied"
                ],
            }
            write_json(run_dir / "parsed_json" / f"{chart_id}.json", parsed)
            errors = validation_errors(parsed, validator)
            canonical_prediction = canonical_prediction_for_scoring(parsed, args.method, expect_wrapper=expect_wrapper)
            if expect_wrapper:
                write_json(run_dir / "canonical_json" / f"{chart_id}.json", canonical_prediction)
                canonical_errors = validation_errors(canonical_prediction, canonical_validator)
                errors.extend([f"canonical_prediction.{error}" for error in canonical_errors])
                item["evidence_box_count"] = evidence_box_count(parsed, args.method, expect_wrapper=expect_wrapper)
            write_json(run_dir / "validation" / f"{chart_id}.json", errors)
            item["validation_error_count"] = len(errors)
            item["validation_errors"] = errors
            if errors:
                failures.append({"sample_id": sample_id, "chart_id": chart_id, "stage": "schema_validation", "error": errors[0]})
            else:
                valid_predictions.append(
                    {"sample_id": sample_id, "chart_id": chart_id, "parsed": canonical_prediction, "item": item}
                )
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
        "canonical_json_schema": str(args.canonical_json_schema)
        if expect_wrapper
        else None,
        "scoring_manifest": str(args.scoring_manifest) if args.scoring_manifest else None,
        "comparison_policy": str(args.comparison_policy) if args.scoring_manifest else None,
        "parser_policy": {
            "strict_json_only": not (
                args.allow_single_missing_final_object_brace or args.allow_json_object_candidate_extraction
            ),
            "strict_json_attempted_first": True,
            "code_fence_stripping_allowed": False,
            "single_missing_final_object_brace_closure_allowed": args.allow_single_missing_final_object_brace,
            "single_missing_final_object_brace_closure_scope": (
                "D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL_only"
                if args.allow_single_missing_final_object_brace
                else None
            ),
            "json_object_candidate_extraction_allowed": args.allow_json_object_candidate_extraction,
            "json_object_candidate_extraction_policy": (
                "after strict JSON failure, parse complete JSON object candidates from model output "
                "and select the last candidate that validates against the active output schema"
                if args.allow_json_object_candidate_extraction
                else None
            ),
            "semantic_repair_allowed": False,
            "assistant_prefill": assistant_prefill,
            "output_mode": args.output_mode,
            "joint_output_canonical_extraction": expect_wrapper,
            "repetition_penalty": args.repetition_penalty,
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
        "parser_event_counts": {
            "strict_json_parse_ok": sum(1 for event in parser_events if event.get("strict_json_parse_ok")),
            "single_missing_final_object_brace_applied": sum(
                1 for event in parser_events if event.get("single_missing_final_object_brace_applied")
            ),
            "json_object_candidate_extraction_applied": sum(
                1 for event in parser_events if event.get("json_object_candidate_extraction_applied")
            ),
            "semantic_repair_applied": sum(1 for event in parser_events if event.get("semantic_repair_applied")),
        },
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
    parser.add_argument(
        "--method",
        required=True,
        choices=[
            "D_BASE_SAME_BACKBONE",
            "D1",
            "CHART_TO_EVIDENCE_SFT",
            "D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL",
        ],
    )
    parser.add_argument("--input-manifest", required=True, type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--adapter-checkpoint", type=Path, default=None)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--json-schema", type=Path, default=None)
    parser.add_argument("--canonical-json-schema", type=Path, default=ROOT / "schemas" / "missed_approach_leg.schema.json")
    parser.add_argument("--scoring-manifest", type=Path, default=None)
    parser.add_argument("--comparison-policy", type=Path, default=ROOT / "benchmark_exports" / "derived" / "v2" / "formal300" / "targets" / "scoring_equivalence_v2" / "comparison_policy_v2.jsonl")
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--assistant-prefill", default=None)
    parser.add_argument(
        "--output-mode",
        choices=["auto", "wrapper", "canonical"],
        default="auto",
        help=(
            "Use wrapper for the joint evidence method by default. Use canonical to score the "
            "D1 evidence-trained checkpoint with the unchanged D1 canonical JSON output."
        ),
    )
    parser.add_argument("--max-new-tokens", type=int, default=1536)
    parser.add_argument("--repetition-penalty", type=float, default=1.0)
    parser.add_argument(
        "--allow-single-missing-final-object-brace",
        action="store_true",
        help=(
            "For the joint evidence-box-plus-canonical method only, allow one pre-registered "
            "mechanical closure when strict JSON parsing fails solely because the final outer "
            "object brace is missing. The candidate must pass the wrapper schema before scoring."
        ),
    )
    parser.add_argument(
        "--allow-json-object-candidate-extraction",
        action="store_true",
        help=(
            "After strict JSON parsing fails, mechanically scan complete JSON object candidates "
            "from the model output and use the last candidate that validates against the active "
            "schema. This does not use targets, scores, raw 424/CIFP records, or other method "
            "predictions."
        ),
    )
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
