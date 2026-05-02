# Experiment 6 Verification Score: V4_tolerant_extract_then_compare_D1_SFT

Status: pre-freeze artifact check, not formal paper result.

## Overall

- total cases: 400
- valid parsed predictions: 400
- invalid/missing predictions: 0
- binary accuracy, invalid counted wrong: 0.5575
- negative reject rate: 0.54
- false negative rate on negative cases: 0.46
- positive accept rate: 0.575
- error-field exact rate on negative cases: 0.005
- normalized error-field exact rate on negative cases: 0.005
- normalized error-field overlap rate on negative cases: 0.475

## By Counterfactual Type

| type | total | valid | negative reject rate | false negative rate | binary acc all |
|---|---:|---:|---:|---:|---:|
| 424_derived_trap | 19 | 19 | 0.42105263157894735 | 0.5789473684210527 | 0.42105263157894735 |
| altitude_perturbation | 18 | 18 | 0.3888888888888889 | 0.6111111111111112 | 0.3888888888888889 |
| ca_omission | 18 | 18 | 0.3333333333333333 | 0.6666666666666666 | 0.3333333333333333 |
| ca_to_df_sequence_error | 18 | 18 | 0.3333333333333333 | 0.6666666666666666 | 0.3333333333333333 |
| course_radial_error | 19 | 19 | 0.6842105263157895 | 0.3157894736842105 | 0.6842105263157895 |
| fix_substitution | 18 | 18 | 1.0 | 0.0 | 1.0 |
| holding_parameter_error | 18 | 18 | 0.3888888888888889 | 0.6111111111111112 | 0.3888888888888889 |
| implicit_hold_time_omission | 18 | 18 | 0.7777777777777778 | 0.2222222222222222 | 0.7777777777777778 |
| path_terminator_substitution | 18 | 18 | 0.6111111111111112 | 0.3888888888888889 | 0.6111111111111112 |
| positive | 200 | 200 | None | None | 0.575 |
| text_only_trap | 18 | 18 | 0.5 | 0.5 | 0.5 |
| turn_direction_flip | 18 | 18 | 0.5 | 0.5 | 0.5 |

## Interpretation

For chart-aware verification, negative reject rate measures how often the verifier flags inconsistent candidates.

False negative rate is safety-critical: it measures inconsistent candidates accepted as consistent.
