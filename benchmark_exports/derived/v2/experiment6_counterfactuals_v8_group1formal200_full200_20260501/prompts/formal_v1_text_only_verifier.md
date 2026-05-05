# Formal V1 Text-Only Verifier Prompt

You are verifying whether a candidate 424-like missed-approach record is
consistent with text evidence from an FAA chart.

Use only:

- the provided OCR/text evidence;
- the candidate 424-like missed-approach record;
- the allowed error_fields vocabulary listed in the input.

Do not use chart images, target JSON, raw CIFP records, labels, scores,
counterfactual type, QC decisions, or outputs from other methods.

Decision rule:

- Return consistent=false only when the candidate has a clear contradiction
  with the provided text evidence.
- If the text evidence is missing, ambiguous, or insufficient for a field,
  return consistent=true for that field.
- Do not reject merely because a 424 path terminator code is not printed in the
  text. Reject a terminator or sequence field only when the represented
  maneuver is clearly inconsistent with the text evidence.
- Prefer the smallest set of one to three error fields that explains the
  inconsistency.

Field path rule:

- Every item in error_fields must be copied exactly from the allowed
  error_fields list.
- Do not add candidate_record prefixes.
- Do not add value suffixes.
- Use the leg_index shown in the candidate record.

Output requirements:

- Return bare JSON only.
- Do not use markdown.
- Do not include explanations outside JSON.
- Use exactly these keys: consistent, error_fields.

Output shape: {"consistent": true, "error_fields": []}
