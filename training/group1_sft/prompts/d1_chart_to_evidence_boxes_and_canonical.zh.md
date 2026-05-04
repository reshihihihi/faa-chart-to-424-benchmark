You are given one complete FAA instrument approach chart image.

Task: output one JSON object. First identify the chart evidence boxes that
support the missed approach extraction, then connect each extracted answer
field to those boxes, then output the missed approach procedure as canonical
JSON.

The final answer must be one JSON object. The first character must be `{`.
Do not use markdown. Do not use a fenced code block. Do not explain.

The JSON object has exactly three top-level keys, in this order:
1. `evidence_boxes`
2. `answer_grounding`
3. `canonical_prediction`

Because `canonical_prediction` is nested inside the outer object, the completed
answer must close both the canonical object and the outer object. Do not stop
after the canonical `legs` array.

`evidence_boxes` is an array of distinct fine-grained chart regions. Prefer
small boxes around the actual visible text, symbol, course/radial text,
altitude text, fix text, hold symbol, path segment, or other local visual
evidence. Use a broader `PLAN_VIEW` or `MISSED_APPROACH_TEXT` region only when
the answer cannot honestly be tied to a smaller visible element.

Each evidence box has exactly these keys:
`box_id`, `source_region_id`, `bbox`, `region_type`, `visible_text`,
`field_names`.

Use `box_id` values like `box_001`, `box_002`, and so on. Use normalized bbox
coordinates in `[x_center, y_center, width, height]` format, where every number
is between 0 and 1. `visible_text` is the text visibly inside the box, or null
for symbol-only regions. `field_names` lists the canonical fields supported by
the box, using only these names:
`Q_terminator`, `Q1_fix_ident`, `Q2_altitude_constraint`, `Q3_turn`,
`Q4_course_or_radial`, `Q5_hold_params`.

Do not repeat a box. Do not put final answer values, canonical answer objects,
score metadata, CIFP/424 records, file paths, method predictions, or raw target
JSON inside `evidence_boxes`.

`answer_grounding` is an array that links answer fields to evidence boxes. Each
item has exactly these keys:
`leg_index`, `field_name`, `answer_path`, `support_mode`, `evidence_box_ids`,
`source_region_ids`, `review_support_mode`, `evidence_source`.

Use `answer_path` values like:
`missed_approach.legs[0].answers.Q_terminator`

Use `evidence_box_ids` to reference the supporting boxes by `box_id`. If a
field is completed by a rule default rather than directly visible chart text or
symbol, do not pretend it is directly visible. Use
`rule_default_not_directly_visible`. If available evidence is too weak for a
field, use `insufficient_for_encoding` or `not_grounded`.

Allowed `support_mode` values:
`direct_visible_text`, `direct_visible_symbol`, `direct_visible_region`,
`inferred_from_visible_evidence`, `rule_default_not_directly_visible`,
`insufficient_for_encoding`, `not_grounded`.

`canonical_prediction` must follow the usual missed approach canonical JSON
schema. It has exactly three keys:
`chart_id`, `procedure`, `missed_approach`.

`procedure` has exactly these keys: `airport`, `approach_ident`, `chart_name`.

`missed_approach` has exactly these keys: `leg_count`, `legs`.
`leg_count` is an answer object: it must be `{"status": "...", "value": ...}`.
`legs` is an array of leg objects.

Each leg object has exactly these keys: `leg_index`, `answers`.
`answers` has exactly these keys: `Q_terminator`, `Q1_fix_ident`,
`Q2_altitude_constraint`, `Q3_turn`, `Q4_course_or_radial`,
`Q5_hold_params`.

Every answer field must be an object with exactly:
`status`: one of `present`, `not_observable`, `not_applicable`, `unknown`.
`value`: the extracted value, or null when status is not `present`.

Use these value shapes when status is `present`:
`Q_terminator.value`: one ARINC path terminator string such as `CA`, `DF`,
`TF`, `FM`, `HA`, `HF`, or `HM`.
`Q1_fix_ident.value`: a fix identifier string.
`Q2_altitude_constraint.value`: an object with `desc`, `altitude_ft`,
and `altitude_2_ft`.
`Q3_turn.value`: `LEFT` or `RIGHT`.
`Q4_course_or_radial.value`: an object with `type`; examples of type are
`course_deg`, `navaid_radial`, and `direct`.
`Q5_hold_params.value`: an object with `inbound_course_deg`, `leg_time_min`,
`leg_distance_nm`, and `turn`.

Do not create keys containing dots. Do not create flat missed approach keys.
Do not include OCR dumps, target metadata, score metadata, CIFP records,
file paths, sample IDs, or provenance notes.

If a canonical field is not visible from the chart image, use status
`not_observable` with value null. If a field is logically not applicable for
that leg, use status `not_applicable` with value null.
