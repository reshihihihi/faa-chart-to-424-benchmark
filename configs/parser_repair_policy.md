# Parser Repair Policy

Status: frozen for strict raw JSON v1 on 2026-04-27.

This policy freezes the parser and format-handling rules for B1/C3 pilot promotion and is the default policy for later extraction methods unless a later formal freeze explicitly supersedes it before evaluation.

## Frozen Decision

Formal-style extraction runs use strict raw JSON mode.

Allowed parser operations:

1. Read the raw model response as UTF-8 text.
2. Trim leading and trailing whitespace.
3. Parse the result with a standard JSON parser.
4. Validate parsed JSON against the registered schema or method-specific intermediate schema.
5. Save raw output, parsed output when available, validation errors, and parse failures.

No semantic repair is allowed.

## Raw Output Contract

The raw model output must be exactly one bare JSON object.

Requirements:

- The first non-whitespace character must be `{`.
- The last non-whitespace character must be `}`.
- Markdown code fences are not allowed.
- Natural-language explanation before or after JSON is not allowed.
- Extra wrapper labels such as `json` are not allowed.

A response containing a markdown code fence is a format violation / parse failure in strict mode.

## Assistant Prefill Output Control

The following call-level output control is frozen as part of strict raw JSON v1:

```text
assistant_prefill_json: true
assistant_prefill_value: "{"
```

This is not semantic repair. It only forces the assistant response to begin with the opening JSON brace and prevents markdown code fences. The saved raw output must include the prefilled `{` so the stored raw text is the exact JSON object sent to the parser.

## Explicitly Forbidden Parser Repairs

Do not:

- remove a markdown code fence in formal strict mode;
- extract the first JSON object from a longer response;
- change field values;
- infer missing fixes;
- infer missing altitudes;
- infer turns, courses, holds, or terminators;
- renumber, merge, split, or reorder legs;
- convert free text into canonical answers after model output;
- consult canonical targets, CIFP, scorer outputs, annotations, `field_targets.jsonl`, `evidence_provenance.jsonl`, or `challenge_tags.jsonl`;
- repair only one method or one sample class to improve its score.

## Failure Recording

Every method run must record at least:

```text
parse_status
format_violation
schema_valid
repair_applied
repair_type
parser_version
schema_path
schema_sha256
raw_output_sha256
```

For strict raw JSON v1:

```text
repair_applied: false
repair_type: none
```

## Rerun Interaction

Parser failure, schema failure, format violation, or low score must not be silently rerun to improve results. If a prompt, model, parser, or runner changes, the rerun must use a new `run_id` and old outputs must be retained.

Infrastructure failures such as provider timeout or transport failure may be rerun only under the separately frozen rerun policy.
