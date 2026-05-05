from __future__ import annotations

import argparse
import gc
import importlib.metadata
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "group1_sft"
sys.path.insert(0, str(SCRIPT_DIR))

from run_qwen2vl_group1_sft_inference import (  # noqa: E402
    CHART_TO_EVIDENCE_PREFILL,
    JSON_OBJECT_PREFILL,
    image_path_from_row,
    infer_one as infer_image_one,
    load_model as load_image_model,
    load_schema_validator,
    strict_json,
    validation_errors,
)
from run_qwen2vl_group1_sft_text_inference import (  # noqa: E402
    infer_one as infer_text_one,
    load_model as load_text_model,
    load_scorer,
    load_targets,
    normalize_questionnaire_schema,
    questionnaire_to_canonical,
)


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


def dependency_versions() -> dict[str, Any]:
    packages = ["torch", "transformers", "peft", "bitsandbytes", "Pillow", "jsonschema"]
    versions: dict[str, Any] = {"python": sys.version}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def model_args(
    *,
    model_dir: Path,
    adapter_checkpoint: Path | None,
    args: argparse.Namespace,
) -> argparse.Namespace:
    return argparse.Namespace(
        model_dir=model_dir,
        adapter_checkpoint=adapter_checkpoint,
        compute_dtype=args.compute_dtype,
        load_in_4bit=args.load_in_4bit,
        bnb_4bit_quant_type=args.bnb_4bit_quant_type,
        bnb_4bit_use_double_quant=args.bnb_4bit_use_double_quant,
        device_map=args.device_map,
        local_files_only=args.local_files_only,
        min_pixels=args.min_pixels,
        max_pixels=args.max_pixels,
    )


