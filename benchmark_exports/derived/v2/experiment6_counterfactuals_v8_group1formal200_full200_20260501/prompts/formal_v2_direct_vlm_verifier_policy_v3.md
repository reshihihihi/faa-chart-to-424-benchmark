# Formal V2 Direct VLM Verifier Prompt, Policy v3

You are verifying whether a candidate 424-like missed-approach record is
consistent with the provided FAA chart image.

Use only:

- the chart image;
- the candidate 424-like missed-approach record;
- the allowed error_fields vocabulary listed in the input.

Do not use OCR side files, target JSON, raw CIFP records, labels, scores,
counterfactual type, QC decisions, or outputs from other methods.

Core rule:

- This is a chart-evidence verification task, not a re-derivation of every
  ARINC 424 internal code.
- Return consistent=false only when a candidate field clearly contradicts
  visible chart evidence.
- If a field is a 424-derived abstraction and the chart does not visibly
  contradict its represented maneuver, do not reject that field.

Display-equivalence calibration:

- Whole-degree chart displays and one-decimal 424-derived values are
  equivalent when they round to the same displayed degree. For example,
  63.3 is consistent with a chart display of 063 or 63; 243.1 is consistent
  with R-243; 338.3 is consistent with 338.
- A real shift is not equivalent. For example, 63.3 vs 73, 243.1 vs 263,
  or 338.3 vs 348 is a contradiction when visible on the chart.
- Ignore harmless display punctuation, spacing, leading zeros, and case in
  fix and navaid names. Do not treat a different name as equivalent.

424-derived field calibration:

- path_terminator values are internal abstractions. Do not reject solely
  because the path_terminator code itself is not printed. Reject only when
  the represented maneuver is visibly extra, missing, reordered, or different.
- For navaid_radial, the chart may show "R-243", "243 radial", or similar
  without explicitly stating the candidate direction. If the navaid and
  rounded radial number match the chart, do not reject only because the
  candidate has direction=inbound or direction=outbound.
- For hold_params.leg_time_min=1.0, do not reject solely because "1 minute"
  is not visibly printed when the chart otherwise shows a standard hold and
  no different time/distance is visible. Reject only when the chart visibly
  specifies a different holding time/distance or a different hold behavior.

Visible contradiction examples:

- wrong named fix or navaid;
- wrong altitude number or clearly wrong altitude relation;
- wrong turn direction when the chart visibly specifies left vs right;
- wrong course/radial number beyond whole-degree display rounding;
- wrong holding turn direction, published inbound course, time, or distance
  when visibly specified;
- visibly extra, missing, or reordered missed-approach sequence.

Ambiguity rule:

- If the chart evidence is unreadable, ambiguous, or only weakly inferable,
  return consistent=true for that field.

Field path rule:

- Every item in error_fields must be copied exactly from the allowed
  error_fields list.
- Do not add candidate_record prefixes.
- Do not add value suffixes.
- Use the leg_index shown in the candidate record.
- Prefer the smallest set of one to three fields that explains the
  inconsistency.

Output requirements:

- Return audit_decision tool JSON or bare JSON only, according to the runner.
- Do not use markdown.
- Do not include prose outside JSON.

Output shape: {"consistent": true, "error_fields": []}
