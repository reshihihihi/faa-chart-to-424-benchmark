# C1 Pilot Prompt v1: Full-Chart Image to Canonical JSON

## Method Boundary

You are running the paper-v2 C1 baseline:

full chart image -> VLM/MLLM -> canonical JSON

C1 tests whether an unfine-tuned vision-language model can recover the missed
approach canonical schema directly from the full chart image. C1 must not
receive OCR text, OCR bounding boxes, ROI labels, field candidates, CIFP/ARINC
424 records, canonical targets, scorer outputs, human annotations, or previous
model outputs for the same chart.

## Allowed Inputs

- `chart_id`
- `airport`
- `approach_ident`
- `chart_name`
- full chart image
- the canonical output contract in this prompt

## Forbidden Inputs

- OCR text
- OCR bbox or coordinates
- ROI / prelabels / human annotation boxes
- automatic field candidates
- field-to-leg candidates
- gold missed-approach prose
- gold observable evidence
- canonical target / answer key
- `field_targets.jsonl`
- `evidence_provenance.jsonl`
- `challenge_tags.jsonl`
- scorer outputs
- CIFP / ARINC 424 records
- historical model output for the same chart

## Task

Read the full FAA approach chart image and output the missed approach procedure
as canonical JSON. If the chart image is ambiguous, too small, occluded, or the
procedure structure cannot be reliably determined from the allowed input, use
`unknown`. Do not invent ARINC terminators, fixes, courses, radials, altitudes,
or hold parameters.

## Status Values

Each answer status must be one of:

- `present`
- `not_applicable`
- `not_observable`
- `unknown`

Use `present` only when the image clearly supports the value. Use `unknown`
when the image is unreadable or ambiguous. Use `not_observable` only when the
field could apply but the allowed input shows no evidence for it. Use
`not_applicable` when the field has no structural meaning for that leg.

When `status` is not `present`, `value` must be `null`.

## Status/Value Separation Hard Rule

The status field is a label about observability only. It must never contain the extracted aviation value.

Allowed status strings are exactly:

- `present`
- `not_applicable`
- `not_observable`
- `unknown`

Do not put ARINC path terminators, fix idents, altitudes, courses, radials, directions, or hold values in status.

If the chart image supports a concrete answer, use status `present` and put the concrete answer in `value`. For example, a DF terminator must be written as status `present` with value `DF`, not status `DF`. A fix ident FKL must be written as status `present` with value `FKL`, not status `FKL`.

If the answer is uncertain, not observable, or not applicable, status must be `unknown`, `not_observable`, or `not_applicable`, and value must be `null`.

## Schema-Bound Output Hard Rules

This run may be transported through a schema-bound tool use. The tool input must be exactly the canonical JSON object and must not contain any wrapper, explanation, evidence sidecar, or diagnostic fields.

- Copy `chart_id`, `airport`, `approach_ident`, and `chart_name` exactly from the input metadata. Do not infer, correct, abbreviate, or replace metadata from the chart image.
- Never encode a nested JSON value as a quoted string.
- Never put the string `unknown` in `value`. If the answer is unknown, use `status: "unknown"` and `value: null`.
- Never put `null` in `value` when `status` is `present`.
- If `leg_count.status` is `present`, `leg_count.value` must equal the number of leg objects.
- If `leg_count.status` is not `present`, `leg_count.value` must be `null` and `legs` must be an empty array.

## Required JSON Shape

The top-level JSON must contain only:

- `chart_id`
- `procedure`
- `missed_approach`

`procedure` must contain only:

- `airport`
- `approach_ident`
- `chart_name`

`missed_approach` must contain only:

- `leg_count`
- `legs`

Each leg must contain:

- `leg_index`, starting at 1 and increasing by 1
- `answers`

Each `answers` object must contain only:

- `Q_terminator`
- `Q1_fix_ident`
- `Q2_altitude_constraint`
- `Q3_turn`
- `Q4_course_or_radial`
- `Q5_hold_params`

If leg count cannot be reliably determined, return:

for `leg_count`, use `{"status":"unknown","value":null}`, and use an empty `legs` array.

## Field Value Constraints

Q_terminator value, when present, must be one of:

CA, CF, CI, CR, DF, FA, FM, HA, HF, HM, IF, RF, TF, VA, VD, VI, VM, VR, AF, CD, FC, FD, VC, PI

Q1_fix_ident value, when present, must be a real fix, waypoint, runway, or navaid ident string with at most 5 characters. Facility labels often contain an ident plus a facility type, such as ORL VORTAC; in that case the ident is ORL and the facility type VORTAC must never be output as Q1_fix_ident. Do not output facility-type words such as VOR, VORTAC, DME, NDB, FIX, WAYPOINT, NAVAID, HOLDING, AIRPORT, RUNWAY, LOCALIZER, LOC, or ILS. If the image shows only a facility type word and not the actual ident, set Q1_fix_ident to unknown with value null.

Q2_altitude_constraint value, when present, must be an object with desc, altitude_ft, and altitude_2_ft. Do not output altitude as a bare string or bare number. desc must be one of AT, AT_OR_ABOVE, AT_OR_BELOW, BETWEEN. altitude_ft and altitude_2_ft must be integers or null. altitude_2_ft is non-null only for BETWEEN.

Q3_turn value, when present, must be LEFT or RIGHT. Do not output R, L, right, or left.

Q4_course_or_radial value, when present, must be exactly one of:

- type course_deg with course_deg
- type navaid_radial with navaid, radial_deg, and direction inbound or outbound
- type direct

Do not output course, radial, heading, or direct as a bare string. For Q4_course_or_radial, status must never be course_deg, navaid_radial, direct, type course_deg, type navaid_radial, or type direct. If a course/radial/direct answer is supported, write status present and put the variant object in value.

Q5_hold_params value, when present, must contain inbound_course_deg, leg_time_min, leg_distance_nm, and turn. Use these exact field names. Do not output inbound_course, turn_direction, leg_time, or leg_distance. For non-hold legs, Q5_hold_params should be not_applicable. For hold legs, Q3_turn should usually be not_applicable because hold turn belongs in Q5_hold_params.

All degree-valued fields (`course_deg`, `radial_deg`, and `inbound_course_deg`) must be in the schema range 0.0 through 359.9. If the chart displays 360 degrees, encode it as 359.9, never as 360.

## Final Internal Check Before Emitting

Before emitting the final object, silently check:

- metadata fields exactly match the input metadata;
- the top-level keys are exactly `chart_id`, `procedure`, and `missed_approach`;
- every answer object has exactly `status` and `value`;
- every `status` is one of the allowed status labels, never an aviation value;
- every non-present answer has `value: null`;
- every present answer has a schema-valid value;
- every `Q1_fix_ident` value is at most 5 characters and is not a facility-type word;
- every degree value is between 0.0 and 359.9;
- if `leg_count.status` is `present`, `leg_count.value` equals the number of legs;
- `leg_index` starts at 1 and increases by 1 without gaps.

If a concrete field would violate these checks, set that field to `{"status":"unknown","value":null}` instead of emitting invalid JSON.

## Output Contract

- Return only JSON.
- The first non-whitespace character must be `{`.
- The last non-whitespace character must be `}`.
- Do not output Markdown.
- Do not output code fences.
- Do not output three backticks anywhere.
- Do not add explanations before or after the JSON.
- Do not include fields outside the required schema.

## Input Metadata

chart_id: {{chart_id}}
airport: {{airport}}
approach_ident: {{approach_ident}}
chart_name: {{chart_name}}
