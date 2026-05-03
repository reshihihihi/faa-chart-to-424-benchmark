from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_b1prime_c4_pilot10 import build_field_candidates  # noqa: E402


EXPERIMENT5_DIR = REPO_ROOT / "benchmark_exports" / "derived" / "v2" / "experiment5_diagnostic"
RUN_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_smoke_20260503_r2"
SMOKE_MANIFEST = EXPERIMENT5_DIR / "smoke20_manifest.jsonl"
ROI_FIELD_SCHEMA = REPO_ROOT / "schemas" / "experiment5_roi_field_candidates.schema.v1.json"

SOURCE_VIEW_MANIFEST = Path(r"E:\experiment3\zu4\source_views\manifests\source_view_manifest.jsonl")
SOURCE_VIEW_SUMMARY_ORIGINAL = Path(r"E:\experiment3\zu4\source_views\reports\source_view_summary.json")
SOURCE_VIEW_SUMMARY_SNAPSHOT = EXPERIMENT5_DIR / "source_view_summary_for_experiment5_current.json"
OCR_ARTIFACTS = {
    "MISSED_APPROACH_TEXT": Path(
        r"E:\experiment3\zu4\ocr_artifacts\V1_ma_text_only\ocr1_paddleocr_ppocrv5_source_view_20260501_r1"
    ),
    "PLAN_VIEW": Path(
        r"E:\experiment3\zu4\ocr_artifacts\V3_plan_view_only\ocr1_paddleocr_ppocrv5_source_view_20260501_r1"
    ),
    "MISSED_APPROACH_DETAIL_AREA": Path(
        r"E:\experiment3\zu4\ocr_artifacts\V4_icon_detail_only\ocr1_paddleocr_ppocrv5_source_view_20260501_r1"
    ),
    "PLAN_DETAIL_NO_MA": Path(
        r"E:\experiment3\zu4\ocr_artifacts\V5_plan_detail_no_ma\ocr1_paddleocr_ppocrv5_source_view_20260501_r1"
    ),
}
SOURCE_VIEW_VARIANTS = {
    "MISSED_APPROACH_TEXT": "V1_ma_text_only",
    "PLAN_VIEW": "V3_plan_view_only",
    "MISSED_APPROACH_DETAIL_AREA": "V4_icon_detail_only",
    "PLAN_DETAIL_NO_MA": "V5_plan_detail_no_ma",
}
SECTION_BY_REGION = {
    "MISSED_APPROACH_TEXT": "missed_approach_text",
    "PLAN_VIEW": "plan_view",
    "MISSED_APPROACH_DETAIL_AREA": "missed_approach_detail_area",
}
REGIONS_BY_PROFILE = {
    "T": ["MISSED_APPROACH_TEXT"],
    "TPD": ["MISSED_APPROACH_TEXT", "PLAN_VIEW", "MISSED_APPROACH_DETAIL_AREA"],
    "PD": ["PLAN_VIEW", "MISSED_APPROACH_DETAIL_AREA"],
}
CANDIDATE_KEYS = [
    "fix_candidates",
    "altitude_candidates",
    "turn_candidates",
    "course_candidates",
    "hold_candidates",
    "instruction_snippets",
    "track_to_fix_snippets",
    "route_sequence_snippets",
    "direct_phrase_snippets",
    "climb_phrase_snippets",
]
REGION_MARKERS = ("[MISSED_APPROACH_TEXT]", "[PLAN_VIEW]", "[MISSED_APPROACH_DETAIL_AREA]")


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def validation_errors(obj: Any, validator: Draft202012Validator) -> list[str]:
    errors = sorted(validator.iter_errors(obj), key=lambda err: list(err.path))
    return [(".".join(str(part) for part in err.path) or "$") + f": {err.message}" for err in errors]


def load_ocr_manifest(run_root: Path) -> dict[str, dict[str, Any]]:
    return {row["chart_id"]: row for row in read_jsonl(run_root / "manifest.jsonl")}


