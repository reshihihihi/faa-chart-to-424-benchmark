# Experiment 6 424-Derived Policy

Status: formal-freeze policy for Experiment Group 6 v7 counterfactual cases.

Date: 2026-04-30

## Purpose

This policy defines the scope of `424_derived_trap` cases. These cases test
whether a verifier can audit candidate 424-like structure when visible chart
tokens look plausible but the encoded maneuver or sequence is wrong.

The intent is not to require a model to see literal ARINC 424 path terminator
codes printed on a chart. The intent is to test whether the candidate record's
encoded maneuver is consistent with the charted missed-approach procedure.

## Frozen Rule

A `424_derived_trap` case is valid when:

- visible text-like values such as fix names and altitudes are kept plausible;
- the candidate path terminator or sequence representation is changed in a way
  that alters the represented maneuver;
- the change is localizable to one or more candidate 424-like fields;
- the candidate remains syntactically plausible and does not contain obvious
  artificial values.

The case is invalid if the only reason for inconsistency is that a literal
terminator code is not printed on the chart. The inconsistency must correspond
to a maneuver-level mismatch, such as climb-to-altitude, direct-to-fix, or
hold-at-fix behavior.

## Allowed Evidence

Construction and QC may use:

- the frozen canonical proxy target;
- same-procedure CIFP-derived projection;
- the full chart image during QC;
- the fixed candidate 424-like schema.

Verifier model inputs must not include the canonical target, CIFP raw records,
gold labels, `error_fields`, counterfactual type, or this policy text.

## Label Rule

For generated `424_derived_trap` cases:

- `consistent` must be `false`;
- `error_fields` must identify the smallest candidate field set that expresses
  the wrong 424-like structure;
- if the error is inherently sequential, `missed_approach.legs.sequence` is an
  allowed label.

## Reporting Rule

`424_derived_trap` must be reported as its own counterfactual type. It should
also be discussed separately from text-explicit errors, because good visible
text extraction alone is not expected to solve it.

## Post-Freeze Change Rule

After freeze, cases cannot be edited based on verifier scores. Any change to
this definition requires a new builder version and a new freeze package.
