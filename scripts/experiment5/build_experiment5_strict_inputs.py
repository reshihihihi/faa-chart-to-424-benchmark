from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DEV_RUN_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_dev50_20260503_r1"
DEFAULT_OUT_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_dev50_20260504_r3_strict_no_leak"

FORBIDDEN_KEYS = {
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
    "schema_field",
}

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"annotation_pr28_json",
        r"canonical_answer",
        r"canonical_leg_index",
        r"Q_terminator",
        r"\bleg_type\b",
        r"candidate_leg_id",
        r"field_review_v2",
        r"AT_OR_ABOVE",
        r"AT_OR_BELOW",
        r"\bMANDATORY\b",
        r"navaid_radial",
        r"path_terminator",
        r"\btarget_value\b",
        r"\bexpected_value\b",
    ]
]

VISIBLE_TEXT_REGION_TYPES = {
    "ALTITUDE_TEXT",
    "FIX_TEXT",
    "HEADING_TEXT",
    "COURSE_TEXT",
    "RADIAL_TEXT",
    "NAVAID_TEXT",
    "TURN_TEXT",
    "HOLD_TEXT",
}

VISIBLE_GRAPHIC_REGION_TYPES = {
    "CLIMB_ARROW",
    "FIX_SYMBOL",
    "HOLDING_PATTERN",
    "PATH_SEGMENT",
    "PROCEDURE_TURN_SYMBOL",
    "OUTBOUND_INBOUND_MARK",
}

COARSE_REGION_TYPES = {
    "MISSED_APPROACH_TEXT",
    "PLAN_VIEW",
    "MISSED_APPROACH_DETAIL_AREA",
}

SAMPLE_CHART_LIMIT = 5


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


def label_visible_part(label: Any) -> str:
    if not isinstance(label, str):
        return ""
    return re.split(r"\s*->\s*", label, maxsplit=1)[0].strip()


def split_label_literal(visible_literal: str) -> tuple[str, str]:
    if ":" not in visible_literal:
        return "", visible_literal.strip()
    prefix, value = visible_literal.split(":", 1)
    return prefix.strip(), value.strip()


def normalized_text(value: str) -> str:
    return (
        value.replace("掳", "deg")
        .replace("°", "deg")
        .replace("\u00ba", "deg")
        .replace("\u02da", "deg")
        .strip()
    )


def safe_region(row: dict[str, Any], source_file: Path) -> dict[str, Any]:
    region_id = row.get("final_region_id") or row.get("source_region_id") or row.get("region_id")
    return {
        "annotation_scope": row.get("annotation_scope"),
        "bbox": row.get("bbox"),
        "chart_id": row.get("chart_id"),
        "region_id": region_id,
        "region_type": row.get("region_type"),
        "review_action": row.get("review_action"),
        "provenance": {
            "derived_from_final_answer": False,
            "source_field": "bbox/region_type/review_action",
            "source_file": str(source_file),
            "source_region_id": row.get("source_region_id") or region_id,
            "source_type": "admin_region_geometry",
            "transform": "copy_safe_region_metadata_only",
        },
    }


def crop_paths(chart_id: str, dev_run_dir: Path) -> dict[str, str]:
    paths = {
        "ma_text_crop": dev_run_dir / "visuals" / "ma_text_crops" / f"{chart_id}_ma_text_crop.png",
        "admin_ma_text_crop_v2": dev_run_dir / "visuals" / "admin_ma_text_crops_v2" / f"{chart_id}_admin_ma_text_crop_v2.png",
    }
    return {key: str(path) for key, path in paths.items() if path.exists()}


