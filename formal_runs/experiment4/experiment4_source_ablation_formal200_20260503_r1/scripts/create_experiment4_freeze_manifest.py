from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_INCLUDE_DIRS = [
    "baseline",
    "logs",
    "manifests",
    "reports",
    "scripts",
    "source_views/manifests",
    "validation",
]

DEFAULT_INCLUDE_FILES = [
    "source_views/reports/source_view_preview_first20.html",
]

DEFAULT_INCLUDE_GLOBS = [
    "runs/formal_eval200/*/D1/reports/*.json",
    "runs/formal_eval200/*/D1/reports/*.jsonl",
    "runs/formal_eval200/*/D1/reports/*.md",
    "runs/formal_eval200/*/D1/method_summary.json",
    "runs/formal_eval200/*/D1/summary_report.json",
]

IMAGE_VARIANTS = [
    "V0_full_chart",
    "V1_ma_text_only",
    "V2_full_minus_ma_prose",
    "V3_plan_view_only",
    "V4_icon_detail_only",
    "V5_plan_detail_no_ma",
]

D1_VARIANTS = [
    "V1_ma_text_only",
    "V2_full_minus_ma_prose",
    "V3_plan_view_only",
    "V4_icon_detail_only",
    "V5_plan_detail_no_ma",
]

D1_INVENTORY_SUBDIRS = [
    "raw_text",
    "canonical_json",
    "validation",
    "scores",
    "strict_scores",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(root: Path, path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "relative_path": path.relative_to(root).as_posix(),
        "size_bytes": stat.st_size,
        "mtime_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "sha256": sha256(path),
    }


def collect_files(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[Path] = set()

    for rel_dir in DEFAULT_INCLUDE_DIRS:
        directory = root / rel_dir
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path not in seen:
                records.append(file_record(root, path))
                seen.add(path)

    for rel_file in DEFAULT_INCLUDE_FILES:
        path = root / rel_file
        if path.exists() and path.is_file() and path not in seen:
            records.append(file_record(root, path))
            seen.add(path)

    for pattern in DEFAULT_INCLUDE_GLOBS:
        for path in sorted(root.glob(pattern)):
            if path.is_file() and path not in seen:
                records.append(file_record(root, path))
                seen.add(path)

    return records


def directory_digest(files: list[Path]) -> str | None:
    if not files:
        return None
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def collect_image_inventory(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    image_root = root / "source_views" / "images"
    for variant in IMAGE_VARIANTS:
        variant_dir = image_root / variant
        files = sorted(variant_dir.glob("*.png")) if variant_dir.exists() else []
        rows.append(
            {
                "variant": variant,
                "directory": str(variant_dir),
                "exists": variant_dir.exists(),
                "png_count": len(files),
                "directory_digest_sha256": directory_digest(files),
            }
        )
    return rows


def collect_d1_inventory(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    run_root = root / "runs" / "formal_eval200"
    for variant in D1_VARIANTS:
        d1_root = run_root / variant / "D1"
        subdirs: dict[str, Any] = {}
        for name in D1_INVENTORY_SUBDIRS:
            directory = d1_root / name
            files = sorted(path for path in directory.glob("*") if path.is_file()) if directory.exists() else []
            subdirs[name] = {
                "directory": str(directory),
                "exists": directory.exists(),
                "file_count": len(files),
                "directory_digest_sha256": directory_digest(files),
            }
        rows.append(
            {
                "variant": variant,
                "d1_root": str(d1_root),
                "exists": d1_root.exists(),
                "subdirs": subdirs,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Experiment 4 freeze manifest with key file hashes.")
    parser.add_argument("--output-root", type=Path, default=Path(r"formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1"))
    args = parser.parse_args()
    root = args.output_root

    files = collect_files(root)
    image_inventory = collect_image_inventory(root)
    d1_inventory = collect_d1_inventory(root)
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_root": str(root),
        "purpose": "Freeze key Experiment 4 artifacts after execution.",
        "roi_source": "prelabel_not_gold",
        "files": files,
        "source_view_image_inventory": image_inventory,
        "d1_output_inventory": d1_inventory,
        "file_count": len(files),
    }
    out_path = root / "reports" / "experiment4_freeze_manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Hashed {len(files)} key files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
