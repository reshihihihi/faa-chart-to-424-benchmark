# V4 Tolerant / Link Extract-Then-Compare Method Card

## Method IDs

- `V4_C4_tolerant`
- `V4_D_SFT_tolerant`

## Task

Experiment 6 chart-grounded 424 counterfactual verification:

```text
extractor canonical JSON + candidate_record
-> audit decision JSON
```

## Motivation

V3-strict showed that naive extract-then-compare can become an all-reject verifier. V4 tests whether adding leg alignment, equivalence rules, numeric tolerance, and partial comparison can reduce false alarms without using forbidden information.

## Inputs

Allowed:

- `candidate_record`
- frozen extractor output canonical JSON
- extractor validation status

Forbidden:

- original chart image
- OCR text
- canonical target / ground truth
- case label
- counterfactual_type
- score files
- human answer
- predictions from methods other than the selected extractor output

## Extractor Sources

`V4_C4_tolerant` uses:

```text
formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_C4/C4/canonical_json
```

`V4_D_SFT_tolerant` uses:

```text
formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_D_SFT/D_SFT/predictions/group1_formal_eval_50_200_50_seed20260437_20260430_r1_D_SFT_D_SFT/canonical_json
```

For D-SFT, missing or schema-invalid extractor output is counted as method failure.

## Comparison Policy

The frozen comparison policy is:

```text
configs/v4_tolerant_compare_policy.md
```

## Output

V4 outputs the same audit decision schema as V1/V2/V3:

```json
{"consistent": false, "error_fields": ["missed_approach.legs[2].fix_ident"]}
```

## Expected Use in the Paper

V4 should be reported alongside V3-strict:

- V3-strict demonstrates the naive extract-then-compare failure mode.
- V4-tolerant tests whether a more careful comparer can reduce that failure mode.

V4 should not be described as changing the data, target, or scoring setup. It changes only the comparison rule applied to the same allowed extractor evidence and candidate record.
