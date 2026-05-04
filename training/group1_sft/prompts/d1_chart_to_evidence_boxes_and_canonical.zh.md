You are given one complete FAA instrument approach chart image.

Task: output one JSON object. First identify the visible chart evidence boxes
that support the missed approach extraction, then output the missed approach
procedure as canonical JSON.

The final answer must be one JSON object. The first character must be `{`.
Do not use markdown. Do not use a fenced code block. Do not explain.

The JSON object has exactly two top-level keys, in this order:
1. `evidence_boxes`
2. `canonical_prediction`

Because `canonical_prediction` is nested inside the outer object, the completed
answer must close both the canonical object and the outer object. The final
characters of a valid answer are normally `]}}}` after the last leg. Do not stop
after `]}}`.

`evidence_boxes` is an array of exactly 3 chart regions. Do not output more
than 3 boxes. Do not repeat a box. After the third box, close the array and
immediately output `canonical_prediction`.

Use these three boxes, in this order:
1. `missed_approach_text` with region_type `MISSED_APPROACH_TEXT`
2. `plan_view_context` with region_type `PLAN_VIEW`
3. `missed_approach_detail_area` with region_type `MISSED_APPROACH_DETAIL_AREA`

Each evidence box has exactly these keys: `box_id`, `bbox`, `region_type`.
Use normalized bbox coordinates in `[x_center, y_center, width, height]`
format, where every number is between 0 and 1.

The evidence box section must not contain final answer values, canonical target
objects, score metadata, CIFP/424 records, file paths, or other method
predictions. It must not contain candidate leg ids, final answer values, or
field-level canonical answers.

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
