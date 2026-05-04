You are given one complete FAA instrument approach chart image.

Task: produce one diagnostic JSON wrapper. First identify fine-grained chart
evidence boxes for the missed approach, then link canonical answer fields to
those boxes, then provide the final missed approach canonical JSON.

The raw answer must be one JSON object. The first character must be `{`.
Do not use markdown. Do not use a fenced code block. Do not explain outside
JSON.

The JSON object has exactly three top-level keys, in this order:
1. `evidence_boxes`
2. `answer_grounding`
3. `canonical_prediction`

`canonical_prediction` is the only object used as the final scored prediction.
It must keep exactly the same missed approach canonical JSON schema used by
the original D1 method. Do not add evidence fields inside
`canonical_prediction`.

`evidence_boxes` is an array of distinct fine-grained chart regions. Prefer
small boxes around the actual visible text, symbol, course/radial text,
altitude text, fix text, holding symbol, holding course/time/distance text,
path segment, or other local visual evidence. Use a broader `PLAN_VIEW`,
`MISSED_APPROACH_TEXT`, or `MISSED_APPROACH_DETAIL_AREA` region only when the
answer cannot honestly be tied to a smaller visible element.

Output no more than 8 evidence boxes. Do not continue listing boxes after
`box_008`. If you are uncertain, output fewer boxes and then immediately write
`answer_grounding` and `canonical_prediction`. Never repeat the same bbox or
alternate between repeated `PLAN_VIEW` boxes.

Each evidence box has exactly these keys:
`box_id`, `bbox`, `region_type`, `visible_text`, `field_names`,
`evidence_role`.

Use `box_id` values like `box_001`, `box_002`, and so on. Use normalized bbox
coordinates in `[x_center, y_center, width, height]` format, where every number
is between 0 and 1. `visible_text` is the text visibly inside the box, or null
for symbol-only regions. `field_names` lists the canonical fields supported by
the box, using only these names:
`Q_terminator`, `Q1_fix_ident`, `Q2_altitude_constraint`, `Q3_turn`,
`Q4_course_or_radial`, `Q5_hold_params`.

Use `evidence_role` to say what the visible region contributes, for example:
`fix_text_evidence`, `altitude_text_evidence`, `course_or_radial_evidence`,
`turn_or_path_symbol_evidence`, `holding_parameter_evidence`, or
`missed_approach_context_evidence`.

Do not repeat a box. Do not put final answer objects, target JSON, score
metadata, CIFP/424 records, file paths, method predictions, backend annotation
IDs, or raw provenance notes inside `evidence_boxes`.

After finishing `evidence_boxes`, close the array and continue to
`answer_grounding`. After `answer_grounding`, always output
`canonical_prediction`. Do not stop inside `evidence_boxes`.

`answer_grounding` is an array that links answer fields to evidence boxes.
Each item has exactly these keys:
`leg_index`, `field_name`, `answer_path`, `support_mode`, `evidence_box_ids`,
`evidence_summary`.

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

Use `evidence_summary` to briefly state where the evidence comes from on the
chart, using the generated `box_id` values and visible chart content. Do not
include backend region IDs, target paths, scores, raw 424/CIFP records, or
other method predictions.

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
file paths, sample IDs, backend annotation IDs, or provenance notes.

If a canonical field is not visible from the chart image, use status
`not_observable` with value null. If a field is logically not applicable for
that leg, use status `not_applicable` with value null.
