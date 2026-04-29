# B1_prime Method Decision

Status: candidate / pre-freeze only, not formally frozen

Date: 2026-04-28

Primary external copy:

```text
E:\experiment3\try_B1_B1'\reports\b1prime_method_decision_20260428.md
```

## Decision

B1_prime remains a valid candidate method for testing whether OCR-text-derived flat field candidates help a text LLM recover missed approach canonical JSON from full-chart OCR. It is not ready for formal freeze.

The current best candidate is B1_prime v8. It may be used for pilot comparisons and method-boundary discussion, but it should not be treated as a final frozen method for formal300.

## Method Boundary

```text
full-chart image
  -> OCR-1 full-chart text
  -> OCR-text-only flat field_candidates
  -> OCR text + field_candidates
  -> text LLM
  -> canonical JSON
```

Allowed inputs:

- chart metadata needed to identify the sample;
- OCR-1 full-chart text from PaddleOCR PP-OCRv5 ordinary OCR;
- OCR-text-only flat field candidates;
- the canonical output schema contract.

Forbidden inputs:

- target JSON;
- scorer rows or score feedback;
- CIFP or ARINC 424 records;
- human annotation, gold observable evidence, or gold missed approach prose;
- chart image pixels at the LLM stage;
- OCR bounding boxes, ROI labels, or visual cell tables;
- `leg_index`, `candidate_leg_id`, schema-field assignment, expected values, or any field-to-leg binding.

## Relationship To B1

B1 uses only OCR-1 full-chart text plus the LLM. B1_prime adds an automatic flat candidate table extracted from the same OCR text. If those candidates are removed, the method becomes B1. If candidates are linked to legs or schema fields, the method is no longer B1_prime.

## Relationship To B1_link And B3V3

B1_link is the correct place to test field-to-leg linking:

```text
OCR-1 text -> flat candidates -> field-to-leg candidate linking -> LLM -> canonical JSON
```

B3V3 is stronger still because it uses region-aware / ROI OCR evidence and candidate-leg structures. B1_prime must not import B3V3-style `candidate_legs` or leg-indexed fields.

## Current Evidence

Pilot100 external validation:

- run_id: `pilot100_b1_b1prime_gpt54_toolcall_schema_retry1_ordinary_ocr_20260428_r1`
- B1: 100/100 schema-valid, 723/2344 = 0.308447
- B1_prime v3: 100/100 schema-valid, 674/2344 = 0.287543
- interpretation: B1_prime was runnable and format-stable but underperformed B1.

B1_prime v7:

- candidate audit: 100/100 `field_candidates` schema-valid, 0 model calls
- smoke18: 18/18 schema-valid, 0 parser repair, 0 schema retries, 159/438 = 0.363014
- probe30: 30/30 schema-valid, 0 parser repair, 2 schema-only retries, 191/606 = 0.315182
- interpretation: v7 fixed the catastrophic empty-leg failure mode but remained below B1 on probe30.

B1_prime v8:

- candidate audit: 100/100 `field_candidates` schema-valid, 0 model calls
- hard4 smoke: 4/4 schema-valid, 0 parser repair, 0 schema retries, 27/160 = 0.16875
- hard4 comparison: v7 13/160, v8 27/160
- interpretation: v8 helps explicit `track ... to FIX` OCR prose but does not solve route-table-only RNAV procedures such as `KLLJ_RNV-A`.

## Main Failure Modes

1. Older B1_prime versions produced schema-valid empty `legs` on some charts. This was largely fixed in v7.
2. Flat candidates can still mislead the model when candidate precision is low.
3. Complex RNAV / LOC procedures are often under-segmented.
4. Route-table or plan-view-only sequences remain weak because B1_prime has no field-to-leg binding.
5. Adding leg binding would answer a different question and must be handled as B1_link / Group 5.

## Decision Rules Going Forward

B1_prime may continue to use flat OCR-derived evidence such as:

- `instruction_snippets`;
- `track_to_fix_snippets`;
- `route_sequence_snippets`;
- flat fix, altitude, turn, course, hold candidates;
- confidence and notes that describe OCR-text-local uncertainty.

B1_prime must not add:

- `candidate_legs`;
- `leg_index`;
- `candidate_leg_id`;
- field-to-leg links;
- schema-field assignment such as `Q1_fix_ident`;
- target-aware sorting, filtering, or rerun selection.

## Freeze Status

B1_prime v8 is candidate / pre-freeze only. It is not formally frozen. The next work on field-to-leg binding should be started as B1_link, not as another B1_prime repair.

## Final Pre-Freeze Optimization Note - 2026-04-29

The final pre-freeze optimization did not add another B1_prime matcher repair. Only generic output/schema hardening was added to the B1_prime prompt:

- exact metadata copy from input metadata;
- status/value separation self-check;
- fix-ident length and facility-type safeguards;
- degree range safeguard including `360 -> 359.9`;
- leg_count and one-based leg_index consistency checks.

Decision unchanged: B1_prime remains candidate / pre-freeze only. Adding leg-indexed field binding, schema-field assignment, or target-aware candidate ranking would change the method into B1_link / Experiment Group 5.
