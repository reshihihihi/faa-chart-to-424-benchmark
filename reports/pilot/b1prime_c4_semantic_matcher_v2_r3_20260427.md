# B1_prime / C4 semantic + matcher v2 r3 result - 2026-04-27

## Run

```text
run_id: pilot10_exp1_b1prime_c4_semantic_matcher_v2_20260427_r3
exit_code: 0
root: repository root / predictions/pilot10_external/pilot10_exp1_b1prime_c4_semantic_matcher_v2_20260427_r3
```

## Purpose

This run tests two candidate changes after r2:

1. C4 prompt v1: adds method-neutral semantic extraction guidance for flown-order decomposition, initial climb legs, track/direct/hold separation, and altitude wording.
2. B1_prime matcher v2: remains OCR-only but reduces obvious chart metadata noise and prioritizes missed-approach-window candidates.

## Recorded hashes

```text
runner:
ae805142a822daf601659c4f75b5acc9e1b910d1946fe331856956fe1f95be6f

B1_prime prompt:
94018da0f40efae16f632bd780658350bab9479982f74d2aebdac9d7ec56efe2

C4 prompt v1:
04b9587ad0caeebaa0884c88645fe3bfb467397026fa871e72989897b9ffa6b8

field_candidates schema:
babd288dd754989813b872f84d232cbcf6bde7ae250532b74c7a6286a7aef4df
```

## Results

| Method | strict JSON | schema-valid | scored | parser repair | failures | score | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| B1_prime | 10/10 | 10/10 | 10/10 | 0 | 0 | 111/220 | 50.45% |
| C4 | 10/10 | 10/10 | 10/10 | 0 | 0 | 132/220 | 60.00% |

## field_candidates validation

All ten B1_prime candidate files validate against `field_candidates_schema_v1_candidate`.

```text
files_checked: 10
schema_error_files: 0
forbidden_key_files: 0
source_sections:
  missed_approach_text: 502
  full_chart_unknown: 442
  profile_view: 18
```

## Comparison across r1, r2, r3

| Method | Run | Main change | schema-valid | score | accuracy |
|---|---|---|---:|---:|---:|
| B1_prime | r1 | old prompt + list candidates | 9/10 | 102/201 | 50.75% |
| B1_prime | r2 | object candidates v1 | 10/10 | 114/220 | 51.82% |
| B1_prime | r3 | matcher v2 | 10/10 | 111/220 | 50.45% |
| C4 | r1 | old C4 prompt | 10/10 | 114/220 | 51.82% |
| C4 | r2 | schema-aligned C4 prompt | 10/10 | 83/220 | 37.73% |
| C4 | r3 | C4 prompt v1 semantic guidance | 10/10 | 132/220 | 60.00% |

## C4 regression samples

C4 r3 recovered the main r2 regression samples:

```text
KDIJ_RNV-A: r1 19/31 -> r2 7/31 -> r3 23/31
KDAG_R22:  r1 16/31 -> r2 6/31 -> r3 18/31
KFKL_V21:  r1 15/19 -> r2 10/19 -> r3 15/19
```

This supports the interpretation that r2's C4 score drop was caused by insufficient prompt guidance for semantic leg decomposition, not by schema or parser failure.

## r3 field-level accuracy

B1_prime:

```text
leg_count: 6/10 = 60.00%
Q_terminator: 10/35 = 28.57%
Q1_fix_ident: 26/35 = 74.29%
Q2_altitude_constraint: 12/35 = 34.29%
Q3_turn: 29/35 = 82.86%
Q4_course_or_radial: 6/35 = 17.14%
Q5_hold_params: 22/35 = 62.86%
```

C4:

```text
leg_count: 8/10 = 80.00%
Q_terminator: 10/35 = 28.57%
Q1_fix_ident: 32/35 = 91.43%
Q2_altitude_constraint: 14/35 = 40.00%
Q3_turn: 30/35 = 85.71%
Q4_course_or_radial: 15/35 = 42.86%
Q5_hold_params: 23/35 = 65.71%
```

## Interpretation

C4 prompt v1 is a better pilot candidate than the r2 prompt because it preserves strict output behavior and improves semantic leg decomposition on the previously degraded samples.

B1_prime matcher v2 is structurally better than v1 because candidate noise is reduced and source-section attribution improves. However, B1_prime score did not improve in r3, so matcher v2 should remain candidate-only until reviewed further. The goal of v2 is provenance and no-leakage cleanliness, not guaranteed score gain.

## Freeze-readiness

Candidate-ready for continued pilot:

- C4 prompt v1;
- B1_prime object `field_candidates` schema;
- B1_prime matcher v2 as a pilot candidate;
- strict JSON parser policy reuse;
- r3 artifact layout.

Not formal-freeze ready:

- B1_prime matcher final rules;
- C4 final prompt;
- model/provider/max token policy;
- formal rerun policy;
- formal300 OCR artifact policy.
