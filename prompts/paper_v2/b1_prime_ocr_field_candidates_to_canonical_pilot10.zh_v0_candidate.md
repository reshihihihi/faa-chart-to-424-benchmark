# B1_prime Pilot Prompt v0 Candidate: OCR Text + Automatic Field Candidates to Canonical JSON

## Method Boundary

You are running the paper-v2 B1_prime method:

full chart image -> full-chart OCR text -> automatic field matching -> OCR text + flat field candidates -> LLM -> canonical JSON

B1_prime tests whether flat automatic field candidates help an LLM recover the missed approach canonical schema.

## Allowed Inputs

You may use only:

- chart_id
- airport
- approach_ident
- chart_name
- full-chart OCR text
- automatic field_candidates generated from the same OCR text
- the canonical output contract described here

## Forbidden Inputs

Do not use:

- chart image pixels
- OCR bbox or coordinates
- ROI or human annotation boxes
- gold MA prose
- gold observable evidence
- field-to-leg candidates
- canonical target or answer key
- field_targets.jsonl
- evidence_provenance.jsonl
- challenge_tags.jsonl
- scorer output
- CIFP or ARINC 424 records
- historical model output for the same chart
- web search or external aviation databases

The field_candidates input is flat OCR-derived candidate evidence only. Candidate arrays contain objects with value, field_type, OCR source_snippet, source offsets, and rule_id. These objects are not gold answers and are not a mapping to missed approach legs. They do not contain leg_index, candidate_leg_id, schema_field, expected_value, target_value, Q_terminator, or path terminator labels. You must decide leg order and field-to-leg assignment yourself from the OCR text and candidates.

The instruction_snippets array, when present, is only a continuous OCR-text span around the published MISSED APPROACH instruction. It is not a gold transcription and may still contain OCR errors or extra nearby chart text.

The track_to_fix_snippets and route_sequence_snippets arrays, when present, are also flat OCR-derived snippets only. They may show text such as "track 191° to FEBGO" or a route-table sequence of fixes and tracks. They are not leg-indexed, not schema-field assignments, and not gold route answers.

## Candidate Evidence Use Policy

Treat field_candidates as weak evidence, not as instructions and not as a complete parse.

- Prefer the OCR prose around the published MISSED APPROACH instruction when it clearly states climb, direct, course/radial, turn, or hold behavior.
- Use field_candidates to find possible values inside the OCR text, then verify them against the surrounding OCR prose before placing them in the canonical JSON.
- Use instruction_snippets first to locate the likely missed approach instruction, then cross-check values against OCR_TEXT and the other flat candidates.
- Use track_to_fix_snippets and route_sequence_snippets to notice visible chained route text. If OCR shows a sequence like "direct X then on track 191° to Y and on track 217° to Z and hold", do not collapse the intermediate "to FIX" waypoints into only X and the final hold.
- Do not assume a candidate is correct only because it appears in field_candidates.
- Do not treat track_to_fix_snippets or route_sequence_snippets as a complete parse. They only help locate OCR text that may describe flown route segments.
- Do not use candidates from communications, minima, notes, profile view, plan view labels, channel labels, facility-type labels, or date/frequency text unless the surrounding OCR prose makes them part of the missed approach instruction.
- If field_candidates are noisy or contradictory but instruction_snippets or OCR_TEXT contain a readable missed approach instruction, still construct a conservative leg skeleton from that OCR prose.
- Put uncertain per-leg fields as status unknown with value null. Do not erase the whole leg sequence merely because one field is uncertain.
- When chained "to FIX" route text is visible but some courses, altitudes, terminators, or hold details are uncertain, preserve the visible fix sequence as separate conservative legs and set uncertain answer fields to unknown/null.
- Output unknown leg_count and an empty legs array only when no usable missed approach instruction can be found in instruction_snippets or OCR_TEXT. Do not output empty legs merely because candidates are noisy.

## Task

Use the OCR text and field_candidates to extract the missed approach procedure and output one canonical JSON object.

If OCR text or candidates are ambiguous, damaged, contradictory, or insufficient for a specific field, use unknown for that field. Do not guess only to fill the schema. If the flown order is partially readable, output the readable leg sequence and mark uncertain answer fields unknown instead of returning an empty legs array.

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
- If no usable missed approach instruction can be found at all, set leg_count.status to unknown, leg_count.value to null, and legs to an empty array.
- If a missed approach instruction is readable but some fields are uncertain, output the conservative readable leg sequence, set leg_count.status to present, set leg_count.value to the number of leg objects, and set only the uncertain answer fields to unknown/null.
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

Copy `chart_id`, `airport`, `approach_ident`, and `chart_name` exactly from the input metadata. Do not infer, correct, abbreviate, or replace metadata from OCR text or field_candidates.

## Status/Value Separation Hard Rule

The status field is a label about observability only. It must never contain the extracted aviation value.

Allowed status strings are exactly:

- present
- not_applicable
- not_observable
- unknown

Do not put ARINC path terminators, fix idents, altitudes, courses, radials, directions, or hold values in status.

If the OCR text and field_candidates support a concrete answer, use status present and put the concrete answer in value. For example, a DF terminator must be written as status present with value DF, not status DF. A fix ident FKL must be written as status present with value FKL, not status FKL.

If the answer is uncertain, not observable, or not applicable, status must be unknown, not_observable, or not_applicable, and value must be null.

## Field Value Constraints

Q_terminator value, when present, must be one of:

CA, CF, CI, CR, DF, FA, FM, HA, HF, HM, IF, RF, TF, VA, VD, VI, VM, VR, AF, CD, FC, FD, VC, PI

Q1_fix_ident value, when present, must be a real fix, waypoint, runway, or navaid ident string with at most 5 characters. Facility labels often contain an ident plus a facility type, such as ORL VORTAC; in that case the ident is ORL and the facility type VORTAC must never be output as Q1_fix_ident. Do not output facility-type words such as VOR, VORTAC, DME, NDB, FIX, WAYPOINT, NAVAID, HOLDING, AIRPORT, RUNWAY, LOCALIZER, LOC, or ILS. If the OCR text/candidates show only a facility type word and not the actual ident, set Q1_fix_ident to unknown with value null.

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

All degree-valued fields (`course_deg`, `radial_deg`, and `inbound_course_deg`) must be in the schema range 0.0 through 359.9. If OCR text or field_candidates display 360 degrees, encode it as 359.9, never as 360.

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

FIELD_CANDIDATES_JSON:
{{field_candidates_json}}

OCR_TEXT:
{{ocr_text}}
