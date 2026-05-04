from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "experiment5"))

from prepare_experiment5_smoke_inputs import (  # noqa: E402
    REGIONS_BY_PROFILE,
    ROI_FIELD_SCHEMA,
    candidate_audit,
    region_aware_candidates,
    sha256_file,
    validation_errors,
)


DEFAULT_RUN_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_dev50_20260504_r6_strict_reviewed_runs"
DEFAULT_REVIEWED_MA_TEXT = (
    REPO_ROOT
    / "formal_runs"
    / "experiment5"
    / "experiment5_dev50_20260504_r5_ma_text_ocr_review"
    / "inputs"
    / "gold_ma_text_dev50_ocr_reviewed.jsonl"
)
DEFAULT_PD_VISIBLE = (
    REPO_ROOT
    / "formal_runs"
    / "experiment5"
    / "experiment5_dev50_20260504_r3_strict_no_leak"
    / "inputs"
    / "pd_visible_candidates_dev50_strict.jsonl"
)

SOURCE_SECTION = {
    "MISSED_APPROACH_TEXT": "missed_approach_text",
    "PLAN_VIEW": "plan_view",
    "MISSED_APPROACH_DETAIL_AREA": "missed_approach_detail_area",
}


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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def load_reviewed_text(path: Path) -> dict[str, dict[str, Any]]:
    return {row["chart_id"]: row for row in read_jsonl(path)}


def load_pd_visible_text(path: Path) -> dict[str, dict[str, Any]]:
    return {row["chart_id"]: row for row in read_jsonl(path)}


