# Degree 360 Policy

Status: frozen for canonical schema v1.

Last updated: 2026-04-29.

## Rule

The canonical schema range for all degree-valued fields is:

```text
0.0 <= degree <= 359.9
```

If chart evidence, OCR text, or CIFP projection yields `360`, the output must
encode it as:

```text
359.9
```

This applies to:

- `Q4_course_or_radial.value.course_deg`
- `Q4_course_or_radial.value.radial_deg`
- `Q5_hold_params.value.inbound_course_deg`

## Applies To

- canonical proxy target generation;
- A1/A2 rules;
- B1/B1_prime/B1_prime_link prompts;
- C1/C2/C3/C4 prompts and retry prompts;
- D-SFT inference outputs;
- formal validator and scorer.

## Rationale

The current canonical schema v1 uses `359.9` as the upper bound. Changing the
schema to accept 360 would require regenerating and refreezing all targets,
prompts, validators, and scorer manifests. Therefore 360 is normalized to 359.9
before schema validation.

This is a schema encoding convention, not a target-aware correction.
