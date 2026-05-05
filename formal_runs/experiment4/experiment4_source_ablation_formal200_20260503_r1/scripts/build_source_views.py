from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


COARSE_TYPES = [
    "MISSED_APPROACH_TEXT",
    "PLAN_VIEW",
    "MISSED_APPROACH_DETAIL_AREA",
]

VARIANTS = {
    "V0_full_chart": {
        "keep": "full",
        "mask": [],
        "operation": "copy_original_full_chart",
    },
    "V1_ma_text_only": {
        "keep": ["MISSED_APPROACH_TEXT"],
        "mask": "outside_keep",
        "operation": "white_canvas_keep_missed_approach_text",
    },
    "V2_full_minus_ma_prose": {
        "keep": "full",
        "mask": ["MISSED_APPROACH_TEXT"],
        "operation": "copy_original_then_white_mask_missed_approach_text",
    },
    "V3_plan_view_only": {
        "keep": ["PLAN_VIEW"],
        "mask": "outside_keep",
        "operation": "white_canvas_keep_plan_view",
    },
    "V4_icon_detail_only": {
        "keep": ["MISSED_APPROACH_DETAIL_AREA"],
        "mask": "outside_keep",
        "operation": "white_canvas_keep_detail_area",
    },
    "V5_plan_detail_no_ma": {
        "keep": ["PLAN_VIEW", "MISSED_APPROACH_DETAIL_AREA"],
        "mask": ["MISSED_APPROACH_TEXT"],
        "operation": "white_canvas_keep_plan_and_detail_then_mask_text",
    },
}

ROI_SOURCE = "human_confirmed_prelabel_not_gold_coarse_roi"
WHITE = (255, 255, 255)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=90) as response:
                path.write_bytes(response.read())
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to download {url}: {last_error}")


def rect_from_bbox(bbox: dict[str, Any], width: int, height: int, dilation: int) -> tuple[int, int, int, int]:
    x0 = int(round((float(bbox["x_center"]) - float(bbox["width"]) / 2) * width)) - dilation
    y0 = int(round((float(bbox["y_center"]) - float(bbox["height"]) / 2) * height)) - dilation
    x1 = int(round((float(bbox["x_center"]) + float(bbox["width"]) / 2) * width)) + dilation
    y1 = int(round((float(bbox["y_center"]) + float(bbox["height"]) / 2) * height)) + dilation
    x0 = max(0, min(width, x0))
    x1 = max(0, min(width, x1))
    y0 = max(0, min(height, y0))
    y1 = max(0, min(height, y1))
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"invalid bbox after conversion: {bbox} -> {(x0, y0, x1, y1)}")
    return x0, y0, x1, y1


def coarse_regions(prelabel: dict[str, Any], width: int, height: int, dilation: int) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {region_type: [] for region_type in COARSE_TYPES}
    for region in prelabel.get("regions", []):
        region_type = region.get("region_type")
        if region_type not in grouped:
            continue
        rect = rect_from_bbox(region["bbox"], width, height, dilation)
        grouped[region_type].append(
            {
                "region_id": region.get("region_id") or f"{prelabel.get('chart_id')}_{region_type}",
                "region_type": region_type,
                "rect": rect,
            }
        )
    missing = [region_type for region_type, rows in grouped.items() if not rows]
    if missing:
        raise ValueError(f"missing coarse ROI types: {missing}")
    return grouped


def paste_regions(source: Image.Image, keep_region_types: list[str], grouped: dict[str, list[dict[str, Any]]]) -> Image.Image:
    output = Image.new("RGB", source.size, WHITE)
    for region_type in keep_region_types:
        for region in grouped[region_type]:
            rect = tuple(region["rect"])
            output.paste(source.crop(rect), rect[:2])
    return output


def mask_regions(image: Image.Image, mask_region_types: list[str], grouped: dict[str, list[dict[str, Any]]]) -> Image.Image:
    output = image.copy()
    draw = ImageDraw.Draw(output)
    for region_type in mask_region_types:
        for region in grouped[region_type]:
            draw.rectangle(tuple(region["rect"]), fill=WHITE)
    return output