def load_source_view_rows(path: Path) -> list[dict[str, Any]]:
    return read_jsonl(path)


def source_view_summary_snapshot(rows: list[dict[str, Any]], manifest_sha256: str | None) -> dict[str, Any]:
    variant_counts = Counter(row.get("variant") for row in rows)
    chart_ids = sorted({row.get("chart_id") for row in rows if row.get("chart_id")})
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary_type": "experiment5_current_source_view_manifest_snapshot",
        "manifest_path": str(SOURCE_VIEW_MANIFEST),
        "manifest_sha256": manifest_sha256,
        "original_summary_path": str(SOURCE_VIEW_SUMMARY_ORIGINAL),
        "original_summary_sha256": sha256_file(SOURCE_VIEW_SUMMARY_ORIGINAL),
        "chart_count": len(chart_ids),
        "row_count": len(rows),
        "variant_counts": dict(sorted(variant_counts.items())),
        "note": "Experiment 5 r2 freezes the current source-view manifest by snapshotting its current sha256.",
    }


def load_source_view_manifest(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(row["chart_id"], row["variant"]): row for row in rows}


def region_text_blocks(
    chart_id: str,
    ocr_by_region: dict[str, dict[str, dict[str, Any]]],
    regions: list[str],
) -> tuple[str, dict[str, dict[str, Any]]]:
    pieces: list[str] = []
    region_meta: dict[str, dict[str, Any]] = {}
    offset = 0
    for region in regions:
        row = ocr_by_region[region][chart_id]
        text = Path(row["full_text_path"]).read_text(encoding="utf-8").strip()
        header = f"[{region}]\n"
        block = f"{header}{text}\n"
        start = offset + len(header)
        end = start + len(text)
        region_meta[region] = {
            "text": text,
            "source_section": SECTION_BY_REGION[region],
            "global_text_start": start,
            "global_text_end": end,
        }
        pieces.append(block)
        offset += len(block) + 1
    return "\n".join(pieces).strip() + "\n", region_meta


def candidate_sort_key(candidate: dict[str, Any]) -> tuple[int, float, int, str]:
    source_order = {
        "MISSED_APPROACH_TEXT": 0,
        "PLAN_VIEW": 1,
        "MISSED_APPROACH_DETAIL_AREA": 2,
    }
    confidence = candidate.get("confidence")
    return (
        source_order.get(candidate.get("source_region"), 9),
        -(confidence if isinstance(confidence, (int, float)) else 0),
        candidate.get("global_start_char") if isinstance(candidate.get("global_start_char"), int) else 10**9,
        str(candidate.get("value")),
    )


