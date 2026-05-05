# Experiment 6 Verification Score: V0_candidate_only

Status: pre-freeze artifact check, not formal paper result.

## Overall

- total cases: 3091
- valid parsed predictions: 3091
- invalid/missing predictions: 0
- binary accuracy, invalid counted wrong: 0.2533160789388547
- candidate-only negative reject rate / artifact score: 0.20315299175922608
- false negative rate on negative cases: 0.7968470082407739
- positive accept rate: 0.72
- error-field exact rate on negative cases: 0.0
- normalized error-field exact rate on negative cases: 0.0
- normalized error-field overlap rate on negative cases: 0.0017914725904693658

## By Counterfactual Type

| type | total | valid | artifact score / negative reject | false negative rate | binary acc all |
|---|---:|---:|---:|---:|---:|
| 424_derived_trap | 300 | 300 | 0.2633333333333333 | 0.7366666666666667 | 0.2633333333333333 |
| altitude_perturbation | 292 | 292 | 0.1095890410958904 | 0.8904109589041096 | 0.1095890410958904 |
| ca_omission | 294 | 294 | 0.04081632653061224 | 0.9591836734693877 | 0.04081632653061224 |
| ca_to_df_sequence_error | 287 | 287 | 0.05226480836236934 | 0.9477351916376306 | 0.05226480836236934 |
| course_radial_error | 299 | 299 | 0.26755852842809363 | 0.7324414715719063 | 0.26755852842809363 |
| fix_substitution | 300 | 300 | 0.30666666666666664 | 0.6933333333333334 | 0.30666666666666664 |
| holding_parameter_error | 298 | 298 | 0.26174496644295303 | 0.738255033557047 | 0.26174496644295303 |
| implicit_hold_time_omission | 35 | 35 | 0.2857142857142857 | 0.7142857142857143 | 0.2857142857142857 |
| path_terminator_substitution | 300 | 300 | 0.23333333333333334 | 0.7666666666666667 | 0.23333333333333334 |
| positive | 300 | 300 | None | None | 0.72 |
| text_only_trap | 300 | 300 | 0.27666666666666667 | 0.7233333333333334 | 0.27666666666666667 |
| turn_direction_flip | 86 | 86 | 0.18604651162790697 | 0.813953488372093 | 0.18604651162790697 |

## Interpretation

For V0, high negative reject rate means the candidate-only baseline can detect synthetic negatives without chart evidence. That is a warning sign for counterfactual artifacts.

For V0, high false negative rate means the candidate-only baseline usually accepts negative records, which is expected when counterfactuals require chart evidence.
