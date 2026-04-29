from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FORMAL300 = ROOT / "benchmark_exports" / "derived" / "v2" / "formal300"
DEFAULT_OUTPUT_ROOT = ROOT / "formal_runs" / "group1"
METHODS = ["A1", "A2", "B1", "B1_prime", "B1_prime_link", "C1", "C2", "C3", "C4", "D_SFT"]


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


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def artifact(path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "path": display(path),
        "exists": exists,
        "sha256": sha256_file(path) if exists and path.is_file() else None,
    }


def method_inputs(
    method: str,
    sample: dict[str, Any],
    *,
    formal300_dir: Path,
    ocr1_root: Path,
    ocr2_root: Path,
) -> dict[str, Any]:
    chart_id = sample["chart_id"]
    image_path = ROOT / sample["image_path"]
    base = {
        "sample_id": sample["sample_id"],
        "chart_id": chart_id,
        "airport": sample["airport"],
        "proc_ident": sample["proc_ident"],
        "chart_name": sample["chart_name"],
        "method_id": method,
        "forbidden_inputs_excluded": [
            "canonical_target",
            "score_file",
            "CIFP_or_ARINC424_record",
            "human_answer",
            "other_method_prediction",
        ],
    }
    if method in {"A1", "A2", "C1", "C2", "C3", "C4", "D_SFT"}:
        base["image"] = artifact(image_path)
    if method in {"A1", "B1", "B1_prime", "B1_prime_link", "C4"}:
        base["OCR-1_full_text"] = artifact(ocr1_root / f"{chart_id}.txt")
    if method == "A2":
        base["OCR-2_full_text"] = artifact(ocr2_root / f"{chart_id}.txt")
    if method == "B1_prime":
        base["field_candidates_policy"] = "generated at run time from OCR-1 text only; no target/scorer/CIFP"
    if method == "B1_prime_link":
        base["field_candidates_policy"] = "generated at run time from OCR-1 text only; no target/scorer/CIFP"
        base["field_to_leg_links_policy"] = "generated at run time from OCR-1 text and field_candidates only; no target/scorer/CIFP"
    if method == "C2":
        base["qa_prompt_bundle"] = "prompts/path_c_qa_v2/"
        base["aggregator"] = "scripts/aggregate_c2_qa_candidate.py"
    if method == "C3":
        base["questionnaire_parser"] = "scripts/c3_questionnaire_to_canonical.py"
    if method == "D_SFT":
        base["checkpoint_policy"] = "training/d_sft/configs/d_sft_training_config.frozen_20260428_r1.json"
    return base


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare no-leakage Group 1 formal input/scoring manifests without running formal300."
    )
    parser.add_argument("--formal300-dir", type=Path, default=DEFAULT_FORMAL300)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default="group1_formal_prepared_20260429_no_eval")
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument(
        "--ocr1-root",
        type=Path,
        default=ROOT / "ocr_artifacts" / "formal300" / "ocr1_paddleocr_ppocrv5_frozen" / "full_text",
    )
    parser.add_argument(
        "--ocr2-root",
        type=Path,
        default=ROOT / "ocr_artifacts" / "formal300" / "ocr2_tesseract5_frozen" / "full_text",
    )
    args = parser.parse_args()

    methods = [item.strip() for item in args.methods.split(",") if item.strip()]
    unknown = sorted(set(methods) - set(METHODS))
    if unknown:
        raise ValueError(f"Unknown Group 1 methods: {unknown}")

    samples = read_jsonl(args.formal300_dir / "sample_manifest.jsonl")
    run_dir = args.output_root / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    scoring_rows = []
    readiness_errors = []
    for sample in samples:
        target = ROOT / str(sample.get("canonical_proxy_gt_file") or "")
        scoring_rows.append(
            {
                "sample_id": sample["sample_id"],
                "chart_id": sample["chart_id"],
                "target": artifact(target),
                "field_targets_path": display(args.formal300_dir / "targets" / "field_targets.jsonl"),
                "scoring_phase_only": True,
            }
        )

    for method in methods:
        rows = [
            method_inputs(
                method,
                sample,
                formal300_dir=args.formal300_dir,
                ocr1_root=args.ocr1_root,
                ocr2_root=args.ocr2_root,
            )
            for sample in samples
        ]
        for row in rows:
            for key, value in row.items():
                if isinstance(value, dict) and value.get("exists") is False:
                    if key.startswith("OCR"):
                        readiness_errors.append(
                            {
                                "method_id": method,
                                "sample_id": row["sample_id"],
                                "chart_id": row["chart_id"],
                                "missing_input": key,
                                "path": value["path"],
                            }
                        )
        write_jsonl(run_dir / method / "input_manifest.jsonl", rows)

    write_jsonl(run_dir / "scoring_manifest.jsonl", scoring_rows)
    run_plan = {
        "status": "prepared_no_formal300_eval_run",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id,
        "formal300_dir": display(args.formal300_dir),
        "sample_count": len(samples),
        "methods": methods,
        "inference_target_access": False,
        "scoring_manifest_separate": True,
        "formal300_evaluation_ran": False,
        "ocr1_root": display(args.ocr1_root),
        "ocr2_root": display(args.ocr2_root),
        "readiness_error_count": len(readiness_errors),
        "readiness_errors_sample": readiness_errors[:50],
        "policies": {
            "invalid_output_scoring": "configs/invalid_output_scoring_policy.md",
            "output_control": "configs/output_control_policy.md",
            "parser_repair": "configs/parser_repair_policy.md",
            "rerun_policy": "docs/rerun_policy.md",
        },
    }
    write_json(run_dir / "run_plan.json", run_plan)
    print(json.dumps(run_plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
