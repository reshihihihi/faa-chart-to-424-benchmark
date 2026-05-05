# Experiment 6 V1-V4 Method Boundary Policy

Status: formal-freeze boundary candidate.

Date: 2026-04-30

## Purpose

This file fixes the Experiment Group 6 method meanings before formal runs.
Experiment Group 6 is a verification task, not a canonical JSON extraction
task.

Common output for all methods:

{"consistent": true, "error_fields": []}

The formal output must be bare JSON or tool-call JSON conforming to
`configs/audit_decision_schema.json`. Markdown fences and prose wrappers are
not valid formal outputs.

## V1: Text-Only Verifier

Input:

- frozen OCR-1 full-chart text from
  `ocr_artifacts/formal300/ocr1_paddleocr_ppocrv5_frozen`;
- candidate 424-like record;
- non-answer metadata needed to identify the case.

Purpose:

Measure how much chart-424 verification can be solved from text evidence
without image reasoning.

Forbidden:

- chart image;
- canonical target;
- raw CIFP;
- label, `error_fields`, `counterfactual_type`;
- score files or QC decisions.

Note:

If a later manually reviewed missed-approach-prose-only text source is frozen,
it must be treated as a new V1 input variant. The current freeze candidate uses
OCR-1 full-chart text because that artifact is already frozen and non-gold.

## V2: Direct VLM Verifier

Input:

- full chart image;
- candidate 424-like record;
- allowed `error_fields` vocabulary derived from the candidate structure;
- non-answer metadata needed to load the chart.

Purpose:

Measure whether a VLM/MLLM can directly audit chart-to-424 consistency.

Formal model candidate:

- `claude-sonnet-4-5-20250929`
- API route: OpenAI-compatible Claude proxy at
  `https://api.claudecode.uk/v1/chat/completions`.

Forbidden:

- OCR side files;
- canonical target;
- raw CIFP;
- label, `error_fields`, `counterfactual_type`;
- score files, QC decisions, or outputs from other methods.

## V3: Extract-Then-Compare

Input:

- a frozen Group 1 canonical extraction output selected before scoring;
- candidate 424-like record;
- symbolic comparer rules.

Purpose:

Test whether canonical schema extraction helps chart-424 verification.

Allowed extractor sources:

- B1/B1_prime/B1_prime_link/C1/C3/C4/D-SFT only when their predictions are
  already frozen and selected without reading Experiment Group 6 labels.

Forbidden:

- canonical target;
- raw CIFP;
- label, `error_fields`, `counterfactual_type`;
- score files or QC decisions during comparison.

## V4: SFT Verifier, Optional

Input:

- full chart image;
- candidate 424-like record.

Purpose:

Measure whether a trained verifier can directly learn chart-to-424 audit
decisions.

V4 must use a train/dev split that excludes formal300, pilot10,
pilot100_external, and all Experiment Group 6 formal evaluation targets unless
a formally documented split explicitly permits a development subset.

V4 is optional. If no stable SFT verifier is available, report V4 as not run
rather than replacing it with D-SFT extraction results.

## Shared No-Leakage Rule

No V1-V4 method may read:

- `label.consistent`;
- `label.error_fields`;
- `label.counterfactual_type`;
- canonical proxy target;
- scorer output;
- QC review decision;
- raw CIFP records;
- any field that directly states whether the candidate is positive or negative.

## Rerun Rule

API failure may be rerun for the exact failed cases only, using the same frozen
input, prompt, model, and parameters. Parse/schema failure may be counted as
failure unless the method's formal runner has a pre-frozen retry/tool-call
policy. Low-score cases may not be selectively rerun.
