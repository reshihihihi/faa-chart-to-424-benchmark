# Group 1 Formal300 Ready-No-Eval Package - 2026-04-29

Status: **ready_no_eval_user_decision_required_before_formal_inference**

This package prepares Group 1 formal300 input and scoring manifests after
generating frozen ordinary OCR artifacts. It does not run formal300 method
inference.

## Run ID

```text
group1_formal300_ready_20260429_no_eval
```

Run plan:

```text
formal_runs/group1/group1_formal300_ready_20260429_no_eval/run_plan.json
```

Run plan SHA256:

```text
27E87F82A7667810BEBA079170CED7F9E233B9996331A7536B3A4DC7756C7050
```

## Readiness

```text
status: prepared_no_formal300_eval_run
sample_count: 300
methods: A1, A2, B1, B1_prime, B1_prime_link, C1, C2, C3, C4, D_SFT
inference_target_access: false
scoring_manifest_separate: true
formal300_evaluation_ran: false
readiness_error_count: 0
```

## OCR Inputs

OCR-1:

```text
ocr_artifacts/formal300/ocr1_paddleocr_ppocrv5_frozen/full_text
manifest SHA256: F31C34258BE5CA46BFD4D083682C4101A45368EFFF1525920FA020CD34EEBE39
```

Used by:

```text
A1, B1, B1_prime, B1_prime_link, C4
```

OCR-2:

```text
ocr_artifacts/formal300/ocr2_tesseract5_frozen/full_text
manifest SHA256: 3B53A370909404899D9CD207E2B15F187AC3E65C7040DABA3818D29575A85D10
```

Used by:

```text
A2
```

OCR audit:

```text
reports/freeze/group1_formal300_ocr_artifacts_audit_20260429.md
```

## Manifests Created

Each method now has a formal input manifest:

```text
formal_runs/group1/group1_formal300_ready_20260429_no_eval/A1/input_manifest.jsonl
formal_runs/group1/group1_formal300_ready_20260429_no_eval/A2/input_manifest.jsonl
formal_runs/group1/group1_formal300_ready_20260429_no_eval/B1/input_manifest.jsonl
formal_runs/group1/group1_formal300_ready_20260429_no_eval/B1_prime/input_manifest.jsonl
formal_runs/group1/group1_formal300_ready_20260429_no_eval/B1_prime_link/input_manifest.jsonl
formal_runs/group1/group1_formal300_ready_20260429_no_eval/C1/input_manifest.jsonl
formal_runs/group1/group1_formal300_ready_20260429_no_eval/C2/input_manifest.jsonl
formal_runs/group1/group1_formal300_ready_20260429_no_eval/C3/input_manifest.jsonl
formal_runs/group1/group1_formal300_ready_20260429_no_eval/C4/input_manifest.jsonl
formal_runs/group1/group1_formal300_ready_20260429_no_eval/D_SFT/input_manifest.jsonl
```

Scoring manifest:

```text
formal_runs/group1/group1_formal300_ready_20260429_no_eval/scoring_manifest.jsonl
SHA256: 92C6DD4693A69A457A976C91DEE4B435CEECFFA8B70D9567304CF780C49DA76A
```

## Remaining User Decision Before Step 7

The technical input-readiness blockers are cleared, but the user should decide
whether to start formal inference now. The known caveat is documented in:

```text
reports/freeze/formal300_pdf_duplicate_pre_run_disposition_20260429.md
```

No formal method evaluation has been run by this package.
