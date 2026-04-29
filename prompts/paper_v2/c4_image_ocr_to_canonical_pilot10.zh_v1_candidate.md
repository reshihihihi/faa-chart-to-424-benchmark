# C4 Pilot Prompt v1 Candidate: Full Chart Image + OCR Text to Canonical JSON

## Method Boundary

You are running the paper-v2 C4 method:

full chart image + full-chart OCR text -> VLM or MLLM -> canonical JSON

C4 tests whether image evidence plus OCR text improves extraction compared with text-only B1 or image-only C3.

## Allowed Inputs

You may use only:

- chart_id
- airport
- approach_ident
- chart_name
- full chart image
- full-chart OCR text generated from the same full chart image
- the canonical output contract described here

## Forbidden Inputs

Do not use:

- OCR text from another input view
- ROI or human annotation boxes
- automatic field candidates
- field-to-leg candidates
- gold MA prose
- gold observable evidence
- canonical target or answer key
- field_targets.jsonl
- evidence_provenance.jsonl
- challenge_tags.jsonl
- scorer output
- CIFP or ARINC 424 records
- historical model output for the same chart
- web search or external aviation databases

For source ablation in later experiments, C4 must use OCR from the current image view. This pilot uses full-chart image and full-chart OCR only.

## Task

Use the full chart image and OCR text together to extract the missed approach procedure and output one canonical JSON object.

Use the image to resolve OCR ambiguity when possible. If image and OCR are unclear, contradictory, or insufficient, use unknown. Do not guess only to fill the schema.

## Semantic Extraction Guidance

First derive the flown missed approach sequence from the missed approach prose in the OCR text. Then use the full chart image to resolve ambiguity or add visual information such as courses, tracks, holding pattern details, and fixes visible outside the prose.

Preserve the flown order. Do not collapse sequential clauses into one leg merely because they appear in one sentence. A missed approach may contain separate segments such as:

- initial climb to an altitude before a `then` transition;
- direct-to-fix segment;
- track/course-to-fix segment;
- holding segment at a fix.

If the procedure says `climb to X, then ...`, treat the initial climb-to-altitude segment as part of the flown sequence. If the evidence supports a separate initial climb segment, represent it as a separate leg rather than merging it into the following direct-to-fix leg.

If the procedure says `direct A and on track/course ... to B and on track/course ... to C and hold`, do not merge the track-to-fix segment into the holding segment. A track/course-to-fix segment and a hold at the same final fix may be separate flown legs.

Do not create an extra leg only because the image shows a holding pattern, inbound course, radial, or localizer/course label. A visual course cue should be assigned to the appropriate flown segment only if the missed approach sequence supports that segment.

For altitude constraints, natural-language instructions such as `climb to X` or `continue climb to X` should generally be represented as `AT_OR_ABOVE` unless the chart explicitly indicates an exact `AT` constraint. If the exact altitude semantics are unclear, use unknown rather than forcing `AT`.

For path terminators, use only what can be inferred from the flown segment and visible evidence. If the segment type is not clear, set Q_terminator to unknown rather than hard-guessing CF, DF, TF, or hold terminators.

For holding legs, put hold turn, inbound course, time, and distance in Q5_hold_params. Do not duplicate hold turn into Q3_turn unless the chart separately indicates a turn before entering the hold.

## Output Schema

Top-level object must contain exactly:

- chart_id
- procedure
- missed_approach

procedure must contain exactly:

- airport
- approach_ident
- chart_name

missed_approach must contain:

- leg_count: an answer object with status and value
- legs: an array of leg objects

Each leg object must contain:

- leg_index
- answers

leg_index must strictly follow these rules:

- The first leg must have leg_index = 1, never 0.
- The second leg must have leg_index = 2, and later legs must increase by 1 without gaps.
- The order of the legs array must match the actual flown order of the missed approach procedure.
- When leg_count.status is present, leg_count.value must equal the number of objects in the legs array.
- If the number or order of legs cannot be determined reliably, set leg_count.status to unknown, leg_count.value to null, and legs to an empty array.
- Do not output zero-based indexes, duplicate indexes, skipped indexes, negative indexes, or string indexes.

answers must contain exactly:

- Q_terminator
- Q1_fix_ident
- Q2_altitude_constraint
- Q3_turn
- Q4_course_or_radial
- Q5_hold_params

