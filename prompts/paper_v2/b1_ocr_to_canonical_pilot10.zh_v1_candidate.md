# B1 Pilot Prompt v1 Candidate: Full-Chart OCR Text to Canonical JSON

## Method Boundary

You are running paper-v2 B1:

full chart image -> registered full-chart ordinary OCR text -> LLM -> canonical JSON

B1 tests whether a text LLM can recover missed-approach procedure semantics from full-chart OCR text alone. B1 must not receive chart image pixels, OCR bounding boxes, ROI labels, automatic field candidates, CIFP/ARINC 424 records, canonical targets, scorer outputs, human annotations, gold missed-approach prose, or previous model outputs for the same chart.

The OCR text in this run must come from the registered ordinary OCR-1 source. MLLM/VLM-generated transcription is not valid OCR for B1.

## Allowed Inputs

Use only:

- chart_id
- airport
- approach_ident
- chart_name
- full-chart OCR text
- the canonical output contract described here

## Forbidden Inputs

Do not use:

- chart image pixels at the LLM stage
- OCR bbox or coordinates
- ROI, prelabels, or human annotation boxes
- automatic field candidates
- field-to-leg candidates
- gold missed-approach prose
- gold observable evidence
- canonical target or answer key
- field_targets.jsonl
- evidence_provenance.jsonl
- challenge_tags.jsonl
- scorer output
- CIFP or ARINC 424 records
- historical model output for the same chart
- web search or external aviation databases

## Task

Use only the OCR text to extract the published missed approach procedure and output one canonical JSON object.

Preserve the flown order of the missed-approach legs. If OCR text is missing, corrupt, ambiguous, contradictory, or insufficient, use unknown. Do not guess ARINC terminators, fixes, courses, radials, altitudes, or hold parameters merely to fill the schema.

## Status Values

Each answer object must use:

- status: one of present, not_applicable, not_observable, unknown
- value: a concrete value only when status is present; otherwise null

Use present only when the OCR text supports the value. Use unknown when OCR quality or procedure semantics are ambiguous. Use not_observable only when the field could apply but the allowed input contains no observable evidence. Use not_applicable when the field has no structural meaning for that leg.

## Status/Value Separation Hard Rule

The status field is a label about observability only. It must never contain the extracted aviation value.

Allowed status strings are exactly:

- present
- not_applicable
- not_observable
- unknown

Do not put ARINC path terminators, fix idents, altitudes, courses, radials, directions, or hold values in status.

If the OCR supports a concrete answer, use status present and put the concrete answer in value. For example, a DF terminator must be written as status present with value DF, not status DF. A fix ident FKL must be written as status present with value FKL, not status FKL.

If the answer is uncertain, not observable, or not applicable, status must be unknown, not_observable, or not_applicable, and value must be null.

## Schema-Bound Output Hard Rules

This run may be transported through a schema-bound tool call. Whether the transport is a raw JSON response or tool-call arguments, the emitted object must be exactly the canonical JSON object.

- Copy `chart_id`, `airport`, `approach_ident`, and `chart_name` exactly from the input metadata. Do not infer, correct, abbreviate, or replace metadata from OCR text.
- Never encode a nested JSON value as a quoted string.
- Never put the string unknown in value. If the answer is unknown, use status unknown and value null.
- Never put null in value when status is present.
- Never put a concrete value in status.
- Do not add confidence, explanation, evidence, source text, page number, bbox, notes, or any diagnostic fields.
- If leg_count.status is present, leg_count.value must equal the number of leg objects.
- If leg_count.status is unknown, not_observable, or not_applicable, leg_count.value must be null and legs must be an empty array.

## Required JSON Shape

The top-level object must contain exactly:

- chart_id
- procedure
- missed_approach

procedure must contain exactly:

- airport
- approach_ident
- chart_name

missed_approach must contain exactly:

- leg_count
- legs

leg_count must be an answer object with status and value. If the leg count cannot be determined reliably, set leg_count.status to unknown, leg_count.value to null, and legs to an empty array.

Each leg object must contain:

- leg_index, starting at 1 and increasing by 1 without gaps
- answers

answers must contain exactly:

- Q_terminator
- Q1_fix_ident
- Q2_altitude_constraint
- Q3_turn
- Q4_course_or_radial
- Q5_hold_params

## Field Value Constraints

Q_terminator value, when present, must be one of:

CA, CF, CI, CR, DF, FA, FM, HA, HF, HM, IF, RF, TF, VA, VD, VI, VM, VR, AF, CD, FC, FD, VC, PI

Q1_fix_ident value, when present, must be a real fix, waypoint, runway, or navaid ident string with at most 5 characters. Facility labels often contain an ident plus a facility type, such as ORL VORTAC; in that case the ident is ORL and the facility type VORTAC must never be output as Q1_fix_ident. Do not output facility-type words such as VOR, VORTAC, DME, NDB, FIX, WAYPOINT, NAVAID, HOLDING, AIRPORT, RUNWAY, LOCALIZER, LOC, or ILS. If the OCR text shows only a facility type word and not the actual ident, set Q1_fix_ident to unknown with value null.

Q2_altitude_constraint value, when present, must contain desc, altitude_ft, and altitude_2_ft. desc must be one of AT, AT_OR_ABOVE, AT_OR_BELOW, BETWEEN. altitude_ft and altitude_2_ft must be integers or null. altitude_2_ft is non-null only for BETWEEN.

Q3_turn value, when present, must be LEFT or RIGHT.

Q4_course_or_radial value, when present, must be exactly one of:

- type course_deg with course_deg
- type navaid_radial with navaid, radial_deg, and direction inbound or outbound
- type direct

For Q4_course_or_radial, status must never be course_deg, navaid_radial, direct, type course_deg, type navaid_radial, or type direct. If a course/radial/direct answer is supported, write status present and put the variant object in value.

Q5_hold_params value, when present, must contain inbound_course_deg, leg_time_min, leg_distance_nm, and turn. For non-hold legs, Q5_hold_params should be not_applicable. For hold legs, Q3_turn should usually be not_applicable because hold turn belongs in Q5_hold_params.

All degree-valued fields (`course_deg`, `radial_deg`, and `inbound_course_deg`) must be in the schema range 0.0 through 359.9. If the OCR text displays 360 degrees, encode it as 359.9, never as 360.

## Final Internal Check Before Emitting

Before emitting the final object, silently check:

- metadata fields exactly match the input metadata;
- the top-level keys are exactly chart_id, procedure, and missed_approach;
- every answer object has exactly status and value;
- every status is one of the allowed status labels, never an aviation value;
- every non-present answer has value null;
- every present answer has a schema-valid value;
- every Q1_fix_ident value is at most 5 characters and is not a facility-type word;
- every degree value is between 0.0 and 359.9;
- if leg_count.status is present, leg_count.value equals the number of legs;
- leg_index starts at 1 and increases by 1 without gaps.

If a concrete field would violate these checks, set that field to status unknown with value null instead of emitting invalid JSON.

## Strict Raw Output Contract

Return exactly one bare JSON object.

- First non-whitespace character must be {.
- Last non-whitespace character must be }.
- Do not output Markdown.
- Do not output code fences.
- Do not output three backticks anywhere.
- Do not output explanation before or after JSON.
- Do not include fields outside the required schema.
- The raw response will be parsed directly as JSON.

## Input

chart_id: {{chart_id}}
airport: {{airport}}
approach_ident: {{approach_ident}}
chart_name: {{chart_name}}

OCR_TEXT:
{{ocr_text}}
