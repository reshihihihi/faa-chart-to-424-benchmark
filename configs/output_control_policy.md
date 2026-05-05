# Output Control Policy

Status: frozen strong output-control policy v1 for OpenAI-compatible text LLM pilot promotion; candidate strong output-control policy v1 for Anthropic-compatible VLM/MLLM pre-freeze validation.

Last updated: 2026-04-28.

## Problem Observed

`gpt-5.4` with ordinary JSON mode produced occasional syntactically invalid JSON for B1:

- missing final closing brace;
- invalid enum placement such as a fix ident in `status`;
- failures occurred before scoring and could not be fixed by parser repair.

This is an output-control problem, not a method-boundary problem. B1 still receives only OCR-1 text; B1_prime still receives only OCR-1 text plus flat OCR-derived `field_candidates`.

## Existing Requirements Checked

This policy is constrained by:

- `reshihihihi/faa-chart-to-424-benchmark#14`: strict JSON / parser repair policy; parser must not silently fix code fences, syntax, schema, or semantics.
- `reshihihihi/faa-chart-to-424-benchmark#11`: method-boundary contract; invalid JSON, parse failure, schema failure, and low-score samples must be retained.
- `reshihihihi/faa-missed-approach-experiment#36`: prompt/model/parser/rerun policy must be frozen and auditable.
- `reshihihihi/faa-missed-approach-experiment#41`: Experiment Group 1 outputs must preserve raw outputs, invalid states, parser repair count, failed samples, and retry reasons.

## Tested Options

### Option A: JSON mode only

Call setting:

```text
response_format = {"type": "json_object"}
```

Result on pilot10 B1 after prompt hardening:

```text
8/10 schema-valid
2/10 JSONDecodeError
```

Decision: not sufficient.

### Option B: `response_format.json_schema`

Call setting:

```text
response_format = {"type": "json_schema", "json_schema": ...}
```

Local proxy smoke test returned syntactically valid JSON but did not enforce the registered canonical schema shape.

Decision: not sufficient for this local proxy.

### Option C: forced tool call with canonical schema

Call setting:

```text
tools[0].function.name = "emit_canonical_json"
tools[0].function.parameters = schemas/missed_approach_leg.schema.json
tools[0].function.strict = true
tool_choice = emit_canonical_json
```

The runner parses only the single tool-call argument string.

Pilot10 result with B1/B1_prime:

```text
run_id: pilot10_group1_b1_b1prime_gpt54_toolcall_schema_retry1_ordinary_ocr_20260428_r1
B1:       10/10 schema-valid, 0 parse failure, 0 parser repair
B1_prime: 10/10 schema-valid, 0 parse failure, 0 parser repair
```

Expanded pilot100 result with B1/B1_prime:

```text
run_id: pilot100_b1_b1prime_gpt54_toolcall_schema_retry1_ordinary_ocr_20260428_r1
artifact_root: <external-artifact-root>/try_B1_B1_prime
B1:       100/100 schema-valid, 7 schema-only retries, 0 parser repair
B1_prime: 100/100 schema-valid, 11 schema-only retries, 0 parser repair
```

Decision: selected for OpenAI-compatible text LLM methods.

## Frozen Policy V1

For OpenAI-compatible text LLM methods that output canonical JSON directly:

```text
output_control = openai_tool_call
tool_name = emit_canonical_json
tool_parameters_schema = schemas/missed_approach_leg.schema.json
tool_choice = required emit_canonical_json
json_mode = false
parser_repair = false
schema_retry_count = 1
schema_retry_uses_target_or_scorer = false
```

Currently applies to:

- B1
- B1_prime

May later apply to:

- C1 or C4 only if they use an OpenAI-compatible VLM endpoint that supports image input and tool calls.

Does not currently apply to:

- C3 under the OpenAI text-LLM policy, because C3 first outputs questionnaire JSON, not canonical JSON;
- Claude VLM/MLLM runs as a formal frozen policy, until a later formal freeze promotes the provider-specific tool-use policy below;
- A1/A2, because they are deterministic rules, not LLM output.

## Anthropic-Compatible Tool-Use Candidate Policy V1

For Anthropic-compatible VLM/MLLM methods in Experiment Group 1, the runner may use provider tool use instead of raw text JSON:

```text
output_control = anthropic_tool_use
tool_choice = required named tool
assistant_prefill_json = false
parser_repair = false
schema_retry_count = 1
schema_retry_uses_target_or_scorer = false
```

Current candidate mapping:

- C1 uses `emit_canonical_json` with `schemas/missed_approach_leg.schema.json`.
- C3 uses `emit_questionnaire_json` with `schemas/c3_questionnaire.schema.candidate.json`, then the deterministic C3 parser maps questionnaire JSON to canonical JSON.
- C4 uses `emit_canonical_json` with `schemas/missed_approach_leg.schema.json`.
- C2 uses one `emit_qa_answer` tool call per fixed QA question, with a question-specific answer schema, followed by the deterministic C2 aggregator.

