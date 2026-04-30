# Group 1 Formal300 OCR Artifacts Audit - 2026-04-29

Status: **formal300_ocr_artifacts_generated_ready_for_pre_run_review**

This audit records the formal300 ordinary OCR artifacts required before Group 1
formal300 evaluation. No formal300 method inference was run in this step.

## OCR-1

OCR-1 is the ordinary OCR source for:

```text
A1, B1, B1_prime, B1_prime_link, C4
```

Artifact root:

```text
ocr_artifacts/formal300/ocr1_paddleocr_ppocrv5_frozen/
```

Configuration:

```text
engine: PaddleOCR
ocr_version: PP-OCRv5
paddleocr_version: 3.5.0
paddle_version: 3.2.2
lang: en
ordinary_ocr_source: true
mlm_or_vlm_transcription: false
line_ordering_rule: paddleocr_engine_returned_rec_texts_order
```

Counts:

```text
manifest rows: 300
full_text files: 300
raw_blocks files: 300
missing referenced files: 0
empty full_text files: 0
min block_count: 89
max block_count: 226
avg block_count: 142.90
```

Hashes:

```text
manifest.jsonl SHA256: F31C34258BE5CA46BFD4D083682C4101A45368EFFF1525920FA020CD34EEBE39
run_manifest.json SHA256: C563A2BCF75D7AD863BC4118FB737B86713F014C659E00343DDC701815FE15B5
```

## OCR-2

OCR-2 is the ordinary OCR source for:

```text
A2
```

Artifact root:

```text
ocr_artifacts/formal300/ocr2_tesseract5_frozen/
```

Configuration:

```text
engine: Tesseract OCR
tesseract_version: 5.5.0.20241111
tesseract_cmd: <local-tesseract-install>\tesseract.exe
lang: eng
oem: 3
psm: 6
ordinary_ocr_source: true
mlm_or_vlm_transcription: false
line_ordering_rule: block_par_line_word_order_from_tesseract_tsv
```

Counts:

```text
manifest rows: 300
full_text files: 300
raw_blocks files: 300
raw_tsv files: 300
missing referenced files: 0
empty full_text files: 0
min block_count: 199
max block_count: 625
avg block_count: 355.87
```

Hashes:

```text
manifest.jsonl SHA256: 3B53A370909404899D9CD207E2B15F187AC3E65C7040DABA3818D29575A85D10
run_manifest.json SHA256: CCCC263A4542B9338F96D6777563C6FB7509C66F7641BE7F404C49C36690E70E
```

## Boundary Decision

Both OCR artifacts are ordinary OCR outputs. They are not LLM, VLM, MLLM, or
human transcription outputs. They should be treated as frozen input artifacts
for the next no-eval formal run preparation.

## Caveat

This audit checks artifact presence, hashes, and basic non-empty text status. It
does not certify OCR correctness.
