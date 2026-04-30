# B1_prime_link Prompt v1 Candidate

Status: candidate for formal smoke and formal300 evaluation. Not final-paper frozen until the Group 1 freeze package is approved.

## Method Boundary

You are running paper-v2 B1_prime_link:

full chart image -> registered ordinary OCR-1 full-chart text -> deterministic field candidate extraction -> deterministic field-to-leg linking -> LLM -> canonical JSON

B1_prime_link tests whether weak field-to-leg candidate links help a text LLM recover the missed-approach procedure. The links are candidate evidence only. They are not labels, not gold leg indices, not scorer output, and not target data.

## Allowed Inputs

Use only:

- chart_id
- airport
- approach_ident
- chart_name
- registered ordinary OCR-1 full-chart text
- automatically generated field_candidates derived from the same OCR-1 text
- automatically generated field_to_leg_links derived from the same OCR-1 text and field_candidates
- the canonical output contract described here

## Forbidden Inputs

Do not use:

- chart image pixels at the LLM stage
- OCR-2 text or OCR text from another source
- OCR bounding boxes or coordinates
- ROI labels, human annotation boxes, or visual cells
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

## How To Use Candidate Links

- Treat field_to_leg_links as weak evidence, not as instructions to copy.
- candidate_leg_index is an automatically generated candidate order. It is not the gold canonical leg_index.
- candidate_legs may be wrong, incomplete, duplicated, noisy, or missing route-table-heavy segments.
- If OCR prose conflicts with a candidate link, rely on the visible OCR missed-approach instruction.
- Do not set leg_count.value equal to the number of candidate_legs unless the OCR instruction itself supports that count.
- Do not mechanically map link_type to Q_terminator. For example, track_to_fix is not always TF, and hold_at_fix is not always HM.
- Do not mechanically copy candidate_legs one-to-one into output legs.
- If direct_to_fix and hold_at_fix share one fix, the procedure may mean direct to the fix and then hold at the fix. Do not merge or split without support in the OCR prose.
- If track_to_fix and hold_at_fix share one fix, inspect OCR prose before deciding whether this is one flown segment or a track segment followed by a hold.
- If route_sequence_snippets or unlinked_candidates contain visible route-chain evidence, consider it, but do not invent missing values.
- If a value is uncertain or not sufficiently supported by OCR text and candidate links, use unknown with value null.

## Task

Use only the OCR-1 text, field_candidates, and field_to_leg_links to extract the published missed approach procedure and output one canonical JSON object.

Preserve the flown order of the missed-approach legs. If evidence is missing, corrupt, ambiguous, contradictory, or insufficient, use unknown. Do not guess ARINC terminators, fixes, courses, radials, altitudes, or hold parameters merely to fill the schema.

## Status Values

Each answer object must use:

- status: one of present, not_applicable, not_observable, unknown
- value: a concrete value only when status is present; otherwise null

The status field is a label about observability only. It must never contain the extracted aviation value.

If the OCR/candidates support a concrete answer, use status present and put the concrete answer in value. For example, a DF terminator must be written as status present with value DF, not status DF. A fix ident FKL must be written as status present with value FKL, not status FKL.

If the answer is uncertain, not observable, or not applicable, status must be unknown, not_observable, or not_applicable, and value must be null.

## Schema-Bound Output Hard Rules

This run may be transported through a schema-bound tool call. Whether the transport is a raw JSON response or tool-call arguments, the emitted object must be exactly the canonical JSON object.

- Copy chart_id, airport, approach_ident, and chart_name exactly from the input metadata. Do not infer, correct, abbreviate, or replace metadata from OCR text.
- Top-level object must contain exactly chart_id, procedure, and missed_approach.
- Output bare JSON only.
- Do not output markdown code fences.
- Do not output explanations, comments, evidence sidecars, confidence fields, or diagnostics.
- Do not include field_candidates or field_to_leg_links in the output.
- All answer objects must obey status/value separation.
- If status is not present, value must be null.
- If status is present, value must follow the canonical schema.
- Every degree field must be from 0.0 through 359.9. If the source shows 360 degrees, encode 359.9.
- Q1_fix_ident.value must be a real fix/navaid/runway ident when present. Do not output facility-type words such as VOR, VORTAC, DME, NDB, FIX, WAYPOINT, NAVAID, HOLDING, AIRPORT, RUNWAY, LOCALIZER, LOC, or ILS as the value.

## Required Metadata

chart_id: {{chart_id}}
airport: {{airport}}
approach_ident: {{approach_ident}}
chart_name: {{chart_name}}

## OCR-1 Full-Chart Text

{{ocr_text}}

## field_candidates

{{field_candidates_json}}

## field_to_leg_links

{{field_to_leg_links_json}}
