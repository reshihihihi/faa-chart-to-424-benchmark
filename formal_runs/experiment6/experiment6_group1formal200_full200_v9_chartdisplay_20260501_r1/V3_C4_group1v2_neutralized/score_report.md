# Experiment 6 Verification Score: V3_C4_group1v2_neutralized

Status: pre-freeze artifact check, not formal paper result.

## Overall

- total cases: 400
- valid parsed predictions: 400
- invalid/missing predictions: 0
- binary accuracy, invalid counted wrong: 0.5
- negative reject rate: 1.0
- false negative rate on negative cases: 0.0
- positive accept rate: 0.0
- error-field exact rate on negative cases: 0.0
- normalized error-field exact rate on negative cases: 0.0
- normalized error-field overlap rate on negative cases: 0.415

## By Counterfactual Type

| type | total | valid | negative reject rate | false negative rate | binary acc all |
|---|---:|---:|---:|---:|---:|
| 424_derived_trap | 19 | 19 | 1.0 | 0.0 | 1.0 |
| altitude_perturbation | 18 | 18 | 1.0 | 0.0 | 1.0 |
| ca_omission | 18 | 18 | 1.0 | 0.0 | 1.0 |
| ca_to_df_sequence_error | 18 | 18 | 1.0 | 0.0 | 1.0 |
| course_radial_error | 19 | 19 | 1.0 | 0.0 | 1.0 |
| fix_substitution | 18 | 18 | 1.0 | 0.0 | 1.0 |
| holding_parameter_error | 18 | 18 | 1.0 | 0.0 | 1.0 |
| implicit_hold_time_omission | 18 | 18 | 1.0 | 0.0 | 1.0 |
| path_terminator_substitution | 18 | 18 | 1.0 | 0.0 | 1.0 |
| positive | 200 | 200 | None | None | 0.0 |
| text_only_trap | 18 | 18 | 1.0 | 0.0 | 1.0 |
| turn_direction_flip | 18 | 18 | 1.0 | 0.0 | 1.0 |

## Interpretation

For chart-aware verification, negative reject rate measures how often the verifier flags inconsistent candidates.

False negative rate is safety-critical: it measures inconsistent candidates accepted as consistent.
