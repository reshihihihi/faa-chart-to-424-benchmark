from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
from jsonschema import Draft202012Validator

from materialize_external_pilot_set import (
    DEFAULT_CIFP,
    DEFAULT_FORMAL300,
    DEFAULT_SCHEMA,
    build_cifp_index,
    collect_checksums,
    download_pdf,
    project_procedure,
    raw_cifp_text,
    render_first_page,
    sha256_file,
    write_json,
    write_jsonl,
    write_text,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "benchmark_exports" / "derived" / "v2" / "formal300"
QUESTION_FIELDS = [
    "Q_terminator",
    "Q1_fix_ident",
    "Q2_altitude_constraint",
    "Q3_turn",
    "Q4_course_or_radial",
    "Q5_hold_params",
]


def normalize_source_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    pdf_file = str(row["pdf_file"]).upper()
    return {
        **row,
        "formal_sample_id": f"formal300_{index:03d}",
        "icao": row["airport"],
        "pdf_name": pdf_file,
        "type": row.get("kind") or row.get("procedure_type"),
        "procedure_type": row.get("kind") or row.get("procedure_type"),
        "apt_ident": row.get("apt_ident"),
        "chart_id": row["chart_id"],
        "proc_ident": row["proc_ident"],
        "chart_name": row["chart_name"],
    }


def target_field_rows(sample: dict[str, Any], canonical: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {
            "sample_id": sample["sample_id"],
            "chart_id": sample["chart_id"],
            "field_path": "missed_approach.leg_count",
            "leg_index": None,
            "question_field": "leg_count",
            "target": canonical["missed_approach"]["leg_count"],
        }
    ]
    for leg in canonical["missed_approach"]["legs"]:
        for field in QUESTION_FIELDS:
            rows.append(
                {
                    "sample_id": sample["sample_id"],
                    "chart_id": sample["chart_id"],
                    "field_path": f"missed_approach.legs[{leg['leg_index']}].answers.{field}",
                    "leg_index": leg["leg_index"],
                    "question_field": field,
                    "target": leg["answers"][field],
                }
            )
    return rows


def evidence_rows(sample: dict[str, Any], canonical: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in target_field_rows(sample, canonical):
        rows.append(
            {
                "sample_id": sample["sample_id"],
                "chart_id": sample["chart_id"],
                "field_path": item["field_path"],
                "evidence_type": "CIFP_projection",
                "source_cycle": "FAA_CIFP_260416_FAACIFP18",
                "raw_cifp_file": sample.get("raw_cifp_file"),
                "projection_script": "scripts/materialize_formal300_dataset.py",
                "projection_note": "Canonical proxy target projected from ARINC 424.18 PF records; not generated from model outputs.",
            }
        )
    return rows


def challenge_tags(sample: dict[str, Any], canonical: dict[str, Any]) -> dict[str, Any]:
    legs = canonical["missed_approach"]["legs"]
    tags = [
        f"procedure_type:{sample.get('procedure_type') or 'UNKNOWN'}",
        f"leg_count:{len(legs)}",
    ]
    if sample.get("holding_required"):
        tags.append("holding_required")
    if any(leg["answers"]["Q5_hold_params"]["status"] == "present" for leg in legs):
        tags.append("has_hold_leg")
    if any(
        leg["answers"]["Q4_course_or_radial"]["status"] == "present"
        and isinstance(leg["answers"]["Q4_course_or_radial"]["value"], dict)
        and leg["answers"]["Q4_course_or_radial"]["value"].get("type") == "navaid_radial"
        for leg in legs
    ):
        tags.append("has_radial")
    if any(
        leg["answers"]["Q4_course_or_radial"]["status"] == "present"
        and isinstance(leg["answers"]["Q4_course_or_radial"]["value"], dict)
        and leg["answers"]["Q4_course_or_radial"]["value"].get("type") == "course_deg"
        for leg in legs
    ):
        tags.append("has_course")
    if len(legs) >= 4:
        tags.append("multi_leg_ge4")
    return {"sample_id": sample["sample_id"], "chart_id": sample["chart_id"], "tags": sorted(set(tags))}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize formal300 PDFs/images and CIFP-derived canonical proxy targets."
    )
    parser.add_argument("--formal300-manifest", type=Path, default=DEFAULT_FORMAL300)
    parser.add_argument("--cifp-file", type=Path, default=DEFAULT_CIFP)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()

    rows = json.loads(args.formal300_manifest.read_text(encoding="utf-8"))
    if args.limit:
        rows = rows[: args.limit]
    selected = [normalize_source_row(row, index) for index, row in enumerate(rows, start=1)]

    output_dir = args.output_dir
    pdf_dir = output_dir / "pdfs"
    image_dir = output_dir / "images"
    target_dir = output_dir / "targets" / "canonical_proxy_gt"
    raw_cifp_dir = output_dir / "targets" / "raw_cifp_per_procedure"
    reports_dir = output_dir / "reports"
    source_dir = output_dir / "source"
    for path in [pdf_dir, image_dir, target_dir, raw_cifp_dir, reports_dir, source_dir]:
        path.mkdir(parents=True, exist_ok=True)

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    extracted, raw_buckets = build_cifp_index(args.cifp_file, selected)

    manifest_rows: list[dict[str, Any]] = []
    field_rows: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    tags: list[dict[str, Any]] = []
    combined_targets: dict[str, Any] = {}
    canonical_leg_index: dict[str, Any] = {}
    target_errors: list[dict[str, Any]] = []
    materialization_errors: list[dict[str, Any]] = []

    for index, row in enumerate(selected, start=1):
        chart_id = row["chart_id"]
        pdf_name = row["pdf_name"]
        pdf_stem = Path(pdf_name).stem
        pdf_path = pdf_dir / pdf_name
        image_name = f"{index:03d}__{chart_id}__{pdf_stem}_p0.png"
        image_path = image_dir / image_name
        target_path = target_dir / f"{chart_id}.json"
        raw_cifp_path = raw_cifp_dir / f"{chart_id}.txt"
        pdf_url = row.get("pdf_url") or f"https://aeronav.faa.gov/d-tpp/2604/{pdf_name}"

        dims: dict[str, int] | None = None
        pdf_error = None
        image_error = None
        try:
            if not args.skip_download:
                download_pdf(pdf_url, pdf_path)
            if pdf_path.exists():
                dims = render_first_page(pdf_path, image_path)
            else:
                pdf_error = "pdf_missing_after_skip_download"
        except Exception as exc:  # noqa: BLE001
            materialization_errors.append({"chart_id": chart_id, "stage": "download_or_render", "error": repr(exc)})
            if not pdf_path.exists():
                pdf_error = repr(exc)
            else:
                image_error = repr(exc)

        extracted_item = extracted.get(chart_id, {"error": "missing_from_cifp_index"})
        canonical = None
        target_error = None
        if extracted_item.get("error"):
            target_error = extracted_item["error"]
        else:
            canonical = project_procedure(extracted_item, row["chart_name"])
            validation_errors = [
                {"path": ".".join(str(part) for part in err.path), "message": err.message}
                for err in sorted(validator.iter_errors(canonical), key=lambda err: list(err.path))
            ]
            if validation_errors:
                target_error = validation_errors
            else:
                write_json(target_path, canonical)
                write_text(raw_cifp_path, raw_cifp_text(chart_id, raw_buckets.get(chart_id, [])))
                combined_targets[chart_id] = canonical
                canonical_leg_index[chart_id] = {
                    "sample_id": row["formal_sample_id"],
                    "leg_count": len(canonical["missed_approach"]["legs"]),
                    "legs": [
                        {
                            "leg_index": leg["leg_index"],
                            "answers": sorted(leg["answers"].keys()),
                        }
                        for leg in canonical["missed_approach"]["legs"]
                    ],
                }

        if target_error:
            target_errors.append({"sample_id": row["formal_sample_id"], "chart_id": chart_id, "error": target_error})

        sample = {
            "sample_id": row["formal_sample_id"],
            "chart_id": chart_id,
            "airport": row["airport"],
            "proc_ident": row["proc_ident"],
            "chart_name": row["chart_name"],
            "procedure_type": row.get("procedure_type"),
            "dataset_split": row.get("dataset_split"),
            "sample_source": row.get("sample_source"),
            "sample_type": row.get("sample_type"),
            "holding_required": row.get("holding_required"),
            "needs_priority_review": row.get("needs_priority_review"),
            "pdf_file": pdf_name,
            "pdf_url": pdf_url,
            "pdf_path": f"benchmark_exports/derived/v2/formal300/pdfs/{pdf_name}",
            "image_file": image_name,
            "image_path": f"benchmark_exports/derived/v2/formal300/images/{image_name}",
            "canonical_proxy_gt_file": f"benchmark_exports/derived/v2/formal300/targets/canonical_proxy_gt/{chart_id}.json"
            if canonical is not None and not target_error
            else None,
            "raw_cifp_file": f"benchmark_exports/derived/v2/formal300/targets/raw_cifp_per_procedure/{chart_id}.txt"
            if canonical is not None and not target_error
            else None,
            "image_dimensions": dims,
            "pdf_sha256": sha256_file(pdf_path) if pdf_path.exists() else None,
            "image_sha256": sha256_file(image_path) if image_path.exists() else None,
            "target_sha256": sha256_file(target_path) if target_path.exists() else None,
            "raw_cifp_sha256": sha256_file(raw_cifp_path) if raw_cifp_path.exists() else None,
            "target_status": "schema_valid" if canonical is not None and not target_error else "missing_or_invalid",
            "pdf_status": "available" if pdf_path.exists() and not pdf_error else "missing_or_failed",
            "image_status": "available" if image_path.exists() and not image_error else "missing_or_failed",
        }
        manifest_rows.append(sample)
        if canonical is not None and not target_error:
            field_rows.extend(target_field_rows(sample, canonical))
            evidence.extend(evidence_rows(sample, canonical))
            tags.append(challenge_tags(sample, canonical))

    write_jsonl(output_dir / "sample_manifest.jsonl", manifest_rows)
    write_json(output_dir / "manifest.json", manifest_rows)
    write_json(source_dir / "formal300_source_manifest.json", selected)
    write_json(target_dir.parent / "canonical_proxy_gt_combined.json", combined_targets)
    write_json(target_dir.parent / "canonical_leg_index.json", canonical_leg_index)
    write_jsonl(target_dir.parent / "field_targets.jsonl", field_rows)
    write_jsonl(target_dir.parent / "evidence_provenance.jsonl", evidence)
    write_jsonl(output_dir / "challenge_tags.jsonl", tags)

    split_rows: dict[str, list[dict[str, str]]] = {}
    for sample in manifest_rows:
        split_rows.setdefault(sample.get("dataset_split") or "unknown", []).append(
            {"sample_id": sample["sample_id"], "chart_id": sample["chart_id"], "pdf_file": sample["pdf_file"]}
        )
    write_json(
        output_dir / "splits.json",
        {
            "status": "materialized_not_formal_evaluated",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "split_counts": {key: len(value) for key, value in sorted(split_rows.items())},
            "splits": split_rows,
        },
    )

    report = {
        "status": "formal300_materialized_ready_for_freeze_review"
        if not target_errors and not materialization_errors
        else "formal300_materialized_with_blockers",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest": str(args.formal300_manifest.resolve()),
        "source_manifest_sha256": sha256_file(args.formal300_manifest),
        "cifp_file": str(args.cifp_file.resolve()),
        "cifp_sha256": sha256_file(args.cifp_file),
        "schema": {"path": str(args.schema.resolve()), "sha256": sha256_file(args.schema)},
        "render_policy": {
            "engine": "PyMuPDF",
            "fitz_version": fitz.version,
            "matrix": "Matrix(2, 2)",
            "page_index": 0,
            "alpha": False,
        },
        "counts": {
            "samples": len(manifest_rows),
            "pdf_available": sum(1 for row in manifest_rows if row["pdf_status"] == "available"),
            "image_available": sum(1 for row in manifest_rows if row["image_status"] == "available"),
            "target_schema_valid": sum(1 for row in manifest_rows if row["target_status"] == "schema_valid"),
            "field_targets": len(field_rows),
            "evidence_rows": len(evidence),
            "challenge_tag_rows": len(tags),
        },
        "split_counts": dict(Counter(row.get("dataset_split") for row in manifest_rows)),
        "procedure_type_counts": dict(Counter(row.get("procedure_type") for row in manifest_rows)),
        "target_errors": target_errors,
        "materialization_errors": materialization_errors,
        "formal_evaluation_ran": False,
    }
    write_json(reports_dir / "formal300_materialization_report.json", report)

    checksums = collect_checksums(output_dir)
    write_text(output_dir / "checksums.sha256", "\n".join(f"{row['sha256']}  {row['path']}" for row in checksums))
    print(json.dumps(report["counts"] | {"status": report["status"], "output_dir": str(output_dir.resolve())}, indent=2))
    return 0 if not target_errors and not materialization_errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