def candidate_from_visible_literal(region_type: str, raw_text: str) -> list[dict[str, Any]]:
    norm = normalized_text(raw_text)
    candidates: list[dict[str, Any]] = []

    if region_type == "ALTITUDE_TEXT":
        match = re.search(r"\b(\d{3,5})\b", norm)
        if match:
            candidates.append(
                {
                    "candidate_type": "altitude_text_literal",
                    "raw_text": raw_text,
                    "value": int(match.group(1)),
                    "value_type": "integer_from_visible_text",
                }
            )
    elif region_type == "FIX_TEXT":
        match = re.search(r"\b[A-Z][A-Z0-9]{1,6}\b", raw_text)
        if match:
            candidates.append(
                {
                    "candidate_type": "fix_ident_literal",
                    "raw_text": raw_text,
                    "value": match.group(0),
                    "value_type": "string_from_visible_text",
                }
            )
    elif region_type == "NAVAID_TEXT":
        match = re.search(r"\b[A-Z][A-Z0-9]{1,5}\b", raw_text)
        if match:
            candidates.append(
                {
                    "candidate_type": "navaid_ident_literal",
                    "raw_text": raw_text,
                    "value": match.group(0),
                    "value_type": "string_from_visible_text",
                }
            )
    elif region_type == "RADIAL_TEXT":
        match = re.search(r"\bR[-\s]?(\d{3})\b", raw_text, flags=re.IGNORECASE)
        if match:
            candidates.append(
                {
                    "candidate_type": "radial_text_literal",
                    "raw_text": raw_text,
                    "value": int(match.group(1)),
                    "value_type": "integer_from_visible_text",
                }
            )
    elif region_type in {"HEADING_TEXT", "COURSE_TEXT"}:
        match = re.search(r"\b(\d{3})\b", norm)
        if match:
            candidates.append(
                {
                    "candidate_type": "degree_text_literal",
                    "raw_text": raw_text,
                    "value": int(match.group(1)),
                    "value_type": "integer_from_visible_text",
                }
            )
    elif region_type in {"TURN_TEXT", "HOLD_TEXT"} and raw_text:
        candidates.append(
            {
                "candidate_type": "instruction_text_literal",
                "raw_text": raw_text,
                "value": raw_text,
                "value_type": "string_from_visible_text",
            }
        )

    return candidates


def visible_observable(row: dict[str, Any], source_file: Path) -> dict[str, Any] | None:
    region_type = str(row.get("region_type") or "")
    region_id = row.get("final_region_id") or row.get("source_region_id")
    if region_type in VISIBLE_TEXT_REGION_TYPES:
        visible_literal = label_visible_part(row.get("label"))
        prefix, raw_text = split_label_literal(visible_literal)
        if not raw_text:
            return None
        return {
            "bbox": row.get("bbox"),
            "candidates": candidate_from_visible_literal(region_type, raw_text),
            "chart_id": row.get("chart_id"),
            "observable_type": "visible_text_literal",
            "raw_visible_text": raw_text,
            "region_id": region_id,
            "region_type": region_type,
            "review_action": row.get("review_action"),
            "visible_label_prefix": prefix or region_type,
            "visible_literal": visible_literal,
            "provenance": {
                "derived_from_final_answer": False,
                "source_field": "label_left_of_arrow",
                "source_file": str(source_file),
                "source_region_id": row.get("source_region_id") or region_id,
                "source_type": "admin_region_visible_label",
                "transform": "strip_label_interpreted_suffix_after_arrow_then_parse_visible_text",
            },
        }

    if region_type in VISIBLE_GRAPHIC_REGION_TYPES:
        return {
            "bbox": row.get("bbox"),
            "candidates": [
                {
                    "candidate_type": "visible_graphic_marker",
                    "raw_text": region_type,
                    "value": region_type,
                    "value_type": "region_type_from_visible_graphic",
                }
            ],
            "chart_id": row.get("chart_id"),
            "observable_type": "visible_graphic_marker",
            "raw_visible_text": "",
            "region_id": region_id,
            "region_type": region_type,
            "review_action": row.get("review_action"),
            "visible_label_prefix": region_type,
            "visible_literal": label_visible_part(row.get("label")) or region_type,
            "provenance": {
                "derived_from_final_answer": False,
                "source_field": "region_type/bbox",
                "source_file": str(source_file),
                "source_region_id": row.get("source_region_id") or region_id,
                "source_type": "admin_region_visible_graphic",
                "transform": "copy_visible_graphic_region_type",
            },
        }
    return None


def coarse_observable(row: dict[str, Any], source_file: Path) -> dict[str, Any]:
    region_type = str(row.get("region_type") or "")
    fact_name = {
        "MISSED_APPROACH_TEXT": "ma_text_region_present",
        "PLAN_VIEW": "plan_view_region_present",
        "MISSED_APPROACH_DETAIL_AREA": "ma_detail_region_present",
    }.get(region_type, "coarse_region_present")
    region_id = row.get("final_region_id") or row.get("source_region_id")
    return {
        "bbox": row.get("bbox"),
        "chart_id": row.get("chart_id"),
        "observable_type": fact_name,
        "region_id": region_id,
        "region_type": region_type,
        "review_action": row.get("review_action"),
        "value": {"region_present": True},
        "provenance": {
            "derived_from_final_answer": False,
            "source_field": "region_type/bbox",
            "source_file": str(source_file),
            "source_region_id": row.get("source_region_id") or region_id,
            "source_type": "admin_region_presence",
            "transform": "copy_coarse_region_presence_only",
        },
    }


