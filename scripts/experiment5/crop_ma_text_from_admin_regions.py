from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_eval200_20260503_r1"
DEFAULT_OUT_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_eval200_20260504_r5_ma_text_ocr_review"
DEFAULT_PDF_DIR = REPO_ROOT / "downloads" / "experiment5_eval200_pdfs_20260504"


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


def download_pdf(url: str, path: Path, timeout: int, retries: int) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "experiment5-ma-text-crop/1.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                path.write_bytes(response.read())
            return
        except Exception as exc:  # pragma: no cover - network dependent
            last_error = exc
            time.sleep(min(2 * attempt, 10))
    raise RuntimeError(f"Failed to download {url}: {last_error}")


def bbox_to_rect(bbox: dict[str, Any], width: float, height: float, pad_fraction: float) -> fitz.Rect:
    x_center = float(bbox["x_center"]) * width
    y_center = float(bbox["y_center"]) * height
    box_width = float(bbox["width"]) * width
    box_height = float(bbox["height"]) * height
    pad_x = pad_fraction * width
    pad_y = pad_fraction * height
    return fitz.Rect(
        max(0, x_center - box_width / 2 - pad_x),
        max(0, y_center - box_height / 2 - pad_y),
        min(width, x_center + box_width / 2 + pad_x),
        min(height, y_center + box_height / 2 + pad_y),
    )


def extract_text_in_rect(page: fitz.Page, rect: fitz.Rect) -> str:
    words = page.get_text("words")
    selected: list[tuple[float, float, str]] = []
    for word in words:
        x0, y0, x1, y1, text = word[:5]
        center = fitz.Point((x0 + x1) / 2, (y0 + y1) / 2)
        if rect.contains(center) and str(text).strip():
            selected.append((round(y0 / 3) * 3, x0, str(text).strip()))
    selected.sort(key=lambda item: (item[0], item[1]))
    return " ".join(text for _, _, text in selected).strip()


def render_crop(pdf_path: Path, bbox: dict[str, Any], crop_path: Path, zoom: float, pad_fraction: float) -> tuple[str, dict[str, Any]]:
    document = fitz.open(pdf_path)
    try:
        page = document[0]
        page_rect = page.rect
        crop_rect = bbox_to_rect(bbox, page_rect.width, page_rect.height, pad_fraction)
        text_layer = extract_text_in_rect(page, crop_rect)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=crop_rect, alpha=False)
        crop_path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        image.save(crop_path)
        return text_layer, {
            "page_width": page_rect.width,
            "page_height": page_rect.height,
            "crop_rect_pdf_points": [crop_rect.x0, crop_rect.y0, crop_rect.x1, crop_rect.y1],
            "crop_image_width": pixmap.width,
            "crop_image_height": pixmap.height,
        }
    finally:
        document.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Crop MA_TEXT regions from admin bbox annotations and chart PDFs.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    parser.add_argument("--artifact-label", default="eval200")
    parser.add_argument("--zoom", type=float, default=3.0)
    parser.add_argument("--pad-fraction", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    manifest_path = args.run_dir / "manifests" / f"{args.artifact_label}_chart_manifest.jsonl"
    regions_path = args.run_dir / "admin_artifacts" / f"admin_regions_{args.artifact_label}.jsonl"
    manifest_rows = read_jsonl(manifest_path)
    if args.limit:
        manifest_rows = manifest_rows[: args.limit]
    manifest_by_chart = {row["chart_id"]: row for row in manifest_rows}

    ma_regions = [
        row for row in read_jsonl(regions_path)
        if row.get("chart_id") in manifest_by_chart and row.get("region_type") == "MISSED_APPROACH_TEXT"
    ]
    by_chart = {row["chart_id"]: row for row in ma_regions}

    crop_dir = args.out_dir / "visuals" / "admin_ma_text_crops_v2"
    pdf_candidate_rows: list[dict[str, Any]] = []
    crop_manifest_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for chart_id, manifest in manifest_by_chart.items():
        region = by_chart.get(chart_id)
        if not region:
            failures.append({"chart_id": chart_id, "reason": "missing_missed_approach_text_region"})
            continue
        pdf_file = str(manifest.get("pdf_file") or f"{chart_id}.PDF")
        pdf_url = str(manifest.get("pdf_url") or "")
        pdf_path = args.pdf_dir / pdf_file
        crop_path = crop_dir / f"{chart_id}_admin_ma_text_crop_v2.png"
        try:
            if pdf_url:
                download_pdf(pdf_url, pdf_path, args.timeout, args.retries)
            text_layer, crop_meta = render_crop(pdf_path, region["bbox"], crop_path, args.zoom, args.pad_fraction)
            pdf_candidate_rows.append(
                {
                    "schema_version": "experiment5_ma_text_pdf_text_layer_candidate_v1",
                    "chart_id": chart_id,
                    "gold_ma_prose": text_layer,
                    "review_status": "candidate_pdf_text_layer_needs_review",
                    "source": "pdf_text_layer_admin_ma_text_bbox",
                    "source_contract": {
                        "allows_pdf_text_layer": True,
                        "allows_admin_ma_text_bbox": True,
                        "allows_final_answer": False,
                        "allows_canonical_target": False,
                        "derived_from_final_answer": False,
                    },
                }
            )
            crop_manifest_rows.append(
                {
                    "schema_version": "experiment5_admin_ma_text_crop_manifest_v1",
                    "chart_id": chart_id,
                    "crop_image_path": str(crop_path),
                    "pdf_path": str(pdf_path),
                    "pdf_url": pdf_url,
                    "source_region_id": region.get("source_region_id") or region.get("final_region_id"),
                    "bbox": region.get("bbox"),
                    "crop_meta": crop_meta,
                }
            )
        except Exception as exc:
            failures.append({"chart_id": chart_id, "reason": type(exc).__name__, "message": str(exc)})

    inputs_dir = args.out_dir / "inputs"
    reports_dir = args.out_dir / "reports"
    write_jsonl(inputs_dir / f"gold_ma_text_{args.artifact_label}_pdf_text_layer_candidate.jsonl", pdf_candidate_rows)
    write_jsonl(reports_dir / f"ma_text_{args.artifact_label}_crop_manifest.jsonl", crop_manifest_rows)
    write_json(
        reports_dir / f"ma_text_{args.artifact_label}_crop_summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "artifact_label": args.artifact_label,
            "run_dir": str(args.run_dir),
            "out_dir": str(args.out_dir),
            "pdf_dir": str(args.pdf_dir),
            "requested_charts": len(manifest_by_chart),
            "crop_rows": len(crop_manifest_rows),
            "pdf_text_layer_candidate_rows": len(pdf_candidate_rows),
            "failure_count": len(failures),
            "failures": failures[:50],
            "zoom": args.zoom,
            "pad_fraction": args.pad_fraction,
        },
    )
    print(json.dumps({"crops": len(crop_manifest_rows), "failures": len(failures), "out_dir": str(args.out_dir)}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
