# Group 1 Method Boundary Audit - 2026-04-28

Status: candidate boundary audit after ordinary-OCR correction.

This audit checks whether the currently designed Experiment Group 1 methods preserve method boundaries, avoid cross-group leakage, and remain compatible with the canonical schema and paper-v2 evaluation logic.

## Audit Criteria

A method passes this audit only if:

- it reads only the inputs registered for that method;
- it does not read canonical targets, CIFP records, scorer outputs, field targets, evidence provenance, challenge tags, human annotations, or previous outputs during prediction;
- it does not mix Experiment Group 5 oracle/diagnostic inputs into Experiment Group 1 methods;
- it outputs, or is deterministically projected into, `schemas/missed_approach_leg.schema.json`;
- targets are used only after prediction and schema validation for pilot analysis/scoring.

## Group 1 Boundary Matrix

| Method | Intended question | Allowed prediction input | Model/rules role | Boundary audit | Formal status |
|---|---|---|---|---|---|
| A1 | OCR-1 + deterministic rules baseline | chart metadata + OCR-1 full-chart text | PaddleOCR PP-OCRv5 -> same A1/A2 rules | PASS as candidate: no image after OCR, no LLM/VLM, no target/scorer/CIFP | candidate, not formal frozen |
| A2 | OCR-source sensitivity with same rules | chart metadata + OCR-2 full-chart text | Tesseract 5.x -> same A1/A2 rules | PASS as candidate: differs from A1 only by OCR source | candidate, not formal frozen |
| B1 | Can a text LLM recover canonical missed-approach JSON from OCR-1 text alone? | chart metadata + OCR-1 full-chart text | gpt-5.4 text LLM | PASS: no image, no bbox, no field candidates, no target/scorer/CIFP | boundary frozen; prompt/model candidate |
| B1_prime | Does flat OCR-derived field evidence help the text LLM? | chart metadata + OCR-1 text + flat OCR-derived `field_candidates` | regex matcher + gpt-5.4 text LLM | PASS as candidate: field candidates are not leg-linked, not target-aware, and not Group 5 B1_link | candidate, not formal frozen |
| C1 | Direct image-to-canonical VLM baseline | chart metadata + full chart image | Claude VLM/MLLM | PASS as candidate: no OCR text, no OCR bbox, no target/scorer/CIFP | candidate, not formal frozen |
| C2 | Multi-QA VLM plus deterministic aggregation | chart metadata + full chart image + fixed QA prompt bundle | Claude QA calls + deterministic aggregator | PASS as candidate with blocker: QA prompts exist; aggregator candidate exists; QA runner and malformed-QA rerun policy not formal frozen | candidate, not formal frozen |
| C3 | Single-call questionnaire VLM then deterministic parser | chart metadata + full chart image | Claude VLM/MLLM + questionnaire-to-canonical parser | PASS: no OCR text, no field candidates, parser only rearranges fields | boundary frozen; prompt/model candidate |
| C4 | Image + ordinary OCR-1 assisted VLM/MLLM | chart metadata + full chart image + OCR-1 full-chart text | Claude VLM/MLLM with OCR-1 side input | PASS as candidate: OCR side input is registered OCR-1, not Claude transcription; no field candidates or target/scorer/CIFP | candidate, not formal frozen |

## Excluded From Group 1 Main Boundary

The following methods must not be mixed into the current Group 1 main extraction runs:

- `B1_link` / `B1-link`: Group 5 diagnostic field-to-leg linking method.
- `B2a`, `B2b`, `B3`, `B4`: Experiment Group 5 oracle/diagnostic variants.
- target-aware PR32 mapping or expected-value matching.
- any use of canonical proxy targets, CIFP, scorer outputs, or human annotation during prediction.

## OCR Boundary Check

Current OCR policy:

```text
OCR-1 = PaddleOCR PP-OCRv5 candidate full-chart ordinary OCR
OCR-2 = Tesseract 5.x candidate full-chart ordinary OCR
```

Allowed OCR use:

- OCR-1: A1, B1, B1_prime, C4
- OCR-2: A2 only
- no OCR text: C1, C2, C3

Claude may be used as VLM/MLLM for C1/C2/C3/C4, but must not be used as OCR-1 or OCR-2. Earlier B1/B1_prime/C4 evidence that used Claude-generated transcription as OCR remains demoted to pipeline/debug only.

## Status/Value Schema Check

All current B1, B1_prime, C1, C3, and C4 candidate prompts now include the same hard rule:

- `status` is only one of `present`, `not_applicable`, `not_observable`, `unknown`;
- extracted values such as `DF`, `FKL`, `3000`, `LEFT`, `R-350`, or hold parameters must go in `value`;
- if status is not `present`, value must be null.

This is a schema-compliance constraint and does not change the method's allowed inputs or scientific purpose.

## C2 Existing Assets Check

Existing:

- `prompts/path_c_qa_v2/` imported from upstream PR #28.

New candidate added:

- `docs/group1_c2_qa_aggregator_candidate_v1.md`
- `scripts/aggregate_c2_qa_candidate.py`

Remaining before formal freeze:

- fixed C2 QA runner;
- QA-call raw output layout;
- malformed QA output policy;
- retry/rerun policy for API failure, parse failure, and schema failure.

## A1/A2 Rules Check

New candidate added:

- `docs/group1_a1_a2_rules_candidate_v1.md`
- `scripts/run_a1_a2_rules_pilot10.py`

Boundary protection:

- same rule set for A1 and A2;
- no LLM/VLM use;
- no target/scorer/CIFP access during prediction;
- targets are read only after schema validation when pilot scoring is requested by the runner.

Remaining before formal freeze:

- review whether the conservative regex rules are acceptable as the formal A1/A2 baseline;
- record final OCR preprocessing and OCR artifact checksums;
- finalize whether malformed OCR artifacts fail the sample or produce unknown outputs.

## Overall Judgment

The current design satisfies the experiment-boundary requirements as candidate Group 1 definitions. It is not formal-evaluation ready because A1/A2 rules, B1_prime matcher, C1/C2/C4 boundaries, model settings, prompts, OCR artifact policy, and rerun policy remain candidate/not formally frozen.
