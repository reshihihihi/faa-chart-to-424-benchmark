# Group 1 C2 Multi-QA Aggregator Candidate v1

Status: candidate implementation spec, final pre-freeze audit completed 2026-04-29, not formal frozen.

## Existing QA Prompt Source

The repository already contains a Method C QA prompt bundle imported from upstream PR #28:

- `prompts/path_c_qa_v2/q0_leg_count.txt`
- `prompts/path_c_qa_v2/q_terminator.txt`
- `prompts/path_c_qa_v2/q1_fix_ident.txt`
- `prompts/path_c_qa_v2/q2_altitude_constraint.txt`
- `prompts/path_c_qa_v2/q3_turn.txt`
- `prompts/path_c_qa_v2/q4_course_or_radial.txt`
- `prompts/path_c_qa_v2/q5_hold_params.txt`

These prompts define the question surfaces and per-question answer schemas. They are candidate prompts, not a final formal freeze.

No frozen deterministic C2 aggregator was found in this repository. This document defines the first candidate aggregator.

## C2 Method Boundary

```text
full chart image
  -> VLM answers fixed QA prompts
  -> deterministic QA aggregator
  -> canonical JSON
```

C2 does not receive OCR text, OCR bbox, field candidates, target answers, scorer output, CIFP records, or human annotations.

## Allowed Aggregator Inputs

The aggregator may read only:

- chart metadata: `chart_id`, `airport`, `approach_ident`, `chart_name`
- per-chart C2 QA JSON outputs produced from the fixed prompt bundle
- canonical JSON schema contract

## Forbidden Aggregator Inputs

The aggregator must not read:

- chart image pixels
- OCR text or OCR bbox
- automatic field candidates
- field-to-leg candidate tables
- gold missed-approach prose
- canonical target or answer key
- `field_targets.jsonl`
- `evidence_provenance.jsonl`
- `challenge_tags.jsonl`
- scorer outputs
- CIFP or ARINC 424 records
- human annotations
- previous model or rule outputs for the same chart
- web search or external aviation databases

## Expected QA Artifact Layout

For each chart:

```text
<qa_root>/<chart_id>/q0_leg_count.json
<qa_root>/<chart_id>/leg_001/q_terminator.json
<qa_root>/<chart_id>/leg_001/q1_fix_ident.json
<qa_root>/<chart_id>/leg_001/q2_altitude_constraint.json
<qa_root>/<chart_id>/leg_001/q3_turn.json
<qa_root>/<chart_id>/leg_001/q4_course_or_radial.json
<qa_root>/<chart_id>/leg_001/q5_hold_params.json
...
```

Every per-question file must contain exactly the answer object requested by its prompt:

```json
{ "status": "unknown", "value": null }
```

The example above shows shape only. If status is `present`, the value must be non-null and must follow the corresponding prompt schema.

## Aggregation Rules

1. Read `q0_leg_count.json`.
2. If `q0_leg_count.status` is not `present`, output unknown leg count and empty legs.
3. If `q0_leg_count.status` is `present`, create `value` legs with one-based `leg_index`.
4. For each leg, copy the six QA answer objects into the canonical fields:
   - `q_terminator.json` -> `Q_terminator`
   - `q1_fix_ident.json` -> `Q1_fix_ident`
   - `q2_altitude_constraint.json` -> `Q2_altitude_constraint`
   - `q3_turn.json` -> `Q3_turn`
   - `q4_course_or_radial.json` -> `Q4_course_or_radial`
   - `q5_hold_params.json` -> `Q5_hold_params`
5. If a per-leg QA file is missing or cannot be parsed, fill that field with `unknown`, `value = null`, except:
   - `Q3_turn`, `Q4_course_or_radial`, and `Q5_hold_params` remain `unknown` rather than inferring `not_applicable`.
6. The aggregator does not resolve semantic conflicts, infer missing values, repair aviation semantics, or consult targets.
7. Diagnostics are saved in a sidecar file; the final prediction contains only canonical schema fields.

## QA Runner Rules

The QA runner is part of the C2 method and must be audited together with the aggregator.

- `q0_leg_count` is called first.
- The number of follow-up leg question sets is determined only by the model answer to `q0_leg_count`.
- The runner must not use target leg count, scorer output, OCR text, field candidates, or CIFP to decide how many follow-up questions to ask.
- Each QA call must receive exactly one chart image, chart metadata, one fixed QA prompt, and the schema-bound tool definition for that question.
- Each valid QA answer is saved as a primary JSON file; invalid attempts are saved only as diagnostics.
- Missing or invalid QA answers are represented by the aggregator as `{"status":"unknown","value":null}` rather than being semantically repaired.
- The C2 final canonical JSON must be produced by deterministic copying from saved QA JSON files, not by another model call.

## Status/Value Rule

The aggregator enforces only structural JSON normalization. It must not convert values hidden in `status` into `value`; that is a model-output schema failure, not an aggregation repair.

## Formal Freeze Blockers

- final C2 prompt bundle state and hashes
- VLM provider/model/image settings
- QA runner layout
- strict raw JSON policy for each QA call
- retry/rerun policy
- validation behavior for malformed QA outputs
- sample image hashes and raw QA response paths in every run manifest

## Final Pre-Freeze Audit Note - 2026-04-29

No target-aware changes were made to the C2 QA prompts or aggregator in the final pre-freeze optimization. The current C2 implementation already enforces:

- image-only QA calls;
- q0 model answer controls the number of follow-up leg questions;
- one fixed question per model call;
- Anthropic-compatible tool-use output control;
- one schema-only retry without target/scorer/CIFP input;
- deterministic aggregation by copying saved QA JSON files;
- malformed or missing QA answers become `unknown/null` via the aggregator instead of semantic repair.

C2 remains a candidate method. Its low pilot100 field score is treated as a method-capability result rather than a reason for target-driven prompt tuning.
