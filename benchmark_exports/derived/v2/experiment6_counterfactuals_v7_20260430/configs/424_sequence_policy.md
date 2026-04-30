# Experiment 6 424 Sequence Policy

Status: formal-freeze policy for Experiment Group 6 v7 counterfactual cases.

Date: 2026-04-30

## Purpose

This policy defines how Experiment Group 6 treats sequence-level errors in
candidate 424-like missed-approach records, including `CA omission` and
`CA_to_DF_sequence_error`.

The purpose is to test whether a verifier can detect that the represented
missed-approach leg sequence is incomplete, merged, or semantically reordered,
not merely whether individual visible tokens are copied.

## Frozen Rule

A sequence counterfactual is valid when:

- it starts from a positive candidate projected from the canonical proxy target;
- it removes, merges, substitutes, or reorders a required maneuver-level leg;
- the altered candidate remains plausible as a 424-like record;
- the change is localizable to leg sequence and/or the affected leg field;
- no target, label, or score information appears in model input.

`CA omission` is valid when a required climb-to-altitude leg is omitted from the
candidate sequence.

`CA_to_DF_sequence_error` is valid when an initial climb-to-altitude behavior is
deleted, merged, or represented as a direct-to-fix style sequence that changes
the procedure semantics.

## Label Rule

Sequence cases must use one or more of the following labels, choosing the
smallest set that describes the error:

- `missed_approach.leg_count`
- `missed_approach.legs.sequence`
- the affected leg's `path_terminator`
- the affected leg's fix, altitude, course/radial, turn, or hold field when the
  sequence error is tied to that field.

When the error cannot be attributed to a single leg without ambiguity,
`missed_approach.legs.sequence` is preferred.

## Reporting Rule

Sequence errors must be reported separately from single-field value errors.
They are expected to be harder because the model must reason over procedure
order and implied maneuver semantics.

## Post-Freeze Change Rule

After freeze, no sequence case may be removed, relabeled, or rewritten based on
model performance. Future changes require a new builder version and new
validation/no-leakage/QC reports.
