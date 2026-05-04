from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATHS = ROOT / "training" / "group1_sft" / "configs" / "local_paths.local.json"
METHOD_SET = ROOT / "training" / "group1_sft" / "configs" / "group1_sft_method_set.json"
CANONICAL_PROMPT = ROOT / "training" / "d_sft" / "prompts" / "d_sft_image_to_canonical.v2.md"
CHART_TO_EVIDENCE_PROMPT = ROOT / "training" / "group1_sft" / "prompts" / "chart_to_evidence.zh.md"
EVIDENCE_TO_QUESTIONNAIRE_PROMPT = ROOT / "training" / "group1_sft" / "prompts" / "evidence_to_questionnaire.zh.md"
D1_EVIDENCE_BOXES_PROMPT = (
    ROOT / "training" / "group1_sft" / "prompts" / "d1_chart_to_evidence_boxes_and_canonical.zh.md"
)
CANONICAL_SCHEMA = ROOT / "schemas" / "missed_approach_leg.schema.json"
EVIDENCE_SCHEMA = ROOT / "training" / "group1_sft" / "manifests" / "evidence_record.schema.json"
QUESTIONNAIRE_SCHEMA = ROOT / "training" / "group1_sft" / "manifests" / "evidence_questionnaire.schema.json"
D1_EVIDENCE_BOXES_SCHEMA = (
    ROOT
    / "training"
    / "group1_sft"
    / "manifests"
    / "d1_chart_to_evidence_boxes_and_canonical.schema.json"
)
POLICY_V2 = (
    ROOT
    / "benchmark_exports"
    / "derived"
    / "v2"
    / "formal300"
    / "targets"
    / "scoring_equivalence_v2"
    / "comparison_policy_v2.jsonl"
)
TARGET_V2 = (
    ROOT
    / "benchmark_exports"
    / "derived"
    / "v2"
    / "formal300"
    / "targets"
    / "scoring_equivalence_v2"
    / "canonical_proxy_gt_chart_display_v2.json"
)
D1_CANONICALIZATION_POLICY = ROOT / "docs" / "d1_output_canonicalization_policy_zh.md"
D1_METHOD_CARD = ROOT / "docs" / "d1_method_card_zh.md"
DEFAULT_SPLIT = (
    ROOT
    / "benchmark_exports"
    / "derived"
    / "v2"
    / "formal300"
    / "split_candidates"
    / "split_50_200_50_seed20260437"
    / "splits_50_200_50_seed20260437.json"
)

DEFAULT_METHODS = [
    "D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL",
]
ALLOWED_METHODS = {
    "D_BASE_SAME_BACKBONE",
    "D1",
    "D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL",
    "CHART_TO_EVIDENCE_SFT",
    "EVIDENCE_TO_SEMANTICS_SFT",
    "TWO_STAGE_AUTO_SFT",
}

CHART_TO_EVIDENCE_TRAIN_RUN_ID = "chart_to_evidence_sft_dev50_with_field_links_20260503_r1"
EVIDENCE_TO_SEMANTICS_TRAIN_RUN_ID = "evidence_to_semantics_sft_dev50_with_field_links_20260503_r1"
D1_EVIDENCE_BOXES_TRAIN_RUN_ID = "d1_chart_to_evidence_boxes_and_canonical_d1_continue_dev50_20260504_r2"

