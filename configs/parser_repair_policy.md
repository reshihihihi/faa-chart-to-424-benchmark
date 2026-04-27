# Parser Repair Policy

Status: draft, not frozen.

## Default

Semantic repair is not allowed.

## Candidate Mechanical Normalization

The following mechanical operation may be considered for pilot or formal runs
only if frozen before the run:

- remove a single outer markdown JSON code fence
- extract exactly one top-level JSON object when the raw response contains no
  other explanatory text

## Forbidden Repair

Do not:

- change field values
- infer missing fixes
- renumber legs
- fill altitudes, courses, turns, holds, or terminators
- consult targets, CIFP, scorer outputs, or annotations
- repair only one method to improve its score

Every repair count must be recorded in the run manifest.

