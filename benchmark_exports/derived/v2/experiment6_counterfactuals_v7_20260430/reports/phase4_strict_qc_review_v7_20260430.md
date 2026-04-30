# Experiment Group 6 Phase 4 Strict QC Review v7

Date: 2026-04-30

Status: v7 is the current freeze candidate for counterfactual case construction. Do not use v4/v5/v6 for formal freeze.

## Scope

Reviewed Experiment Group 6 424 counterfactual verification cases against the paper-v2 requirements:

- input task: full chart + candidate 424-like record;
- positive case: exactly projected from canonical proxy target;
- negative case: plausible, minimal, localizable semantic perturbation;
- no answer/label leakage in verifier inputs;
- candidate-only artifact baseline must not trivially solve the negative set;
- high-risk implicit / 424-derived / sequence cases require explicit policy freeze.

## Final Candidate

- Builder version: `experiment6_counterfactual_builder_prefreeze_v7`
- Case file: `cases/verification_counterfactuals_v7_formal300.jsonl`
- Case count: 3091
- Source charts: 300 formal300 charts

Current package hashes are recorded in `checksums.sha256` and
`freeze_manifest.json`.

## PR #21 Audit Fixes

During the PR #21 freeze-readiness audit, the following documentation and
label-vocabulary issues were fixed before formal runs:

- V1/V2/V3 numbering in `no_leakage_policy.md` was aligned with the method
  card.
- V1 text-only input was clarified as frozen OCR-1 full-chart text.
- `audit_decision_schema.json` was tightened to exactly two output keys:
  `consistent` and `error_fields`.
- V2 runner parsing was tightened to reject markdown/prose wrappers and
  extra keys.
- V2 runner output control now uses a required `audit_decision` tool call when
  routed through the OpenAI-compatible Claude API; the tool arguments are then
  parsed by the same strict two-key JSON parser.
- `ca_omission` labels were changed from whole-leg paths such as
  `missed_approach.legs[1]` to the sequence-level field
  `missed_approach.legs.sequence`.
- `hold_params.value.leg_time_min` was added to the formal output vocabulary
  for implicit hold-time omission cases.

## Issues Found During Strict Review

### Fixed in v5

`altitude_perturbation` in v4 used `+100 ft` when no second target altitude existed. This did not strictly match the paper plan's "replace with another plausible chart altitude" requirement.

Fix: v5/v7 only replace an altitude with another canonical altitude from the same candidate; otherwise the mutation is skipped. This reduced altitude cases from 300 to 292.

### Fixed in v6

`fix_substitution` in v4 used a global external fix pool. This did not strictly match the paper plan's "same-chart fix substitution" requirement.

Fix: v6/v7 use the same chart/procedure raw CIFP transition pool and do not use global external fixes.

### Fixed in v7

v6 could choose localizer-style `I...` identifiers from the raw CIFP pool. They are sourced from the same procedure, but less natural as replacement fixes.

Fix: v7 prioritizes 5-letter waypoint-style identifiers, then 3-letter navaids, and avoids localizer-style `I...` identifiers when alternatives exist. In v7, all 300 fix substitutions use 5-letter non-target same-procedure replacements.

## v7 Counts

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

Skipped cases are expected when the source target lacks the required field.

## Validation Results

Structural validation:

```text
status: pass
case_count: 3091
duplicate_ids: 0
error_count: 0
```

No-leakage:

```text
V0 candidate-only inputs: pass, finding_count=0
V1 text-only inputs:      pass, finding_count=0
V2 direct VLM inputs:     pass, finding_count=0
V3 extract-compare inputs: pass, finding_count=0
```

## V0 Candidate-Only Artifact Check

Run: `runs/v0_candidate_only/`

The first run had 10 transient API/parse failures. The original file was backed up, failed rows were removed, and those exact 10 cases were rerun. Final run status:

```text
records: 3091
parse_ok: 3091
parse_fail: 0
api_error: 0
```

