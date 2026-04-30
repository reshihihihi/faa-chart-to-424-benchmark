from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "group1_formal_eval_50_200_50_seed20260437_20260430_r1"
SPLIT_ID = "formal300_50_200_50_seed20260437"
PACKAGE_ID = "group1_formal_freeze_20260430_r1"
EXPECTED_METHODS = [
    "A1",
    "A2",
    "B1",
    "B1_prime",
    "B1_prime_link",
    "C1",
    "C2",
    "C3",
    "C4",
    "D_SFT",
]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_dir(path: Path) -> str | None:
    if not path.exists() or not path.is_dir():
        return None
    digest = hashlib.sha256()
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        rel_path = file_path.relative_to(path).as_posix()
        digest.update(rel_path.encode("utf-8"))
        digest.update(b"\0")
        file_hash = sha256_file(file_path)
        digest.update((file_hash or "").encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def artifact(path: str, kind: str = "file", required: bool = True) -> dict[str, Any]:
    abs_path = ROOT / path
    if kind == "directory":
        digest = sha256_dir(abs_path)
        exists = abs_path.is_dir()
    else:
        digest = sha256_file(abs_path)
        exists = abs_path.is_file()
    return {
        "path": path,
        "kind": kind,
        "exists": exists,
        "required": required,
        "sha256": digest,
        "bytes": abs_path.stat().st_size if exists and abs_path.is_file() else None,
    }


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_timestamped(reports_dir: Path, pattern: str) -> Path:
    candidates = sorted(
        (item for item in reports_dir.glob(pattern) if "latest" not in item.name),
        key=lambda item: item.stat().st_mtime,
    )
    if not candidates:
        raise FileNotFoundError(f"No timestamped report matches {pattern} in {reports_dir}")
    return candidates[-1]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def row_for_method(audit_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "method": audit_row.get("method"),
        "status": audit_row.get("status"),
        "samples_total": audit_row.get("samples_total"),
        "schema_valid": audit_row.get("schema_valid"),
        "samples_scored": audit_row.get("samples_scored"),
        "method_failure_count": audit_row.get("method_failure_count"),
        "correct": audit_row.get("correct"),
        "total": audit_row.get("total"),
        "accuracy": audit_row.get("accuracy"),
        "schema_retry_count_total": audit_row.get("schema_retry_count_total"),
        "qa_schema_retry_count_total": audit_row.get("qa_schema_retry_count_total"),
    }


def method_boundaries() -> list[dict[str, Any]]:
    return [
        {
            "method": "A1",
            "formal_definition": "OCR-1 full-chart text -> deterministic rules -> canonical JSON",
            "allowed_inputs": ["chart metadata", "OCR-1 PaddleOCR PP-OCRv5 full-chart text"],
            "forbidden_inputs": ["chart image at rule stage", "OCR-2", "LLM/VLM", "field candidates", "target", "score", "CIFP/ARINC 424", "human answer"],
            "model": "none",
            "runner_or_logic": "scripts/run_group1_formal_manifest.py + docs/group1_a1_a2_rules_candidate_v1.md",
        },
        {
            "method": "A2",
            "formal_definition": "OCR-2 full-chart text -> deterministic rules -> canonical JSON",
            "allowed_inputs": ["chart metadata", "OCR-2 Tesseract 5.x full-chart text"],
            "forbidden_inputs": ["chart image at rule stage", "OCR-1", "LLM/VLM", "field candidates", "target", "score", "CIFP/ARINC 424", "human answer"],
            "model": "none",
            "runner_or_logic": "scripts/run_group1_formal_manifest.py + docs/group1_a1_a2_rules_candidate_v1.md",
        },
        {
            "method": "B1",
            "formal_definition": "OCR-1 full-chart text -> LLM -> canonical JSON",
            "allowed_inputs": ["chart metadata", "OCR-1 PaddleOCR PP-OCRv5 full-chart text", "B1 prompt"],
            "forbidden_inputs": ["chart image at LLM stage", "OCR bounding boxes", "field candidates", "target", "score", "CIFP/ARINC 424", "human answer"],
            "model": "gpt-5.4",
            "runner_or_logic": "scripts/run_group1_formal_manifest.py",
            "prompt": "prompts/paper_v2/b1_ocr_to_canonical_pilot10.zh_v1_candidate.md",
        },
        {
            "method": "B1_prime",
            "formal_definition": "OCR-1 full-chart text -> deterministic field candidates -> LLM -> canonical JSON",
            "allowed_inputs": ["chart metadata", "OCR-1 PaddleOCR PP-OCRv5 full-chart text", "OCR-only field_candidates", "B1_prime prompt"],
            "forbidden_inputs": ["chart image at LLM stage", "manual/gold field candidates", "field-to-leg links", "target", "score", "CIFP/ARINC 424", "human answer"],
            "model": "gpt-5.4",
            "runner_or_logic": "scripts/run_group1_formal_manifest.py",
            "prompt": "prompts/paper_v2/b1_prime_ocr_field_candidates_to_canonical_pilot10.zh_v0_candidate.md",
        },
        {
            "method": "B1_prime_link",
            "formal_definition": "OCR-1 full-chart text -> deterministic field candidates -> deterministic field-to-leg links -> LLM -> canonical JSON",
            "allowed_inputs": ["chart metadata", "OCR-1 PaddleOCR PP-OCRv5 full-chart text", "OCR-only field_candidates", "OCR-only field_to_leg_links", "B1_prime_link prompt"],
            "forbidden_inputs": ["chart image at LLM stage", "manual/gold links", "target", "score", "CIFP/ARINC 424", "human answer"],
            "model": "gpt-5.4",
            "runner_or_logic": "scripts/run_group1_formal_manifest.py + scripts/build_field_to_leg_links.py",
            "prompt": "prompts/paper_v2/b1_prime_link_ocr_candidates_links_to_canonical.zh_v0_candidate.md",
        },
        {
            "method": "C1",
            "formal_definition": "full chart image -> VLM -> canonical JSON",
            "allowed_inputs": ["chart metadata", "full chart image", "C1 prompt"],
            "forbidden_inputs": ["OCR text", "field candidates", "target", "score", "CIFP/ARINC 424", "human answer"],
            "model": "claude-sonnet-4-5-20250929",
            "runner_or_logic": "scripts/run_group1_formal_manifest.py",
            "prompt": "prompts/paper_v2/c1_image_to_canonical_pilot10.zh_v1_candidate.md",
        },
        {
            "method": "C2",
            "formal_definition": "full chart image -> fixed per-field QA prompts -> deterministic aggregator -> canonical JSON",
            "allowed_inputs": ["chart metadata", "full chart image", "prompts/path_c_qa_v2 QA bundle", "deterministic aggregator"],
            "forbidden_inputs": ["OCR text", "field candidates", "target", "score", "CIFP/ARINC 424", "human answer"],
            "model": "claude-sonnet-4-5-20250929",
            "runner_or_logic": "scripts/run_group1_formal_manifest.py + scripts/aggregate_c2_qa_candidate.py",
            "prompt": "prompts/path_c_qa_v2",
        },
        {
            "method": "C3",
            "formal_definition": "full chart image -> questionnaire-style VLM extraction -> canonical JSON",
            "allowed_inputs": ["chart metadata", "full chart image", "C3 questionnaire prompt"],
            "forbidden_inputs": ["OCR text", "field candidates", "target", "score", "CIFP/ARINC 424", "human answer"],
            "model": "claude-sonnet-4-5-20250929",
            "runner_or_logic": "scripts/run_group1_formal_manifest.py",
            "prompt": "prompts/paper_v2/c3_questionnaire_pilot10.zh_v1_candidate.md",
        },
        {
            "method": "C4",
            "formal_definition": "full chart image + OCR-1 full-chart text -> VLM -> canonical JSON",
            "allowed_inputs": ["chart metadata", "full chart image", "OCR-1 PaddleOCR PP-OCRv5 full-chart text", "C4 prompt"],
            "forbidden_inputs": ["OCR-2", "field candidates", "target", "score", "CIFP/ARINC 424", "human answer"],
            "model": "claude-sonnet-4-5-20250929",
            "runner_or_logic": "scripts/run_group1_formal_manifest.py",
            "prompt": "prompts/paper_v2/c4_image_ocr_to_canonical_pilot10.zh_v1_candidate.md",
        },
        {
            "method": "D_SFT",
            "formal_definition": "full chart image -> SFT VLM checkpoint -> canonical JSON",
            "allowed_inputs": ["chart metadata", "full chart image", "D-SFT frozen prompt", "selected D-SFT checkpoint"],
            "forbidden_inputs": ["OCR text", "field candidates", "target at inference", "score", "CIFP/ARINC 424", "human answer", "other method predictions"],
            "model": "Qwen/Qwen2-VL-2B-Instruct + QLoRA adapter checkpoint",
            "runner_or_logic": "scripts/d_sft_infer_qwen2vl_lora.py",
            "prompt": "training/d_sft/prompts/d_sft_image_to_canonical.v2.md",
        },
    ]


def write_boundary_csv(path: Path, boundaries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "method",
                "formal_definition",
                "allowed_inputs",
                "forbidden_inputs",
                "model",
                "runner_or_logic",
                "prompt",
            ],
        )
        writer.writeheader()
        for row in boundaries:
            csv_row = dict(row)
            csv_row["allowed_inputs"] = "; ".join(row.get("allowed_inputs", []))
            csv_row["forbidden_inputs"] = "; ".join(row.get("forbidden_inputs", []))
            writer.writerow(csv_row)