def grouped_regions(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        chart_id = str(row.get("chart_id") or "")
        if chart_id:
            grouped[chart_id].append(row)
    return dict(sorted(grouped.items()))


def build_a3_b2_rows(grouped: dict[str, list[dict[str, Any]]], source_file: Path, dev_run_dir: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for chart_id, rows in grouped.items():
        ma_regions = [row for row in rows if row.get("region_type") == "MISSED_APPROACH_TEXT"]
        legal_texts = [
            str(row.get("ocr_text") or "").strip()
            for row in ma_regions
            if str(row.get("ocr_text") or "").strip()
        ]
        status = "ready" if legal_texts else "blocked_missing_visible_ma_text"
        out.append(
            {
                "schema_version": "experiment5_strict_gold_ma_text_input_v1",
                "chart_id": chart_id,
                "method_groups": ["A3", "B2"],
                "strict_input_status": status,
                "blocked_reason": "" if legal_texts else "admin_regions has MA_TEXT bbox but no OCR/corrected visible MA text",
                "gold_ma_prose": legal_texts[0] if legal_texts else "",
                "legal_text_sources": [
                    {
                        "source_file": str(source_file),
                        "source_field": "ocr_text",
                        "source_region_id": row.get("source_region_id") or row.get("final_region_id"),
                        "source_type": "admin_region_ocr_text",
                        "transform": "copy_nonempty_visible_text",
                        "derived_from_final_answer": False,
                    }
                    for row in ma_regions
                    if str(row.get("ocr_text") or "").strip()
                ],
                "ma_text_regions": [safe_region(row, source_file) for row in ma_regions],
                "manual_review_images": crop_paths(chart_id, dev_run_dir),
            }
        )
    return out


def build_roi_text_rows(grouped: dict[str, list[dict[str, Any]]], source_file: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for chart_id, rows in grouped.items():
        coarse_regions = [row for row in rows if row.get("region_type") in COARSE_REGION_TYPES]
        roi_regions = []
        nonempty_text_count = 0
        for row in coarse_regions:
            text = str(row.get("ocr_text") or "").strip()
            if text:
                nonempty_text_count += 1
            roi_regions.append(
                {
                    "region": safe_region(row, source_file),
                    "ocr_text": text,
                    "text_status": "ocr_text_available" if text else "missing_roi_text",
                    "provenance": {
                        "derived_from_final_answer": False,
                        "source_field": "ocr_text",
                        "source_file": str(source_file),
                        "source_region_id": row.get("source_region_id") or row.get("final_region_id"),
                        "source_type": "admin_region_ocr_text",
                        "transform": "copy_nonempty_visible_text_else_mark_missing",
                    },
                }
            )
        status = "ready" if nonempty_text_count == len(coarse_regions) and coarse_regions else "blocked_missing_roi_text"
        out.append(
            {
                "schema_version": "experiment5_strict_roi_text_input_v1",
                "chart_id": chart_id,
                "method_group": "B3_T",
                "strict_input_status": status,
                "blocked_reason": "" if status == "ready" else "coarse ROI regions have bbox but no OCR/corrected text",
                "roi_regions": roi_regions,
            }
        )
    return out


def build_pd_rows(grouped: dict[str, list[dict[str, Any]]], source_file: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for chart_id, rows in grouped.items():
        observables = [
            obs
            for row in rows
            if (obs := visible_observable(row, source_file)) is not None
        ]
        candidate_counts = Counter()
        for obs in observables:
            for candidate in obs.get("candidates", []):
                candidate_counts[str(candidate.get("candidate_type"))] += 1
        status = "ready_visible_region_labels" if observables else "blocked_missing_pd_observables"
        out.append(
            {
                "schema_version": "experiment5_strict_pd_visible_candidates_v1",
                "chart_id": chart_id,
                "method_group": "B3_PD",
                "strict_input_status": status,
                "blocked_reason": "" if observables else "no plan/detail visible text labels or graphic markers",
                "source_contract": {
                    "allows_bbox": True,
                    "allows_visible_label_left_of_arrow": True,
                    "allows_visible_graphic_region_type": True,
                    "allows_interpreted_label_suffix_after_arrow": False,
                    "allows_canonical_target": False,
                    "allows_final_answer": False,
                },
                "candidate_counts": dict(sorted(candidate_counts.items())),
                "visible_observables": observables,
            }
        )
    return out


def build_g_rows(grouped: dict[str, list[dict[str, Any]]], source_file: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for chart_id, rows in grouped.items():
        coarse = [coarse_observable(row, source_file) for row in rows if row.get("region_type") in COARSE_REGION_TYPES]
        visible = [obs for row in rows if (obs := visible_observable(row, source_file)) is not None]
        facts = coarse + visible
        out.append(
            {
                "schema_version": "experiment5_strict_visible_gold_observables_v1",
                "chart_id": chart_id,
                "method_group": "G",
                "strict_input_status": "ready_visible_observable_no_final_answers" if facts else "blocked_missing_observables",
                "source_contract": {
                    "allows_human_reviewed_observable_regions": True,
                    "allows_bbox": True,
                    "allows_visible_text_literal": True,
                    "allows_visible_graphic_region_type": True,
                    "allows_canonical_target": False,
                    "allows_final_answer": False,
                    "allows_leg_index": False,
                    "allows_terminator_or_leg_type": False,
                },
                "observable_facts": facts,
            }
        )
    return out


def build_tpd_rows(roi_rows: list[dict[str, Any]], pd_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pd_by_chart = {row["chart_id"]: row for row in pd_rows}
    out: list[dict[str, Any]] = []
    for roi in roi_rows:
        chart_id = roi["chart_id"]
        pd = pd_by_chart[chart_id]
        roi_ready = roi["strict_input_status"] == "ready"
        pd_ready = pd["strict_input_status"].startswith("ready")
        if roi_ready and pd_ready:
            status = "ready"
            reason = ""
        elif pd_ready:
            status = "partial_missing_text"
            reason = "PD visible observables exist, but ROI text is missing."
        else:
            status = "blocked_missing_inputs"
            reason = "Missing ROI text and PD visible observables."
        out.append(
            {
                "schema_version": "experiment5_strict_tpd_combined_input_v1",
                "chart_id": chart_id,
                "method_groups": ["B3_TPD", "B4_TPD"],
                "strict_input_status": status,
                "blocked_reason": reason,
                "roi_text_input": roi,
                "pd_visible_input": pd,
                "source_contract": {
                    "allows_roi_text": True,
                    "allows_pd_visible_observables": True,
                    "allows_canonical_target": False,
                    "allows_final_answer": False,
                },
            }
        )
    return out


def flatten_paths(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        out: list[tuple[str, Any]] = []
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            out.append((path, child))
            out.extend(flatten_paths(child, path))
        return out
    if isinstance(value, list):
        out = []
        for index, child in enumerate(value):
            out.extend(flatten_paths(child, f"{prefix}[{index}]"))
        return out
    return []


def key_tail(path: str) -> str:
    return re.sub(r"\[\d+\]", "", path).split(".")[-1]


def scan_generated_files(paths: list[Path]) -> dict[str, Any]:
    forbidden_key_hits: list[dict[str, Any]] = []
    forbidden_value_hits: list[dict[str, Any]] = []
    arrow_suffix_hits: list[dict[str, Any]] = []
    scanned_rows = 0

    for path in paths:
        rows = read_jsonl(path)
        for line_no, row in enumerate(rows, start=1):
            scanned_rows += 1
            for key_path, value in flatten_paths(row):
                tail = key_tail(key_path)
                if tail in FORBIDDEN_KEYS:
                    forbidden_key_hits.append({"file": str(path), "line": line_no, "key_path": key_path})
                if isinstance(value, str):
                    if "->" in value:
                        arrow_suffix_hits.append({"file": str(path), "line": line_no, "key_path": key_path, "value": value})
                    for pattern in FORBIDDEN_VALUE_PATTERNS:
                        if pattern.search(value):
                            forbidden_value_hits.append(
                                {
                                    "file": str(path),
                                    "line": line_no,
                                    "key_path": key_path,
                                    "pattern": pattern.pattern,
                                    "value": value,
                                }
                            )

    return {
        "scanned_files": [str(path) for path in paths],
        "scanned_rows": scanned_rows,
        "forbidden_key_hit_count": len(forbidden_key_hits),
        "forbidden_key_hits": forbidden_key_hits[:50],
        "forbidden_value_hit_count": len(forbidden_value_hits),
        "forbidden_value_hits": forbidden_value_hits[:50],
        "interpreted_arrow_suffix_hit_count": len(arrow_suffix_hits),
        "interpreted_arrow_suffix_hits": arrow_suffix_hits[:50],
        "status": "PASS" if not forbidden_key_hits and not forbidden_value_hits and not arrow_suffix_hits else "FAIL",
    }


def manifest_rows(
    a3_b2_rows: list[dict[str, Any]],
    roi_rows: list[dict[str, Any]],
    pd_rows: list[dict[str, Any]],
    tpd_rows: list[dict[str, Any]],
    g_rows: list[dict[str, Any]],
    paths: dict[str, Path],
) -> list[dict[str, Any]]:
    by_chart: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in a3_b2_rows:
        by_chart[row["chart_id"]]["A3"] = row
        by_chart[row["chart_id"]]["B2"] = row
    for row in roi_rows:
        by_chart[row["chart_id"]]["B3_T"] = row
    for row in pd_rows:
        by_chart[row["chart_id"]]["B3_PD"] = row
    for row in tpd_rows:
        by_chart[row["chart_id"]]["B3_TPD"] = row
        by_chart[row["chart_id"]]["B4_TPD"] = row
    for row in g_rows:
        by_chart[row["chart_id"]]["G"] = row

    method_to_path = {
        "A3": paths["a3_b2"],
        "B2": paths["a3_b2"],
        "B3_T": paths["roi"],
        "B3_PD": paths["pd"],
        "B3_TPD": paths["tpd"],
        "B4_TPD": paths["tpd"],
        "G": paths["g"],
    }
    out: list[dict[str, Any]] = []
    for chart_id in sorted(by_chart):
        for method in ["A3", "B2", "B3_T", "B3_PD", "B3_TPD", "B4_TPD", "G"]:
            row = by_chart[chart_id][method]
            out.append(
                {
                    "schema_version": "experiment5_strict_method_input_manifest_v1",
                    "chart_id": chart_id,
                    "method": method,
                    "input_path": str(method_to_path[method]),
                    "strict_input_status": row["strict_input_status"],
                    "blocked_reason": row.get("blocked_reason", ""),
                    "derived_from_final_answer": False,
                }
            )
    return out


def render_provenance_report(
    a3_b2_rows: list[dict[str, Any]],
    roi_rows: list[dict[str, Any]],
    pd_rows: list[dict[str, Any]],
    tpd_rows: list[dict[str, Any]],
    g_rows: list[dict[str, Any]],
    no_leakage: dict[str, Any],
) -> str:
    def count_status(rows: list[dict[str, Any]]) -> dict[str, int]:
        return dict(Counter(row["strict_input_status"] for row in rows).most_common())

    lines = [
        "# Experiment 5 dev50 strict input provenance audit",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## 输入生成结果",
        "",
        f"- A3/B2: {count_status(a3_b2_rows)}",
        f"- B3_T: {count_status(roi_rows)}",
        f"- B3_PD: {count_status(pd_rows)}",
        f"- B3_TPD/B4_TPD: {count_status(tpd_rows)}",
        f"- G: {count_status(g_rows)}",
        "",
        "## no-leakage scan",
        "",
        f"- status: `{no_leakage['status']}`",
        f"- scanned rows: {no_leakage['scanned_rows']}",
        f"- forbidden key hits: {no_leakage['forbidden_key_hit_count']}",
        f"- forbidden value hits: {no_leakage['forbidden_value_hit_count']}",
        f"- interpreted `->` suffix hits: {no_leakage['interpreted_arrow_suffix_hit_count']}",
        "",
        "## 结论",
        "",
        "已生成 dev50 strict 输入工件，但只有 B3_PD 与 G-visible-observable 是完整可用输入。A3/B2/B3_T 仍缺合法 MA_TEXT/ROI 文本，因此 B3_TPD/B4_TPD 目前只能算 partial input，不能正式报告完整 TPD 分数。",
        "",
        "下一步应先人工确认 B3_PD/G 的可见 label literal 是否符合预期；如果要跑 A3/B2/B3_T/TPD，则必须补合法图面 OCR 或人工校正 MA_TEXT/ROI 文本。",
    ]
    return "\n".join(lines) + "\n"


def render_sample_review(
    a3_b2_rows: list[dict[str, Any]],
    pd_rows: list[dict[str, Any]],
    g_rows: list[dict[str, Any]],
) -> str:
    a3_by_chart = {row["chart_id"]: row for row in a3_b2_rows}
    pd_by_chart = {row["chart_id"]: row for row in pd_rows}
    g_by_chart = {row["chart_id"]: row for row in g_rows}
    chart_ids = sorted(a3_by_chart)[:SAMPLE_CHART_LIMIT]
    lines = [
        "# Experiment 5 strict 输入抽样",
        "",
        "请人工重点确认这些输入是否只包含图上可见信息，没有最终答案反推内容。",
        "",
    ]
    for chart_id in chart_ids:
        a3 = a3_by_chart[chart_id]
        pd = pd_by_chart[chart_id]
        g = g_by_chart[chart_id]
        lines.append(f"## {chart_id}")
        lines.append("")
        lines.append(f"- A3/B2 status: `{a3['strict_input_status']}`")
        if a3["manual_review_images"]:
            for label, path in a3["manual_review_images"].items():
                lines.append(f"- {label}: `{path}`")
        lines.append(f"- B3_PD status: `{pd['strict_input_status']}`, observables: {len(pd['visible_observables'])}")
        for obs in pd["visible_observables"][:8]:
            candidate_bits = ", ".join(
                f"{candidate['candidate_type']}={candidate['value']}"
                for candidate in obs.get("candidates", [])[:3]
            )
            if not candidate_bits:
                candidate_bits = "no parsed candidate"
            lines.append(
                f"  - `{obs['region_type']}` `{obs['review_action']}`: {obs['visible_literal']} ({candidate_bits})"
            )
        lines.append(f"- G facts: {len(g['observable_facts'])}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev-run-dir", type=Path, default=DEFAULT_DEV_RUN_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--artifact-label", default="dev50")
    parser.add_argument("--admin-regions", type=Path)
    args = parser.parse_args()

    artifact_label = args.artifact_label
    source_file = args.admin_regions or args.dev_run_dir / "admin_artifacts" / f"admin_regions_{artifact_label}.jsonl"
    rows = read_jsonl(source_file)
    grouped = grouped_regions(rows)

    inputs_dir = args.out_dir / "inputs"
    manifests_dir = args.out_dir / "manifests"
    reports_dir = args.out_dir / "reports"
    paths = {
        "a3_b2": inputs_dir / f"gold_ma_text_{artifact_label}_strict.jsonl",
        "roi": inputs_dir / f"roi_text_{artifact_label}_strict.jsonl",
        "pd": inputs_dir / f"pd_visible_candidates_{artifact_label}_strict.jsonl",
        "tpd": inputs_dir / f"tpd_combined_visible_inputs_{artifact_label}_strict.jsonl",
        "g": inputs_dir / f"g_visible_observables_{artifact_label}_strict.jsonl",
        "manifest": manifests_dir / f"strict_method_input_manifest_{artifact_label}.jsonl",
    }

    a3_b2_rows = build_a3_b2_rows(grouped, source_file, args.dev_run_dir)
    roi_rows = build_roi_text_rows(grouped, source_file)
    pd_rows = build_pd_rows(grouped, source_file)
    tpd_rows = build_tpd_rows(roi_rows, pd_rows)
    g_rows = build_g_rows(grouped, source_file)
    manifest = manifest_rows(a3_b2_rows, roi_rows, pd_rows, tpd_rows, g_rows, paths)

    write_jsonl(paths["a3_b2"], a3_b2_rows)
    write_jsonl(paths["roi"], roi_rows)
    write_jsonl(paths["pd"], pd_rows)
    write_jsonl(paths["tpd"], tpd_rows)
    write_jsonl(paths["g"], g_rows)
    write_jsonl(paths["manifest"], manifest)

    generated_inputs = [paths["a3_b2"], paths["roi"], paths["pd"], paths["tpd"], paths["g"], paths["manifest"]]
    no_leakage = scan_generated_files(generated_inputs)
    write_json(reports_dir / "strict_no_leakage_report.json", no_leakage)
    (reports_dir / "strict_input_provenance_audit_zh.md").write_text(
        render_provenance_report(a3_b2_rows, roi_rows, pd_rows, tpd_rows, g_rows, no_leakage),
        encoding="utf-8",
    )
    (reports_dir / "strict_input_sample_review_zh.md").write_text(
        render_sample_review(a3_b2_rows, pd_rows, g_rows),
        encoding="utf-8",
    )

    summary = {
        "out_dir": str(args.out_dir),
        "input_files": {key: str(path) for key, path in paths.items()},
        "no_leakage_status": no_leakage["status"],
        "chart_count": len(grouped),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