Overall:

| Metric | Value |
|---|---:|
| candidate-only negative reject / artifact score | 0.20315299175922608 |
| false negative rate on negative cases | 0.7968470082407739 |
| positive accept rate | 0.72 |

By type:

| Type | Artifact score |
|---|---:|
| fix_substitution | 0.30666666666666664 |
| implicit_hold_time_omission | 0.2857142857142857 |
| text_only_trap | 0.27666666666666667 |
| course_radial_error | 0.26755852842809363 |
| 424_derived_trap | 0.2633333333333333 |
| holding_parameter_error | 0.26174496644295303 |
| path_terminator_substitution | 0.23333333333333334 |
| turn_direction_flip | 0.18604651162790697 |
| altitude_perturbation | 0.1095890410958904 |
| ca_to_df_sequence_error | 0.05226480836236934 |
| ca_omission | 0.04081632653061224 |

Interpretation: v7 no longer has the v5 `fix_substitution = 0.909` hard artifact blocker. Remaining artifact scores are acceptable for pre-freeze review but should still be reported.

## Phase 4 QC Sample Review

Final v7 QC packet:

```text
external QC packet retained outside the repository; summary is recorded here
```

Reviewed sample count: 215

Stage A required:

- all 35 `implicit_hold_time_omission`;
- 20 each for `text_only_trap`, `424_derived_trap`, `ca_to_df_sequence_error`;
- 10 positive;
- 5 each for the remaining major types.

Stage B extended: 75 additional cases.

Auto review result:

```text
reviewed_cases: 215
decision_counts: keep=215
needs_builder_fix_by_type: {}
wrong_label: 0
wrong_error_fields: 0
```

Policy-dependent but structurally valid:

| Policy | Sample count |
|---|---:|
| implicit_hold_time_policy | 35 |
| 424_derived_policy | 40 |
| 424_sequence_policy | 30 |

These are not builder errors. They must be explicitly frozen before final formal evaluation.

## Manual Image Check

13 sampled cases had weak OCR-only evidence and were checked visually:

- 9 `text_only_trap`;
- 4 `course_radial_error`.

The visual check confirmed that these cases are structurally valid and should remain `keep`. The weak OCR status comes from OCR not fully capturing decimal degrees or hold-pattern graphics, not from case construction errors.

Examples:

- `KABE_I06`: chart shows heading 063 and STW R-243 / hold pattern; candidate perturbations to 073.3 or 263.1 are inconsistent.
- `KAVL_I17`: missed approach fix/hold depiction supports BRA holding course; candidate 006.8 is a perturbation of the canonical 346.8.
- `KBUY_I06-Z`: chart/profile shows LIB holding around 056/236; candidate 256.0 is inconsistent.
- `KAXH_L09`: chart/profile shows 089; candidate 109.2 is inconsistent.
- `KCEC_L12`: missed approach fix CHIDE / CEC R-166 implies reciprocal holding course around 346; candidate 005.8 is inconsistent.
- `KALO_L12`: DEWAR / ALO R-096 holding depiction supports 276; candidate 296.5 is inconsistent.

## Final QC Judgment

v7 resolves the strict plan-alignment issues found in v4/v5/v6 and passes repeated checks:

1. schema validation;
2. no-leakage validation for V0 and V3 inputs;
3. plan-specific mutation constraints;
4. candidate-only artifact check;
5. sampled target/candidate diff review;
6. high-risk type visual review.

Remaining before formal freeze:

1. Freeze `implicit_hold_time_policy`.
2. Freeze `424_derived_policy`.
3. Freeze `424_sequence_policy`.
4. Decide and document the acceptable artifact-score reporting threshold.
5. Move v7 artifacts into a formal freeze package after those policy documents are written.

Conclusion: `prefreeze_v7` is suitable as the Experiment Group 6 counterfactual construction freeze candidate. It should replace v4/v5/v6 in subsequent Experiment Group 6 work.
