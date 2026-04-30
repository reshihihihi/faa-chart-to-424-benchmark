# Experiment 6 Artifact Control Policy

Status: formal-freeze policy for Experiment Group 6 v7 counterfactual cases.

Date: 2026-04-30

## Purpose

This policy defines how Experiment Group 6 controls synthetic-counterfactual
artifacts. The central risk is that a model could identify negative candidates
from unnatural candidate-record patterns without reading the chart.

## Frozen Baseline

V0 candidate-only is the artifact baseline. V0 receives only:

- `verification_case_id`
- `chart_id`
- `sample_id`
- `candidate_record`

V0 must not receive chart image, OCR text, target JSON, labels, `error_fields`,
counterfactual type, score files, QC decisions, or this policy text.

## Frozen v7 Artifact Evidence

The v7 artifact check is:

- run directory:
  `runs/v0_candidate_only/`
- cases:
  `cases/verification_counterfactuals_v7_formal300.jsonl`
- model:
  `gpt-5.4`
- final records:
  3091
- parse/API status:
  3091 parsed, 0 parse failures, 0 API failures
- overall candidate-only negative reject rate / artifact score:
  0.20315299175922608
- positive accept rate:
  0.72

The v7 set is accepted as a freeze candidate because the previous hard artifact
blocker was removed: v5 `fix_substitution` had a candidate-only reject rate of
0.909, while v7 `fix_substitution` is 0.30666666666666664.

## Reporting Rule

The candidate-only artifact score must be reported with formal Experiment Group
6 results. It is not a chart-reasoning score. It estimates how much of the
negative set can be detected from candidate artifacts alone.

Formal method reports must include:

- V0 overall artifact score;
- V0 artifact score by counterfactual type;
- a note that high V0 negative reject rate weakens claims about chart evidence
  for the affected type.

## Rework Rule

A counterfactual type requires builder rework before formal freeze if either is
true:

- candidate-only negative reject rate is at or above 0.50 for that type;
- manual/QC review finds a systematic non-chart artifact that explains V0
  success.

Values below 0.50 are not automatically "artifact-free"; they remain reportable
residual risk.

## Post-Freeze Change Rule

After freeze, cases may not be selectively removed or changed because a formal
method performs well or poorly. Any artifact-related redesign requires a new
builder version and a new freeze package.
