from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
import sys

sys.path.insert(0, str(SCRIPT_DIR))

from materialize_external_pilot_set import (  # noqa: E402
    DEFAULT_CANDIDATES,
    DEFAULT_CIFP,
    DEFAULT_FORMAL300,
    DEFAULT_PILOT10,
    DEFAULT_SCHEMA,
    build_cifp_index,
    download_pdf,
    raw_cifp_text,
    render_first_page,
    project_procedure,
    read_jsonl,
    sha256_file,
    write_json,
    write_jsonl,
    write_text,
)


DEFAULT_PILOT100 = (
    Path("E:/experiment3/try_B1_B1'")
    / "data"
    / "pilot100_external"
    / "pilot100_external_manifest.jsonl"
)
DEFAULT_OUTPUT_ROOT = Path("E:/experiment3/d_sft")
DEFAULT_PROMPT = ROOT / "training" / "d_sft" / "prompts" / "d_sft_image_to_canonical.v0.md"


def normalize_pdf(row: dict[str, Any]) -> str:
    return str(row.get("pdf_name") or row.get("pdf_file") or "").upper()


def airport_of(row: dict[str, Any]) -> str:
    return str(row.get("icao") or row.get("airport") or "").upper()


def proc_ident_of(row: dict[str, Any]) -> str:
    return str(row.get("proc_ident") or row.get("approach_ident") or "").upper()


def procedure_type_of(row: dict[str, Any]) -> str:
    return str(row.get("type") or row.get("procedure_type") or row.get("kind") or "UNKNOWN").upper()


def runway_key(row: dict[str, Any]) -> str:
    chart_name = str(row.get("chart_name") or "").upper()
    proc_ident = proc_ident_of(row)
    match = re.search(r"\bRWY\s+([0-9]{1,2}[LRC]?)\b", chart_name)
    if match:
        return "RWY" + match.group(1).zfill(2)
    match = re.search(r"\b([0-9]{2}[LRC]?)\b", proc_ident)
    if match:
        return "RWY" + match.group(1)
    if "-" in proc_ident:
        return proc_ident
    return re.sub(r"[^A-Z0-9]+", "_", chart_name or proc_ident)[:40]


def family_key(row: dict[str, Any]) -> str:
    return "|".join([airport_of(row), runway_key(row), procedure_type_of(row)])


def exact_proc_key(row: dict[str, Any]) -> str:
    return "|".join([airport_of(row), proc_ident_of(row)])


def forbidden_row(row: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "source": source,
        "chart_id": row.get("chart_id"),
        "airport": airport_of(row),
        "proc_ident": proc_ident_of(row),
        "chart_name": row.get("chart_name"),
        "procedure_type": procedure_type_of(row),
        "pdf_name": normalize_pdf(row),
        "exact_proc_key": exact_proc_key(row),
        "family_key": family_key(row),
        "image_path": row.get("image_path"),
        "target_path": row.get("target_path") or row.get("canonical_proxy_gt_file"),
    }


