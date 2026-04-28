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

## Task

Use the OCR text and field_candidates to extract the missed approach procedure and output one canonical JSON object.

If OCR text or candidates are ambiguous, damaged, contradictory, or insufficient, use unknown. Do not guess only to fill the schema.

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

## Field Value Constraints

Q_terminator value, when present, must be one of:

CA, CF, CI, CR, DF, FA, FM, HA, HF, HM, IF, RF, TF, VA, VD, VI, VM, VR, AF, CD, FC, FD, VC, PI

Q1_fix_ident value, when present, must be a real fix, waypoint, runway, or navaid ident string, not a facility type such as VOR, NDB, FIX, WAYPOINT, NAVAID, HOLDING, AIRPORT, or RUNWAY.

Q2_altitude_constraint value, when present, must be:

{"desc":"AT_OR_ABOVE","altitude_ft":3000,"altitude_2_ft":null}

desc must be one of AT, AT_OR_ABOVE, AT_OR_BELOW, BETWEEN. altitude_ft and altitude_2_ft must be integers or null. altitude_2_ft is non-null only for BETWEEN.

Q3_turn value, when present, must be LEFT or RIGHT.

Q4_course_or_radial value, when present, must be exactly one of:

{"type":"course_deg","course_deg":70.0}

{"type":"navaid_radial","navaid":"ABC","radial_deg":123.0,"direction":"outbound"}

{"type":"direct"}

Q5_hold_params value, when present, must be:

{"inbound_course_deg":70.0,"leg_time_min":1.0,"leg_distance_nm":null,"turn":"RIGHT"}

For non-hold legs, Q5_hold_params should be not_applicable. For hold legs, Q3_turn should usually be not_applicable because hold turn belongs in Q5_hold_params.

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
