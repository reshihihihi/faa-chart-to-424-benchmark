from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import pytesseract
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_RUN_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_dev50_20260503_r1"
DEFAULT_OUT_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_dev50_20260504_r5_ma_text_ocr_review"
DEFAULT_TESSERACT_CMD = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
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


def normalize_ocr_text(text: str) -> str:
    text = text.replace("\u00b0", "°").replace("掳", "°")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"\s*:\s*", ": ", text)
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r"\s+\.", ".", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def extract_missed_approach_clause(text: str) -> str:
    match = re.search(r"\bMISSED\s+APPROACH\s*[:.]?\s*(.*)", text, flags=re.IGNORECASE)
    if not match:
        return text.strip()
    clause = "MISSED APPROACH: " + match.group(1).strip()
    return normalize_ocr_text(clause)


def markdown_image_path(path: str) -> str:
    return path.replace("\\", "/")


def preprocess_image(src: Path, dst: Path) -> None:
    image = cv2.imread(str(src), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise RuntimeError(f"Unable to read image: {src}")
    image = cv2.resize(image, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    image = cv2.fastNlMeansDenoising(image, h=10)
    image = cv2.copyMakeBorder(image, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
    binary = cv2.adaptiveThreshold(
        image,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dst), binary)


def ocr_image(path: Path, *, psm: int) -> tuple[str, float | None]:
    config = f"--oem 3 --psm {psm} -c preserve_interword_spaces=1"
    data = pytesseract.image_to_data(Image.open(path), lang="eng", config=config, output_type=pytesseract.Output.DICT)
    words: list[str] = []
    confidences: list[float] = []
    for text, conf in zip(data.get("text", []), data.get("conf", [])):
        text = str(text or "").strip()
        try:
            conf_value = float(conf)
        except ValueError:
            conf_value = -1.0
        if text:
            words.append(text)
            if conf_value >= 0:
                confidences.append(conf_value)
    mean_conf = round(sum(confidences) / len(confidences), 2) if confidences else None
    return normalize_ocr_text(" ".join(words)), mean_conf


def choose_ocr(variants: list[dict[str, Any]]) -> dict[str, Any]:
    nonempty = [item for item in variants if item["text"]]
    if not nonempty:
        return {"psm": None, "text": "", "mean_confidence": None}
    return sorted(
        nonempty,
        key=lambda item: (
            item["mean_confidence"] if item["mean_confidence"] is not None else -1,
            len(item["text"]),
        ),
        reverse=True,
    )[0]


def chart_id_from_crop(path: Path) -> str:
    return path.name.replace("_admin_ma_text_crop_v2.png", "")


def load_pdf_candidates(run_dir: Path, artifact_label: str) -> dict[str, str]:
    candidate_paths = [
        run_dir / "inputs" / f"gold_ma_text_{artifact_label}_pdf_text_layer_candidate.jsonl",
        run_dir / "inputs" / f"gold_ma_text_{artifact_label}_candidate.jsonl",
        run_dir / "inputs" / "gold_ma_text_dev50_candidate.jsonl",
    ]
    candidates: dict[str, str] = {}
    for path in candidate_paths:
        if not path.exists():
            continue
        for row in read_jsonl(path):
            chart_id = row.get("chart_id")
            text = row.get("gold_ma_prose")
            if chart_id and isinstance(text, str):
                candidates[str(chart_id)] = normalize_ocr_text(text)
        if candidates:
            break
    return candidates


def render_review_sheet(rows: list[dict[str, Any]], artifact_label: str) -> str:
    lines = [
        f"# Experiment 5 {artifact_label} MA_TEXT OCR 人工校验表",
        "",
        "说明：这里的 OCR/PDF text-layer 都只是候选。请以图片为准，把确认后的文本填入 review JSONL 的 `reviewed_gold_ma_prose`。",
        "",
        "严格规则：确认前不能把这些候选当作正式 A3/B2/B3_T 输入；确认后才可以生成 `gold_ma_text_dev50_ocr_reviewed.jsonl`。",
        "",
    ]
    for row in rows:
        lines.append(f"## {row['chart_id']}")
        lines.append("")
        lines.append(f"![{row['chart_id']} MA_TEXT crop]({markdown_image_path(row['crop_image_path'])})")
        lines.append("")
        lines.append(f"- OCR candidate confidence: `{row['selected_ocr_mean_confidence']}`")
        lines.append("")
        lines.append("OCR raw candidate:")
        lines.append("")
        lines.append("```text")
        lines.append(row["ocr_text_candidate"] or "")
        lines.append("```")
        lines.append("")
        lines.append("OCR MISSED APPROACH candidate:")
        lines.append("")
        lines.append("```text")
        lines.append(row["ocr_missed_approach_candidate"] or "")
        lines.append("```")
        lines.append("")
        lines.append("PDF text-layer candidate:")
        lines.append("")
        lines.append("```text")
        lines.append(row["pdf_text_layer_candidate"] or "")
        lines.append("```")
        lines.append("")
        lines.append("PDF MISSED APPROACH candidate:")
        lines.append("")
        lines.append("```text")
        lines.append(row["pdf_missed_approach_candidate"] or "")
        lines.append("```")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR Experiment 5 dev50 admin MA_TEXT crops for human review.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--tesseract-cmd", type=Path, default=DEFAULT_TESSERACT_CMD)
    parser.add_argument("--artifact-label", default="dev50")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if args.tesseract_cmd.exists():
        pytesseract.pytesseract.tesseract_cmd = str(args.tesseract_cmd)

    crop_dir = args.run_dir / "visuals" / "admin_ma_text_crops_v2"
    crop_paths = sorted(
        path
        for path in crop_dir.glob("*_admin_ma_text_crop_v2.png")
        if not path.name.startswith("dev50_")
    )
    if args.limit:
        crop_paths = crop_paths[: args.limit]

    pdf_candidates = load_pdf_candidates(args.run_dir, args.artifact_label)
    preprocessed_dir = args.out_dir / "visuals" / "preprocessed_admin_ma_text_crops_v2"
    rows: list[dict[str, Any]] = []

    for crop_path in crop_paths:
        chart_id = chart_id_from_crop(crop_path)
        processed_path = preprocessed_dir / f"{chart_id}_admin_ma_text_crop_v2_ocr_preprocessed.png"
        preprocess_image(crop_path, processed_path)
        variants: list[dict[str, Any]] = []
        for psm in [6, 7, 11]:
            text, confidence = ocr_image(processed_path, psm=psm)
            variants.append({"psm": psm, "text": text, "mean_confidence": confidence})
        selected = choose_ocr(variants)
        pdf_text_layer_candidate = pdf_candidates.get(chart_id, "")
        rows.append(
            {
                "schema_version": "experiment5_ma_text_ocr_human_review_queue_v1",
                "chart_id": chart_id,
                "crop_image_path": str(crop_path.resolve()),
                "preprocessed_image_path": str(processed_path.resolve()),
                "ocr_engine": "tesseract_eng",
                "ocr_variants": variants,
                "selected_ocr_psm": selected["psm"],
                "selected_ocr_mean_confidence": selected["mean_confidence"],
                "ocr_text_candidate": selected["text"],
                "ocr_missed_approach_candidate": extract_missed_approach_clause(selected["text"]),
                "pdf_text_layer_candidate": pdf_text_layer_candidate,
                "pdf_missed_approach_candidate": extract_missed_approach_clause(pdf_text_layer_candidate),
                "review_status": "needs_human_review",
                "reviewed_gold_ma_prose": "",
                "review_notes": "",
                "source_contract": {
                    "allows_chart_crop_pixels": True,
                    "allows_ocr_text": True,
                    "allows_pdf_text_layer_candidate_for_review": True,
                    "allows_final_answer": False,
                    "allows_canonical_target": False,
                    "derived_from_final_answer": False,
                },
            }
        )

    inputs_dir = args.out_dir / "inputs"
    reports_dir = args.out_dir / "reports"
    queue_path = inputs_dir / f"gold_ma_text_{args.artifact_label}_ocr_review_queue.jsonl"
    template_path = inputs_dir / f"gold_ma_text_{args.artifact_label}_ocr_review_template.jsonl"
    report_path = reports_dir / f"ma_text_{args.artifact_label}_ocr_review_sheet_zh.md"
    summary_path = reports_dir / f"ma_text_{args.artifact_label}_ocr_review_summary.json"

    write_jsonl(queue_path, rows)
    write_jsonl(template_path, rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_review_sheet(rows, args.artifact_label), encoding="utf-8")
    write_json(
        summary_path,
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "chart_count": len(rows),
            "artifact_label": args.artifact_label,
            "queue_path": str(queue_path),
            "template_path": str(template_path),
            "report_path": str(report_path),
            "ocr_engine": "tesseract_eng",
            "ready_for_formal_input": False,
            "reason": "Human review is required before these OCR candidates can become formal gold MA text.",
            "confidence_summary": {
                "with_ocr_text": sum(1 for row in rows if row["ocr_text_candidate"]),
                "empty_ocr_text": sum(1 for row in rows if not row["ocr_text_candidate"]),
                "mean_confidence_min": min(
                    [row["selected_ocr_mean_confidence"] for row in rows if row["selected_ocr_mean_confidence"] is not None],
                    default=None,
                ),
                "mean_confidence_max": max(
                    [row["selected_ocr_mean_confidence"] for row in rows if row["selected_ocr_mean_confidence"] is not None],
                    default=None,
                ),
            },
        },
    )
    print(json.dumps({"rows": len(rows), "queue_path": str(queue_path), "report_path": str(report_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
