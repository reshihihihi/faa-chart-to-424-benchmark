# Experiment 6 Verification Score: V2_direct_image_policyv3_chartdisplay_v2

Status: pre-freeze artifact check, not formal paper result.

## Overall

- total cases: 400
- valid parsed predictions: 400
- invalid/missing predictions: 0
- binary accuracy, invalid counted wrong: 0.5675
- negative reject rate: 0.73
- false negative rate on negative cases: 0.27
- positive accept rate: 0.405
- error-field exact rate on negative cases: 0.115
- normalized error-field exact rate on negative cases: 0.235
- normalized error-field overlap rate on negative cases: 0.25

## By Counterfactual Type

| type | total | valid | negative reject rate | false negative rate | binary acc all |
|---|---:|---:|---:|---:|---:|
| 424_derived_trap | 19 | 19 | 0.5789473684210527 | 0.42105263157894735 | 0.5789473684210527 |
| altitude_perturbation | 18 | 18 | 0.5555555555555556 | 0.4444444444444444 | 0.5555555555555556 |
| ca_omission | 18 | 18 | 0.6666666666666666 | 0.3333333333333333 | 0.6666666666666666 |
| ca_to_df_sequence_error | 18 | 18 | 0.8333333333333334 | 0.16666666666666666 | 0.8333333333333334 |
| course_radial_error | 19 | 19 | 0.7368421052631579 | 0.2631578947368421 | 0.7368421052631579 |
| fix_substitution | 18 | 18 | 0.7777777777777778 | 0.2222222222222222 | 0.7777777777777778 |
| holding_parameter_error | 18 | 18 | 0.8888888888888888 | 0.1111111111111111 | 0.8888888888888888 |
| implicit_hold_time_omission | 18 | 18 | 0.8333333333333334 | 0.16666666666666666 | 0.8333333333333334 |
| path_terminator_substitution | 18 | 18 | 0.5 | 0.5 | 0.5 |
| positive | 200 | 200 | None | None | 0.405 |
| text_only_trap | 18 | 18 | 0.9444444444444444 | 0.05555555555555555 | 0.9444444444444444 |
| turn_direction_flip | 18 | 18 | 0.7222222222222222 | 0.2777777777777778 | 0.7222222222222222 |

## Interpretation

For chart-aware verification, negative reject rate measures how often the verifier flags inconsistent candidates.

False negative rate is safety-critical: it measures inconsistent candidates accepted as consistent.
