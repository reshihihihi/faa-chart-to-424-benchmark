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

IMAGE: {{chart_image}}

OCR_TEXT:
{{ocr_text}}
