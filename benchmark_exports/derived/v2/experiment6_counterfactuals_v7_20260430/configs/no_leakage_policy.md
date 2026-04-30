# Experiment 6 No-Leakage Policy

Status: pre-freeze candidate.

## Principle

The verifier may see the chart and candidate record, but it must not see any
answer labels or target-derived explanation that directly tells it whether the
candidate is correct.

## Forbidden In Verifier Inputs

The packed model input must not contain keys or values corresponding to:

- `label`
- `consistent`
- `error_fields`
- `counterfactual_type`
- `target`
- `canonical_target`
- `canonical_proxy_gt`
- `score`
- `expected`
- `answer_key`
- `evidence_provenance`
- `challenge_tags`
- `raw_cifp`
- `source_target_sha256`
- `mutation_rule`
- `mutation_notes`

## Allowed In Verifier Inputs

Allowed:

- `verification_case_id`
- `chart_id`
- `sample_id`
- `image_path`
- `image_sha256`
- `candidate_record`
- method-specific prompt text
- non-answer metadata required for loading the image

## Baseline-Specific Rules

V0 candidate-only:

- only `candidate_record` and non-answer IDs are allowed;
- chart image and text are forbidden.

V2 text-only:

- missed approach prose and candidate record are allowed;
- full chart image is forbidden.

V3 direct VLM:

- full chart image and candidate record are allowed;
- target, labels, provenance, and challenge tags are forbidden.

V4 extract-then-compare:

- extraction predictions may be used only as the explicit input to the symbolic
  comparer;
- ground-truth target must not be used by the comparer except for scoring.

## Required Check

Run `scripts/check_no_leakage_verification.py` on every packed input JSONL
before calling a model.