IMAGE_METHODS = {
    "D_BASE_SAME_BACKBONE",
    "D1",
    "CHART_TO_EVIDENCE_SFT",
    "TWO_STAGE_AUTO_SFT",
    "D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL",
}
OPTIONAL_EVIDENCE_METHODS = {"EVIDENCE_TO_SEMANTICS_SFT"}


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact(path: Path) -> dict[str, Any]:
    item: dict[str, Any] = {"path": repo_display(path), "exists": path.exists()}
    if path.exists() and path.is_file():
        item.update({"bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return item


def is_placeholder(value: str | None) -> bool:
    return not value or "CHANGE_ME" in value


def resolve_path(value: str, *, repo_root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return repo_root / path


def repo_display(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def load_sample_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        return read_jsonl(path)
    data = read_json(path)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict) and isinstance(data.get("samples"), list):
        return [row for row in data["samples"] if isinstance(row, dict)]
    if isinstance(data, dict) and isinstance(data.get("splits"), dict):
        rows: list[dict[str, Any]] = []
        for split_name, split_rows in data["splits"].items():
            for row in split_rows:
                if isinstance(row, dict):
                    rows.append({**row, "dataset_split": split_name})
        return rows
    raise ValueError(f"Unsupported formal manifest shape: {path}")


def scoring_manifest_from_config(config: dict[str, str], *, repo_root: Path) -> Path:
    explicit = config.get("group1_formal_scoring_manifest")
    if explicit and not is_placeholder(explicit):
        return resolve_path(explicit, repo_root=repo_root)
    split_value = config.get("group1_formal_split")
    if split_value and not is_placeholder(split_value):
        split_path = resolve_path(split_value, repo_root=repo_root)
        if split_path.is_dir():
            return split_path / "scoring_manifest.jsonl"
        if split_path.name == "scoring_manifest.jsonl":
            return split_path
        return split_path.parent / "scoring_manifest.jsonl"
    return (
        repo_root
        / "formal_runs"
        / "group1"
        / "group1_formal_eval_50_200_50_seed20260437_20260430_r1"
        / "scoring_manifest.jsonl"
    )


def canonical_targets_dir_from_config(config: dict[str, str], *, repo_root: Path) -> Path:
    value = config.get("canonical_targets_dir")
    if value and not is_placeholder(value):
        return resolve_path(value, repo_root=repo_root)
    return (
        repo_root
        / "benchmark_exports"
        / "derived"
        / "v2"
        / "formal300"
        / "targets"
        / "scoring_equivalence_v2"
    )


def formal_manifest_from_config(config: dict[str, str], *, repo_root: Path) -> Path:
    value = config.get("formal_manifest")
    if value and not is_placeholder(value):
        return resolve_path(value, repo_root=repo_root)
    return repo_root / "benchmark_exports" / "derived" / "v2" / "formal300" / "manifest.json"


def checkpoint_path_from_config(
    config: dict[str, str],
    *,
    key: str,
    method: str,
    default_run_id: str,
    repo_root: Path,
) -> Path:
    value = config.get(key)
    if value and not is_placeholder(value):
        return resolve_path(value, repo_root=repo_root)
    local_root = config.get("local_root")
    if local_root and not is_placeholder(local_root):
        root = resolve_path(local_root, repo_root=repo_root)
    else:
        output_root = resolve_path(config.get("output_root", "formal_runs/group1_sft"), repo_root=repo_root)
        root = output_root.parent
    return root / "checkpoints" / method / default_run_id / "checkpoint-final"


def image_path_for_sample(sample: dict[str, Any], config: dict[str, str], *, repo_root: Path) -> Path:
    image_file = sample.get("image_file")
    images_dir = config.get("formal_images_dir")
    if image_file and images_dir and not is_placeholder(images_dir):
        return resolve_path(images_dir, repo_root=repo_root) / str(image_file)
    image_path = sample.get("image_path") or sample.get("annotation_image_source")
    if image_path:
        return resolve_path(str(image_path), repo_root=repo_root)
    raise ValueError(f"Sample has no image path: {sample.get('chart_id')}")


def target_path_from_scoring_row(row: dict[str, Any], *, repo_root: Path) -> Path | None:
    target = row.get("target")
    if isinstance(target, dict) and target.get("path"):
        return resolve_path(str(target["path"]), repo_root=repo_root)
    return None


def build_scoring_manifest_rows(
    *,
    source_rows: list[dict[str, Any]],
    canonical_targets_dir: Path,
    run_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    combined_path = canonical_targets_dir / "canonical_proxy_gt_chart_display_v2.json"
    policy_path = canonical_targets_dir / "comparison_policy_v2.jsonl"
    field_targets_path = canonical_targets_dir / "field_targets_chart_display_v2.jsonl"
    if combined_path.exists() and policy_path.exists():
        combined = read_json(combined_path)
        target_dir = run_dir / "scoring_targets_v2"
        rows: list[dict[str, Any]] = []
        missing: list[str] = []
        for source_row in source_rows:
            chart_id = source_row["chart_id"]
            target = combined.get(chart_id) if isinstance(combined, dict) else None
            if target is None:
                missing.append(chart_id)
                continue
            target_out = target_dir / f"{chart_id}.json"
            write_json(target_out, target)
            rows.append(
                {
                    "sample_id": source_row.get("sample_id"),
                    "chart_id": chart_id,
                    "scoring_phase_only": True,
                    "scoring_mode": "chart_display_aware_v2",
                    "target": {
                        "path": str(target_out),
                        "exists": True,
                        "sha256": sha256_file(target_out),
                        "source_combined": repo_display(combined_path),
                    },
                    "field_targets_path": repo_display(field_targets_path),
                    "comparison_policy_path": repo_display(policy_path),
                }
            )
        meta = {
            "source": "scoring_equivalence_v2",
            "combined_target": artifact(combined_path),
            "comparison_policy": artifact(policy_path),
            "field_targets": artifact(field_targets_path),
            "missing_chart_ids": missing,
        }
        return rows, meta
    return source_rows, {
        "source": "source_scoring_manifest_passthrough",
        "reason": "v2 combined target or comparison policy not found",
        "canonical_targets_dir": str(canonical_targets_dir),
    }


def make_image_row(
    *,
    method: str,
    sample: dict[str, Any],
    config: dict[str, str],
    repo_root: Path,
    prompt_path: Path,
    schema_path: Path,
) -> dict[str, Any]:
    image_path = image_path_for_sample(sample, config, repo_root=repo_root)
    expected_sha = sample.get("image_sha256") or sample.get("annotation_image_source_sha256")
    image: dict[str, Any] = {
        "path": str(image_path),
        "exists": image_path.exists(),
        "sha256_expected": expected_sha,
    }
    if image_path.exists() and image_path.is_file():
        image["sha256"] = sha256_file(image_path)
        image["sha256_matches_expected"] = image["sha256"] == expected_sha if expected_sha else None
    return {
        "schema": "group1_sft_image_input_v1",
        "sample_id": sample["sample_id"],
        "chart_id": sample["chart_id"],
        "airport": sample.get("airport"),
        "proc_ident": sample.get("proc_ident"),
        "chart_name": sample.get("chart_name"),
        "method_id": method,
        "image": image,
        "prompt": artifact(prompt_path),
        "output_schema": artifact(schema_path),
        "target_excluded_from_input_manifest": True,
        "forbidden_inputs_excluded": [
            "canonical_target",
            "score_file",
            "CIFP_or_ARINC424_record",
            "human_answer",
            "other_method_prediction",
        ],
    }


def strip_evidence_row_for_inference(row: dict[str, Any], *, split_subset: str) -> dict[str, Any]:
    messages = row.get("messages")
    safe_messages = [messages[0]] if isinstance(messages, list) and messages else []
    source_annotation = row.get("source_annotation")
    if isinstance(source_annotation, dict):
        source_annotation = {
            **source_annotation,
            "uses_field_reviews_as_label": False,
            "assistant_label_removed_for_inference": True,
        }
    return {
        "sample_id": row.get("sample_id"),
        "split": split_subset,
        "chart_id": row["chart_id"],
        "evidence_record": row.get("evidence_record"),
        "field_evidence_links": row.get("field_evidence_links"),
        "declared_oracle_human_evidence_input": True,
        "messages": safe_messages,
        "source_annotation": source_annotation,
    }


def copy_evidence_manifest(
    *,
    config: dict[str, str],
    repo_root: Path,
    out_path: Path,
    selected_chart_ids: list[str],
    split_subset: str,
) -> tuple[int, list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    if split_subset == "development":
        sources = [
            config.get("evidence_to_semantics_train_jsonl"),
            config.get("evidence_to_semantics_dev_jsonl"),
        ]
        if any(is_placeholder(value) for value in sources):
            write_jsonl(out_path, [])
            blockers.append(
                {
                    "method": "EVIDENCE_TO_SEMANTICS_SFT",
                    "blocker": "missing_development_evidence_jsonl",
                    "detail": "Set evidence_to_semantics_train_jsonl and evidence_to_semantics_dev_jsonl in local_paths.local.json.",
                }
            )
            return 0, blockers
        source_paths = [resolve_path(str(value), repo_root=repo_root) for value in sources if value]
    else:
        value = config.get("evidence_to_semantics_eval_jsonl")
        if is_placeholder(value):
            write_jsonl(out_path, [])
            blockers.append(
                {
                    "method": "EVIDENCE_TO_SEMANTICS_SFT",
                    "blocker": "missing_evidence_to_semantics_eval_jsonl",
                    "detail": "Set evidence_to_semantics_eval_jsonl in local_paths.local.json.",
                }
            )
            return 0, blockers
        source_paths = [resolve_path(str(value), repo_root=repo_root)]

    missing_sources = [str(path) for path in source_paths if not path.exists()]
    if missing_sources:
        write_jsonl(out_path, [])
        blockers.append(
            {
                "method": "EVIDENCE_TO_SEMANTICS_SFT",
                "blocker": "evidence_jsonl_not_found",
                "paths": missing_sources,
            }
        )
        return 0, blockers

    rows_by_chart: dict[str, dict[str, Any]] = {}
    for source in source_paths:
        for row in read_jsonl(source):
            if row.get("chart_id"):
                rows_by_chart[row["chart_id"]] = strip_evidence_row_for_inference(row, split_subset=split_subset)
    rows = [rows_by_chart[chart_id] for chart_id in selected_chart_ids if chart_id in rows_by_chart]
    missing_charts = [chart_id for chart_id in selected_chart_ids if chart_id not in rows_by_chart]
    safe_rows = []
    forbidden_fragments = ["target", "score", "canonical_proxy_gt", "cifp", "answer_key"]
    for row in rows:
        leaked_keys = [key for key in row if any(fragment in key.lower() for fragment in forbidden_fragments)]
        safe_rows.append(
            {
                **row,
                "method_id": "EVIDENCE_TO_SEMANTICS_SFT",
                "target_excluded_from_input_manifest": not leaked_keys,
                "forbidden_key_hits": leaked_keys,
            }
        )
    write_jsonl(out_path, safe_rows)
    if any(row["forbidden_key_hits"] for row in safe_rows):
        blockers.append(
            {
                "method": "EVIDENCE_TO_SEMANTICS_SFT",
                "blocker": "forbidden_keys_in_evidence_eval_jsonl",
                "paths": [str(path) for path in source_paths],
            }
        )
    if missing_charts:
        blockers.append(
            {
                "method": "EVIDENCE_TO_SEMANTICS_SFT",
                "blocker": "missing_evidence_rows_for_selected_split",
                "count": len(missing_charts),
                "examples": missing_charts[:10],
            }
        )
    return len(safe_rows), blockers


def method_prompt_and_schema(method: str) -> tuple[Path, Path]:
    if method in {"D_BASE_SAME_BACKBONE", "D1"}:
        return CANONICAL_PROMPT, CANONICAL_SCHEMA
    if method == "D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL":
        return CANONICAL_PROMPT, CANONICAL_SCHEMA
    if method in {"CHART_TO_EVIDENCE_SFT", "TWO_STAGE_AUTO_SFT"}:
        return CHART_TO_EVIDENCE_PROMPT, EVIDENCE_SCHEMA
    if method == "EVIDENCE_TO_SEMANTICS_SFT":
        return EVIDENCE_TO_QUESTIONNAIRE_PROMPT, QUESTIONNAIRE_SCHEMA
    raise ValueError(method)


def write_commands(run_dir: Path, config: dict[str, str], methods: list[str], *, split_subset: str) -> None:
    base_model = config.get("base_vlm_model_dir", "<BASE_MODEL_DIR>")
    adapter = config.get("d1_lora_or_checkpoint_dir", "<D1_LORA_OR_CHECKPOINT_DIR>")
    repo_root = resolve_path(config.get("repo_root", str(ROOT)), repo_root=ROOT) if not is_placeholder(config.get("repo_root")) else ROOT
    chart_adapter = checkpoint_path_from_config(
        config,
        key="chart_to_evidence_lora_or_checkpoint_dir",
        method="CHART_TO_EVIDENCE_SFT",
        default_run_id=CHART_TO_EVIDENCE_TRAIN_RUN_ID,
        repo_root=repo_root,
    )
    semantics_adapter = checkpoint_path_from_config(
        config,
        key="evidence_to_semantics_lora_or_checkpoint_dir",
        method="EVIDENCE_TO_SEMANTICS_SFT",
        default_run_id=EVIDENCE_TO_SEMANTICS_TRAIN_RUN_ID,
        repo_root=repo_root,
    )
    d1_evidence_boxes_adapter = checkpoint_path_from_config(
        config,
        key="d1_evidence_boxes_lora_or_checkpoint_dir",
        method="D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL",
        default_run_id=D1_EVIDENCE_BOXES_TRAIN_RUN_ID,
        repo_root=repo_root,
    )
    lines = [
        "# Group 1 SFT extension run commands",
        "",
        "## 1. Validate local paths",
        "",
        "```powershell",
        "python scripts\\group1_sft\\validate_group1_sft_workspace.py --paths training\\group1_sft\\configs\\local_paths.local.json",
        "```",
        "",
        "## 2. Rebuild this run package",
        "",
        "```powershell",
        "python scripts\\group1_sft\\prepare_group1_sft_run_package.py --paths training\\group1_sft\\configs\\local_paths.local.json "
        + f"--split-subset {split_subset} --out-dir {run_dir}",
        "```",
        "",
        "## 3. Train D1 plus chart evidence boxes on the development-50 train split",
        "",
        "```powershell",
        "python scripts\\group1_sft\\train_qwen2vl_group1_sft_lora.py "
        + "--method D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL "
        + "--paths training\\group1_sft\\configs\\local_paths.local.json "
        + f"--run-id {D1_EVIDENCE_BOXES_TRAIN_RUN_ID} "
                + "--epochs 1 "
                + "--learning-rate 5e-5 "
                + "--max-seq-length 5120",
        "```",
        "",
    ]
    if "D_BASE_SAME_BACKBONE" in methods:
        dbase_raw_run_id = f"{run_dir.name}_D_BASE_SAME_BACKBONE_raw"
        dbase_output_root = run_dir / "D_BASE_SAME_BACKBONE"
        lines.extend(
            [
                "## 4. Same-backbone unfinetuned control",
                "",
                "```powershell",
                "python scripts\\group1_sft\\run_qwen2vl_group1_sft_inference.py "
                + "--method D_BASE_SAME_BACKBONE "
                + f"--input-manifest {run_dir / 'D_BASE_SAME_BACKBONE' / 'input_manifest.jsonl'} "
                + f"--model-dir {base_model} "
                + "--prompt training\\d_sft\\prompts\\d_sft_image_to_canonical.v2.md "
                + "--json-schema schemas\\missed_approach_leg.schema.json "
                + f"--scoring-manifest {run_dir / 'scoring_manifest.jsonl'} "
                + f"--output-root {dbase_output_root} "
                + f"--run-id {dbase_raw_run_id}",
                "```",
                "",
                "## 4b. Canonicalize and score the same-backbone control outputs",
                "",
                "This post-processing uses the same mechanical D1 canonicalization policy: it fixes the output envelope and schema shape without using targets, scores, raw 424/CIFP records, OCR, or other method predictions to change answer values. Targets are used only after canonical JSON is written, for scoring.",
                "",
                "```powershell",
                "python scripts\\run_d1_output_canonicalizer.py "
                + f"--sample-manifest {run_dir / 'scoring_manifest.jsonl'} "
                + f"--input-manifest {run_dir / 'D_BASE_SAME_BACKBONE' / 'input_manifest.jsonl'} "
                + f"--raw-dir {dbase_output_root / 'predictions' / dbase_raw_run_id / 'raw_text'} "
                + "--schema schemas\\missed_approach_leg.schema.json "
                + "--scorer scripts\\scorers\\group1_canonical_field_scorer_v2.py "
                + f"--target-v2 {TARGET_V2} "
                + f"--comparison-policy-v2 {POLICY_V2} "
                + f"--policy {D1_CANONICALIZATION_POLICY} "
                + f"--method-card {D1_METHOD_CARD} "
                + f"--out-root {run_dir / 'D_BASE_SAME_BACKBONE_CANONICALIZED'} "
                + f"--run-id {run_dir.name}_D_BASE_SAME_BACKBONE_CANONICALIZED "
                + "--method D_BASE_SAME_BACKBONE "
                + "--policy-id dbase_output_canonicalization_same_as_d1",
                "```",
                "",
            ]
        )
    if "D1" in methods:
        lines.extend(
            [
                "## 5. D1 rerun with the same entry point",
                "",
                "```powershell",
                "python scripts\\group1_sft\\run_qwen2vl_group1_sft_inference.py "
                + "--method D1 "
                + f"--input-manifest {run_dir / 'D1' / 'input_manifest.jsonl'} "
                + f"--model-dir {base_model} "
                + f"--adapter-checkpoint {adapter} "
                + "--prompt training\\d_sft\\prompts\\d_sft_image_to_canonical.v2.md "
                + "--json-schema schemas\\missed_approach_leg.schema.json "
                + f"--scoring-manifest {run_dir / 'scoring_manifest.jsonl'} "
                + f"--output-root {run_dir / 'D1'}",
                "```",
                "",
            ]
        )
    if "D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL" in methods:
        d1_evidence_boxes_raw_run_id = f"{run_dir.name}_D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL_raw"
        d1_evidence_boxes_output_root = run_dir / "D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL"
        lines.extend(
            [
                "## 6. D1 plus chart evidence boxes formal inference",
                "",
                "The checkpoint was continued with evidence-box supervision, but the formal scored output remains the unchanged D1 canonical JSON. The evidence wrapper is a diagnostic training target, not the formal scoring file.",
                "",
                "```powershell",
                "python scripts\\group1_sft\\run_qwen2vl_group1_sft_inference.py "
                + "--method D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL "
                + f"--input-manifest {run_dir / 'D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL' / 'input_manifest.jsonl'} "
                + f"--model-dir {base_model} "
                + f"--adapter-checkpoint {d1_evidence_boxes_adapter} "
                + "--prompt training\\d_sft\\prompts\\d_sft_image_to_canonical.v2.md "
                + "--json-schema schemas\\missed_approach_leg.schema.json "
                + "--output-mode canonical "
                + "--allow-json-object-candidate-extraction "
                + f"--output-root {d1_evidence_boxes_output_root} "
                + f"--run-id {d1_evidence_boxes_raw_run_id} "
                + "--max-new-tokens 1024 "
                + "--repetition-penalty 1.08",
                "```",
                "",
                "## 6b. Canonicalize and score D1 plus chart evidence boxes outputs",
                "",
                "This post-processing uses the same mechanical D1 canonicalization policy as D1 and the same-backbone control. It fixes only the JSON envelope and schema shape without using targets, scores, raw 424/CIFP records, OCR, or other method predictions to change answer values. Targets are used only after canonical JSON is written, for scoring.",
                "",
                "```powershell",
                "python scripts\\run_d1_output_canonicalizer.py "
                + f"--sample-manifest {run_dir / 'scoring_manifest.jsonl'} "
                + f"--input-manifest {run_dir / 'D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL' / 'input_manifest.jsonl'} "
                + f"--raw-dir {d1_evidence_boxes_output_root / 'predictions' / d1_evidence_boxes_raw_run_id / 'raw_text'} "
                + "--schema schemas\\missed_approach_leg.schema.json "
                + "--scorer scripts\\scorers\\group1_canonical_field_scorer_v2.py "
                + f"--target-v2 {TARGET_V2} "
                + f"--comparison-policy-v2 {POLICY_V2} "
                + f"--policy {D1_CANONICALIZATION_POLICY} "
                + f"--method-card {D1_METHOD_CARD} "
                + f"--out-root {run_dir / 'D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL_CANONICALIZED'} "
                + f"--run-id {run_dir.name}_D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL_CANONICALIZED "
                + "--method D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL "
                + "--policy-id d1_evidence_output_canonicalization_same_as_d1",
                "```",
                "",
            ]
        )
    if "CHART_TO_EVIDENCE_SFT" in methods:
        lines.extend(
            [
                "## 7. CHART_TO_EVIDENCE_SFT inference",
                "",
                "This runner uses the registered evidence-record assistant prefill by default: "
                + "`{\"chart_id\":null,\"evidence_items\":[{`.",
                "",
                "```powershell",
                "python scripts\\group1_sft\\run_qwen2vl_group1_sft_inference.py "
                + "--method CHART_TO_EVIDENCE_SFT "
                + f"--input-manifest {run_dir / 'CHART_TO_EVIDENCE_SFT' / 'input_manifest.jsonl'} "
                + f"--model-dir {base_model} "
                + f"--adapter-checkpoint {chart_adapter} "
                + "--prompt training\\group1_sft\\prompts\\chart_to_evidence.zh.md "
                + "--json-schema training\\group1_sft\\manifests\\evidence_record.schema.json "
                + f"--output-root {run_dir / 'CHART_TO_EVIDENCE_SFT'}",
                "```",
                "",
            ]
        )
    if "EVIDENCE_TO_SEMANTICS_SFT" in methods:
        lines.extend(
            [
                "## 8. EVIDENCE_TO_SEMANTICS_SFT inference with declared human evidence records",
                "",
                "```powershell",
                "python scripts\\group1_sft\\run_qwen2vl_group1_sft_text_inference.py "
                + "--method EVIDENCE_TO_SEMANTICS_SFT "
                + f"--input-manifest {run_dir / 'EVIDENCE_TO_SEMANTICS_SFT' / 'input_manifest.jsonl'} "
                + f"--model-dir {base_model} "
                + f"--adapter-checkpoint {semantics_adapter} "
                + "--json-schema training\\group1_sft\\manifests\\evidence_questionnaire.schema.json "
                + f"--scoring-manifest {run_dir / 'scoring_manifest.jsonl'} "
                + f"--output-root {run_dir / 'EVIDENCE_TO_SEMANTICS_SFT'}",
                "```",
                "",
            ]
        )
    if "TWO_STAGE_AUTO_SFT" in methods:
        lines.extend(
            [
                "## 9. TWO_STAGE_AUTO_SFT full automatic two-stage inference",
                "",
                "This runner uses separate defaults for the two stages: evidence-record prefill for stage 1 and JSON-object prefill for stage 2.",
                "",
                "```powershell",
                "python scripts\\group1_sft\\run_group1_sft_two_stage_auto.py "
                + f"--input-manifest {run_dir / 'TWO_STAGE_AUTO_SFT' / 'input_manifest.jsonl'} "
                + f"--model-dir {base_model} "
                + f"--chart-to-evidence-adapter-checkpoint {chart_adapter} "
                + f"--evidence-to-semantics-adapter-checkpoint {semantics_adapter} "
                + "--chart-to-evidence-prompt training\\group1_sft\\prompts\\chart_to_evidence.zh.md "
                + "--evidence-to-semantics-prompt training\\group1_sft\\prompts\\evidence_to_questionnaire.zh.md "
                + "--evidence-schema training\\group1_sft\\manifests\\evidence_record.schema.json "
                + "--questionnaire-schema training\\group1_sft\\manifests\\evidence_questionnaire.schema.json "
                + f"--scoring-manifest {run_dir / 'scoring_manifest.jsonl'} "
                + f"--output-root {run_dir / 'TWO_STAGE_AUTO_SFT'}",
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "Notes:",
            "",
            "- Do not pass target JSON, score files, raw 424 records, or other method predictions to inference.",
            "- `scoring_manifest.jsonl` is for post-prediction scoring only.",
            "- `D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL` is the only new default method: it starts from the existing D1 adapter, learns fine evidence boxes, and keeps the formal scored prediction as the original canonical JSON shape.",
            "- `evidence_boxes` and `answer_grounding` are diagnostic side outputs; the formal score uses only the extracted `canonical_prediction` object.",
            "- The parser is strict JSON only; semantic repair is not applied.",
            "",
        ]
    )
    (run_dir / "RUN_COMMANDS.md").write_text("\n".join(lines), encoding="utf-8")


def build_package(args: argparse.Namespace) -> dict[str, Any]:
    paths_file = Path(args.paths)
    config = read_json(paths_file)
    repo_root = resolve_path(config.get("repo_root", str(ROOT)), repo_root=ROOT) if not is_placeholder(config.get("repo_root")) else ROOT
    formal_manifest = formal_manifest_from_config(config, repo_root=repo_root)
    scoring_manifest = scoring_manifest_from_config(config, repo_root=repo_root)
    canonical_targets_dir = canonical_targets_dir_from_config(config, repo_root=repo_root)
    sample_rows = load_sample_rows(formal_manifest)
    samples_by_chart = {row["chart_id"]: row for row in sample_rows if row.get("chart_id")}
    if args.split_subset == "evaluation":
        scoring_rows = read_jsonl(scoring_manifest, args.limit)
    else:
        split = read_json(args.split_json)
        split_rows = split["splits"][args.split_subset]
        scoring_rows = [
            {
                "sample_id": row["sample_id"],
                "chart_id": row["chart_id"],
                "scoring_phase_only": True,
                "source_split_subset": args.split_subset,
            }
            for row in split_rows[: args.limit]
        ]
    selected_samples = []
    blockers: list[dict[str, Any]] = []
    for scoring_row in scoring_rows:
        sample = samples_by_chart.get(scoring_row["chart_id"])
        if sample is None:
            blockers.append(
                {
                    "method": "ALL",
                    "blocker": "scoring_chart_missing_from_formal_manifest",
                    "chart_id": scoring_row["chart_id"],
                }
            )
            continue
        selected_samples.append(sample)
    selected_chart_ids = [sample["chart_id"] for sample in selected_samples]

    run_id = args.run_id or f"group1_sft_extension_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    if args.out_dir:
        run_dir = Path(args.out_dir)
    else:
        output_root = resolve_path(config.get("output_root", "formal_runs/group1_sft"), repo_root=repo_root)
        run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=args.overwrite)
    methods = [item.strip() for item in args.methods.split(",") if item.strip()]
    unknown = sorted(set(methods) - ALLOWED_METHODS)
    if unknown:
        raise ValueError(f"Unknown methods: {unknown}")

    scoring_out = run_dir / "scoring_manifest.jsonl"
    scoring_output_rows, scoring_target_meta = build_scoring_manifest_rows(
        source_rows=scoring_rows,
        canonical_targets_dir=canonical_targets_dir,
        run_dir=run_dir,
    )
    if scoring_target_meta.get("missing_chart_ids"):
        blockers.append(
            {
                "method": "SCORING",
                "blocker": "missing_v2_targets_for_scoring_rows",
                "count": len(scoring_target_meta["missing_chart_ids"]),
                "examples": scoring_target_meta["missing_chart_ids"][:10],
            }
        )
    write_jsonl(scoring_out, scoring_output_rows)

    method_reports: dict[str, Any] = {}
    for method in methods:
        method_dir = run_dir / method
        prompt_path, schema_path = method_prompt_and_schema(method)
        if method in IMAGE_METHODS:
            rows = [
                make_image_row(
                    method=method,
                    sample=sample,
                    config=config,
                    repo_root=repo_root,
                    prompt_path=prompt_path,
                    schema_path=schema_path,
                )
                for sample in selected_samples
            ]
            write_jsonl(method_dir / "input_manifest.jsonl", rows)
            missing_images = [row["chart_id"] for row in rows if not row["image"]["exists"]]
            sha_mismatches = [
                row["chart_id"]
                for row in rows
                if row["image"].get("sha256_matches_expected") is False
            ]
            if missing_images:
                blockers.append(
                    {
                        "method": method,
                        "blocker": "missing_images",
                        "count": len(missing_images),
                        "examples": missing_images[:10],
                    }
                )
            if sha_mismatches:
                blockers.append(
                    {
                        "method": method,
                        "blocker": "image_sha256_mismatch",
                        "count": len(sha_mismatches),
                        "examples": sha_mismatches[:10],
                    }
                )
            method_reports[method] = {
                "input_manifest": repo_display(method_dir / "input_manifest.jsonl"),
                "rows": len(rows),
                "missing_images": len(missing_images),
                "sha256_mismatches": len(sha_mismatches),
                "prompt": artifact(prompt_path),
                "output_schema": artifact(schema_path),
            }
        elif method in OPTIONAL_EVIDENCE_METHODS:
            count, method_blockers = copy_evidence_manifest(
                config=config,
                repo_root=repo_root,
                out_path=method_dir / "input_manifest.jsonl",
                selected_chart_ids=selected_chart_ids,
                split_subset=args.split_subset,
            )
            blockers.extend(method_blockers)
            method_reports[method] = {
                "input_manifest": repo_display(method_dir / "input_manifest.jsonl"),
                "rows": count,
                "prompt": artifact(prompt_path),
                "output_schema": artifact(schema_path),
            }

    base_model = config.get("base_vlm_model_dir")
    if is_placeholder(base_model) or not resolve_path(str(base_model), repo_root=repo_root).exists():
        blockers.append({"method": "D_BASE_SAME_BACKBONE", "blocker": "base_vlm_model_dir_missing", "path": base_model})
    d1_checkpoint = config.get("d1_lora_or_checkpoint_dir")
    if "D1" in methods and (is_placeholder(d1_checkpoint) or not resolve_path(str(d1_checkpoint), repo_root=repo_root).exists()):
        blockers.append({"method": "D1", "blocker": "d1_lora_or_checkpoint_dir_missing", "path": d1_checkpoint})
    chart_checkpoint = checkpoint_path_from_config(
        config,
        key="chart_to_evidence_lora_or_checkpoint_dir",
        method="CHART_TO_EVIDENCE_SFT",
        default_run_id=CHART_TO_EVIDENCE_TRAIN_RUN_ID,
        repo_root=repo_root,
    )
    semantics_checkpoint = checkpoint_path_from_config(
        config,
        key="evidence_to_semantics_lora_or_checkpoint_dir",
        method="EVIDENCE_TO_SEMANTICS_SFT",
        default_run_id=EVIDENCE_TO_SEMANTICS_TRAIN_RUN_ID,
        repo_root=repo_root,
    )
    d1_evidence_boxes_checkpoint = checkpoint_path_from_config(
        config,
        key="d1_evidence_boxes_lora_or_checkpoint_dir",
        method="D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL",
        default_run_id=D1_EVIDENCE_BOXES_TRAIN_RUN_ID,
        repo_root=repo_root,
    )
    if any(method in methods for method in ["CHART_TO_EVIDENCE_SFT", "TWO_STAGE_AUTO_SFT"]) and not chart_checkpoint.exists():
        blockers.append(
            {
                "method": "CHART_TO_EVIDENCE_SFT",
                "blocker": "chart_to_evidence_lora_or_checkpoint_dir_missing",
                "path": str(chart_checkpoint),
                "detail": "Train CHART_TO_EVIDENCE_SFT or set chart_to_evidence_lora_or_checkpoint_dir in local_paths.local.json.",
            }
        )
    if any(method in methods for method in ["EVIDENCE_TO_SEMANTICS_SFT", "TWO_STAGE_AUTO_SFT"]) and not semantics_checkpoint.exists():
        blockers.append(
            {
                "method": "EVIDENCE_TO_SEMANTICS_SFT",
                "blocker": "evidence_to_semantics_lora_or_checkpoint_dir_missing",
                "path": str(semantics_checkpoint),
                "detail": "Train EVIDENCE_TO_SEMANTICS_SFT or set evidence_to_semantics_lora_or_checkpoint_dir in local_paths.local.json.",
            }
        )
    if "D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL" in methods and not d1_evidence_boxes_checkpoint.exists():
        blockers.append(
            {
                "method": "D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL",
                "blocker": "d1_evidence_boxes_lora_or_checkpoint_dir_missing",
                "path": str(d1_evidence_boxes_checkpoint),
                "detail": "Train D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL or set d1_evidence_boxes_lora_or_checkpoint_dir in local_paths.local.json.",
            }
        )

    package_manifest = {
        "schema": "group1_sft_run_package_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "run_dir": str(run_dir),
        "split_subset": args.split_subset,
        "paths_file": str(paths_file),
        "repo_root": str(repo_root),
        "formal_manifest": artifact(formal_manifest),
        "scoring_manifest": artifact(scoring_manifest),
        "scoring_manifest_copy": artifact(scoring_out),
        "canonical_targets_dir": artifact(canonical_targets_dir) if canonical_targets_dir.exists() else {"path": str(canonical_targets_dir), "exists": False},
        "scoring_target_source": scoring_target_meta,
        "method_set": artifact(METHOD_SET),
        "methods": method_reports,
        "model_paths": {
            "base_vlm_model_dir": {"path": base_model, "exists": False if is_placeholder(base_model) else resolve_path(str(base_model), repo_root=repo_root).exists()},
            "d1_lora_or_checkpoint_dir": {
                "path": d1_checkpoint,
                "exists": False if is_placeholder(d1_checkpoint) else resolve_path(str(d1_checkpoint), repo_root=repo_root).exists(),
            },
            "chart_to_evidence_lora_or_checkpoint_dir": {
                "path": str(chart_checkpoint),
                "exists": chart_checkpoint.exists(),
            },
            "evidence_to_semantics_lora_or_checkpoint_dir": {
                "path": str(semantics_checkpoint),
                "exists": semantics_checkpoint.exists(),
            },
            "d1_evidence_boxes_lora_or_checkpoint_dir": {
                "path": str(d1_evidence_boxes_checkpoint),
                "exists": d1_evidence_boxes_checkpoint.exists(),
            },
        },
        "policy": {
            "input_manifests_exclude_targets": True,
            "scoring_manifest_for_post_prediction_only": True,
            "development_split_results_are_internal_validation_only": args.split_subset == "development",
            "forbidden_inference_inputs": [
                "target_json",
                "raw_424_record",
                "score_file",
                "other_method_prediction",
                "human_answer_except_declared_oracle_evidence_method",
            ],
        },
        "blockers": blockers,
        "ready_for_remote_execution": not blockers,
    }
    write_json(run_dir / "run_package_manifest.json", package_manifest)
    write_json(run_dir / "reports" / "preflight_report.json", package_manifest)
    write_preflight_markdown(run_dir / "reports" / "preflight_report_zh.md", package_manifest)
    write_commands(run_dir, config, methods, split_subset=args.split_subset)
    return package_manifest


def _write_preflight_markdown_legacy_unused(path: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# 实验组1 SFT 扩展 run package preflight",
        "",
        f"- run_id: `{manifest['run_id']}`",
        f"- ready_for_remote_execution: `{manifest['ready_for_remote_execution']}`",
        f"- blockers: `{len(manifest['blockers'])}`",
        "",
        "## 方法清单",
        "",
    ]
    for method, report in manifest["methods"].items():
        lines.append(f"- `{method}`: rows={report['rows']}, manifest=`{report['input_manifest']}`")
    lines.extend(["", "## Blockers", ""])
    if manifest["blockers"]:
        for blocker in manifest["blockers"]:
            lines.append(f"- `{blocker.get('method')}` / `{blocker.get('blocker')}`: {json.dumps(blocker, ensure_ascii=False)}")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## 边界",
            "",
            "- input manifests 不包含 target JSON、score、CIFP/424 原始记录或其它方法预测。",
            "- scoring manifest 只允许在预测完成后用于评分。",
            "- 人工证据方法必须在报告中标成 oracle/diagnostic second-stage SFT。",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_preflight_markdown(path: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# 实验组 1 SFT 扩展 run package preflight",
        "",
        f"- run_id: `{manifest['run_id']}`",
        f"- split_subset: `{manifest.get('split_subset', 'evaluation')}`",
        f"- ready_for_remote_execution: `{manifest['ready_for_remote_execution']}`",
        f"- blockers: `{len(manifest['blockers'])}`",
        "",
        "## 方法清单",
        "",
    ]
    for method, report in manifest["methods"].items():
        lines.append(f"- `{method}`: rows={report['rows']}, manifest=`{report['input_manifest']}`")
    lines.extend(["", "## Blockers", ""])
    if manifest["blockers"]:
        for blocker in manifest["blockers"]:
            lines.append(f"- `{blocker.get('method')}` / `{blocker.get('blocker')}`: {json.dumps(blocker, ensure_ascii=False)}")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## 边界",
            "",
            "- input manifests 不包含 target JSON、score、CIFP/424 原始记录或其他方法预测。",
            "- scoring manifest 只允许在预测完成后用于评分。",
            "- 新增默认方法只比较 `canonical_prediction` 的正式分数；`evidence_boxes` 只做诊断分析。",
            "- 旧的人工证据/自动两阶段方法不再是本轮默认方法。",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Group 1 SFT extension run package.")
    parser.add_argument("--paths", default=str(DEFAULT_PATHS), help="Path to local_paths.local.json.")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output run package directory.")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--methods", default=",".join(DEFAULT_METHODS))
    parser.add_argument("--split-subset", choices=["development", "evaluation"], default="evaluation")
    parser.add_argument("--split-json", type=Path, default=DEFAULT_SPLIT)
    parser.add_argument("--limit", type=int, default=None, help="Limit samples for a smoke package.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--fail-on-blockers", action="store_true")
    args = parser.parse_args()

    manifest = build_package(args)
    print(
        json.dumps(
            {
                "run_dir": manifest["run_dir"],
                "ready_for_remote_execution": manifest["ready_for_remote_execution"],
                "blocker_count": len(manifest["blockers"]),
                "methods": {key: value["rows"] for key, value in manifest["methods"].items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.fail_on_blockers and manifest["blockers"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
