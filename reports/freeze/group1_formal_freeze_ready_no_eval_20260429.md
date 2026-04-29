# Group 1 Formal Freeze Package - No Formal300 Run

Status: **group1_model_prompt_rerun_frozen_no_formal300_eval_run**

Formal300 assets, targets, field/evidence/challenge exports, scorer, invalid-output scoring, degree policy, formal input/scoring manifest separation, model choices, prompts, and rerun policies are recorded. No formal300 method evaluation has been run.

## Current Formal300 Asset Counts

- samples: 300
- images: 300
- PDFs: 299 (must be reviewed: likely duplicate-PDF reuse or a materialization gap)
- canonical proxy targets: 300
- field_targets rows: 6084
- evidence_provenance rows: 6084
- challenge_tags rows: 300

## Current C4 Output-Control Status

C4 high retry has been resolved in pilot100 external feasibility validation:

- report: `reports/pilot/c4_output_control_fix_pilot100_20260429.md`
- schema-valid: 100/100 after API-failure recovery
- schema retry: 0
- parser repair: 0
- wrapper-like final outputs: 0
- mechanical root unwrap: disabled

## Remaining Before Running Formal300

- Generate and freeze formal300 OCR-1 PaddleOCR artifacts for A1/B1/B1_prime/B1_prime_link/C4.
- Generate and freeze formal300 OCR-2 Tesseract artifacts for A2.
- Review whether 299 PDF files for 300 samples are expected duplicate-PDF reuse or a materialization gap, then record the decision.
- Do not run formal300 method evaluation until OCR artifacts, final run ids, and reviewer-approved manifests are in place.

## Key Files

- `configs/group1_formal_freeze_manifest_20260429.json`
- `benchmark_exports/derived/v2/formal300/`
- `formal_runs/group1/group1_formal_prepared_20260429_no_eval/run_plan.json`
- `configs/scorer_validator_manifest.json`
- `reports/pilot/c4_output_control_fix_pilot100_20260429.md`
