You are given one complete FAA instrument approach chart image.

Task: output the missed approach procedure as canonical JSON only.

The final answer must be one JSON object. The first character must be `{`.
Do not use markdown. Do not use a fenced code block. Do not explain.

The JSON object has exactly three top-level keys:
1. `chart_id`
2. `procedure`
3. `missed_approach`

`procedure` has exactly these keys: `airport`, `approach_ident`, `chart_name`.
Do not put `missed_approach` inside `procedure`.

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

Do not create keys containing dots, such as `missed_approach.leg_count`.
Do not create flat keys such as `missed_approach_leg_count`.
Do not include OCR text, score metadata, target metadata, CIFP records,
file paths, sample IDs, or provenance notes.

If a field is not visible from the chart image, use status `not_observable`
with value null. If a field is logically not applicable for that leg, use
status `not_applicable` with value null.
