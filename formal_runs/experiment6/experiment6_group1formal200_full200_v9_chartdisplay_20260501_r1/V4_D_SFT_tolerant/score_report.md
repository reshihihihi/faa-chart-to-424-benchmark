# Experiment 6 Verification Score: V4_tolerant_extract_then_compare_D_SFT

Status: pre-freeze artifact check, not formal paper result.

## Overall

- total cases: 400
- valid parsed predictions: 370
- invalid/missing predictions: 30
- binary accuracy, invalid counted wrong: 0.52
- negative reject rate: 0.5483870967741935
- false negative rate on negative cases: 0.45161290322580644
- positive accept rate: 0.5760869565217391
- error-field exact rate on negative cases: 0.005376344086021506
- normalized error-field exact rate on negative cases: 0.005376344086021506
- normalized error-field overlap rate on negative cases: 0.4838709677419355

## By Counterfactual Type

| type | total | valid | negative reject rate | false negative rate | binary acc all |
|---|---:|---:|---:|---:|---:|
| 424_derived_trap | 19 | 18 | 0.3888888888888889 | 0.6111111111111112 | 0.3684210526315789 |
| altitude_perturbation | 18 | 17 | 0.35294117647058826 | 0.6470588235294118 | 0.3333333333333333 |
| ca_omission | 18 | 16 | 0.375 | 0.625 | 0.3333333333333333 |
| ca_to_df_sequence_error | 18 | 16 | 0.375 | 0.625 | 0.3333333333333333 |
| course_radial_error | 19 | 16 | 0.6875 | 0.3125 | 0.5789473684210527 |
| fix_substitution | 18 | 18 | 1.0 | 0.0 | 1.0 |
| holding_parameter_error | 18 | 16 | 0.4375 | 0.5625 | 0.3888888888888889 |
| implicit_hold_time_omission | 18 | 17 | 0.7647058823529411 | 0.23529411764705882 | 0.7222222222222222 |
| path_terminator_substitution | 18 | 16 | 0.625 | 0.375 | 0.5555555555555556 |
| positive | 200 | 184 | None | None | 0.53 |
| text_only_trap | 18 | 18 | 0.5 | 0.5 | 0.5 |
| turn_direction_flip | 18 | 18 | 0.5 | 0.5 | 0.5 |

## Interpretation

For chart-aware verification, negative reject rate measures how often the verifier flags inconsistent candidates.

False negative rate is safety-critical: it measures inconsistent candidates accepted as consistent.