def build_variant_image(variant: str, source_path: Path, output_path: Path, grouped: dict[str, list[dict[str, Any]]]) -> None:
    source = Image.open(source_path).convert("RGB")
    policy = VARIANTS[variant]
    if variant == "V0_full_chart":
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, output_path)
        return

    keep = policy["keep"]
    if keep == "full":
        output = source.copy()
    else:
        output = paste_regions(source, list(keep), grouped)
    mask = policy["mask"]
    if isinstance(mask, list) and mask:
        output = mask_regions(output, mask, grouped)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.save(output_path)


def variant_roi_types(variant: str) -> list[str]:
    if variant == "V0_full_chart":
        return COARSE_TYPES[:]
    keep = VARIANTS[variant]["keep"]
    if keep == "full":
        mask = VARIANTS[variant]["mask"]
        if isinstance(mask, list):
            return [region_type for region_type in COARSE_TYPES if region_type not in mask]
        return COARSE_TYPES[:]
    return list(keep)


def write_preview_html(rows: list[dict[str, Any]], output_root: Path, limit_charts: int = 20) -> None:
    by_chart: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_chart[row["chart_id"]].append(row)
    chart_ids = list(by_chart)[:limit_charts]
    lines = [
        "<!doctype html>",
        '<meta charset="utf-8">',
        "<title>Experiment 4 source-view preview</title>",
        "<style>",
        "body{font-family:Arial,sans-serif;margin:24px;background:#fafafa;color:#111}",
        ".chart{margin-bottom:28px}.grid{display:grid;grid-template-columns:repeat(6,minmax(150px,1fr));gap:10px}",
        ".card{background:#fff;border:1px solid #ddd;padding:8px}",
        "img{width:100%;height:auto;border:1px solid #ccc}.id{font-weight:700;margin-bottom:6px}.v{font-size:12px;color:#333;margin-bottom:4px}",
        "</style>",
        "<h1>Experiment 4 source-view preview</h1>",
        f"<p>Showing first {len(chart_ids)} charts. Full manifest covers {len(by_chart)} charts.</p>",
    ]
    for chart_id in chart_ids:
        lines.append(f'<div class="chart"><div class="id">{chart_id}</div><div class="grid">')
        for row in sorted(by_chart[chart_id], key=lambda item: item["variant"]):
            rel = Path(row["output_image_path"]).resolve().relative_to(output_root.resolve()).as_posix()
            lines.extend(
                [
                    '<div class="card">',
                    f'<div class="v">{row["variant"]}</div>',
                    f'<a href="{rel}"><img src="{rel}" alt="{chart_id} {row["variant"]}"></a>',
                    "</div>",
                ]
            )
        lines.append("</div></div>")
    (output_root / "source_views" / "reports" / "source_view_preview_first20.html").write_text("\n".join(lines), encoding="utf-8")