def load_forbidden(formal300_manifest: Path, pilot10_manifest: Path, pilot100_manifest: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(forbidden_row(row, "formal300_forbidden_default") for row in json.loads(formal300_manifest.read_text(encoding="utf-8")))
    rows.extend(forbidden_row(row, "pilot10_forbidden") for row in read_jsonl(pilot10_manifest))
    if pilot100_manifest.exists():
        rows.extend(forbidden_row(row, "pilot100_external_forbidden_heldout") for row in read_jsonl(pilot100_manifest))
    return rows


def forbidden_sets(rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    return {
        "chart_id": {str(row["chart_id"]) for row in rows if row.get("chart_id")},
        "pdf_name": {str(row["pdf_name"]).upper() for row in rows if row.get("pdf_name")},
        "exact_proc_key": {str(row["exact_proc_key"]) for row in rows if row.get("exact_proc_key")},
        "family_key": {str(row["family_key"]) for row in rows if row.get("family_key")},
        "image_path": {str(row["image_path"]) for row in rows if row.get("image_path")},
        "target_path": {str(row["target_path"]) for row in rows if row.get("target_path")},
    }


def leg_count_from_candidate(row: dict[str, Any]) -> int:
    groups = row.get("missed_groups") or []
    if not groups:
        return 0
    return max(int(group[1]) for group in groups)


def select_candidates(
    candidates: list[dict[str, Any]],
    forbidden: dict[str, set[str]],
    required_count: int,
    candidate_margin: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    eligible: list[dict[str, Any]] = []
    exclusion_counts: Counter[str] = Counter()
    for row in candidates:
        chart_id = str(row.get("chart_id"))
        pdf_name = normalize_pdf(row)
        ekey = exact_proc_key(row)
        fkey = family_key(row)
        if chart_id in forbidden["chart_id"]:
            exclusion_counts["forbidden_chart_id"] += 1
            continue
        if pdf_name in forbidden["pdf_name"]:
            exclusion_counts["forbidden_pdf_name"] += 1
            continue
        if ekey in forbidden["exact_proc_key"]:
            exclusion_counts["forbidden_exact_proc_key"] += 1
            continue
        if fkey in forbidden["family_key"]:
            exclusion_counts["forbidden_family_key"] += 1
            continue
        if leg_count_from_candidate(row) <= 0:
            exclusion_counts["no_missed_approach_legs"] += 1
            continue
        eligible.append(row)

    buckets: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        buckets[(procedure_type_of(row), leg_count_from_candidate(row))].append(row)
    for rows in buckets.values():
        rows.sort(key=lambda item: (airport_of(item), proc_ident_of(item), normalize_pdf(item)))

    target = required_count + candidate_margin
    selected: list[dict[str, Any]] = []
    used = {"chart_id": set(), "pdf_name": set(), "exact_proc_key": set(), "family_key": set()}
    bucket_keys = sorted(buckets, key=lambda key: (-len(buckets[key]), key[0], key[1]))
    while len(selected) < target and bucket_keys:
        progress = False
        for key in list(bucket_keys):
            rows = buckets[key]
            picked_index = None
            for index, row in enumerate(rows):
                values = {
                    "chart_id": str(row.get("chart_id")),
                    "pdf_name": normalize_pdf(row),
                    "exact_proc_key": exact_proc_key(row),
                    "family_key": family_key(row),
                }
                if any(values[name] in used[name] for name in used):
                    continue
                picked_index = index
                break
            if picked_index is None:
                bucket_keys.remove(key)
                continue
            row = rows.pop(picked_index)
            selected.append(row)
            for name, values in used.items():
                values.add({
                    "chart_id": str(row.get("chart_id")),
                    "pdf_name": normalize_pdf(row),
                    "exact_proc_key": exact_proc_key(row),
                    "family_key": family_key(row),
                }[name])
            progress = True
            if len(selected) >= target:
                break
        if not progress:
            break

    report = {
        "candidate_count": len(candidates),
        "eligible_count": len(eligible),
        "requested_materialized_count": required_count,
        "candidate_margin": candidate_margin,
        "selected_candidate_count": len(selected),
        "exclusion_counts": dict(exclusion_counts),
        "selected_candidate_type_distribution": dict(Counter(procedure_type_of(row) for row in selected)),
        "selected_candidate_leg_count_distribution": dict(Counter(leg_count_from_candidate(row) for row in selected)),
    }
    if len(selected) < required_count:
        raise RuntimeError(f"Only selected {len(selected)} candidates; need {required_count}.")
    return selected, report


def sample_record(
    *,
    output_index: int,
    row: dict[str, Any],
    split: str,
    output_root: Path,
    dataset_dir: Path,
    image_path: Path,
    pdf_path: Path,
    target_path: Path,
    raw_cifp_path: Path,
    dims: dict[str, int],
    canonical: dict[str, Any],
    label_source: str,
) -> dict[str, Any]:
    chart_id = row["chart_id"]
    return {
        "sample_id": f"d_sft_{split}_{output_index:04d}",
        "split": split,
        "chart_id": chart_id,
        "airport": row["icao"],
        "apt_ident": row.get("apt_ident"),
        "airport_name": row.get("airport_name"),
        "city": row.get("city"),
        "state": row.get("state"),
        "volume": row.get("volume"),
        "proc_ident": row["proc_ident"],
        "chart_name": row["chart_name"],
        "procedure_type": procedure_type_of(row),
        "pdf_name": normalize_pdf(row),
        "pdf_url": f"https://aeronav.faa.gov/d-tpp/2604/{normalize_pdf(row)}",
        "pdf_path": str(pdf_path.resolve()),
        "image_path": str(image_path.resolve()),
        "target_path": str(target_path.resolve()),
        "raw_cifp_file": str(raw_cifp_path.resolve()),
        "family_key": family_key(row),
        "exact_proc_key": exact_proc_key(row),
        "leg_count": len(canonical["missed_approach"]["legs"]),
        "image_dimensions": dims,
        "pdf_sha256": sha256_file(pdf_path),
        "image_sha256": sha256_file(image_path),
        "target_sha256": sha256_file(target_path),
        "raw_cifp_sha256": sha256_file(raw_cifp_path),
        "label_source": label_source,
        "excluded_from_formal300": True,
        "excluded_from_pilot10": True,
        "excluded_from_pilot100_external": True,
        "excluded_from_formal_evaluation": True,
        "sample_role": "d_sft_training_or_dev_only_not_formal_evaluation",
    }


def build_training_jsonl(rows: list[dict[str, Any]], prompt_text: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            target = json.loads(Path(row["target_path"]).read_text(encoding="utf-8"))
            completion = json.dumps(target, ensure_ascii=False, separators=(",", ":"))
            item = {
                "sample_id": row["sample_id"],
                "split": row["split"],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": row["image_path"]},
                            {"type": "text", "text": prompt_text},
                        ],
                    },
                    {"role": "assistant", "content": completion},
                ],
            }
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def leakage_report(
    rows: list[dict[str, Any]],
    forbidden_rows: list[dict[str, Any]],
    training_jsonl_paths: list[Path],
) -> dict[str, Any]:
    forbidden = forbidden_sets(forbidden_rows)
    overlaps: dict[str, list[str]] = {}
    key_map = {
        "chart_id": {row["chart_id"] for row in rows},
        "pdf_name": {normalize_pdf(row) for row in rows},
        "exact_proc_key": {row["exact_proc_key"] for row in rows},
        "family_key": {row["family_key"] for row in rows},
        "image_path": {row["image_path"] for row in rows},
        "target_path": {row["target_path"] for row in rows},
    }
    for key, values in key_map.items():
        overlaps[key] = sorted(str(value) for value in (values & forbidden[key]))

    train_rows = [row for row in rows if row["split"] == "train"]
    dev_rows = [row for row in rows if row["split"] == "dev"]
    train_dev_overlaps = {
        "chart_id": sorted({row["chart_id"] for row in train_rows} & {row["chart_id"] for row in dev_rows}),
        "pdf_name": sorted({row["pdf_name"] for row in train_rows} & {row["pdf_name"] for row in dev_rows}),
        "family_key": sorted({row["family_key"] for row in train_rows} & {row["family_key"] for row in dev_rows}),
    }

    forbidden_target_strings = {str(row.get("target_path")) for row in forbidden_rows if row.get("target_path")}
    forbidden_image_strings = {str(row.get("image_path")) for row in forbidden_rows if row.get("image_path")}
    jsonl_leaks = []
    for path in training_jsonl_paths:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        target_hits = sorted(item for item in forbidden_target_strings if item and item in text)
        image_hits = sorted(item for item in forbidden_image_strings if item and item in text)
        if target_hits or image_hits:
            jsonl_leaks.append({"path": str(path), "target_hits": target_hits, "image_hits": image_hits})

    hard_leakage = any(overlaps[key] for key in ["chart_id", "pdf_name", "exact_proc_key", "family_key"])
    hard_leakage = hard_leakage or any(train_dev_overlaps.values()) or bool(jsonl_leaks)
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "hard_leakage": hard_leakage,
        "forbidden_overlap_counts": {key: len(value) for key, value in overlaps.items()},
        "forbidden_overlaps": overlaps,
        "train_dev_overlap_counts": {key: len(value) for key, value in train_dev_overlaps.items()},
        "train_dev_overlaps": train_dev_overlaps,
        "training_jsonl_forbidden_reference_hits": jsonl_leaks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare D-SFT train/dev data with no-leakage checks.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--train-count", type=int, default=500)
    parser.add_argument("--dev-count", type=int, default=100)
    parser.add_argument("--fallback-train-count", type=int, default=200)
    parser.add_argument("--fallback-dev-count", type=int, default=50)
    parser.add_argument("--candidate-margin", type=int, default=120)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--cifp-file", type=Path, default=DEFAULT_CIFP)
    parser.add_argument("--formal300-manifest", type=Path, default=DEFAULT_FORMAL300)
    parser.add_argument("--pilot10-manifest", type=Path, default=DEFAULT_PILOT10)
    parser.add_argument("--pilot100-manifest", type=Path, default=DEFAULT_PILOT100)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--dataset-name", default="d_sft_train500_dev100")
    args = parser.parse_args()

    output_root = args.output_root
    dataset_dir = output_root / "data" / args.dataset_name
    pdf_dir = dataset_dir / "pdfs"
    image_dir = dataset_dir / "images"
    target_dir = dataset_dir / "targets" / "canonical_proxy_gt"
    raw_cifp_dir = dataset_dir / "targets" / "raw_cifp_per_procedure"
    source_dir = dataset_dir / "source"
    reports_dir = output_root / "reports"
    training_jsonl_dir = output_root / "training_jsonl"

    forbidden_rows = load_forbidden(args.formal300_manifest, args.pilot10_manifest, args.pilot100_manifest)
    forbidden_dir = output_root / "data" / "forbidden"
    write_jsonl(forbidden_dir / "forbidden_manifest.jsonl", forbidden_rows)
    fsets = forbidden_sets(forbidden_rows)
    write_json(
        forbidden_dir / "forbidden_overlap_keys.json",
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sources": {
                "formal300_manifest": str(args.formal300_manifest.resolve()),
                "pilot10_manifest": str(args.pilot10_manifest.resolve()),
                "pilot100_manifest": str(args.pilot100_manifest.resolve()),
            },
            "counts": {key: len(value) for key, value in fsets.items()},
            "keys": {key: sorted(value) for key, value in fsets.items()},
        },
    )

    candidates = json.loads(args.candidates.read_text(encoding="utf-8"))
    required_count = args.train_count + args.dev_count
    try:
        selected, selection_report = select_candidates(candidates, fsets, required_count, args.candidate_margin)
        train_count = args.train_count
        dev_count = args.dev_count
        fallback_used = False
    except RuntimeError:
        train_count = args.fallback_train_count
        dev_count = args.fallback_dev_count
        required_count = train_count + dev_count
        selected, selection_report = select_candidates(candidates, fsets, required_count, args.candidate_margin)
        fallback_used = True

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    extracted, raw_buckets = build_cifp_index(args.cifp_file, selected)

    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    materialized_candidates: list[dict[str, Any]] = []

    for row in selected:
        if len(rows) >= required_count:
            break
        chart_id = row["chart_id"]
        extracted_item = extracted.get(chart_id, {})
        if extracted_item.get("error"):
            skipped.append({"chart_id": chart_id, "reason": f"cifp_extraction_{extracted_item.get('error')}"})
            continue
        canonical = project_procedure(extracted_item, row["chart_name"])
        validation_errors = [error.message for error in validator.iter_errors(canonical)]
        if validation_errors:
            skipped.append({"chart_id": chart_id, "reason": "canonical_schema_validation_failed", "error": validation_errors[0]})
            continue

        split = "train" if len([item for item in rows if item["split"] == "train"]) < train_count else "dev"
        output_index = len([item for item in rows if item["split"] == split]) + 1
        pdf_name = normalize_pdf(row)
        pdf_base = Path(pdf_name).stem
        image_name = f"{split}_{output_index:04d}__{chart_id}__{pdf_base}_p0.png"
        pdf_path = pdf_dir / split / pdf_name
        image_path = image_dir / split / image_name
        target_path = target_dir / split / f"{chart_id}.json"
        raw_cifp_path = raw_cifp_dir / split / f"{chart_id}.txt"

        download_pdf(f"https://aeronav.faa.gov/d-tpp/2604/{pdf_name}", pdf_path)
        dims = render_first_page(pdf_path, image_path)
        write_json(target_path, canonical)
        write_text(raw_cifp_path, raw_cifp_text(chart_id, raw_buckets.get(chart_id, [])))
        rows.append(
            sample_record(
                output_index=output_index,
                row=row,
                split=split,
                output_root=output_root,
                dataset_dir=dataset_dir,
                image_path=image_path,
                pdf_path=pdf_path,
                target_path=target_path,
                raw_cifp_path=raw_cifp_path,
                dims=dims,
                canonical=canonical,
                label_source="cifp_projection_canonical_proxy",
            )
        )
        materialized_candidates.append(row)

    if len(rows) < required_count:
        raise RuntimeError(f"Materialized {len(rows)} D-SFT rows; required {required_count}.")

    train_rows = [row for row in rows if row["split"] == "train"]
    dev_rows = [row for row in rows if row["split"] == "dev"]
    write_jsonl(dataset_dir / "train_manifest.jsonl", train_rows)
    write_jsonl(dataset_dir / "dev_manifest.jsonl", dev_rows)
    write_jsonl(dataset_dir / "combined_manifest.jsonl", rows)
    write_json(source_dir / "selected_candidates.json", materialized_candidates)

    prompt_text = args.prompt.read_text(encoding="utf-8").strip()
    train_jsonl = training_jsonl_dir / f"{args.dataset_name}.train.jsonl"
    dev_jsonl = training_jsonl_dir / f"{args.dataset_name}.dev.jsonl"
    build_training_jsonl(train_rows, prompt_text, train_jsonl)
    build_training_jsonl(dev_rows, prompt_text, dev_jsonl)

    leak_report = leakage_report(rows, forbidden_rows, [train_jsonl, dev_jsonl])
    write_json(reports_dir / "d_sft_no_leakage_report.json", leak_report)
    if leak_report["hard_leakage"]:
        raise RuntimeError("Hard D-SFT leakage detected; refusing to continue.")

    prep_report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_name": args.dataset_name,
        "fallback_used": fallback_used,
        "train_count": len(train_rows),
        "dev_count": len(dev_rows),
        "output_root": str(output_root.resolve()),
        "dataset_dir": str(dataset_dir.resolve()),
        "formal300_default_forbidden": True,
        "pilot10_forbidden": True,
        "pilot100_external_forbidden": True,
        "selection_report": selection_report,
        "materialized_type_distribution": dict(Counter(row["procedure_type"] for row in rows)),
        "materialized_leg_count_distribution": dict(Counter(row["leg_count"] for row in rows)),
        "materialized_family_count": len({row["family_key"] for row in rows}),
        "skipped_count": len(skipped),
        "skipped": skipped,
        "schema": {"path": str(args.schema.resolve()), "sha256": sha256_file(args.schema)},
        "prompt": {"path": str(args.prompt.resolve()), "sha256": sha256_file(args.prompt)},
        "training_jsonl": {
            "train": str(train_jsonl.resolve()),
            "train_sha256": sha256_file(train_jsonl),
            "dev": str(dev_jsonl.resolve()),
            "dev_sha256": sha256_file(dev_jsonl),
        },
        "no_leakage_report": str((reports_dir / "d_sft_no_leakage_report.json").resolve()),
    }
    write_json(reports_dir / "d_sft_dataset_preparation_report.json", prep_report)
    write_json(dataset_dir / "manifest_summary.json", prep_report)
    checksum_lines = []
    for path in sorted(p for p in dataset_dir.rglob("*") if p.is_file()):
        checksum_lines.append(f"{sha256_file(path)}  {path.relative_to(dataset_dir).as_posix()}")
    write_text(dataset_dir / "checksums.sha256", "\n".join(checksum_lines))
    print(json.dumps(prep_report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
