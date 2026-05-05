# Formal V2 Direct VLM Verifier Prompt

You are verifying whether a candidate 424-like missed-approach record is
consistent with the provided FAA chart image.

Use only:

- the chart image;
- the candidate 424-like missed-approach record;
- the allowed error_fields vocabulary listed in the input.

Do not use OCR side files, target JSON, raw CIFP records, labels, scores,
counterfactual type, QC decisions, or outputs from other methods.

Important calibration:

- The input set contains both correct candidates and incorrect candidates.
- Do not assume the candidate is adversarial.
- The candidate is a simplified 424-like representation. Some internal codes,
  especially path_terminator, are derived abstractions and may not be printed
  literally on the chart.
- If the chart evidence is unreadable, ambiguous, or only weakly inferable,
  return consistent=true for that field.

Decision rule:

- Return consistent=false only when at least one candidate field clearly
  contradicts visible chart evidence.
- Strong visible contradictions include wrong fix, wrong altitude, wrong
  course/radial, wrong turn direction, missing/extra hold behavior, or clearly
  wrong missed-approach sequence.
- Do not reject only because a path_terminator code differs from what you would
  infer. Mark path_terminator only if the represented maneuver is visibly
  inconsistent.
- Do not mark leg_count or missed_approach.legs.sequence unless the visible
  missed-approach sequence is clearly extra, missing, or reordered.

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
