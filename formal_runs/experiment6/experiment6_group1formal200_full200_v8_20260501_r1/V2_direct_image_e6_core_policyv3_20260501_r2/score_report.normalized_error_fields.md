# Experiment 6 Verification Score: V2_direct_image_e6_core_policyv3_20260501_r2

Status: pre-freeze artifact check, not formal paper result.

## Overall

- total cases: 400
- valid parsed predictions: 400
- invalid/missing predictions: 0
- binary accuracy, invalid counted wrong: 0.5225
- negative reject rate: 0.67
- false negative rate on negative cases: 0.33
- positive accept rate: 0.375
- error-field exact rate on negative cases: 0.145
- normalized error-field exact rate on negative cases: 0.165
- normalized error-field overlap rate on negative cases: 0.205

## By Counterfactual Type

| type | total | valid | negative reject rate | false negative rate | binary acc all |
|---|---:|---:|---:|---:|---:|
| 424_derived_trap | 19 | 19 | 0.5263157894736842 | 0.47368421052631576 | 0.5263157894736842 |
| altitude_perturbation | 18 | 18 | 0.5 | 0.5 | 0.5 |
| ca_omission | 18 | 18 | 0.7222222222222222 | 0.2777777777777778 | 0.7222222222222222 |
| ca_to_df_sequence_error | 18 | 18 | 0.6111111111111112 | 0.3888888888888889 | 0.6111111111111112 |
| course_radial_error | 19 | 19 | 0.7368421052631579 | 0.2631578947368421 | 0.7368421052631579 |
| fix_substitution | 18 | 18 | 0.7222222222222222 | 0.2777777777777778 | 0.7222222222222222 |
| holding_parameter_error | 18 | 18 | 0.9444444444444444 | 0.05555555555555555 | 0.9444444444444444 |
| implicit_hold_time_omission | 18 | 18 | 0.5555555555555556 | 0.4444444444444444 | 0.5555555555555556 |
| path_terminator_substitution | 18 | 18 | 0.6111111111111112 | 0.3888888888888889 | 0.6111111111111112 |
| positive | 200 | 200 | None | None | 0.375 |
| text_only_trap | 18 | 18 | 0.8333333333333334 | 0.16666666666666666 | 0.8333333333333334 |
| turn_direction_flip | 18 | 18 | 0.6111111111111112 | 0.3888888888888889 | 0.6111111111111112 |

## Interpretation

For chart-aware verification, negative reject rate measures how often the verifier flags inconsistent candidates.

False negative rate is safety-critical: it measures inconsistent candidates accepted as consistent.
