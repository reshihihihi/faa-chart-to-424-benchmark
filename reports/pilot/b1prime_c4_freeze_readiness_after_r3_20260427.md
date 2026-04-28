# Freeze readiness after r3 - 2026-04-27

## Current best pilot run

```text
pilot10_exp1_b1prime_c4_semantic_matcher_v2_20260427_r3
```

## Can be kept as candidate settings

The following are now suitable for continued pilot use:

- canonical schema reuse;
- strict raw JSON parser policy with assistant prefill `{`;
- B1_prime method boundary;
- C4 method boundary;
- `field_candidates_schema_v1_candidate`;
- C4 prompt v1 as a candidate prompt;
- B1_prime matcher v2 as a candidate matcher;
- OCR artifact manifest format for pilot provenance;
- r3 artifact layout.

## Still not formal-frozen

Do not mark these as formal-ready yet:

- B1_prime matcher final rules;
- B1_prime prompt final text;
- C4 prompt final text;
- OCR artifact policy for formal300;
- model/provider/max token settings;
- API failure / parse failure / schema failure rerun policy;
- formal300 sample/split/target freeze.

## Why not formal-freeze yet

r3 is a 10-sample pilot only. It proves the pipeline can run cleanly and that the candidate changes are plausible, but formal freeze needs:

- a stable OCR artifact manifest for formal300;
- final run policy;
- final model/provider;
- formal sample manifest;
- no-leakage validation at runner level;
- review of whether B1_prime matcher v2's noise reduction changes the intended method strength.

## Recommended next action

Before expanding beyond pilot10, create repo-level candidate files or issues for:

1. OCR artifact manifest policy;
2. B1_prime matcher v2 review and freeze criteria;
3. C4 prompt v1 review and freeze criteria;
4. formal rerun policy.

Only after those are decided should the formal300 experiment run be prepared.
