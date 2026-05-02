# Experiment 6 Verification Score: V1_text_only

Status: pre-freeze artifact check, not formal paper result.

## Overall

- total cases: 400
- valid parsed predictions: 400
- invalid/missing predictions: 0
- binary accuracy, invalid counted wrong: 0.49
- negative reject rate: 0.285
- false negative rate on negative cases: 0.715
- positive accept rate: 0.695
- error-field exact rate on negative cases: 0.09
- normalized error-field exact rate on negative cases: 0.09
- normalized error-field overlap rate on negative cases: 0.165

## By Counterfactual Type

| type | total | valid | negative reject rate | false negative rate | binary acc all |
|---|---:|---:|---:|---:|---:|
| 424_derived_trap | 19 | 19 | 0.15789473684210525 | 0.8421052631578947 | 0.15789473684210525 |
| altitude_perturbation | 18 | 18 | 0.05555555555555555 | 0.9444444444444444 | 0.05555555555555555 |
| ca_omission | 18 | 18 | 0.05555555555555555 | 0.9444444444444444 | 0.05555555555555555 |
| ca_to_df_sequence_error | 18 | 18 | 0.0 | 1.0 | 0.0 |
| course_radial_error | 19 | 19 | 0.3157894736842105 | 0.6842105263157895 | 0.3157894736842105 |
| fix_substitution | 18 | 18 | 1.0 | 0.0 | 1.0 |
| holding_parameter_error | 18 | 18 | 0.2777777777777778 | 0.7222222222222222 | 0.2777777777777778 |
| implicit_hold_time_omission | 18 | 18 | 0.1111111111111111 | 0.8888888888888888 | 0.1111111111111111 |
| path_terminator_substitution | 18 | 18 | 0.2222222222222222 | 0.7777777777777778 | 0.2222222222222222 |
| positive | 200 | 200 | None | None | 0.695 |
| text_only_trap | 18 | 18 | 0.2222222222222222 | 0.7777777777777778 | 0.2222222222222222 |
| turn_direction_flip | 18 | 18 | 0.7222222222222222 | 0.2777777777777778 | 0.7222222222222222 |

## Interpretation

For chart-aware verification, negative reject rate measures how often the verifier flags inconsistent candidates.

False negative rate is safety-critical: it measures inconsistent candidates accepted as consistent.