def pd_lines(row: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for obs in row.get("visible_observables") or []:
        region_type = obs.get("region_type")
        if obs.get("observable_type") == "visible_text_literal":
            literal = str(obs.get("visible_literal") or "").strip()
            if literal:
                lines.append(literal)
        elif region_type:
            lines.append(str(region_type))
    return lines


def roi_text_for_profile(chart_id: str, profile: str, ma_rows: dict[str, dict[str, Any]], pd_rows: dict[str, dict[str, Any]]) -> tuple[str, dict[str, dict[str, Any]]]:
    region_text: dict[str, str] = {
        "MISSED_APPROACH_TEXT": "",
        "PLAN_VIEW": "",
        "MISSED_APPROACH_DETAIL_AREA": "",
    }
    if profile in {"T", "TPD"}:
        region_text["MISSED_APPROACH_TEXT"] = str(ma_rows[chart_id]["gold_ma_prose"]).strip()
    if profile in {"PD", "TPD"}:
        region_text["MISSED_APPROACH_DETAIL_AREA"] = "\n".join(pd_lines(pd_rows[chart_id])).strip()

    pieces: list[str] = []
    region_meta: dict[str, dict[str, Any]] = {}
    offset = 0
    for region in REGIONS_BY_PROFILE[profile]:
        text = region_text[region]
        header = f"[{region}]\n"
        block = f"{header}{text}\n"
        start = offset + len(header)
        end = start + len(text)
        pieces.append(block)
        region_meta[region] = {
            "text": text,
            "source_section": SOURCE_SECTION[region],
            "global_text_start": start,
            "global_text_end": end,
        }
        offset += len(block) + 1
    return "\n".join(pieces).strip() + "\n", region_meta


def scan_forbidden(paths: list[Path]) -> dict[str, Any]:
    forbidden_keys = {
        "annotation_pr28_json",
        "target",
        "score",
        "canonical_answer",
        "canonical_leg_index",
        "Q_terminator",
        "leg_type",
        "field_review_v2",
        "candidate_leg_id",
        "expected_value",
        "target_value",
    }
    hits: list[dict[str, Any]] = []

    def visit(value: Any, path: str, source: Path, line: int) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                next_path = f"{path}.{key}" if path else key
                if key in forbidden_keys:
                    hits.append({"file": rel(source), "line": line, "key_path": next_path})
                visit(child, next_path, source, line)
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                visit(child, f"{path}[{idx}]", source, line)

    rows_scanned = 0
    for source in paths:
        for line, row in enumerate(read_jsonl(source), start=1):
            rows_scanned += 1
            visit(row, "", source, line)
    return {
        "status": "PASS" if not hits else "FAIL",
        "rows_scanned": rows_scanned,
        "forbidden_key_hit_count": len(hits),
        "forbidden_key_hits": hits[:50],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare dev50 B3/B4 ROI inputs from reviewed MA text and strict PD observables.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--reviewed-ma-text", type=Path, default=DEFAULT_REVIEWED_MA_TEXT)
    parser.add_argument("--pd-visible", type=Path, default=DEFAULT_PD_VISIBLE)
    args = parser.parse_args()

    ma_rows = load_reviewed_text(args.reviewed_ma_text)
    pd_rows = load_pd_visible_text(args.pd_visible)
    chart_ids = sorted(set(ma_rows) & set(pd_rows))
    missing_ma = sorted(set(pd_rows) - set(ma_rows))
    missing_pd = sorted(set(ma_rows) - set(pd_rows))

    schema = json.loads(ROI_FIELD_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    manifest_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    audit_totals: Counter[str] = Counter()

    for chart_id in chart_ids:
        for profile in ["T", "TPD", "PD"]:
            regions = REGIONS_BY_PROFILE[profile]
            roi_text, region_meta = roi_text_for_profile(chart_id, profile, ma_rows, pd_rows)
            method_dir = f"B3_{profile}"
            input_path = args.run_dir / "inputs" / method_dir / f"{chart_id}.txt"
            candidate_path = args.run_dir / "field_candidates" / method_dir / f"{chart_id}.json"
            validation_path = args.run_dir / "field_candidates_validation" / method_dir / f"{chart_id}.json"
            write_text(input_path, roi_text)
            candidates = region_aware_candidates(
                chart_id=chart_id,
                region_profile=profile,
                region_meta=region_meta,
                regions=regions,
            )
            errors = validation_errors(candidates, validator)
            write_json(candidate_path, candidates)
            write_json(validation_path, errors)
            audit = candidate_audit(candidates)
            audit_totals["candidate_count_total"] += audit["candidate_count_total"]
            audit_totals["unknown_source_section_count"] += audit["unknown_source_section_count"]
            audit_totals["cross_region_snippet_count"] += audit["cross_region_snippet_count"]
            manifest_rows.append(
                {
                    "schema_version": "experiment5_dev50_reviewed_roi_input_manifest_v1",
                    "chart_id": chart_id,
                    "region_profile": profile,
                    "regions": regions,
                    "roi_ocr_input_text_path": rel(input_path),
                    "roi_ocr_input_text_sha256": sha256_file(input_path),
                    "field_candidates_path": rel(candidate_path),
                    "field_candidates_sha256": sha256_file(candidate_path),
                    "field_candidates_schema_path": rel(ROI_FIELD_SCHEMA),
                    "field_candidates_schema_sha256": sha256_file(ROI_FIELD_SCHEMA),
                    "field_candidates_validation_path": rel(validation_path),
                    "field_candidates_validation_error_count": len(errors),
                    "candidate_audit": audit,
                    "reviewed_ma_text_input_path": rel(args.reviewed_ma_text) if profile in {"T", "TPD"} else None,
                    "pd_visible_input_path": rel(args.pd_visible) if profile in {"PD", "TPD"} else None,
                    "allowed_methods": {
                        "A3_GoldText_Rules": False,
                        "B2a_GoldText_LLM": False,
                        "B2b_GoldText_FieldCandidates_LLM": False,
                        "B3_T": profile == "T",
                        "B3_PD": profile == "PD",
                        "B3_TPD": profile == "TPD",
                        "B4_TPD": profile == "TPD",
                    },
                    "leakage_policy": candidates["leakage_policy"],
                    "source_contract": {
                        "ma_text_source": "user_reviewed_admin_ma_text_crop_ocr" if profile in {"T", "TPD"} else "withheld",
                        "pd_source": "strict_admin_visible_label_left_of_arrow_and_graphic_markers" if profile in {"PD", "TPD"} else "withheld",
                        "uses_final_answer": False,
                        "uses_canonical_answer": False,
                    },
                }
            )
            validation_rows.append(
                {
                    "chart_id": chart_id,
                    "region_profile": profile,
                    "validation_error_count": len(errors),
                    "validation_errors": errors,
                    "candidate_audit": audit,
                }
            )

    manifest_path = args.run_dir / "manifests" / "roi_ocr_candidate_input_manifest_dev50_reviewed_strict.jsonl"
    validation_report_path = args.run_dir / "reports" / "roi_field_candidate_validation_dev50_reviewed_strict.jsonl"
    write_jsonl(manifest_path, manifest_rows)
    write_jsonl(validation_report_path, validation_rows)
    leakage = scan_forbidden([manifest_path])
    write_json(args.run_dir / "reports" / "roi_reviewed_input_no_leakage_report.json", leakage)

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "chart_count": len(chart_ids),
        "candidate_input_rows": len(manifest_rows),
        "manifest_path": rel(manifest_path),
        "validation_report_path": rel(validation_report_path),
        "reviewed_ma_text": rel(args.reviewed_ma_text),
        "pd_visible": rel(args.pd_visible),
        "missing_ma_count": len(missing_ma),
        "missing_pd_count": len(missing_pd),
        "missing_ma": missing_ma,
        "missing_pd": missing_pd,
        "candidate_validation_error_rows": sum(1 for row in validation_rows if row["validation_error_count"]),
        "candidate_count_total": audit_totals["candidate_count_total"],
        "unknown_source_section_count": audit_totals["unknown_source_section_count"],
        "cross_region_snippet_count": audit_totals["cross_region_snippet_count"],
        "no_leakage_status": leakage["status"],
        "ready_for_b3_b4_dev50": (
            len(chart_ids) == 50
            and not missing_ma
            and not missing_pd
            and not any(row["validation_error_count"] for row in validation_rows)
            and leakage["status"] == "PASS"
        ),
    }
    write_json(args.run_dir / "reports" / "experiment5_dev50_reviewed_roi_input_readiness.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ready_for_b3_b4_dev50"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