def build(args: argparse.Namespace) -> int:
    output_root = args.output_root.resolve()
    source_cache = output_root / "source_cache" / f"pr18_{args.commit[:12]}"
    source_views_root = output_root / "source_views"
    manifest_path = source_views_root / "manifests" / "source_view_manifest.jsonl"
    failures_path = source_views_root / "reports" / "source_view_failures.json"
    summary_path = source_views_root / "reports" / "source_view_summary.json"

    base_url = (
        "https://raw.githubusercontent.com/reshihihihi/"
        f"faa-chart-to-424-benchmark/{args.commit}/"
        "annotation_tools/shujuji_annotation"
    )
    formal_manifest_path = source_cache / "formal300_manifest.json"
    download(f"{base_url}/datasets/formal300/manifests/formal300_manifest.json", formal_manifest_path)
    formal_manifest = json.loads(formal_manifest_path.read_text(encoding="utf-8"))
    formal_manifest = formal_manifest[: args.limit] if args.limit else formal_manifest

    script_path = Path(__file__).resolve()
    script_sha = sha256_file(script_path)
    created_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    variant_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()

    for index, item in enumerate(formal_manifest, start=1):
        chart_id = item["chart_id"]
        try:
            image_rel = item["image_path"]
            image_file = Path(image_rel).name
            image_path = source_cache / "images" / image_file
            prelabel_path = source_cache / "prelabels" / f"{chart_id}.json"
            download(f"{base_url}/{image_rel}", image_path)
            download(f"{base_url}/datasets/formal300/prelabels/{chart_id}.json", prelabel_path)

            source = Image.open(image_path).convert("RGB")
            width, height = source.size
            expected_dims = item.get("image_dimensions") or {}
            if expected_dims and (width != expected_dims.get("width") or height != expected_dims.get("height")):
                raise ValueError(f"image dimensions mismatch: actual {(width, height)} expected {expected_dims}")
            prelabel = json.loads(prelabel_path.read_text(encoding="utf-8"))
            grouped = coarse_regions(prelabel, width, height, args.mask_dilation_pixels)
            all_rects = {
                region_type: list(grouped[region_type][0]["rect"])
                for region_type in COARSE_TYPES
            }
            source_hash = sha256_file(image_path)
            for variant in VARIANTS:
                output_path = source_views_root / "images" / variant / f"{index:03d}__{chart_id}__{variant}.png"
                build_variant_image(variant, image_path, output_path, grouped)
                roi_types = variant_roi_types(variant)
                roi_ids = [
                    region["region_id"]
                    for region_type in roi_types
                    for region in grouped[region_type]
                ]
                row = {
                    "sample_id": f"{chart_id}__{variant}",
                    "base_sample_index": index,
                    "chart_id": chart_id,
                    "proc_ident": item["proc_ident"],
                    "dataset_split": item["dataset_split"],
                    "variant": variant,
                    "source_image_path": str(image_path.resolve()),
                    "source_image_sha256": source_hash,
                    "output_image_path": str(output_path.resolve()),
                    "output_image_sha256": sha256_file(output_path),
                    "image_width": width,
                    "image_height": height,
                    "roi_source": ROI_SOURCE,
                    "roi_ids": roi_ids,
                    "roi_types": roi_types,
                    "roi_rects_pixels": all_rects,
                    "mask_policy": {
                        "fill_rgb": list(WHITE),
                        "dilation_pixels": args.mask_dilation_pixels,
                        "operation": VARIANTS[variant]["operation"],
                    },
                    "crop_policy": "no_crop_full_canvas",
                    "canvas_policy": "preserve_original_dimensions_white_fill",
                    "source_pr": 18,
                    "source_commit": args.commit,
                    "created_by_script": str(script_path),
                    "created_by_script_sha256": script_sha,
                    "created_at_utc": created_at,
                }
                rows.append(row)
                variant_counts[variant] += 1
            split_counts[item["dataset_split"]] += 1
            print(f"[{index:03d}/{len(formal_manifest):03d}] {chart_id} ok")
        except Exception as exc:  # noqa: BLE001
            failure = {"index": index, "chart_id": chart_id, "error": str(exc)}
            failures.append(failure)
            print(f"[{index:03d}/{len(formal_manifest):03d}] {chart_id} FAILED: {exc}", file=sys.stderr)

    write_jsonl(manifest_path, rows)
    write_json(failures_path, failures)
    summary = {
        "created_at_utc": created_at,
        "source_pr": 18,
        "source_commit": args.commit,
        "roi_source": ROI_SOURCE,
        "chart_count_requested": len(formal_manifest),
        "chart_count_succeeded": len({row["chart_id"] for row in rows}),
        "source_view_count": len(rows),
        "expected_source_view_count": len(formal_manifest) * len(VARIANTS),
        "variant_counts": dict(sorted(variant_counts.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "failures_count": len(failures),
        "manifest_path": str(manifest_path.resolve()),
        "manifest_sha256": sha256_file(manifest_path),
        "formal300_manifest_cache_path": str(formal_manifest_path.resolve()),
        "formal300_manifest_sha256": sha256_file(formal_manifest_path),
        "mask_policy": {"fill_rgb": list(WHITE), "dilation_pixels": args.mask_dilation_pixels},
        "crop_policy": "no_crop_full_canvas",
        "canvas_policy": "preserve_original_dimensions_white_fill",
    }
    write_json(summary_path, summary)
    write_preview_html(rows, output_root)
    if failures or len(rows) != len(formal_manifest) * len(VARIANTS):
        return 1
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Experiment 4 source-view images and manifest.")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--commit", default="5446f8f4750489face8dac163df0d57a2464f58d")
    parser.add_argument("--limit", type=int, default=300, help="Number of formal300 charts; use 0 for all.")
    parser.add_argument("--mask-dilation-pixels", type=int, default=3)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(build(parse_args()))