This policy is selected for the final pre-freeze optimization because the prior C1/C3/C4 pilot100 run was mechanically schema-valid under Anthropic tool use, but C4 still required many schema-only retries. The optimization target is fewer format/schema failures, not higher score.

### C4 Transport Hardening - 2026-04-29

The C4 pilot100 retry audit showed that 50 of 51 first-attempt retries were caused by provider/tool transport wrappers such as `$PARAMETER_NAME` or `chart` around an otherwise complete canonical object. The selected fix changes only the Anthropic-compatible tool transport setup:

- strip transport-level `$schema` and `$id` metadata from the provider-facing `input_schema` copy;
- strengthen the tool description so the tool input root is explicitly the canonical object itself;
- explicitly forbid `parameter`, `$PARAMETER_NAME`, `chart`, `output`, `result`, `arguments`, or any other wrapper key.

No C4 method input changed. C4 still receives only full chart image, OCR-1 full-chart text, metadata, and the canonical schema. No target, scorer, CIFP, field candidates, field-to-leg links, or prior method output is available to C4 inference.

Pilot100 external validation after this change:

```text
run_id: pilot100_group1_c4_output_control_fix_no_retry_20260429_r1
api_failure_recovery_run_id: pilot100_group1_c4_output_control_fix_no_retry_20260429_r1_api_retry_081
sample role: pilot100 external feasibility only, excluded from formal300
schema-valid after API-failure recovery: 100/100
schema-only retries: 0
parser repair: 0
wrapper-like final outputs: 0
score: 1248/2344 = 0.532423
report: reports/pilot/c4_output_control_fix_pilot100_20260429.md
```

The one non-schema main-run failure was an API 524 network error on `KAFO_R16`, recovered once under a separate run id. This is transport recovery, not score-based rerun.

Mechanical root unwrap remains disabled. If future provider behavior reintroduces wrappers, any unwrap policy must be pre-registered before formal evaluation and must be limited to transport wrappers whose inner object is already schema-valid.

The parser may only:

1. read the single saved tool-use input object;
2. unwrap a provider compatibility wrapper only when the tool input is exactly `{ "parameter": <object> }`;
3. serialize the tool input as JSON for the raw-output record;
4. parse JSON;
5. validate against the registered schema or method-specific intermediate schema.

For the current Anthropic-compatible proxy, two additional transport wrapper
forms are allowed only when the wrapped value is already a complete canonical
object with top-level `chart_id`, `procedure`, and `missed_approach`:

```text
{ "$PARAMETER_NAME": <canonical object> }
{ "chart": <canonical object> }
```

This is transport-wrapper normalization, not semantic repair. It may only remove
the single wrapper key. It must not alter field values, add missing fields, move
values between `status` and `value`, or consult target/scorer/CIFP data.

The parser must not:

- alter field values;
- move values from `status` to `value`;
- infer missing fields;
- repair metadata;
- select a better attempt by score;
- consult target, scorer, CIFP, annotations, OCR for no-OCR methods, or any other forbidden input.

Promotion from candidate to formal frozen policy requires the formal freeze manifest to record provider, model, tool schema path and hash, retry count, raw response path, tool-use input path, parser version, and per-sample attempt count.

## Schema-Only Retry Rule

Exactly one schema-only retry is allowed for this policy.

Allowed retry inputs:

- the original method prompt and allowed method inputs;
- previous model output;
- JSON parse error and/or schema validation errors.

Forbidden retry inputs:

- canonical target;
- CIFP or ARINC 424 records;
- scorer outputs;
- `field_targets.jsonl`;
- `evidence_provenance.jsonl`;
- `challenge_tags.jsonl`;
- human annotations;
- previous outputs from other methods;
- score, correctness, or low-performance information.

If the retry still fails parse or schema validation, the sample remains failed. No additional retry is allowed.

## Parser Rule

The parser may only:

1. read the saved tool-call argument string;
2. trim whitespace;
3. parse JSON;
4. validate against the registered schema;
5. write parsed JSON if valid;
6. record parse/schema failure if invalid.

The parser must not:

- add missing braces;
- remove code fences;
- extract a JSON substring;
- change field values;
- move values from `status` to `value`;
- infer missing fields;
- consult targets, scorer outputs, CIFP, annotations, or field-level labels.

## Required Run Manifest Fields

Every run using this policy must record:

```text
output_control
tool_name
tool_parameters_schema_path
tool_parameters_schema_sha256
schema_retry_count
schema_retry_uses_target_or_scorer
parser_repair_applied
attempt_count per sample
schema_retry_count per sample
raw API response path
tool-call argument path
validation path
```

## Interpretation

This policy is output control, not parser repair. It changes how the model is required to emit its answer, but it does not add target information, scorer feedback, CIFP records, or new chart evidence.
