from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "benchmark_exports" / "derived" / "v2" / "pilot10_external"
DEFAULT_MANIFEST = DATA_DIR / "pilot10_manifest.jsonl"
DEFAULT_OUTPUT_ROOT = ROOT / "ocr_artifacts" / "pilot10_external"


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


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + ("\n" if value and not value.endswith("\n") else ""), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def resolve_package_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def normalize_poly(poly: Any) -> list[list[int | float]]:
    if poly is None:
        return []
    if hasattr(poly, "tolist"):
        poly = poly.tolist()
    return poly


def result_list(result: dict[str, Any], key: str) -> list[Any]:
    value = result.get(key)
    if value is None:
        return []
    if hasattr(value, "tolist"):
        return value.tolist()
    return list(value)


def run_paddleocr(
    rows: list[dict[str, Any]],
    output_root: Path,
    *,
    sample_manifest: Path = DEFAULT_MANIFEST,
    sample_role: str = "pilot10_external_excluded_from_formal_evaluation",
) -> list[dict[str, Any]]:
    import paddle
    import paddleocr
    from paddleocr import PaddleOCR

    run_dir = output_root / "ocr1_paddleocr_ppocrv5_20260428_r1"
    raw_dir = run_dir / "raw_blocks"
    text_dir = run_dir / "full_text"

    ocr = PaddleOCR(
        lang="en",
        ocr_version="PP-OCRv5",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )

    manifest_rows: list[dict[str, Any]] = []
    for row in rows:
        chart_id = row["chart_id"]
        image_path = resolve_package_path(row["image_path"])
        result = ocr.predict(str(image_path))[0]

        rec_texts = result_list(result, "rec_texts")
        rec_scores = result_list(result, "rec_scores")
        rec_boxes = result_list(result, "rec_boxes")
        rec_polys = result_list(result, "rec_polys") or result_list(result, "dt_polys")
        blocks = []
        for index, text in enumerate(rec_texts):
            blocks.append(
                {
                    "index": index,
                    "text": text,
                    "score": safe_float(rec_scores[index]) if index < len(rec_scores) else None,
                    "box": normalize_poly(rec_boxes[index]) if index < len(rec_boxes) else [],
                    "poly": normalize_poly(rec_polys[index]) if index < len(rec_polys) else [],
                }
            )

        raw = {
            "ocr_id": "OCR-1",
            "engine": "PaddleOCR",
            "paddleocr_version": getattr(paddleocr, "__version__", None),
            "paddle_version": getattr(paddle, "__version__", None),
            "ocr_version": "PP-OCRv5",
            "lang": "en",
            "settings": {
                "use_doc_orientation_classify": False,
                "use_doc_unwarping": False,
                "use_textline_orientation": False,
                "line_ordering_rule": "paddleocr_engine_returned_rec_texts_order",
                "text_det_params": result.get("text_det_params"),
                "text_rec_score_thresh": result.get("text_rec_score_thresh"),
            },
            "chart_id": chart_id,
            "image_path": rel(image_path),
            "blocks": blocks,
        }
        full_text = "\n".join(text for text in rec_texts if str(text).strip())
        raw_path = raw_dir / f"{chart_id}.json"
        text_path = text_dir / f"{chart_id}.txt"
        write_json(raw_path, raw)
        write_text(text_path, full_text)
        manifest_rows.append(
            {
                "ocr_id": "OCR-1",
                "engine": "PaddleOCR",
                "ocr_version": "PP-OCRv5",
                "chart_id": chart_id,
                "image_path": rel(image_path),
                "raw_blocks_path": rel(raw_path),
                "full_text_path": rel(text_path),
                "raw_blocks_sha256": sha256_file(raw_path),
                "full_text_sha256": sha256_file(text_path),
                "block_count": len(blocks),
            }
        )

    write_run_manifest(
        run_dir,
        {
            "ocr_id": "OCR-1",
            "engine": "PaddleOCR",
            "paddleocr_version": getattr(paddleocr, "__version__", None),
            "paddle_version": getattr(paddle, "__version__", None),
            "ocr_version": "PP-OCRv5",
            "lang": "en",
            "line_ordering_rule": "paddleocr_engine_returned_rec_texts_order",
            "ordinary_ocr_source": True,
            "mlm_or_vlm_transcription": False,
        },
        manifest_rows,
        sample_manifest=sample_manifest,
        sample_role=sample_role,
    )
    return manifest_rows


