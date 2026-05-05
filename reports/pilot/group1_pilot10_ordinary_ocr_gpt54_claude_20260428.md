# Group 1 Pilot10 Summary - Ordinary OCR Boundary Corrected

Status: pilot evidence only, not formal evaluation.

Date: 2026-04-28.

Sample scope: `pilot10_external`, excluded from the formal 300-chart evaluation.

## Purpose

This report records the current Experiment Group 1 pilot10 state after correcting the OCR boundary:

- OCR-1 is ordinary PaddleOCR PP-OCRv5, not an MLLM transcription.
- OCR-2 is ordinary Tesseract 5.x.
- B1/B1_prime use `gpt-5.4` as text LLM through the OpenAI-compatible local proxy.
- C1/C2/C3/C4 use `claude-sonnet-4-5-20250929` as the VLM/MLLM image-input model.
- All methods produce final canonical JSON matching `schemas/missed_approach_leg.schema.json`.

Targets and scorer are used only after JSON parsing and schema validation.

## Result Table

| Method | Boundary | Run ID | Final schema-valid | Parser repair | Schema retry | Score |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| A1 | OCR-1 -> Rules -> canonical JSON | `pilot10_group1_a1_a2_rules_ordinary_ocr_20260428_r1` | 10/10 | 0 | n/a | 62/220 = 0.2818 |
| A2 | OCR-2 -> same Rules -> canonical JSON | `pilot10_group1_a1_a2_rules_ordinary_ocr_20260428_r1` | 10/10 | 0 | n/a | 44/220 = 0.2000 |
| B1 | OCR-1 -> gpt-5.4 -> canonical JSON | `pilot10_group1_b1_b1prime_gpt54_toolcall_schema_retry1_ordinary_ocr_20260428_r1` | 10/10 | 0 | 0 | 75/220 = 0.3409 |
| B1_prime | OCR-1 -> OCR-derived field_candidates -> gpt-5.4 -> canonical JSON | `pilot10_group1_b1_b1prime_gpt54_toolcall_schema_retry1_ordinary_ocr_20260428_r1` | 10/10 | 0 | 0 | 89/220 = 0.4045 |
| C1 | chart image -> Claude VLM -> canonical JSON | `pilot10_group1_c1_c3_c4_claude_tooluse_fixident_ordinary_ocr_20260428_r2` | 10/10 | 0 | 0 | 99/220 = 0.4500 |
| C2 | chart image -> fixed QA calls -> deterministic aggregator -> canonical JSON | `pilot10_group1_c2_claude_tooluse_qa_q4loose_tool_strict_validate_ordinary_ocr_20260428_r3` | 10/10 | 0 | 1 QA retry | 60/220 = 0.2727 |
| C3 | chart image -> questionnaire JSON -> deterministic parser -> canonical JSON | `pilot10_group1_c1_c3_c4_claude_tooluse_fixident_ordinary_ocr_20260428_r2` | 10/10 | 0 | 0 | 94/220 = 0.4273 |
| C4 | chart image + OCR-1 text -> Claude VLM -> canonical JSON | `pilot10_group1_c1_c3_c4_claude_tooluse_fixident_ordinary_ocr_20260428_r2` | 10/10 | 0 | 3 | 117/220 = 0.5318 |

## C2 Notes

The first full C2 run showed a uniform Q4 formatting failure: the model emitted `Q4_course_or_radial.value` as a stringified JSON object. The final C2 run fixed this by using:

- proxy-compatible tool schema for Q4 that requires `value` to be an object or null;
- strict local validation against the canonical answer schema before saving QA JSON;
- no post-hoc parsing of stringified objects.

Final C2 run:

- QA calls total: 238
- QA calls saved: 238
- QA schema retries: 1
- final canonical schema-valid: 10/10

## Current Freeze Interpretation

Already frozen or effectively frozen for this pilot line:

- canonical final output schema: `schemas/missed_approach_leg.schema.json`
- pilot10 external exclusion from formal evaluation
- parser repair policy: no code-fence stripping, no JSON substring extraction, no semantic repair
- B1/C3 method boundary concepts already recorded as frozen in the existing manifest
- ordinary OCR boundary correction: Claude/MLLM transcription is not OCR-1 or OCR-2
- OpenAI-compatible text LLM tool-call output control for B1/B1_prime

Still candidate / not formal frozen:

- OCR-1 PaddleOCR PP-OCRv5 full formal artifact policy
- OCR-2 Tesseract 5.x full formal artifact policy
- A1/A2 rules implementation
- B1_prime field_candidates matcher/schema implementation
- C1/C2/C3/C4 prompts and prompt hashes
- Claude tool-use output control for C1/C2/C3/C4
- C2 QA runner, Q4 proxy-compatible tool schema, and deterministic aggregator
- model/provider/max_tokens/base URL policy
- schema-only retry policy for formal evaluation
- formal300 sample manifest, targets, scorer, and split

## Boundary Checks

- A1, B1, B1_prime, and C4 use OCR-1 only where OCR text is allowed.
- A2 uses OCR-2.
- C1, C2, and C3 do not receive OCR text.
- B1_prime uses OCR-derived field_candidates only, not target-derived or scorer-derived candidates.
- C2 uses model-predicted Q0 leg count to decide how many per-leg QA calls to make.
- Targets are used only after final canonical JSON validation for scoring.

## Remaining Before Formal Freeze

1. Update candidate manifests to reflect the latest prompt hashes, C2 runner, and Claude tool-use policy.
2. Decide whether the C2 Q4 proxy-compatible tool schema is acceptable as an output-control device.
3. Audit A1/A2 rules for target leakage and document the final rule set.
4. Decide formal model/provider/max_tokens/image settings.
5. Freeze formal300 sample manifest, canonical targets, scorer, rerun policy, and OCR artifact policy.
