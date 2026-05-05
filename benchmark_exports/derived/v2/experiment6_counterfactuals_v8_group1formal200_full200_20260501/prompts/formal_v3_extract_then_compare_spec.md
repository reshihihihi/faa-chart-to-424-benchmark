# Formal V3 Extract-Then-Compare Specification

V3 is not a free-form verifier prompt. It is a deterministic pipeline:

1. Read a preselected frozen Group 1 canonical extraction output.
2. Normalize it into the candidate 424-like field surface.
3. Compare it with the candidate 424-like record.
4. Return audit decision JSON.

The comparer may read:

- chart_id, sample_id, verification_case_id;
- candidate_record;
- the selected Group 1 method's canonical JSON prediction;
- the frozen comparer rules.

The comparer must not read:

- canonical target;
- raw CIFP;
- labels;
- counterfactual type;
- gold error_fields;
- score files;
- QC decisions.

Formal output shape: {"consistent": true, "error_fields": []}

If the selected Group 1 extraction is missing or schema-invalid, V3 must output
consistent=true and error_fields=[] with a recorded diagnostic status, or count
the case as invalid according to the pre-frozen run policy. It must not fill the
missing extraction from the target.