def write_result_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "method",
                "status",
                "samples_total",
                "schema_valid",
                "samples_scored",
                "method_failure_count",
                "correct",
                "total",
                "accuracy",
                "schema_retry_count_total",
                "qa_schema_retry_count_total",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_markdown(path: Path, package: dict[str, Any]) -> None:
    results = package["formal_results"]["method_table"]
    boundaries = package["method_boundaries"]
    lines = [
        "# Group 1 Formal Freeze Package",
        "",
        f"- Package id: `{package['package_id']}`",
        f"- Created at: `{package['created_at_utc']}`",
        f"- Formal run id: `{package['formal_run']['run_id']}`",
        f"- Split id: `{package['sample_and_split_freeze']['split_id']}`",
        f"- Evaluation samples: `{package['sample_and_split_freeze']['evaluation_sample_count']}`",
        f"- Completion decision: `{package['formal_results']['completion_decision']}`",
        f"- Hard blockers: `{package['formal_results']['hard_blocker_count']}`",
        "",
        "## Freeze Steps",
        "",
    ]
    for step in package["freeze_steps"]:
        lines.append(f"{step['step']}. **{step['name']}**: {step['status']}")
        lines.append(f"   - {step['meaning']}")
    lines.extend(
        [
            "",
            "## Method Boundaries",
            "",
            "| method | formal definition | model | runner / logic |",
            "|---|---|---|---|",
        ]
    )
    for row in boundaries:
        lines.append(f"| `{row['method']}` | {row['formal_definition']} | {row['model']} | `{row['runner_or_logic']}` |")
    lines.extend(
        [
            "",
            "## Formal Result Table",
            "",
            "| method | status | total | schema_valid | scored | failures | correct | score_total | accuracy |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in results:
        accuracy = row.get("accuracy")
        accuracy_text = f"{accuracy:.6f}" if isinstance(accuracy, (float, int)) else ""
        lines.append(
            f"| `{row.get('method')}` | {row.get('status')} | {row.get('samples_total')} | {row.get('schema_valid')} | {row.get('samples_scored')} | {row.get('method_failure_count')} | {row.get('correct')} | {row.get('total')} | {accuracy_text} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Field accuracy is `correct / total` over schema-valid scored samples.",
            "- Parse, schema, API, and missing-prediction failures are retained as method failures and must be reported with coverage.",
            "- C2 is frozen as a combined result from the interrupted source slice plus continuation chunks; the combined audit report is the reporting source of truth.",
            "- D-SFT accuracy is not comparable without its 184/200 scored coverage being reported beside it.",
            "- This package supersedes the 2026-04-29 pre-run freeze manifest for reporting the completed formal Group 1 run.",
            "",
            "## Output Files",
            "",
        ]
    )
    for key, value in package["package_outputs"].items():
        lines.append(f"- `{key}`: `{value}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_package(base_run_id: str, output_dir: Path) -> dict[str, Any]:
    run_dir = ROOT / "formal_runs" / "group1" / base_run_id
    reports_dir = run_dir / "reports"
    audit_path = latest_timestamped(reports_dir, "final_completion_audit_*.json")
    failure_path = latest_timestamped(reports_dir, "final_failure_details_*.json")
    result_csv_path = latest_timestamped(reports_dir, "final_combined_summary_*.csv")
    markdown_audit_path = latest_timestamped(reports_dir, "FORMAL_GROUP1_COMPLETION_AUDIT_*.md")
    audit = read_json(audit_path)
    method_rows = [row_for_method(row) for row in audit["method_table"]]
    boundaries = method_boundaries()

    files = {
        "sample_manifest": artifact("benchmark_exports/derived/v2/formal300/split_candidates/split_50_200_50_seed20260437/sample_manifest_50_200_50_seed20260437.jsonl"),
        "split_policy": artifact("benchmark_exports/derived/v2/formal300/split_candidates/split_50_200_50_seed20260437/SPLIT_POLICY_50_200_50_seed20260437.md"),
        "split_json": artifact("benchmark_exports/derived/v2/formal300/split_candidates/split_50_200_50_seed20260437/splits_50_200_50_seed20260437.json"),
        "schema": artifact("schemas/missed_approach_leg.schema.json"),
        "scorer": artifact("scripts/scorers/group1_canonical_field_scorer.py"),
        "scorer_validator_manifest": artifact("configs/scorer_validator_manifest.json"),
        "field_targets": artifact("benchmark_exports/derived/v2/formal300/targets/field_targets.jsonl"),
        "evidence_provenance": artifact("benchmark_exports/derived/v2/formal300/targets/evidence_provenance.jsonl"),
        "canonical_proxy_gt_combined": artifact("benchmark_exports/derived/v2/formal300/targets/canonical_proxy_gt_combined.json"),
        "invalid_output_policy": artifact("configs/invalid_output_scoring_policy.md"),
        "output_control_policy": artifact("configs/output_control_policy.md"),
        "parser_repair_policy": artifact("configs/parser_repair_policy.md"),
        "rerun_policy": artifact("docs/rerun_policy.md"),
        "no_leakage_policy": artifact("docs/no_leakage_policy.md"),
        "ocr1_manifest": artifact("ocr_artifacts/formal300/ocr1_paddleocr_ppocrv5_frozen/manifest.jsonl"),
        "ocr1_run_manifest": artifact("ocr_artifacts/formal300/ocr1_paddleocr_ppocrv5_frozen/run_manifest.json"),
        "ocr2_manifest": artifact("ocr_artifacts/formal300/ocr2_tesseract5_frozen/manifest.jsonl"),
        "ocr2_run_manifest": artifact("ocr_artifacts/formal300/ocr2_tesseract5_frozen/run_manifest.json"),
        "formal_run_plan": artifact(f"formal_runs/group1/{base_run_id}/run_plan.json"),
        "formal_run_manifest": artifact(f"formal_runs/group1/{base_run_id}/formal_run_manifest.json"),
        "scoring_manifest": artifact(f"formal_runs/group1/{base_run_id}/scoring_manifest.jsonl"),
        "boundary_audit": artifact(f"formal_runs/group1/{base_run_id}/reports/boundary_audit.json"),
        "completion_audit": artifact(rel(audit_path)),
        "completion_audit_markdown": artifact(rel(markdown_audit_path)),
        "failure_details": artifact(rel(failure_path)),
        "combined_summary_csv": artifact(rel(result_csv_path)),
        "runner_prepare": artifact("scripts/prepare_group1_formal_run.py"),
        "runner_execute": artifact("scripts/run_group1_formal_manifest.py"),
        "runner_audit_completion": artifact("scripts/audit_group1_formal_completion.py"),
        "rules_doc_a1_a2": artifact("docs/group1_a1_a2_rules_candidate_v1.md"),
        "b1_prompt": artifact("prompts/paper_v2/b1_ocr_to_canonical_pilot10.zh_v1_candidate.md"),
        "b1_prime_prompt": artifact("prompts/paper_v2/b1_prime_ocr_field_candidates_to_canonical_pilot10.zh_v0_candidate.md"),
        "b1_prime_link_prompt": artifact("prompts/paper_v2/b1_prime_link_ocr_candidates_links_to_canonical.zh_v0_candidate.md"),
        "c1_prompt": artifact("prompts/paper_v2/c1_image_to_canonical_pilot10.zh_v1_candidate.md"),
        "c2_qa_prompt_bundle": artifact("prompts/path_c_qa_v2", kind="directory"),
        "c2_aggregator": artifact("scripts/aggregate_c2_qa_candidate.py"),
        "c2_aggregator_doc": artifact("docs/group1_c2_qa_aggregator_candidate_v1.md"),
        "c3_prompt": artifact("prompts/paper_v2/c3_questionnaire_pilot10.zh_v1_candidate.md"),
        "c4_prompt": artifact("prompts/paper_v2/c4_image_ocr_to_canonical_pilot10.zh_v1_candidate.md"),
        "field_candidate_schema": artifact("schemas/field_candidates.schema.candidate.json"),
        "field_to_leg_link_schema": artifact("schemas/field_to_leg_links.schema.candidate.json"),
        "field_to_leg_link_builder": artifact("scripts/build_field_to_leg_links.py"),
        "d_sft_prompt": artifact("training/d_sft/prompts/d_sft_image_to_canonical.v2.md"),
        "d_sft_training_config": artifact("training/d_sft/configs/d_sft_training_config.frozen_20260428_r1.json"),
        "d_sft_infer_runner": artifact("scripts/d_sft_infer_qwen2vl_lora.py"),
        "d_sft_formal_summary": artifact(f"formal_runs/group1/{base_run_id}_D_SFT/D_SFT/predictions/{base_run_id}_D_SFT_D_SFT/summary_report.json"),
    }

    missing_required = [key for key, value in files.items() if value["required"] and not value["exists"]]
    hard_blocker_count = int(audit.get("hard_blocker_count") or 0) + len(missing_required)
    completion_decision = audit.get("decision")

    package = {
        "package_id": PACKAGE_ID,
        "manifest_version": "1.0.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "frozen" if hard_blocker_count == 0 else "blocked",
        "supersedes": ["configs/group1_formal_freeze_manifest_20260429.json"],
        "formal_run": {
            "run_id": base_run_id,
            "run_dir": f"formal_runs/group1/{base_run_id}",
            "split_filter": "evaluation",
            "inference_target_access": False,
            "scoring_manifest_separate": True,
        },
        "freeze_steps": [
            {
                "step": 1,
                "name": "sample and split",
                "status": "frozen",
                "meaning": "The formal reporting split is fixed to the 200-sample evaluation subset of formal300_50_200_50_seed20260437.",
            },
            {
                "step": 2,
                "name": "schema target scorer",
                "status": "frozen",
                "meaning": "Canonical schema, proxy targets, field scorer, and invalid-output scoring policy are fixed by path and sha256.",
            },
            {
                "step": 3,
                "name": "method boundaries",
                "status": "frozen",
                "meaning": "Each method's allowed inputs and forbidden leakage sources are fixed for Group 1 reporting.",
            },
            {
                "step": 4,
                "name": "model and call parameters",
                "status": "frozen",
                "meaning": "OCR engines, LLM/VLM identities, D-SFT checkpoint role, deterministic settings, and retry policy are fixed for this run.",
            },
            {
                "step": 5,
                "name": "runner prompt rule aggregator",
                "status": "frozen",
                "meaning": "Runners, prompts, rules, link builder, QA aggregator, and D-SFT inference prompt are fixed by path and sha256.",
            },
            {
                "step": 6,
                "name": "results and failure accounting",
                "status": "frozen",
                "meaning": "Final method table, C2 combination policy, coverage, method failures, and field accuracy are fixed from the timestamped completion audit.",
            },
            {
                "step": 7,
                "name": "freeze package",
                "status": "generated",
                "meaning": "This package is the reporting source for Group 1 formal results before moving to later experiment groups.",
            },
        ],
        "sample_and_split_freeze": {
            "split_id": SPLIT_ID,
            "formal300_dir": "benchmark_exports/derived/v2/formal300",
            "split_filter": "evaluation",
            "evaluation_sample_count": 200,
            "development_sample_count": 50,
            "probe_sample_count": 50,
            "artifacts": {
                "sample_manifest": files["sample_manifest"],
                "split_policy": files["split_policy"],
                "split_json": files["split_json"],
            },
        },
        "schema_target_scorer_freeze": {
            "schema": files["schema"],
            "scorer": files["scorer"],
            "scorer_validator_manifest": files["scorer_validator_manifest"],
            "targets": {
                "field_targets": files["field_targets"],
                "evidence_provenance": files["evidence_provenance"],
                "canonical_proxy_gt_combined": files["canonical_proxy_gt_combined"],
            },
            "policies": {
                "invalid_output_policy": files["invalid_output_policy"],
                "output_control_policy": files["output_control_policy"],
                "parser_repair_policy": files["parser_repair_policy"],
                "rerun_policy": files["rerun_policy"],
                "no_leakage_policy": files["no_leakage_policy"],
            },
        },
        "model_call_freeze": {
            "OCR_1": {
                "engine": "PaddleOCR PP-OCRv5",
                "role": "ordinary OCR for A1/B1/B1_prime/B1_prime_link/C4",
                "manifest": files["ocr1_manifest"],
                "run_manifest": files["ocr1_run_manifest"],
            },
            "OCR_2": {
                "engine": "Tesseract 5.x",
                "role": "alternative OCR for A2 only in Group 1",
                "manifest": files["ocr2_manifest"],
                "run_manifest": files["ocr2_run_manifest"],
            },
            "LLM_B_methods": {
                "provider": "openai_compatible",
                "model": "gpt-5.4",
                "temperature": 0.0,
                "max_tokens": 4096,
                "output_control": "forced tool call / schema-bound canonical JSON",
                "schema_retry_count": 1,
                "parser_repair": False,
            },
            "VLM_C_methods": {
                "provider": "anthropic_compatible",
                "model": "claude-sonnet-4-5-20250929",
                "temperature": 0.0,
                "max_tokens": {"C1": 4096, "C2_QA_call": 2048, "C3": 4096, "C4": 4096},
                "output_control": "anthropic tool use / schema-bound canonical JSON",
                "schema_retry_count": 1,
                "parser_repair": False,
            },
            "D_SFT": {
                "base_model": "Qwen/Qwen2-VL-2B-Instruct",
                "adapter": "QLoRA adapter selected by D-SFT dev split only",
                "training_config": files["d_sft_training_config"],
                "inference_runner": files["d_sft_infer_runner"],
                "parser_policy": "strict_json_only; no code fence stripping; no semantic repair; no selective retry",
            },
        },
        "method_boundaries": boundaries,
        "runner_prompt_rule_freeze": {
            key: value
            for key, value in files.items()
            if key
            in {
                "runner_prepare",
                "runner_execute",
                "runner_audit_completion",
                "rules_doc_a1_a2",
                "b1_prompt",
                "b1_prime_prompt",
                "b1_prime_link_prompt",
                "c1_prompt",
                "c2_qa_prompt_bundle",
                "c2_aggregator",
                "c2_aggregator_doc",
                "c3_prompt",
                "c4_prompt",
                "field_candidate_schema",
                "field_to_leg_link_schema",
                "field_to_leg_link_builder",
                "d_sft_prompt",
                "d_sft_training_config",
                "d_sft_infer_runner",
            }
        },
        "formal_results": {
            "completion_decision": completion_decision,
            "hard_blocker_count": hard_blocker_count,
            "missing_required_artifacts": missing_required,
            "method_table": method_rows,
            "result_artifacts": {
                "completion_audit": files["completion_audit"],
                "completion_audit_markdown": files["completion_audit_markdown"],
                "failure_details": files["failure_details"],
                "combined_summary_csv": files["combined_summary_csv"],
                "d_sft_formal_summary": files["d_sft_formal_summary"],
            },
            "interpretation_rules": [
                "Report coverage beside accuracy.",
                "Do not count parse/schema/API failures as correct.",
                "Use zero_for_all_target_fields policy for invalid outputs in paper tables when reporting full-sample denominator.",
                "The audit table's field-level accuracy is over schema-valid scored samples; full-sample summaries must separately apply invalid-output policy.",
            ],
        },
        "all_artifact_hashes": files,
    }
    return package


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Group 1 formal freeze package.")
    parser.add_argument("--base-run-id", default=RUN_ID)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "freeze")
    args = parser.parse_args()

    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    package = build_package(args.base_run_id, output_dir)
    base = "group1_formal_freeze_package_20260430_r1"
    manifest_path = output_dir / f"{base}.json"
    md_path = output_dir / f"{base}.md"
    boundary_csv_path = output_dir / "group1_formal_method_boundaries_20260430_r1.csv"
    result_csv_path = output_dir / "group1_formal_result_table_20260430_r1.csv"

    package["package_outputs"] = {
        "manifest_json": rel(manifest_path),
        "markdown": rel(md_path),
        "method_boundary_csv": rel(boundary_csv_path),
        "result_table_csv": rel(result_csv_path),
    }
    write_json(manifest_path, package)
    write_markdown(md_path, package)
    write_boundary_csv(boundary_csv_path, package["method_boundaries"])
    write_result_csv(result_csv_path, package["formal_results"]["method_table"])

    latest_manifest = output_dir / "group1_formal_freeze_package_latest.json"
    latest_md = output_dir / "group1_formal_freeze_package_latest.md"
    write_json(latest_manifest, package)
    write_markdown(latest_md, package)

    print(json.dumps(
        {
            "status": package["status"],
            "hard_blocker_count": package["formal_results"]["hard_blocker_count"],
            "manifest": rel(manifest_path),
            "markdown": rel(md_path),
            "boundary_csv": rel(boundary_csv_path),
            "result_csv": rel(result_csv_path),
            "latest_manifest": rel(latest_manifest),
            "latest_markdown": rel(latest_md),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0 if package["status"] == "frozen" else 1


if __name__ == "__main__":
    raise SystemExit(main())