Each answer object must use:

- status: one of present, not_applicable, not_observable, unknown
- value: concrete value when status is present; otherwise null

For leg_count, status may be present, not_observable, or unknown. If leg_count is unknown, value must be null and legs must be an empty array.

## Status/Value Separation Hard Rule

The status field is a label about observability only. It must never contain the extracted aviation value.

Allowed status strings are exactly:

- present
- not_applicable
- not_observable
- unknown

Do not put ARINC path terminators, fix idents, altitudes, courses, radials, directions, or hold values in status.

If the chart image and OCR-1 text support a concrete answer, use status present and put the concrete answer in value. For example, a DF terminator must be written as status present with value DF, not status DF. A fix ident FKL must be written as status present with value FKL, not status FKL.

If the answer is uncertain, not observable, or not applicable, status must be unknown, not_observable, or not_applicable, and value must be null.

## Schema-Bound Output Hard Rules

This run may be transported through a schema-bound tool use. The tool input must be exactly the canonical JSON object and must not contain any wrapper, explanation, evidence sidecar, or diagnostic fields.

- Copy `chart_id`, `airport`, `approach_ident`, and `chart_name` exactly from the input metadata. Do not infer, correct, abbreviate, or replace metadata from the chart image or OCR text.
- Never encode a nested JSON value as a quoted string.
- Never put the string unknown in value. If the answer is unknown, use status unknown and value null.
- Never put null in value when status is present.
- Never put a concrete value in status.
- If leg_count.status is present, leg_count.value must equal the number of leg objects.
- If leg_count.status is unknown, not_observable, or not_applicable, leg_count.value must be null and legs must be an empty array.

## Field Value Constraints

Q_terminator value, when present, must be one of:

CA, CF, CI, CR, DF, FA, FM, HA, HF, HM, IF, RF, TF, VA, VD, VI, VM, VR, AF, CD, FC, FD, VC, PI

Q1_fix_ident value, when present, must be a real fix, waypoint, runway, or navaid ident string with at most 5 characters. Facility labels often contain an ident plus a facility type, such as ORL VORTAC; in that case the ident is ORL and the facility type VORTAC must never be output as Q1_fix_ident. Do not output facility-type words such as VOR, VORTAC, DME, NDB, FIX, WAYPOINT, NAVAID, HOLDING, AIRPORT, RUNWAY, LOCALIZER, LOC, or ILS. If the image/OCR text shows only a facility type word and not the actual ident, set Q1_fix_ident to unknown with value null.

Q2_altitude_constraint value, when present, must be:

{"desc":"AT_OR_ABOVE","altitude_ft":3000,"altitude_2_ft":null}

desc must be one of AT, AT_OR_ABOVE, AT_OR_BELOW, BETWEEN. altitude_ft and altitude_2_ft must be integers or null. altitude_2_ft is non-null only for BETWEEN.

Q3_turn value, when present, must be LEFT or RIGHT.

Q4_course_or_radial value, when present, must be exactly one of:

{"type":"course_deg","course_deg":70.0}

{"type":"navaid_radial","navaid":"ABC","radial_deg":123.0,"direction":"outbound"}

{"type":"direct"}

For Q4_course_or_radial, status must never be course_deg, navaid_radial, direct, type course_deg, type navaid_radial, or type direct. If a course/radial/direct answer is supported, write status present and put the variant object in value.

Q5_hold_params value, when present, must be:

{"inbound_course_deg":70.0,"leg_time_min":1.0,"leg_distance_nm":null,"turn":"RIGHT"}

For non-hold legs, Q5_hold_params should be not_applicable. For hold legs, Q3_turn should usually be not_applicable because hold turn belongs in Q5_hold_params.

All degree-valued fields (`course_deg`, `radial_deg`, and `inbound_course_deg`) must be in the schema range 0.0 through 359.9. If the chart/OCR displays 360 degrees, encode it as 359.9, never as 360.

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
- The raw response will be parsed directly as JSON.

## Input

chart_id: {{chart_id}}
airport: {{airport}}
approach_ident: {{approach_ident}}
chart_name: {{chart_name}}

IMAGE: {{chart_image}}

OCR_TEXT:
{{ocr_text}}
