# V4 Tolerant / Link Extract-Then-Compare Policy

## 1. Purpose

V4 is an additional Experiment 6 method. It does not replace V3-strict.

V4 tests whether a less mechanical extract-then-compare verifier can reduce the all-reject failure mode observed in V3-C4-strict and V3-D-SFT-strict.

## 2. Allowed Inputs

V4 may use only:

- `candidate_record` from the verification case;
- frozen Group 1 extractor output canonical JSON;
- extractor schema validation status.

V4 must not use:

- chart image;
- OCR text;
- canonical target / ground truth;
- label;
- counterfactual_type;
- score files;
- human answer;
- other method prediction.

## 3. Methods

V4 has two variants:

- `V4-C4-tolerant`: candidate record + Group 1 C4 canonical JSON.
- `V4-D-SFT-tolerant`: candidate record + Group 1 D-SFT canonical JSON.

## 4. Core Differences from V3-Strict

V3-strict compares by mapped leg index and exact field equality with limited numeric tolerance.

V4-tolerant adds:

1. Leg alignment before field comparison.
2. Field-level semantic equivalence.
3. Numeric tolerance.
4. Partial compare: missing or unknown extractor fields are not treated as evidence against the candidate.
5. Mismatch evidence thresholding: weak isolated mismatches are not enough to reject a candidate.
6. Error-field limiting: sequence errors are emitted only when the extractor provides enough unmatched evidence.

## 5. Leg Alignment

Candidate legs and extractor legs are aligned by similarity score, not only by `leg_index`.

Similarity scoring uses:

| Field | Match weight |
|---|---:|
| same `leg_index` | 0.5 |
| `fix_ident` equivalent | 4.0 |
| `path_terminator` equivalent | 1.5 |
| `altitude_constraint` equivalent | 2.5 |
| `course_or_radial` equivalent | 2.5 |
| `hold_params` equivalent | 2.0 |
| `turn` equivalent | 1.0 |

Unknown or missing fields contribute no score.

The alignment is greedy over all candidate/extractor leg pairs sorted by score. A pair is accepted if its score is at least `2.0`, or if it has the same `leg_index` and at least one comparable field.

## 6. Field Equivalence

Field comparison uses these rules:

- Strings are compared case-insensitively after trimming whitespace.
- If both sides are non-present (`unknown`, `not_applicable`, missing, or `null`), the field is treated as not comparable rather than a mismatch.
- If extractor value is unknown or missing, the field is skipped. Lack of extractor evidence does not disprove the candidate.
- If extractor value is present and candidate value is absent, this is a mismatch only after the candidate/extractor legs have been aligned.

## 7. Numeric Tolerance

Numeric comparison uses:

| Field type | Tolerance |
|---|---:|
| course / radial / heading | 2 degrees |
| altitude | 50 ft |
| distance | 0.1 NM |
| time | 0.1 min |
| other small numeric fields <= 360 | 2 units |
| other large numeric fields | 50 units |

## 8. Course / Radial Handling

For `course_or_radial`:

- Same type, same navaid, and angular difference within tolerance counts as equivalent.
- If direction differs by inbound/outbound, reciprocal angular relation within tolerance is considered weakly equivalent.
- If one side has no usable course/radial evidence, the field is skipped.

## 9. Holding Parameter Handling

For `hold_params`:

- `turn`, `inbound_course_deg`, `leg_time_min`, and `leg_distance_nm` are compared with the tolerance rules above.
- Missing extractor hold parameter values do not disprove candidate values.
- If one specific hold subfield mismatches, the returned error field may be narrowed to that subfield, e.g. `hold_params.value.leg_time_min`.

## 10. Sequence / Leg Count Handling

V4 does not automatically emit `missed_approach.leg_count` or `missed_approach.legs.sequence` simply because leg counts differ.

It emits sequence-related errors only when:

- an extractor leg with at least two present evidence fields cannot be aligned to any candidate leg; or
- a candidate leg and extractor leg are aligned only weakly and several strong fields disagree.

This avoids rejecting a correct candidate solely because the extractor omitted or hallucinated a leg.

## 11. Mismatch Evidence Threshold

V4 records field-level mismatches, but it returns `consistent=false` only when the total mismatch evidence is strong enough.

Mismatch weights:

| Mismatch type | Weight |
|---|---:|
| `fix_ident` | 4.0 |
| `altitude_constraint` | 2.0 |
| `course_or_radial` | 2.0 |
| `hold_params` | 1.5 |
| `turn` | 1.0 |
| `path_terminator` | 0.5 |
| `legs.sequence` | 2.0 |

Decision rule:

```text
if mismatch_score >= 4.0:
    consistent = false
else:
    consistent = true
```

This is still a symbolic verifier, but it avoids rejecting a candidate because of one weak extractor discrepancy, such as an uncertain terminator or a single holding-course mismatch.

## 12. Output

Output schema is unchanged:

```json
{
  "consistent": false,
  "error_fields": ["missed_approach.legs[2].fix_ident"]
}
```

The output must contain only:

- `consistent`: boolean;
- `error_fields`: array of strings.

At most five error fields are returned, matching V3-strict.

## 13. Interpretation

V4 is a diagnostic extension. If V4 improves positive accept while preserving useful negative rejection, it suggests V3-strict failed partly because the comparer was too mechanical.

If V4 still fails, the limiting factor is more likely extractor quality or insufficient chart-grounded evidence in the extraction output.
