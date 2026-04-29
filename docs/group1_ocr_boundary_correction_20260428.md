# Experiment Group 1 OCR Boundary Correction - 2026-04-28

Status: active correction.

## Problem

The pilot run `pilot10_exp1_b1_c3_strict_json_prefill_20260427_r1`
generated B1 OCR text with `claude-sonnet-4-5-20250929`. That model is a
multimodal/LLM model, not an ordinary OCR engine.

This makes the saved B1 pilot result invalid as evidence for the formal
Experiment Group 1 B1 method, because the plan separates:

- A/B methods: ordinary OCR text, gold text, or ROI text followed by rules or
  text LLMs;
- C methods: VLM/MLLM image methods.

Using Claude as OCR would mix C-family visual model capability into the A/B
OCR baseline.

## Corrected Interpretation

The saved B1 output is retained only as a pipeline/debug artifact:

```text
MLLM-generated full-chart transcription -> LLM -> canonical JSON
```

It must not be reported as formal B1 evidence.

The saved C3 output is not invalidated by this OCR issue because C3 is an
image-only VLM/MLLM questionnaire method. It remains pilot-only evidence and is
still not a formal frozen result.

The closed PR #17 B1_prime/C4 artifacts have the same OCR source problem:

- B1_prime reused the Claude-generated OCR text;
- C4 used image plus Claude-generated OCR text.

Those artifacts are pipeline/debug only and must be rerun with ordinary OCR-1
before they can be used as B1_prime/C4 pilot evidence.

## Corrected Group 1 OCR Rule

For formal-style Experiment Group 1 runs:

```text
OCR-1 = ordinary OCR source used by A1, B1, B1_prime, and C4
OCR-2 = second ordinary OCR source used only by A2
```

C1, C2, and C3 do not receive OCR text unless a separate method variant is
registered.

## Candidate OCR Sources

The current candidate policy is recorded in `configs/ocr_source_manifest.json`:

- OCR-1: PaddleOCR PP-OCRv5 full-chart OCR.
- OCR-2: Tesseract 5.x full-chart OCR.

Both are candidate sources, not formal frozen sources, until their exact package
versions, preprocessing, output layout, checksums, and OCR artifacts are
generated and reviewed.

## Required Reruns

The following results must be regenerated with ordinary OCR-1 before being used
as pilot or formal evidence:

- A1: OCR-1 -> Rules -> canonical JSON.
- B1: OCR-1 -> LLM -> canonical JSON.
- B1_prime: OCR-1 -> field candidates -> LLM -> canonical JSON.
- C4: image + OCR-1 -> VLM/MLLM -> canonical JSON.

A2 must be generated with OCR-2:

- A2: OCR-2 -> Rules -> canonical JSON.

C1 still needs to be run separately:

- C1: image -> VLM/MLLM -> canonical JSON.
