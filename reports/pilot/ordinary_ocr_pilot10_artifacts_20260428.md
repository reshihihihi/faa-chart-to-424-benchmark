# Ordinary OCR Pilot10 Artifacts - 2026-04-28

Status: candidate pilot artifacts, not formal frozen.

## Purpose

This report records the correction from MLLM-generated OCR text to ordinary OCR
sources for Experiment Group 1 pilot work.

The earlier B1 pilot used Claude-generated OCR text and is demoted to
pipeline/debug only. The corrected ordinary OCR sources are:

| OCR id | Engine | Role | Pilot artifact |
|---|---|---|---|
| OCR-1 | PaddleOCR PP-OCRv5 | Primary ordinary OCR for A1/B1/B1_prime/C4 | `ocr_artifacts/pilot10_external/ocr1_paddleocr_ppocrv5_20260428_r1/` |
| OCR-2 | Tesseract OCR 5.5.0 | Secondary ordinary OCR for A2 | `ocr_artifacts/pilot10_external/ocr2_tesseract5_20260428_r1/` |

## Group 1 Usage Rule

```text
A1, B1, B1_prime, and C4 use OCR-1.
A2 uses OCR-2.
C1, C2, and C3 do not receive OCR text.
```

## OCR-1 Environment

```text
engine: PaddleOCR
ocr_version: PP-OCRv5
paddleocr_version: 3.5.0
paddlepaddle_version: 3.2.2
lang: en
doc_orientation_classify: false
doc_unwarping: false
textline_orientation: false
line_ordering_rule: paddleocr_engine_returned_rec_texts_order
```

## OCR-2 Environment

```text
engine: Tesseract OCR
tesseract_version: 5.5.0.20241111
python_wrapper: pytesseract 0.3.13
lang: eng
oem: 3
psm: 6
line_ordering_rule: block_par_line_word_order_from_tesseract_tsv
```

The local executable path is intentionally not recorded in committed manifests.

## Generated Files

OCR-1 stores:

```text
raw_blocks/*.json
full_text/*.txt
manifest.jsonl
run_manifest.json
```

OCR-2 stores:

```text
raw_tsv/*.tsv
raw_blocks/*.json
full_text/*.txt
manifest.jsonl
run_manifest.json
```

Both artifacts preserve per-chart checksums in their `manifest.jsonl` files.

## Current Limitation

These are pilot10 artifacts only. Formal300 OCR artifacts still need to be
generated after the formal300 split and source policy are frozen.
