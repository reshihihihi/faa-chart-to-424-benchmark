# Parser Repair Policy

Status: draft, not frozen.

## Pilot10 B1/C3 Strict JSON Candidate

For `pilot10_exp1_b1_c3_strict_json_prefill_20260427_r1`, parser repair is
disabled:

- raw model output must be a single bare JSON object;
- strict JSON parsing is the only accepted extraction policy;
- markdown code fences or any extra natural-language wrapper are format
  violations;
- no semantic repair is allowed;
- no target, CIFP, annotation, scorer output, or historical model output may be
  used during parsing.

The pilot uses an Anthropic Messages assistant prefill of `{` for B1 and C3 to
discourage markdown code fences. The stored raw text already includes the
prefilled opening brace and is parsed as one complete JSON object.

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