def run_tesseract(
    rows: list[dict[str, Any]],
    output_root: Path,
    tesseract_cmd: str,
    *,
    sample_manifest: Path = DEFAULT_MANIFEST,
    sample_role: str = "pilot10_external_excluded_from_formal_evaluation",
) -> list[dict[str, Any]]:
    import pytesseract
    from PIL import Image
    from pytesseract import Output

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    version = str(pytesseract.get_tesseract_version())

    run_dir = output_root / "ocr2_tesseract5_20260428_r1"
    raw_dir = run_dir / "raw_tsv"
    raw_json_dir = run_dir / "raw_blocks"
    text_dir = run_dir / "full_text"

    manifest_rows: list[dict[str, Any]] = []
    for row in rows:
        chart_id = row["chart_id"]
        image_path = resolve_package_path(row["image_path"])
        image = Image.open(image_path)
        data = pytesseract.image_to_data(
            image,
            lang="eng",
            config="--oem 3 --psm 6",
            output_type=Output.DICT,
        )
        records = []
        count = len(data.get("text", []))
        for index in range(count):
            records.append(
                {
                    "index": index,
                    "level": safe_int(data["level"][index]),
                    "page_num": safe_int(data["page_num"][index]),
                    "block_num": safe_int(data["block_num"][index]),
                    "par_num": safe_int(data["par_num"][index]),
                    "line_num": safe_int(data["line_num"][index]),
                    "word_num": safe_int(data["word_num"][index]),
                    "left": safe_int(data["left"][index]),
                    "top": safe_int(data["top"][index]),
                    "width": safe_int(data["width"][index]),
                    "height": safe_int(data["height"][index]),
                    "conf": safe_float(data["conf"][index]),
                    "text": data["text"][index],
                }
            )

        lines: dict[tuple[int | None, int | None, int | None], list[dict[str, Any]]] = {}
        for record in records:
            text = str(record["text"]).strip()
            if not text:
                continue
            key = (record["block_num"], record["par_num"], record["line_num"])
            lines.setdefault(key, []).append(record)
        full_text_lines = []
        for key in sorted(lines):
            words = sorted(lines[key], key=lambda item: (item["word_num"] or 0, item["left"] or 0))
            full_text_lines.append(" ".join(str(item["text"]).strip() for item in words if str(item["text"]).strip()))
        full_text = "\n".join(full_text_lines)

        tsv_path = raw_dir / f"{chart_id}.tsv"
        tsv_path.parent.mkdir(parents=True, exist_ok=True)
        with tsv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()) if records else ["index"])
            writer.writeheader()
            writer.writerows(records)

        raw_json = {
            "ocr_id": "OCR-2",
            "engine": "Tesseract OCR",
            "tesseract_version": version,
            "lang": "eng",
            "settings": {
                "oem": 3,
                "psm": 6,
                "line_ordering_rule": "block_par_line_word_order_from_tesseract_tsv",
            },
            "chart_id": chart_id,
            "image_path": rel(image_path),
            "blocks": records,
        }
        raw_json_path = raw_json_dir / f"{chart_id}.json"
        text_path = text_dir / f"{chart_id}.txt"
        write_json(raw_json_path, raw_json)
        write_text(text_path, full_text)
        manifest_rows.append(
            {
                "ocr_id": "OCR-2",
                "engine": "Tesseract OCR",
                "tesseract_version": version,
                "chart_id": chart_id,
                "image_path": rel(image_path),
                "raw_tsv_path": rel(tsv_path),
                "raw_blocks_path": rel(raw_json_path),
                "full_text_path": rel(text_path),
                "raw_tsv_sha256": sha256_file(tsv_path),
                "raw_blocks_sha256": sha256_file(raw_json_path),
                "full_text_sha256": sha256_file(text_path),
                "block_count": len(records),
                "nonempty_word_count": sum(1 for record in records if str(record["text"]).strip()),
            }
        )

    write_run_manifest(
        run_dir,
        {
            "ocr_id": "OCR-2",
            "engine": "Tesseract OCR",
            "tesseract_version": version,
            "lang": "eng",
            "settings": {
                "oem": 3,
                "psm": 6,
                "line_ordering_rule": "block_par_line_word_order_from_tesseract_tsv",
            },
            "ordinary_ocr_source": True,
            "mlm_or_vlm_transcription": False,
            "tesseract_cmd_recorded": False,
        },
        manifest_rows,
        sample_manifest=sample_manifest,
        sample_role=sample_role,
    )
    return manifest_rows


def write_run_manifest(
    run_dir: Path,
    config: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    sample_manifest: Path = DEFAULT_MANIFEST,
    sample_role: str = "pilot10_external_excluded_from_formal_evaluation",
) -> None:
    manifest_path = run_dir / "manifest.jsonl"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sample_manifest": rel(sample_manifest),
        "sample_role": sample_role,
        "config": config,
        "sample_count": len(rows),
        "manifest_path": rel(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
    }
    write_json(run_dir / "run_manifest.json", summary)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ordinary OCR-1/OCR-2 artifacts for pilot10.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--engine", choices=["paddleocr", "tesseract", "both"], default="both")
    parser.add_argument("--tesseract-cmd", default="tesseract")
    parser.add_argument("--sample-role", default="pilot10_external_excluded_from_formal_evaluation")
    args = parser.parse_args()

    rows = read_jsonl(args.manifest)[: args.limit]
    if args.engine in {"paddleocr", "both"}:
        run_paddleocr(rows, args.output_root, sample_manifest=args.manifest, sample_role=args.sample_role)
    if args.engine in {"tesseract", "both"}:
        run_tesseract(
            rows,
            args.output_root,
            args.tesseract_cmd,
            sample_manifest=args.manifest,
            sample_role=args.sample_role,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