def unique_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for candidate in sorted(candidates, key=candidate_sort_key):
        key = json.dumps(
            {
                "value": candidate.get("value"),
                "field_type": candidate.get("field_type"),
                "source_region": candidate.get("source_region"),
                "source_snippet": candidate.get("source_snippet"),
                "region_local_start_char": candidate.get("region_local_start_char"),
                "region_local_end_char": candidate.get("region_local_end_char"),
                "rule_id": candidate.get("rule_id"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(candidate)
    return out


def region_aware_candidates(
    *,
    chart_id: str,
    region_profile: str,
    region_meta: dict[str, dict[str, Any]],
    regions: list[str],
) -> dict[str, Any]:
    combined: dict[str, list[dict[str, Any]]] = {key: [] for key in CANDIDATE_KEYS}
    for region in regions:
        meta = region_meta[region]
        raw = build_field_candidates(meta["text"], chart_id)
        for key in CANDIDATE_KEYS:
            for item in raw["field_candidates"].get(key, []):
                local_start = item.get("source_start_char")
                local_end = item.get("source_end_char")
                global_start = meta["global_text_start"] + local_start if isinstance(local_start, int) else None
                global_end = meta["global_text_start"] + local_end if isinstance(local_end, int) else None
                fixed = dict(item)
                fixed["source_region"] = region
                fixed["source_section"] = meta["source_section"]
                fixed["region_local_start_char"] = local_start
                fixed["region_local_end_char"] = local_end
                fixed["global_start_char"] = global_start
                fixed["global_end_char"] = global_end
                fixed["source_start_char"] = global_start
                fixed["source_end_char"] = global_end
                combined[key].append(fixed)
    return {
        "schema_version": "experiment5_roi_field_candidates_schema_v1",
        "chart_id": chart_id,
        "candidate_source": "experiment5_roi_ocr_region_aware_field_matcher_v1_from_b1prime_v8",
        "region_profile": region_profile,
        "source_contract": {
            "source": "same_chart_human_confirmed_roi_ocr_text",
            "allows_human_confirmed_roi": True,
            "allows_ocr_bbox": False,
            "allows_chart_image_pixels": False,
            "allows_canonical_target": False,
            "allows_gold_observable_evidence": False,
        },
        "leakage_policy": {
            "uses_canonical_target": False,
            "uses_expected_value": False,
            "uses_gold_field_to_leg_mapping": False,
            "uses_human_evidence_provenance": False,
            "uses_gold_observable_evidence": False,
            "uses_cifp_or_arinc_424": False,
            "uses_scorer_output": False,
        },
        "field_candidates": {key: unique_candidates(value) for key, value in combined.items()},
    }


def candidate_counts(candidates: dict[str, Any]) -> dict[str, int]:
    return {key: len(value) for key, value in candidates["field_candidates"].items()}


def candidate_audit(candidates: dict[str, Any]) -> dict[str, Any]:
    source_sections = Counter()
    source_regions = Counter()
    cross_region_snippets = 0
    unknown_source_sections = 0
    for items in candidates["field_candidates"].values():
        for item in items:
            section = item.get("source_section") or "unknown"
            region = item.get("source_region") or "unknown"
            source_sections[section] += 1
            source_regions[region] += 1
            if section == "unknown":
                unknown_source_sections += 1
            snippet = str(item.get("source_snippet") or "")
            if any(marker in snippet for marker in REGION_MARKERS):
                cross_region_snippets += 1
    return {
        "candidate_count_total": sum(candidate_counts(candidates).values()),
        "candidate_counts": candidate_counts(candidates),
        "candidate_source_sections": dict(sorted(source_sections.items())),
        "candidate_source_regions": dict(sorted(source_regions.items())),
        "unknown_source_section_count": unknown_source_sections,
        "cross_region_snippet_count": cross_region_snippets,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Experiment 5 smoke20 r2 ROI OCR manifests and candidates.")
    parser.add_argument("--smoke-manifest", type=Path, default=SMOKE_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=EXPERIMENT5_DIR)
    parser.add_argument("--run-dir", type=Path, default=RUN_DIR)
    args = parser.parse_args()

    smoke_rows = read_jsonl(args.smoke_manifest)
    smoke_ids = [row["chart_id"] for row in smoke_rows]
    source_view_rows = load_source_view_rows(SOURCE_VIEW_MANIFEST)
    source_view_manifest_sha256 = sha256_file(SOURCE_VIEW_MANIFEST)
    source_view_summary = source_view_summary_snapshot(source_view_rows, source_view_manifest_sha256)
    write_json(SOURCE_VIEW_SUMMARY_SNAPSHOT, source_view_summary)
    source_views = load_source_view_manifest(source_view_rows)
    source_view_summary_sha256 = sha256_file(SOURCE_VIEW_SUMMARY_SNAPSHOT)
    source_view_summary_manifest_sha256 = source_view_summary.get("manifest_sha256")
    source_view_hash_matches_summary = source_view_manifest_sha256 == source_view_summary_manifest_sha256
    ocr_by_region = {region: load_ocr_manifest(root) for region, root in OCR_ARTIFACTS.items()}

    schema = json.loads(ROI_FIELD_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    roi_rows: list[dict[str, Any]] = []
    roi_ocr_rows: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []

    for chart_id in smoke_ids:
        regions: dict[str, Any] = {}
        for region, variant in SOURCE_VIEW_VARIANTS.items():
            source_row = source_views.get((chart_id, variant))
            ocr_row = ocr_by_region[region].get(chart_id)
            if source_row is None:
                missing.append({"chart_id": chart_id, "missing": f"source_view:{variant}"})
                continue
            if ocr_row is None:
                missing.append({"chart_id": chart_id, "missing": f"roi_ocr:{region}"})
                continue
            regions[region] = {
                "region": region,
                "variant": variant,
                "source_view_image_path": source_row["output_image_path"],
                "source_view_image_sha256": source_row["output_image_sha256"],
                "source_image_path": source_row["source_image_path"],
                "source_image_sha256": source_row["source_image_sha256"],
                "roi_rects_pixels": source_row.get("roi_rects_pixels"),
                "roi_ids": source_row.get("roi_ids"),
                "roi_source": source_row.get("roi_source"),
                "source_pr": source_row.get("source_pr"),
                "source_commit": source_row.get("source_commit"),
            }
            text_path = Path(ocr_row["full_text_path"])
            text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
            roi_ocr_rows.append(
                {
                    "chart_id": chart_id,
                    "region": region,
                    "variant": variant,
                    "ocr_id": ocr_row.get("ocr_id"),
                    "engine": ocr_row.get("engine"),
                    "ocr_version": ocr_row.get("ocr_version"),
                    "block_count": ocr_row.get("block_count"),
                    "image_path": ocr_row.get("image_path"),
                    "full_text_path": ocr_row.get("full_text_path"),
                    "full_text_sha256": ocr_row.get("full_text_sha256"),
                    "raw_blocks_path": ocr_row.get("raw_blocks_path"),
                    "raw_blocks_sha256": ocr_row.get("raw_blocks_sha256"),
                    "char_count": len(text),
                    "nonempty": bool(text.strip()),
                }
            )
        roi_rows.append(
            {
                "chart_id": chart_id,
                "source": "experiment4_pr18_human_confirmed_source_views_current_snapshot",
                "source_view_manifest_path": str(SOURCE_VIEW_MANIFEST),
                "source_view_manifest_sha256": source_view_manifest_sha256,
                "source_view_summary_path": str(SOURCE_VIEW_SUMMARY_SNAPSHOT),
                "source_view_summary_sha256": source_view_summary_sha256,
                "source_view_summary_manifest_sha256": source_view_summary_manifest_sha256,
                "source_view_hash_matches_summary": source_view_hash_matches_summary,
                "regions": regions,
            }
        )

    input_manifest_rows: list[dict[str, Any]] = []
    candidate_validation_rows: list[dict[str, Any]] = []
    profile_counter: Counter[str] = Counter()
    audit_totals: Counter[str] = Counter()

    for chart_id in smoke_ids:
        for profile, regions in REGIONS_BY_PROFILE.items():
            ocr_text, region_meta = region_text_blocks(chart_id, ocr_by_region, regions)
            input_path = args.run_dir / "inputs" / f"B3_{profile}" / f"{chart_id}.txt"
            write_text(input_path, ocr_text)
            candidates = region_aware_candidates(
                chart_id=chart_id,
                region_profile=profile,
                region_meta=region_meta,
                regions=regions,
            )
            audit = candidate_audit(candidates)
            audit_totals["unknown_source_section_count"] += audit["unknown_source_section_count"]
            audit_totals["cross_region_snippet_count"] += audit["cross_region_snippet_count"]
            candidate_path = args.run_dir / "field_candidates" / f"B3_{profile}" / f"{chart_id}.json"
            write_json(candidate_path, candidates)
            errors = validation_errors(candidates, validator)
            validation_path = args.run_dir / "field_candidates_validation" / f"B3_{profile}" / f"{chart_id}.json"
            write_json(validation_path, errors)
            input_manifest_rows.append(
                {
                    "chart_id": chart_id,
                    "region_profile": profile,
                    "regions": regions,
                    "roi_ocr_input_text_path": str(input_path),
                    "roi_ocr_input_text_sha256": sha256_file(input_path),
                    "field_candidates_path": str(candidate_path),
                    "field_candidates_sha256": sha256_file(candidate_path),
                    "field_candidates_schema_path": str(ROI_FIELD_SCHEMA),
                    "field_candidates_schema_sha256": sha256_file(ROI_FIELD_SCHEMA),
                    "field_candidates_validation_path": str(validation_path),
                    "field_candidates_validation_error_count": len(errors),
                    "candidate_audit": audit,
                    "allowed_methods": {
                        "A3_GoldText_Rules": False,
                        "B2a_GoldText_LLM": False,
                        "B2b_GoldText_FieldCandidates_LLM": False,
                        "B3_T": profile == "T",
                        "B3_TPD": profile == "TPD",
                        "B4_TPD": profile == "TPD",
                        "B3_PD": profile == "PD",
                    },
                    "leakage_policy": candidates["leakage_policy"],
                }
            )
            profile_counter[profile] += 1
            candidate_validation_rows.append(
                {
                    "chart_id": chart_id,
                    "region_profile": profile,
                    "validation_error_count": len(errors),
                    "validation_errors": errors,
                    "candidate_audit": audit,
                }
            )

    write_jsonl(args.out_dir / "roi_manifest_for_experiment5_smoke20.jsonl", roi_rows)
    write_jsonl(args.out_dir / "roi_ocr_manifest_smoke20.jsonl", roi_ocr_rows)
    write_jsonl(args.out_dir / "roi_ocr_candidate_input_manifest_smoke20.jsonl", input_manifest_rows)
    write_jsonl(args.run_dir / "manifests" / "roi_manifest_for_experiment5_smoke20.jsonl", roi_rows)
    write_jsonl(args.run_dir / "manifests" / "roi_ocr_manifest_smoke20.jsonl", roi_ocr_rows)
    write_jsonl(args.run_dir / "manifests" / "roi_ocr_candidate_input_manifest_smoke20.jsonl", input_manifest_rows)
    write_jsonl(args.run_dir / "reports" / "roi_field_candidate_validation_smoke20.jsonl", candidate_validation_rows)

    candidate_validation_error_rows = sum(1 for row in candidate_validation_rows if row["validation_error_count"])
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_dir.name,
        "smoke20_count": len(smoke_ids),
        "source_view_manifest": str(SOURCE_VIEW_MANIFEST),
        "source_view_manifest_sha256": source_view_manifest_sha256,
        "source_view_summary": str(SOURCE_VIEW_SUMMARY_SNAPSHOT),
        "source_view_summary_sha256": source_view_summary_sha256,
        "source_view_summary_manifest_sha256": source_view_summary_manifest_sha256,
        "source_view_hash_matches_summary": source_view_hash_matches_summary,
        "source_view_original_summary": str(SOURCE_VIEW_SUMMARY_ORIGINAL),
        "source_view_original_summary_sha256": sha256_file(SOURCE_VIEW_SUMMARY_ORIGINAL),
        "region_profiles_prepared": dict(sorted(profile_counter.items())),
        "roi_rows": len(roi_rows),
        "roi_ocr_rows": len(roi_ocr_rows),
        "candidate_input_rows": len(input_manifest_rows),
        "missing_count": len(missing),
        "missing": missing,
        "candidate_schema": str(ROI_FIELD_SCHEMA),
        "candidate_schema_sha256": sha256_file(ROI_FIELD_SCHEMA),
        "candidate_validation_error_rows": candidate_validation_error_rows,
        "candidate_unknown_source_section_count": audit_totals["unknown_source_section_count"],
        "candidate_cross_region_snippet_count": audit_totals["cross_region_snippet_count"],
        "ready_for_smoke_b3_b4": (
            not missing
            and candidate_validation_error_rows == 0
            and source_view_hash_matches_summary
            and audit_totals["unknown_source_section_count"] == 0
            and audit_totals["cross_region_snippet_count"] == 0
        ),
        "provenance_warnings": []
        if source_view_hash_matches_summary
        else ["source-view current manifest hash still does not match Experiment 5 snapshot summary."],
        "blocked_human_inputs": [
            "gold_ma_text_smoke20_template.jsonl must be completed before A3/B2a/B2b.",
            "gold_observable_smoke20_template.jsonl must be completed before G0/G1/G2/G3.",
            "rule_registry.yaml must be reviewed before A3/B4/G1/G3 formal claims.",
        ],
    }
    write_json(args.run_dir / "reports" / "experiment5_smoke_input_readiness.json", summary)

    report_md = [
        "# Experiment 5 smoke20 r2 input readiness",
        "",
        f"- run_id: `{summary['run_id']}`",
        f"- created_at_utc: `{summary['created_at_utc']}`",
        f"- smoke20_count: {summary['smoke20_count']}",
        f"- source_view_hash_matches_summary: {summary['source_view_hash_matches_summary']}",
        f"- candidate_schema: `{summary['candidate_schema']}`",
        f"- candidate_validation_error_rows: {summary['candidate_validation_error_rows']}",
        f"- candidate_unknown_source_section_count: {summary['candidate_unknown_source_section_count']}",
        f"- candidate_cross_region_snippet_count: {summary['candidate_cross_region_snippet_count']}",
        f"- ready_for_smoke_b3_b4: {summary['ready_for_smoke_b3_b4']}",
        "",
        "## Region profiles prepared",
        "",
        "| profile | rows |",
        "|---|---:|",
    ]
    report_md.extend(f"| `{key}` | {value} |" for key, value in sorted(profile_counter.items()))
    report_md.extend(
        [
            "",
            "## Notes",
            "",
            "- r2 uses a current Experiment 5 source-view summary snapshot to close source-view provenance.",
            "- r2 candidates are generated per region and then merged; snippets must not cross region markers.",
            "- Human gold inputs are still required before A3/B2/G methods.",
        ]
    )
    write_text(args.run_dir / "reports" / "experiment5_smoke_input_readiness.md", "\n".join(report_md) + "\n")

    report_zh = [
        "# 实验组5 smoke20 r2 输入准备报告",
        "",
        f"- run_id: `{summary['run_id']}`",
        f"- 生成时间 UTC: `{summary['created_at_utc']}`",
        f"- smoke20 样本数: {summary['smoke20_count']}",
        f"- source-view hash 是否闭合: {summary['source_view_hash_matches_summary']}",
        f"- candidate schema: `{summary['candidate_schema']}`",
        f"- candidate validation error rows: {summary['candidate_validation_error_rows']}",
        f"- unknown source_section 数量: {summary['candidate_unknown_source_section_count']}",
        f"- cross-region snippet 数量: {summary['candidate_cross_region_snippet_count']}",
        f"- B3/B4 smoke 前置是否就绪: {summary['ready_for_smoke_b3_b4']}",
        "",
        "## 已准备的 region profiles",
        "",
        "| profile | 含义 | 行数 | 可用于 |",
        "|---|---|---:|---|",
        f"| `T` | 只使用 MISSED_APPROACH_TEXT ROI OCR | {profile_counter.get('T', 0)} | B3-T |",
        f"| `TPD` | 使用 MISSED_APPROACH_TEXT + PLAN_VIEW + DETAIL_AREA ROI OCR | {profile_counter.get('TPD', 0)} | B3-TPD, B4-TPD |",
        f"| `PD` | 使用 PLAN_VIEW + DETAIL_AREA ROI OCR，不含复飞文字 | {profile_counter.get('PD', 0)} | B3-PD optional |",
        "",
        "## 说明",
        "",
        "- r2 通过 Experiment 5 当前 source-view summary snapshot 闭合 provenance。",
        "- r2 candidates 按区域独立生成后再合并，候选片段不得跨越区域标签。",
        "- A3/B2/G 系列仍需要人工 gold text / gold observable 后才能执行。",
    ]
    write_text(args.run_dir / "reports" / "experiment5_smoke_input_readiness_zh.md", "\n".join(report_zh) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ready_for_smoke_b3_b4"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
