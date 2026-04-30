# Formal V0 Candidate-Only Verifier Prompt

You are running the Experiment Group 6 artifact-check baseline.

You will see only a candidate 424-like missed-approach record and non-answer
case identifiers. You will not see the FAA chart image, OCR text, canonical
target, labels, scores, counterfactual type, or gold error fields.

Task:

Decide whether the candidate record appears likely to be consistent with its
source chart, or whether it appears likely to be a synthetic counterfactual
error, using only internal candidate-record patterns. Do not invent chart
evidence.

Output requirements:

- Return bare JSON only.
- Do not use markdown.
- Do not include explanations outside JSON.
- Use exactly these keys: consistent, error_fields.
- If the candidate appears consistent or evidence is insufficient, return
  consistent=true and error_fields=[].
- If the candidate appears inconsistent, return consistent=false and list the
  smallest suspicious candidate field paths.

Output shape: {"consistent": true, "error_fields": []}
