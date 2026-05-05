# V4 PR25-Narrowed Extract-Then-Compare Policy

Status: pre-freeze diagnostic policy

## 1. Purpose

This policy tests the impact of PR #25's narrowed Group 1 scoring-equivalence rules on Experiment 6 extract-then-compare verification.

It is intentionally narrower than `v4_tolerant_compare_policy.md`.

## 2. Allowed Inputs

The comparer may use only:

- `candidate_record` from the Experiment 6 verification case;
- frozen Group 1 extractor output canonical JSON;
- extractor schema validation status.

It must not use:

- chart image;
- OCR text;
- canonical target / ground truth;
- label;
- counterfactual_type;
- score files;
- human answer;
- V1/V2/V3/V4 predictions.

## 3. Allowed Equivalence Rules

Only two PR #25 equivalence classes are allowed.

### 3.1 Fix / Navaid Normalized String

Allowed only for:

- `fix_ident`;
- navaid display strings inside course/radial objects.

Normalization:

- trim whitespace;
- uppercase;
- remove localizer hyphen, e.g. `I-ABC` equals `IABC`;
- remove explicit facility suffixes such as `VOR`, `VORTAC`, `NDB`, `LOC`, `LOCALIZER`, or `DME`.

Not allowed:

- fuzzy matching;
- edit-distance matching;
- matching different fixes because they look similar.

### 3.2 Degree Display Rounding

Allowed only for degree display fields:

- `course_or_radial.course_deg`;
- `course_or_radial.radial_deg`;
- `hold_params.value.inbound_course_deg`.

Rule:

```text
424 decimal degree value is equivalent to the integer chart-display degree if round-half-up(value) is equal.
```

Examples:

- `63.3` equals `63`;
- `243.1` equals `243`;
- `234.6` equals `235`.

Not allowed:

- automatic reciprocal equivalence;
- broad angle tolerance;
- changing course/radial type semantics.

## 4. Explicitly Forbidden Relaxations

This policy does not allow:

- altitude tolerance;
- turn semantic relaxation;
- holding default time;
- holding distance tolerance;
- automatic radial/course reciprocal equivalence;
- leg alignment changes;
- broad partial compare;
- mismatch-threshold broadening.

## 5. Comparison Behavior

The comparer keeps V3-style strict leg-index comparison and strict status/value comparison, except for the two PR #25 equivalence classes above.

V3 strict remains unchanged as the failure-mode baseline. This policy is a separate diagnostic method and must use a new run id.

