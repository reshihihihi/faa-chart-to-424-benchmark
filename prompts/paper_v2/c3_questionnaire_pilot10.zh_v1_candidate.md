# C3 Pilot Prompt v1 Candidate: Full-Chart Image to Questionnaire JSON

## Method Boundary

You are running paper-v2 C3:

full chart image -> VLM fixed questionnaire JSON -> deterministic parser -> canonical JSON

C3 tests whether a fixed questionnaire output protocol reduces formatting errors and hallucination compared with direct canonical JSON. Your output must be questionnaire JSON only. A separate deterministic parser will convert it to canonical JSON.

C3 must not receive OCR text, OCR bounding boxes, ROI labels, field candidates, CIFP/ARINC 424 records, canonical targets, scorer outputs, human annotations, gold missed-approach prose, or previous model outputs for the same chart.

## Allowed Inputs

Use only:

- chart_id
- airport
- approach_ident
- chart_name
- full chart image
- the questionnaire output contract described here

## Forbidden Inputs

Do not use:

- external OCR text
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

Read the full FAA approach chart image and fill a structured missed-approach questionnaire. You may use visible missed-approach prose, plan view, profile view, holding depiction, icons, and chart labels in the image. Preserve the flown order of the missed-approach legs.

If the image is too small, ambiguous, occluded, contradictory, or insufficient, use unknown. Do not guess ARINC terminators, fixes, courses, radials, altitudes, or hold parameters merely to fill the questionnaire.

## Status Values

Each answer object must use:

- status: one of present, not_applicable, not_observable, unknown
- value: a concrete value only when status is present; otherwise null

Use present only when the chart image supports the value. Use unknown when image readability or procedure semantics are ambiguous. Use not_observable only when the field could apply but the image shows no observable evidence. Use not_applicable when the field has no structural meaning for that leg.

## Status/Value Separation Hard Rule

The status field is a label about observability only. It must never contain the extracted aviation value.

Allowed status strings are exactly:

- present
- not_applicable
- not_observable
- unknown

Do not put ARINC path terminators, fix idents, altitudes, courses, radials, directions, or hold values in status.

If the chart image supports a concrete answer, use status present and put the concrete answer in value. For example, a DF terminator must be written as status present with value DF, not status DF. A fix ident FKL must be written as status present with value FKL, not status FKL.

If the answer is uncertain, not observable, or not applicable, status must be unknown, not_observable, or not_applicable, and value must be null.

## Schema-Bound Output Hard Rules

This run may be transported through a schema-bound tool use. The tool input must be exactly the questionnaire JSON object and must not contain canonical JSON, prose, evidence sidecars, or diagnostic fields.

- Copy `chart_id`, `airport`, `approach_ident`, and `chart_name` exactly from the input metadata. Do not infer, correct, abbreviate, or replace metadata from the chart image.
- Never encode a nested JSON value as a quoted string.
- Never put the string unknown in value. If the answer is unknown, use status unknown and value null.
- Never put null in value when status is present.
- If Q0_leg_count.status is present, Q0_leg_count.value must equal the number of questionnaire leg objects.
- If Q0_leg_count.status is unknown, not_observable, or not_applicable, Q0_leg_count.value must be null and legs must be an empty array.

## Questionnaire JSON Shape

The top-level object must contain exactly:

- chart_id
- procedure
- questionnaire

procedure must contain exactly:

- airport
- approach_ident
- chart_name

questionnaire must contain exactly:

- Q0_leg_count
- legs

Q0_leg_count must be an answer object with status and value. If the leg count cannot be determined reliably, set Q0_leg_count.status to unknown, Q0_leg_count.value to null, and legs to an empty array.

Each questionnaire leg object must contain exactly:

- leg_index, starting at 1 and increasing by 1 without gaps
- Q_terminator
- Q1_fix_ident
- Q2_altitude_constraint
- Q3_turn
- Q4_course_or_radial
- Q5_hold_params

## Field Value Constraints

Q_terminator value, when present, must be one of:

CA, CF, CI, CR, DF, FA, FM, HA, HF, HM, IF, RF, TF, VA, VD, VI, VM, VR, AF, CD, FC, FD, VC, PI

Q1_fix_ident value, when present, must be a real fix, waypoint, runway, or navaid ident string with at most 5 characters. Facility labels often contain an ident plus a facility type, such as ORL VORTAC; in that case the ident is ORL and the facility type VORTAC must never be output as Q1_fix_ident. Do not output facility-type words such as VOR, VORTAC, DME, NDB, FIX, WAYPOINT, NAVAID, HOLDING, AIRPORT, RUNWAY, LOCALIZER, LOC, or ILS. If the image shows only a facility type word and not the actual ident, set Q1_fix_ident to unknown with value null.

Q2_altitude_constraint value, when present, must contain desc, altitude_ft, and altitude_2_ft. desc must be one of AT, AT_OR_ABOVE, AT_OR_BELOW, BETWEEN. altitude_ft and altitude_2_ft must be integers or null. altitude_2_ft is non-null only for BETWEEN.

Q3_turn value, when present, must be LEFT or RIGHT.

Q4_course_or_radial value, when present, must be exactly one of:

- type course_deg with course_deg
- type navaid_radial with navaid, radial_deg, and direction inbound or outbound
- type direct

For Q4_course_or_radial, status must never be course_deg, navaid_radial, direct, type course_deg, type navaid_radial, or type direct. If a course/radial/direct answer is supported, write status present and put the variant object in value.

Q5_hold_params value, when present, must contain inbound_course_deg, leg_time_min, leg_distance_nm, and turn. For non-hold legs, Q5_hold_params should be not_applicable. For hold legs, Q3_turn should usually be not_applicable because hold turn belongs in Q5_hold_params.

All degree-valued fields (`course_deg`, `radial_deg`, and `inbound_course_deg`) must be in the schema range 0.0 through 359.9. If the chart displays 360 degrees, encode it as 359.9, never as 360.

## Final Internal Check Before Emitting

Before emitting the questionnaire object, silently check:

- metadata fields exactly match the input metadata;
- the top-level keys are exactly chart_id, procedure, and questionnaire;
- every answer object has exactly status and value;
- every status is one of the allowed status labels, never an aviation value;
- every non-present answer has value null;
- every present answer has a schema-valid value;
- every Q1_fix_ident value is at most 5 characters and is not a facility-type word;
- every degree value is between 0.0 and 359.9;
- if Q0_leg_count.status is present, Q0_leg_count.value equals the number of questionnaire legs;
- leg_index starts at 1 and increases by 1 without gaps.

If a concrete field would violate these checks, set that field to status unknown with value null instead of emitting invalid JSON.

## Parser Contract

The deterministic parser may only map:

- questionnaire.Q0_leg_count to missed_approach.leg_count
- each questionnaire leg to one canonical missed_approach.legs item
- each Q field to the same-named canonical answers field

The parser must not use targets, CIFP, annotations, OCR, external databases, or semantic repair.

## Strict Raw Output Contract

Return exactly one bare questionnaire JSON object.

- First non-whitespace character must be {.
- Last non-whitespace character must be }.
- Do not output Markdown.
- Do not output code fences.
- Do not output three backticks anywhere.
- Do not output explanation before or after JSON.
- Do not return canonical JSON.
- The raw response will be parsed directly as JSON.

## Input Metadata

chart_id: {{chart_id}}
airport: {{airport}}
approach_ident: {{approach_ident}}
chart_name: {{chart_name}}
