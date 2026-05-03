from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_dev50_20260503_r1"
DEFAULT_DEV50_MANIFEST = DEFAULT_RUN_DIR / "manifests" / "dev50_chart_manifest.jsonl"
DEFAULT_SANITIZED_REGIONS = DEFAULT_RUN_DIR / "inputs" / "admin_regions_sanitized_dev50.jsonl"

FORBIDDEN_KEYS = {
    "target",
    "score",
    "canonical_answer",
    "canonical_leg_index",
    "Q_terminator",
    "leg_type",
    "field_review_v2",
    "field_reviews",
}

COLORS = {
    "MISSED_APPROACH_TEXT": (220, 20, 60),
    "PLAN_VIEW": (30, 144, 255),
    "MISSED_APPROACH_DETAIL_AREA": (255, 140, 0),
    "ALTITUDE_TEXT": (148, 0, 211),
    "FIX_TEXT": (0, 128, 0),
    "FIX_SYMBOL": (46, 139, 87),
    "CLIMB_ARROW": (255, 0, 255),
    "HEADING_TEXT": (0, 139, 139),
    "RADIAL_TEXT": (178, 34, 34),
    "NAVAID_TEXT": (139, 69, 19),
    "PATH_SEGMENT": (0, 0, 0),
    "OUTBOUND_INBOUND_MARK": (105, 105, 105),
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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_label_to_facts(region: dict[str, Any]) -> list[dict[str, Any]]:
    chart_id = region["chart_id"]
    region_id = region.get("final_region_id") or region.get("source_region_id")
    region_type = region.get("region_type")
    label = str(region.get("label") or "")
    base = {
        "chart_id": chart_id,
        "evidence_region_id": region_id,
        "region_type": region_type,
        "bbox": region.get("bbox"),
        "review_action": region.get("review_action"),
        "annotation_scope": region.get("annotation_scope"),
        "label": label,
    }
    facts: list[dict[str, Any]] = []

    def add(fact_type: str, value: Any, status: str = "observed") -> None:
        facts.append({**base, "fact_type": fact_type, "status": status, "value": value})

    if region_type == "MISSED_APPROACH_TEXT":
        add("ma_text_region_present", {"region_id": region_id})
        return facts
    if region_type == "PLAN_VIEW":
        add("plan_view_region_present", {"region_id": region_id})
        return facts
    if region_type == "MISSED_APPROACH_DETAIL_AREA":
        add("ma_detail_region_present", {"region_id": region_id})
        return facts
    if region_type == "CLIMB_ARROW":
        add("climb_arrow_visible", True)
        return facts
    if region_type == "FIX_SYMBOL":
        add("fix_symbol_visible", True)
        return facts
    if region_type == "PATH_SEGMENT":
        add("path_segment_visible", True)
        return facts

    for match in re.finditer(r"FIX_TEXT:\s*([A-Z0-9]+)\s*->\s*([A-Z0-9]+)", label):
        add("fix_text_visible", {"raw_text": match.group(1), "fix_ident": match.group(2)})

    for match in re.finditer(r"ALTITUDE_TEXT:\s*([0-9]{2,5})\s*->\s*AT_OR_ABOVE\s*([0-9]{2,5})\s*ft", label):
        add(
            "altitude_text_visible",
            {"raw_text": match.group(1), "constraint": "AT_OR_ABOVE", "altitude_ft": int(match.group(2))},
        )

    for match in re.finditer(r"HEADING_TEXT:\s*(.*?)\s*->\s*type=course_deg,\s*course_deg=([0-9.]+)", label):
        add("heading_text_visible", {"raw_text": match.group(1).strip(), "course_deg": float(match.group(2))})

    radial_pattern = re.compile(
        r"(?:RADIAL_TEXT|NAVAID_TEXT|OUTBOUND_INBOUND_MARK):\s*(.*?)\s*->\s*"
        r"type=navaid_radial,\s*navaid=([A-Z0-9]+),\s*radial_deg=([0-9.]+),\s*direction=([a-zA-Z_]+)"
    )
    for match in radial_pattern.finditer(label):
        add(
            "navaid_radial_text_visible",
            {
                "raw_text": match.group(1).strip(),
                "navaid": match.group(2),
                "radial_deg": float(match.group(3)),
                "direction": match.group(4),
            },
        )

    if not facts and region_type in {"ALTITUDE_TEXT", "FIX_TEXT", "HEADING_TEXT", "RADIAL_TEXT", "NAVAID_TEXT"}:
        add("unparsed_text_annotation_visible", {"raw_label": label}, status="observed_unparsed")
    return facts


def scan_for_forbidden_keys(value: Any) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []

    def visit(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            for key, item in obj.items():
                if key in FORBIDDEN_KEYS:
                    hits.append({"path": path, "key": key})
                visit(item, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                visit(item, f"{path}[{index}]")

    visit(value, "")
    return {"hit_count": len(hits), "hits": hits[:50], "truncated": len(hits) > 50}


def bbox_to_pixels(bbox: dict[str, Any], width: int, height: int) -> tuple[int, int, int, int]:
    x0 = int((float(bbox["x_center"]) - float(bbox["width"]) / 2.0) * width)
    x1 = int((float(bbox["x_center"]) + float(bbox["width"]) / 2.0) * width)
    y0 = int((float(bbox["y_center"]) - float(bbox["height"]) / 2.0) * height)
    y1 = int((float(bbox["y_center"]) + float(bbox["height"]) / 2.0) * height)
    return max(0, x0), max(0, y0), min(width - 1, x1), min(height - 1, y1)


def draw_admin_overlays(run_dir: Path, regions_by_chart: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    page_dir = run_dir / "visuals" / "pdf_pages"
    overlay_dir = run_dir / "visuals" / "admin_box_overlays"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()
    thumbnails: list[Image.Image] = []
    overlay_rows: list[dict[str, Any]] = []

    for chart_id in sorted(regions_by_chart):
        page_path = page_dir / f"{chart_id}.png"
        if not page_path.exists():
            continue
        img = Image.open(page_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        width, height = img.size
        for region in regions_by_chart[chart_id]:
            bbox = region.get("bbox")
            if not isinstance(bbox, dict):
                continue
            color = COLORS.get(str(region.get("region_type")), (0, 0, 0))
            box = bbox_to_pixels(bbox, width, height)
            line_width = 5 if region.get("region_type") in {"MISSED_APPROACH_TEXT", "PLAN_VIEW"} else 3
            draw.rectangle(box, outline=color, width=line_width)
            label = str(region.get("region_type") or "")
            draw.rectangle((box[0], max(0, box[1] - 14), box[0] + min(170, len(label) * 7 + 6), box[1]), fill=color)
            draw.text((box[0] + 3, max(0, box[1] - 13)), label, fill=(255, 255, 255), font=font)
        overlay_path = overlay_dir / f"{chart_id}_admin_boxes.png"
        img.save(overlay_path)
        overlay_rows.append({"chart_id": chart_id, "overlay_image": rel(overlay_path), "region_count": len(regions_by_chart[chart_id])})

        thumb = img.copy()
        thumb.thumbnail((360, 560), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (380, 600), "white")
        cdraw = ImageDraw.Draw(canvas)
        cdraw.text((8, 6), chart_id, fill=(0, 0, 0), font=font)
        canvas.paste(thumb, (10, 28))
        thumbnails.append(canvas)

    sheet_path: Path | None = None
    if thumbnails:
        cols = 3
        rows = (len(thumbnails) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 380, rows * 600), "white")
        for index, thumb in enumerate(thumbnails):
            sheet.paste(thumb, ((index % cols) * 380, (index // cols) * 600))
        sheet_path = run_dir / "visuals" / "admin_box_overlays_contact_sheet.png"
        sheet.save(sheet_path)
    return {
        "overlay_count": len(overlay_rows),
        "overlay_dir": rel(overlay_dir),
        "contact_sheet": rel(sheet_path) if sheet_path is not None else None,
        "overlays": overlay_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build method-safe split observables from admin box annotations.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--chart-manifest", "--dev50-manifest", dest="chart_manifest", type=Path, default=DEFAULT_DEV50_MANIFEST)
    parser.add_argument("--sanitized-regions", type=Path, default=DEFAULT_SANITIZED_REGIONS)
    parser.add_argument("--artifact-label", default="dev50")
    args = parser.parse_args()

    artifact_label = args.artifact_label
    dev_rows = read_jsonl(args.chart_manifest)
    regions = read_jsonl(args.sanitized_regions)
    dev_ids = [row["chart_id"] for row in dev_rows]
    regions_by_chart: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for region in regions:
        regions_by_chart[region["chart_id"]].append(region)

    observable_rows: list[dict[str, Any]] = []
    fact_rows: list[dict[str, Any]] = []
    for chart_id in dev_ids:
        chart_regions = regions_by_chart.get(chart_id, [])
        facts: list[dict[str, Any]] = []
        for region in chart_regions:
            facts.extend(parse_label_to_facts(region))
        row = {
            "schema_version": "experiment5_gold_observable_admin_regions_v1",
            "chart_id": chart_id,
            "review_status": "admin_box_observable_extracted_needs_policy_review",
            "source": "admin_region_annotations_sanitized",
            "checked_scopes": ["MISSED_APPROACH_TEXT", "PLAN_VIEW", "MISSED_APPROACH_DETAIL_AREA"],
            "evidence_region_ids": [
                region.get("final_region_id") or region.get("source_region_id") for region in chart_regions
            ],
            "observable_facts": facts,
            "notes": "Derived from admin box region_type/label/bbox only; answer-side mapping structures are not included.",
        }
        observable_rows.append(row)
        fact_rows.extend(facts)

    forbidden_scan = scan_for_forbidden_keys(observable_rows)
    overlay_summary = draw_admin_overlays(args.run_dir, regions_by_chart)
    fact_counter = Counter(fact.get("fact_type") for fact in fact_rows)
    region_counter = Counter(region.get("region_type") for region in regions)
    review_counter = Counter(region.get("review_action") for region in regions)
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_dir.name,
        "artifact_label": artifact_label,
        "chart_count": len(dev_ids),
        "dev50_chart_count": len(dev_ids),
        "admin_region_rows": len(regions),
        "observable_rows": len(observable_rows),
        "observable_fact_rows": len(fact_rows),
        "region_type_counts": dict(sorted(region_counter.items())),
        "review_action_counts": dict(sorted(review_counter.items())),
        "fact_type_counts": dict(sorted(fact_counter.items())),
        "forbidden_key_scan": forbidden_scan,
        "hard_leakage_detected": forbidden_scan["hit_count"] > 0,
        "output_path": rel(args.run_dir / "inputs" / f"gold_observable_{artifact_label}_admin.jsonl"),
        "fact_table_path": rel(args.run_dir / "reports" / f"gold_observable_{artifact_label}_admin_facts.jsonl"),
        "overlay_summary": overlay_summary,
        "source_admin_regions_path": rel(args.sanitized_regions),
        "source_admin_regions_sha256": sha256_file(args.sanitized_regions),
    }

    write_jsonl(args.run_dir / "inputs" / f"gold_observable_{artifact_label}_admin.jsonl", observable_rows)
    write_jsonl(args.run_dir / "reports" / f"gold_observable_{artifact_label}_admin_facts.jsonl", fact_rows)
    write_json(args.run_dir / "reports" / f"gold_observable_{artifact_label}_admin_summary.json", summary)
    write_json(args.run_dir / "visuals" / "admin_box_overlay_manifest.json", overlay_summary["overlays"])

    report = [
        "# 实验组5 dev50 admin 框标注处理报告",
        "",
        f"- 生成时间 UTC: `{summary['created_at_utc']}`",
        f"- charts: {summary['chart_count']}",
        f"- admin region rows: {summary['admin_region_rows']}",
        f"- observable rows: {summary['observable_rows']}",
        f"- observable fact rows: {summary['observable_fact_rows']}",
        f"- forbidden key hits: {summary['forbidden_key_scan']['hit_count']}",
        f"- hard leakage detected: `{summary['hard_leakage_detected']}`",
        "",
        "## 输出",
        "",
        f"- gold observable: `{summary['output_path']}`",
        f"- flat facts: `{summary['fact_table_path']}`",
        f"- admin box overlay contact sheet: `{overlay_summary['contact_sheet']}`",
        f"- per-chart overlays: `{overlay_summary['overlay_dir']}`",
        "",
        "## 说明",
        "",
        "- 这里处理的是 admin 里的框标注，不再使用 PDF text-layer 抽 MA prose 作为主要来源。",
        "- 输出只来自 `region_type`、`label`、`bbox`、`review_action`、`annotation_scope` 等可观察标注字段。",
        "- 已在上游 sanitized 文件中去掉 accepted/candidate mappings、field review 结构和答案侧字段。",
    ]
    write_text(args.run_dir / "reports" / f"gold_observable_{artifact_label}_admin_report_zh.md", "\n".join(report) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not summary["hard_leakage_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
