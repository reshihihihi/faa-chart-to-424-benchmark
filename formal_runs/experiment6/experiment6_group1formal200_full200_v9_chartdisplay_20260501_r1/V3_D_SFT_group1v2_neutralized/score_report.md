# Experiment 6 Verification Score: V3_D_SFT_group1v2_neutralized

Status: pre-freeze artifact check, not formal paper result.

## Overall

- total cases: 400
- valid parsed predictions: 370
- invalid/missing predictions: 30
- binary accuracy, invalid counted wrong: 0.4825
- negative reject rate: 1.0
- false negative rate on negative cases: 0.0
- positive accept rate: 0.03804347826086957
- error-field exact rate on negative cases: 0.021505376344086023
- normalized error-field exact rate on negative cases: 0.04838709677419355
- normalized error-field overlap rate on negative cases: 0.8118279569892473

## By Counterfactual Type

| type | total | valid | negative reject rate | false negative rate | binary acc all |
|---|---:|---:|---:|---:|---:|
| 424_derived_trap | 19 | 18 | 1.0 | 0.0 | 0.9473684210526315 |
| altitude_perturbation | 18 | 17 | 1.0 | 0.0 | 0.9444444444444444 |
| ca_omission | 18 | 16 | 1.0 | 0.0 | 0.8888888888888888 |
| ca_to_df_sequence_error | 18 | 16 | 1.0 | 0.0 | 0.8888888888888888 |
| course_radial_error | 19 | 16 | 1.0 | 0.0 | 0.8421052631578947 |
| fix_substitution | 18 | 18 | 1.0 | 0.0 | 1.0 |
| holding_parameter_error | 18 | 16 | 1.0 | 0.0 | 0.8888888888888888 |
| implicit_hold_time_omission | 18 | 17 | 1.0 | 0.0 | 0.9444444444444444 |
| path_terminator_substitution | 18 | 16 | 1.0 | 0.0 | 0.8888888888888888 |
| positive | 200 | 184 | None | None | 0.035 |
| text_only_trap | 18 | 18 | 1.0 | 0.0 | 1.0 |
| turn_direction_flip | 18 | 18 | 1.0 | 0.0 | 1.0 |

## Interpretation

For chart-aware verification, negative reject rate measures how often the verifier flags inconsistent candidates.

False negative rate is safety-critical: it measures inconsistent candidates accepted as consistent.
