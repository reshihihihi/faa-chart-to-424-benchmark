# Experiment 6 Implicit Hold Time Policy

Status: formal-freeze policy for Experiment Group 6 v7 counterfactual cases.

Date: 2026-04-30

## Purpose

This policy defines how Experiment Group 6 treats holding-leg time when the FAA
chart does not explicitly print a leg time, but the candidate 424-like record
contains or omits a default holding time.

The goal is to keep `implicit_hold_time_omission` cases consistent with the
paper-v2 requirement: implicit/conventional 424-relevant information can be
tested, but the rule must be fixed before model evaluation.

## Frozen Rule

For the v7 verification set, a holding leg may include
`hold_params.leg_time_min = 1.0` when all of the following are true:

- the canonical proxy target contains a holding leg;
- the holding leg is not distance-based;
- no explicit chart evidence indicates a different holding leg time or
  distance;
- the source canonical projection represents the hold as a one-minute hold by
  convention.

An `implicit_hold_time_omission` negative case is valid when the candidate is
otherwise unchanged but omits this convention-derived one-minute hold time.

## Allowed Evidence

The builder and QC may use:

- the frozen canonical proxy target;
- the source chart image during QC;
- same-procedure CIFP-derived canonical projection metadata;
- the fixed v7 construction rule.

Verifier model inputs must not include this policy text, the gold label, the
gold `error_fields`, or the counterfactual type.

## Label Rule

For generated `implicit_hold_time_omission` cases:

- `consistent` must be `false`;
- `error_fields` must point to the affected holding parameter field;
- the case must remain otherwise minimally changed.

If the chart or target explicitly supports a different hold time or distance,
the case must be excluded rather than relabeled after model evaluation.

## Reporting Rule

Because this type depends on convention rather than fully explicit chart text,
results must be reported separately by counterfactual type. Low performance on
this type should be interpreted as difficulty with implicit 424 conventions,
not as ordinary OCR failure.

## Post-Freeze Change Rule

After this policy is frozen, individual cases may not be deleted, relabeled, or
rewritten based on model performance. Any future change requires a new
counterfactual builder version and a new freeze package.
