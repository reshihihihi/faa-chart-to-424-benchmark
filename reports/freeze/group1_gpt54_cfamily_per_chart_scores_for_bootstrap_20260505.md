# Group 1 GPT-5.4 C-Family Per-Chart Scores for Bootstrap

- Created UTC: 2026-05-05T02:30:27.244757+00:00
- Split: `formal300_50_200_50_seed20260437/evaluation`
- Purpose: provide explicit `method, chart_id, correct, total, accuracy` rows for formal bootstrap and paired delta CI.
- This supplements the per-chart `scores/*.json` files already committed under each run directory.

## Files

- CSV: `reports/freeze/group1_gpt54_cfamily_per_chart_scores_for_bootstrap_20260505.csv`
- JSON: `reports/freeze/group1_gpt54_cfamily_per_chart_scores_for_bootstrap_20260505.json`

## Integrity

| Method | Rows | Unique charts | Correct/Total from rows | Accuracy | Matches method summary |
|---|---:|---:|---:|---:|---|
| `C1_GPT54` | 200 | 200 | 1201/4052 | 0.296397 | True |
| `C2_GPT54_batched_leg` | 200 | 200 | 1884/4052 | 0.464956 | True |
| `C3_GPT54` | 200 | 200 | 1218/4052 | 0.300592 | True |
| `C4_GPT54` | 200 | 200 | 1757/4052 | 0.433613 | True |

## Bootstrap Use

Use `chart_id` as the resampling unit. For paired method deltas, inner-join rows by `chart_id` across methods, then resample chart IDs with replacement.
