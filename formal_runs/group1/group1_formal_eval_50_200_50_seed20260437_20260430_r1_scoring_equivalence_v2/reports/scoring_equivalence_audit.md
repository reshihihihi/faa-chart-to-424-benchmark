# Group 1 scoring-equivalence v2 rescore audit

Run ID: `group1_rescore_scoring_equivalence_v2_20260501_r1`

This audit re-scores existing Group 1 predictions using chart-display-aware target/scoring v2.
It does not rerun OCR, LLM, VLM, or D-SFT inference.

## Method Summary

| method | valid | invalid | strict old acc | v2 display-aware acc | delta acc | delta correct | changed rows |
|---|---:|---:|---:|---:|---:|---:|---:|
| A1 | 200 | 0 | 0.2922 | 0.2922 | 0.0000 | 0 | 0 |
| A2 | 200 | 0 | 0.2261 | 0.2261 | 0.0000 | 0 | 0 |
| B1 | 200 | 0 | 0.2725 | 0.2739 | 0.0015 | 6 | 6 |
| B1_prime | 200 | 0 | 0.3216 | 0.3228 | 0.0012 | 5 | 5 |
| B1_prime_link | 185 | 15 | 0.1949 | 0.1949 | 0.0000 | 0 | 0 |
| C1 | 200 | 0 | 0.3709 | 0.3939 | 0.0230 | 93 | 93 |
| C2 | 200 | 0 | 0.2394 | 0.2651 | 0.0257 | 104 | 104 |
| C3 | 196 | 2 | 0.3828 | 0.4007 | 0.0179 | 71 | 71 |
| C4 | 200 | 0 | 0.4008 | 0.4042 | 0.0035 | 14 | 14 |
| D_SFT | 184 | 12 | 0.7355 | 0.7814 | 0.0459 | 171 | 171 |

## Interpretation

- Positive deltas mainly come from chart-display degree rounding and conservative string/number normalization.
- Invalid predictions remain invalid and are not silently repaired by scoring v2.
- Q_terminator remains strict and is only marked as 424-derived for reporting separation.

## Files

- CSV delta table: `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2\reports\old_vs_new_score_delta.csv`
- JSON audit: `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2\reports\scoring_equivalence_audit.json`
