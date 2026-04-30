# Experiment Group 6 Counterfactual Verification Package v7

Status: formal freeze candidate, ready for user approval before full V1/V2/V3 runs.

Date: 2026-04-30

## Scope

This package contains the paper-v2 Experiment Group 6 counterfactual
verification set and pre-run assets. The task is:

```text
chart evidence + candidate 424-like missed-approach record
-> audit decision JSON
```

It is a verification task, not a full canonical JSON extraction task.

## What Is Included

- `cases/verification_counterfactuals_v7_formal300.jsonl`
  The labeled v7 verification cases. Labels are for scoring only and must not
  be included in method inputs.
- `packed_inputs/`
  Label-free V0/V1/V2/V3 inputs.
- `configs/`
  Schemas, method card, no-leakage policy, construction policy, and the four
  pre-run freeze policies.
- `prompts/`
  Formal V0/V1/V2 prompts and V3/V4 specifications.
- `scripts/`
  Builder, packer, no-leakage checker, validator, runners, and scorer used for
  this package.
- `qc/`
  Builder summary, validation report, and no-leakage reports.
- `runs/v0_candidate_only/`
  V0 candidate-only artifact baseline summary and report.
- `reports/`
  Strict QC review and formal pre-run steps 1-5 report.
- `freeze_manifest.json` and `checksums.sha256`
  Package manifest and file hashes.

## Case Counts

Total cases: 3091 from formal300.

| Type | Count |
|---|---:|
| positive | 300 |
| fix_substitution | 300 |
| altitude_perturbation | 292 |
| turn_direction_flip | 86 |
| course_radial_error | 299 |
| holding_parameter_error | 298 |
| implicit_hold_time_omission | 35 |
| path_terminator_substitution | 300 |
| ca_omission | 294 |
| ca_to_df_sequence_error | 287 |
| text_only_trap | 300 |
| 424_derived_trap | 300 |

## Frozen Method Meanings

- V0 candidate-only baseline
  Candidate record only. Used for artifact control.
- V1 text-only verifier
  Frozen OCR-1 full-chart text plus candidate.
- V2 direct VLM verifier
  Full chart image plus candidate.
- V3 extract-then-compare
  Frozen Group 1 extraction plus symbolic comparer.
- V4 SFT verifier
  Optional; not run until a no-leakage SFT verifier checkpoint is frozen.

## Key Pre-Run Results

- Case validation: pass.
- V0/V1/V2/V3 no-leakage: pass.
- V0 candidate-only artifact score: 0.20315299175922608.
- V1/V2/V3 smoke tests: 5 of 5 parsed successfully for each method.
- V2 must use the OpenAI-compatible Claude proxy route, not Anthropic native
  Messages API, because the native route returned 403 in the smoke test.

## Formal-Run Rule

After this package is accepted for freeze, do not modify cases, labels,
`error_fields`, prompts, method inputs, or retry rules based on model
performance. Any redesign requires a new builder version and a new package.