def stage2_messages(prompt_text: str, evidence_record: dict[str, Any]) -> list[dict[str, Any]]:
    evidence_text = json.dumps(evidence_record, ensure_ascii=False, separators=(",", ":"))
    text = prompt_text.strip() + "\n\n图上证据记录：\n" + evidence_text
    return [{"role": "user", "content": [{"type": "text", "text": text}]}]


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(args.input_manifest, args.limit)
    run_id = args.run_id or f"TWO_STAGE_AUTO_SFT_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    run_dir = args.output_root / "predictions" / run_id
    if run_dir.exists() and not args.overwrite:
        raise RuntimeError(f"Prediction run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=args.overwrite)

    chart_prompt = args.chart_to_evidence_prompt.read_text(encoding="utf-8").strip()
    semantics_prompt = args.evidence_to_semantics_prompt.read_text(encoding="utf-8").strip()
    evidence_validator = load_schema_validator(args.evidence_schema)
    questionnaire_validator = load_schema_validator(args.questionnaire_schema)
    stage1_assistant_prefill = args.stage1_assistant_prefill
    stage2_assistant_prefill = args.stage2_assistant_prefill
    if args.assistant_prefill is not None:
        stage1_assistant_prefill = stage1_assistant_prefill or args.assistant_prefill
        stage2_assistant_prefill = stage2_assistant_prefill or args.assistant_prefill
    stage1_assistant_prefill = stage1_assistant_prefill or CHART_TO_EVIDENCE_PREFILL
    stage2_assistant_prefill = stage2_assistant_prefill or JSON_OBJECT_PREFILL

    image_model, image_processor = load_image_model(
        model_args(
            model_dir=args.model_dir,
            adapter_checkpoint=args.chart_to_evidence_adapter_checkpoint,
            args=args,
        )
    )
    stage1_records: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for row in rows:
        sample_id = row.get("sample_id")
        chart_id = row["chart_id"]
        item: dict[str, Any] = {
            "method": "TWO_STAGE_AUTO_SFT",
            "sample_id": sample_id,
            "chart_id": chart_id,
            "stage1_validation_error_count": None,
            "stage2_validation_error_count": None,
            "score": None,
        }
        try:
            image_path = image_path_from_row(row)
            text = infer_image_one(
                model=image_model,
                processor=image_processor,
                image_path=image_path,
                prompt_text=chart_prompt,
                max_new_tokens=args.stage1_max_new_tokens,
                assistant_prefill=stage1_assistant_prefill,
            )
            write_text(run_dir / "stage1_raw_text" / f"{chart_id}.txt", text)
            evidence = strict_json(text)
            write_json(run_dir / "stage1_evidence_json" / f"{chart_id}.json", evidence)
            errors = validation_errors(evidence, evidence_validator)
            write_json(run_dir / "stage1_validation" / f"{chart_id}.json", errors)
            item["stage1_validation_error_count"] = len(errors)
            item["stage1_validation_errors"] = errors
            if errors:
                failures.append({"sample_id": sample_id, "chart_id": chart_id, "stage": "stage1_schema_validation", "error": errors[0]})
                item["failure"] = "stage1_schema_validation"
            else:
                stage1_records[chart_id] = {"row": row, "evidence": evidence, "item": item}
        except Exception as exc:  # noqa: BLE001
            err = repr(exc)
            write_text(run_dir / "stage1_errors" / f"{chart_id}.txt", err)
            item["failure"] = err
            failures.append({"sample_id": sample_id, "chart_id": chart_id, "stage": "stage1_inference_or_parse", "error": err})
        results.append(item)

    del image_model, image_processor
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass

    text_model, text_processor = load_text_model(
        model_args(
            model_dir=args.model_dir,
            adapter_checkpoint=args.evidence_to_semantics_adapter_checkpoint,
            args=args,
        )
    )
    score_rows: list[dict[str, Any]] = []
    valid_predictions: list[dict[str, Any]] = []
    result_by_chart = {item["chart_id"]: item for item in results}
    for chart_id, stage1 in stage1_records.items():
        row = stage1["row"]
        sample_id = row.get("sample_id")
        item = result_by_chart[chart_id]
        try:
            messages = stage2_messages(semantics_prompt, stage1["evidence"])
            text = infer_text_one(
                model=text_model,
                processor=text_processor,
                messages=messages,
                max_new_tokens=args.stage2_max_new_tokens,
                assistant_prefill=stage2_assistant_prefill,
            )
            write_text(run_dir / "stage2_raw_text" / f"{chart_id}.txt", text)
            questionnaire = strict_json(text)
            write_json(run_dir / "stage2_questionnaire_json" / f"{chart_id}.json", questionnaire)
            normalized_questionnaire, normalization_actions = normalize_questionnaire_schema(questionnaire)
            if normalization_actions:
                write_json(run_dir / "stage2_normalized_questionnaire_json" / f"{chart_id}.json", normalized_questionnaire)
                write_json(run_dir / "stage2_normalization" / f"{chart_id}.json", normalization_actions)
            errors = validation_errors(normalized_questionnaire, questionnaire_validator)
            write_json(run_dir / "stage2_validation" / f"{chart_id}.json", errors)
            item["stage2_validation_error_count"] = len(errors)
            item["stage2_validation_errors"] = errors
            item["stage2_normalization_action_count"] = len(normalization_actions)
            if errors:
                failures.append({"sample_id": sample_id, "chart_id": chart_id, "stage": "stage2_schema_validation", "error": errors[0]})
                item["failure"] = "stage2_schema_validation"
                continue
            canonical = questionnaire_to_canonical(row, normalized_questionnaire)
            write_json(run_dir / "canonical_json" / f"{chart_id}.json", canonical)
            valid_predictions.append({"sample_id": sample_id, "chart_id": chart_id, "canonical": canonical, "item": item})
        except Exception as exc:  # noqa: BLE001
            err = repr(exc)
            write_text(run_dir / "stage2_errors" / f"{chart_id}.txt", err)
            item["failure"] = err
            failures.append({"sample_id": sample_id, "chart_id": chart_id, "stage": "stage2_inference_or_parse", "error": err})

    if args.scoring_manifest:
        targets = load_targets(args.scoring_manifest)
        policies, score_canonical = load_scorer(args.comparison_policy)
        for prediction in valid_predictions:
            chart_id = prediction["chart_id"]
            if chart_id in targets and policies is not None and score_canonical is not None:
                target = read_json(targets[chart_id])
                score = score_canonical(prediction["canonical"], target, chart_id=chart_id, policies=policies)
                write_json(run_dir / "scores" / f"{chart_id}.json", score)
                item = prediction["item"]
                item["score"] = {key: score[key] for key in ["correct", "total", "accuracy"]}
                score_rows.append({"sample_id": prediction["sample_id"], "chart_id": chart_id, **item["score"]})

    correct = sum(row["correct"] for row in score_rows)
    total = sum(row["total"] for row in score_rows)
    summary = {
        "schema": "group1_sft_two_stage_auto_summary_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "method_id": "TWO_STAGE_AUTO_SFT",
        "input_manifest": str(args.input_manifest),
        "model_dir": str(args.model_dir),
        "chart_to_evidence_adapter_checkpoint": str(args.chart_to_evidence_adapter_checkpoint),
        "evidence_to_semantics_adapter_checkpoint": str(args.evidence_to_semantics_adapter_checkpoint),
        "chart_to_evidence_prompt": str(args.chart_to_evidence_prompt),
        "evidence_to_semantics_prompt": str(args.evidence_to_semantics_prompt),
        "evidence_schema": str(args.evidence_schema),
        "questionnaire_schema": str(args.questionnaire_schema),
        "scoring_manifest": str(args.scoring_manifest) if args.scoring_manifest else None,
        "comparison_policy": str(args.comparison_policy) if args.scoring_manifest else None,
        "parser_policy": {
            "strict_json_only": True,
            "code_fence_stripping_allowed": False,
            "semantic_repair_allowed": False,
            "mechanical_schema_normalization": [
                "stage2 questionnaire null or missing question answer -> {'status':'unknown','value':null}",
                "stage2 questionnaire non-object question answer -> {'status':'unknown','value':null}",
                "stage2 questionnaire answer missing status/value -> fill unknown/null",
            ],
            "stage1_assistant_prefill": stage1_assistant_prefill,
            "stage2_assistant_prefill": stage2_assistant_prefill,
        },
        "input_boundary": {
            "stage1_inference_input": ["full_chart_image", "chart_to_evidence_prompt"],
            "stage2_inference_input": ["auto_generated_evidence_record", "evidence_to_questionnaire_prompt"],
            "human_evidence_used_at_inference": False,
            "target_used_for_prompt_or_parsing": False,
            "scoring_manifest_used_after_prediction_only": bool(args.scoring_manifest),
            "forbidden_inference_inputs": [
                "human_confirmed_evidence_at_inference",
                "target_json",
                "raw_424_record",
                "raw_cifp_record",
                "score_file",
                "other_method_prediction",
            ],
        },
        "samples_total": len(rows),
        "stage1_schema_valid": sum(1 for item in results if item.get("stage1_validation_error_count") == 0),
        "stage2_schema_valid": sum(1 for item in results if item.get("stage2_validation_error_count") == 0),
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
    parser = argparse.ArgumentParser(description="Run Group 1 TWO_STAGE_AUTO_SFT pipeline.")
    parser.add_argument("--input-manifest", required=True, type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--chart-to-evidence-adapter-checkpoint", required=True, type=Path)
    parser.add_argument("--evidence-to-semantics-adapter-checkpoint", required=True, type=Path)
    parser.add_argument("--chart-to-evidence-prompt", required=True, type=Path)
    parser.add_argument("--evidence-to-semantics-prompt", required=True, type=Path)
    parser.add_argument("--evidence-schema", required=True, type=Path)
    parser.add_argument("--questionnaire-schema", required=True, type=Path)
    parser.add_argument("--scoring-manifest", type=Path, default=None)
    parser.add_argument(
        "--comparison-policy",
        type=Path,
        default=ROOT / "benchmark_exports" / "derived" / "v2" / "formal300" / "targets" / "scoring_equivalence_v2" / "comparison_policy_v2.jsonl",
    )
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--assistant-prefill", default=None, help="Legacy option applied to both stages if stage-specific prefill is not set.")
    parser.add_argument("--stage1-assistant-prefill", default=None)
    parser.add_argument("--stage2-assistant-prefill", default=None)
    parser.add_argument("--stage1-max-new-tokens", type=int, default=1536)
    parser.add_argument("--stage2-max-new-tokens", type=int, default=1536)
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
