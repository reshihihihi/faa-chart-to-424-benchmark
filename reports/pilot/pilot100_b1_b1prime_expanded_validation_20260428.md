# B1/B1_prime Pilot100 Expanded Validation

Status: expanded feasibility validation only; not formal300 evaluation.

Date: 2026-04-28.

External artifact root: `<external-artifact-root>/try_B1_B1_prime`

## Step 1 - Evidence Fix

Current valid pilot100 evidence:

- run_id: `pilot100_b1_b1prime_gpt54_toolcall_schema_retry1_ordinary_ocr_20260428_r1`
- run directory: `<external-artifact-root>/try_B1_B1_prime\predictions\pilot100_b1_b1prime_gpt54_toolcall_schema_retry1_ordinary_ocr_20260428_r1`
- result summary: `<external-artifact-root>/try_B1_B1_prime\reports\pilot100_b1_b1prime_result_summary_20260428_r1.json`
- expanded validation report: `<external-artifact-root>/try_B1_B1_prime\reports\pilot100_b1_b1prime_expanded_validation_report_20260428_r1.md`

This evidence is separate from pilot10 and formal300:

- sample count: 100
- unique chart_id: 100
- unique PDF: 100
- formal300 chart_id overlap: 0
- formal300 PDF overlap: 0
- pilot10 chart_id overlap: 0
- pilot10 PDF overlap: 0

Therefore this run can be used as expanded pilot evidence, but not as formal evaluation.

## Step 2 - Manifest / Hash / Artifact Record

Data:

- sample manifest: `<external-artifact-root>/try_B1_B1_prime\data\pilot100_external\pilot100_external_manifest.jsonl`
- checksums: `<external-artifact-root>/try_B1_B1_prime\data\pilot100_external\checksums.sha256`
- data audit: `<external-artifact-root>/try_B1_B1_prime\reports\pilot100_external_audit_20260428_r1.json`

OCR-1:

- engine: PaddleOCR PP-OCRv5 ordinary OCR
- PaddleOCR version: 3.5.0
- OCR text files: 100/100
- raw block files: 100/100
- empty OCR text files: 0
- OCR audit: `<external-artifact-root>/try_B1_B1_prime\reports\ocr1_paddleocr_pilot100_external_audit_20260428_r1.json`

Schema and prompts used:

- canonical schema: `schemas/missed_approach_leg.schema.json`
- canonical schema sha256: `cd62edf995344d73ae45fcfad4e9bff3412f58a42f9fb591f9ca08e399e26be9`
- field candidates schema: `schemas/field_candidates.schema.candidate.json`
- field candidates schema sha256: `babd288dd754989813b872f84d232cbcf6bde7ae250532b74c7a6286a7aef4df`
- B1 prompt sha256: `bbaa3e85730bbc1c4da5c45bede142b891d915502313843b363140377be822bf`
- B1_prime prompt sha256: `f8c8d403dea1e5602825de3763474ed55bf8259ed3eee0fbd4a4c1a1ffb5f0f6`

Model and output control:

- provider: `openai_compatible`
- model: `gpt-5.4`
- base URL: `http://127.0.0.1:8080/v1`
- temperature: 0.0
- max_tokens: 4096
- output control: forced `openai_tool_call`
- tool name: `emit_canonical_json`
- schema retry count allowed: 1
- retry uses target/scorer: false
- parser repair: false

## Step 3 - Method Boundary Review

B1 boundary:

```text
OCR-1 full-chart text -> gpt-5.4 -> canonical JSON
```

Allowed B1 inputs:

- chart metadata
- OCR-1 full-chart text from ordinary PaddleOCR
- canonical schema / output contract

Forbidden B1 inputs:

- chart image pixels at LLM stage
- OCR boxes / ROI labels / human annotations
- field candidates
- targets, scorer outputs, CIFP/ARINC 424 records
- previous model outputs for the same chart

B1_prime boundary:

```text
OCR-1 full-chart text
  -> OCR-derived flat field_candidates
  -> gpt-5.4
  -> canonical JSON
```

Allowed B1_prime inputs:

- chart metadata
- OCR-1 full-chart text from ordinary PaddleOCR
- flat field_candidates produced from OCR text only
- canonical schema / output contract

Forbidden B1_prime inputs:

- chart image pixels at LLM stage
- target-aware mappings
- field-to-leg gold or oracle links
- scorer outputs
- CIFP/ARINC 424 records
- human annotations

Boundary conclusion:

- B1 and B1_prime stayed inside the intended Group 1 method boundaries in this pilot100 run.
- Scoring used targets only after final canonical JSON validation.
- No parse repair, code-fence stripping, target-aware repair, or semantic post-processing was used.

## Step 4 - Pre-Freeze Decision

B1:

- final schema-valid: 100/100
- parser repair: 0
- schema retries: 7/100
- score: 723/2344 = 0.308447

Decision:

- B1 method boundary remains suitable to keep frozen.
- B1 prompt/model/provider/max_tokens should remain candidate, not formally frozen.
- B1 output-control policy is strengthened by this 100-sample evidence, but formal rerun policy still needs final freeze.

B1_prime:

- final schema-valid: 100/100
- parser repair: 0
- field_candidates schema-valid: 100/100
- schema retries: 11/100
- score: 674/2344 = 0.287543

Decision:

- B1_prime is runnable and schema-stable.
- Do not formally freeze B1_prime implementation yet.
- The pilot100 result reverses the pilot10 direction: B1_prime is lower than B1 on 100 external samples.
- The field_candidates matcher/schema should remain candidate until error analysis explains when it helps or hurts.

## Step 5 - PR Organization

Recommended PR contents:

- this pilot100 report;
- manifest updates recording the pilot100 evidence;
- prompt hash updates for B1 and B1_prime;
- model manifest update showing both pilot10 and pilot100 evidence for `gpt-5.4` tool-call output control.

Do not commit the large external pilot100 image/PDF/prediction artifact tree directly unless the repository intentionally accepts generated artifacts. The artifact root should remain referenced as:

```text
<external-artifact-root>/try_B1_B1_prime
```

PR description must say:

- pilot100 is expanded feasibility validation only;
- pilot100 has no formal300 or pilot10 overlap;
- B1/B1_prime final outputs are schema-valid 100/100;
- B1_prime underperforms B1 on this expanded set, so its matcher is not ready for formal freeze.

## Step 6 - Expanded Validation Conclusion

The 100-sample run strengthens confidence in the B1/B1_prime execution path:

- no API failures;
- no missing OCR files;
- no final schema failures;
- no parser repair;
- no field_candidates schema failures.

The main unresolved scientific/engineering issue is not format stability but method quality:

- B1 accuracy is modest;
- B1_prime accuracy is lower than B1 in the expanded run;
- B1_prime needs targeted error analysis before formal freeze.

Recommended next action:

1. keep B1 as boundary-frozen with candidate prompt/model parameters;
2. keep B1_prime as candidate runnable method;
3. analyze low-score and retry cases before freezing the matcher;
4. do not tune B1_prime using target answers or scorer feedback.
