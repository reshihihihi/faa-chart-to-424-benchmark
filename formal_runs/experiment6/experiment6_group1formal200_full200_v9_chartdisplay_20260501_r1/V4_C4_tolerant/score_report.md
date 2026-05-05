# Experiment 6 Verification Score: V4_tolerant_extract_then_compare_C4

Status: pre-freeze artifact check, not formal paper result.

## Overall

- total cases: 400
- valid parsed predictions: 400
- invalid/missing predictions: 0
- binary accuracy, invalid counted wrong: 0.505
- negative reject rate: 0.395
- false negative rate on negative cases: 0.605
- positive accept rate: 0.615
- error-field exact rate on negative cases: 0.0
- normalized error-field exact rate on negative cases: 0.0
- normalized error-field overlap rate on negative cases: 0.2

## By Counterfactual Type

| type | total | valid | negative reject rate | false negative rate | binary acc all |
|---|---:|---:|---:|---:|---:|
| 424_derived_trap | 19 | 19 | 0.10526315789473684 | 0.8947368421052632 | 0.10526315789473684 |
| altitude_perturbation | 18 | 18 | 0.2777777777777778 | 0.7222222222222222 | 0.2777777777777778 |
| ca_omission | 18 | 18 | 0.3333333333333333 | 0.6666666666666666 | 0.3333333333333333 |
| ca_to_df_sequence_error | 18 | 18 | 0.2777777777777778 | 0.7222222222222222 | 0.2777777777777778 |
| course_radial_error | 19 | 19 | 0.42105263157894735 | 0.5789473684210527 | 0.42105263157894735 |
| fix_substitution | 18 | 18 | 1.0 | 0.0 | 1.0 |
| holding_parameter_error | 18 | 18 | 0.5555555555555556 | 0.4444444444444444 | 0.5555555555555556 |
| implicit_hold_time_omission | 18 | 18 | 0.2222222222222222 | 0.7777777777777778 | 0.2222222222222222 |
| path_terminator_substitution | 18 | 18 | 0.3333333333333333 | 0.6666666666666666 | 0.3333333333333333 |
| positive | 200 | 200 | None | None | 0.615 |
| text_only_trap | 18 | 18 | 0.5 | 0.5 | 0.5 |
| turn_direction_flip | 18 | 18 | 0.3333333333333333 | 0.6666666666666666 | 0.3333333333333333 |

## Interpretation

For chart-aware verification, negative reject rate measures how often the verifier flags inconsistent candidates.

False negative rate is safety-critical: it measures inconsistent candidates accepted as consistent.
