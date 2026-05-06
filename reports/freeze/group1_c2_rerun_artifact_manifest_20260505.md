# Group 1 C2 Rerun Artifact Manifest

- Created: 2026-05-05
- Purpose: enumerate the important artifacts that must accompany the Group 1 C2 method-effect rerun PR, especially per-chart score files needed for bootstrap analysis.
- Split: `formal300_50_200_50_seed20260437` evaluation, 200 samples.

## Included Artifact Policy

The original score/bootstrap PR includes final summary reports plus per-chart score evidence for the rerun methods. Raw model responses, logs, and retry attempt text were intentionally excluded from that PR because they are not needed for bootstrap scoring and would make the score-focused review noisy.

Raw API response envelopes were later added as a separate traceability supplement. See `reports/freeze/group1_raw_api_responses_artifact_manifest_20260506.md` for the committed `raw_responses/` directories, file counts, provider formats, and Claude shard notes.

For bootstrap and formal verification, the required unit is one score JSON per chart. These files contain each scored field row with prediction, target, and correctness, so they are sufficient to resample chart-level outcomes.

## GPT-5.4 C-Family Rerun

Run directory:

`formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_gpt54_current_oauth_responses_batched_c2`

Included for each direct GPT-5.4 method:

| Method | Included files | Count |
|---|---|---:|
| `C1_GPT54` | `method_summary.json`, `input_manifest.jsonl`, `canonical_json/*.json`, `scores/*.json` | 1 + 1 + 200 + 200 |
| `C3_GPT54` | `method_summary.json`, `input_manifest.jsonl`, `canonical_json/*.json`, `scores/*.json` | 1 + 1 + 200 + 200 |
| `C4_GPT54` | `method_summary.json`, `input_manifest.jsonl`, `canonical_json/*.json`, `scores/*.json` | 1 + 1 + 200 + 200 |

Included GPT-5.4 summary reports:

- `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_gpt54_current_oauth_responses_batched_c2/reports/combined_gpt54_current_oauth_batched_c2_summary.md`
- `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_gpt54_current_oauth_responses_batched_c2/reports/combined_gpt54_current_oauth_batched_c2_summary.json`

Bootstrap-ready per-chart score tables:

- `reports/freeze/group1_gpt54_cfamily_per_chart_scores_for_bootstrap_20260505.csv`
- `reports/freeze/group1_gpt54_cfamily_per_chart_scores_for_bootstrap_20260505.json`
- `reports/freeze/group1_gpt54_cfamily_per_chart_scores_for_bootstrap_20260505.md`

These tables contain one row per method/chart with explicit `chart_id`, `correct`, `total`, and `accuracy`. They cover `C1_GPT54`, `C2_GPT54_batched_leg`, `C3_GPT54`, and `C4_GPT54`, 200 rows per method, 800 rows total.

## GPT-5.4 C2 Batched Rerun

C2 uses a shorter directory to avoid Windows nested path length issues:

`formal_runs/group1/g1_gpt54_oauth_c2b_20260504`

Included:

| Method | Included files | Count |
|---|---|---:|
| `C2_GPT54_batched_leg` | `method_summary.json`, `input_manifest.jsonl`, `canonical_json/*.json`, `scores/*.json` | 1 + 1 + 200 + 200 |

## Claude C2 Batched Rerun

Combined run directory:

`formal_runs/group1/g1_claude_c2b_combined_20260504`

Included:

| Method | Included files | Count |
|---|---|---:|
| `C2_CLAUDE_batched_leg` | `method_summary.json`, `canonical_json/*.json`, `validation/*.json`, `scores/*.json` | 1 + 200 + 200 + 200 |

The Claude C2 combined directory was materialized from two 100-sample shards according to the combined `method_summary.json`. The extra sample produced when the front shard was stopped is not included.

Included Claude comparison reports:

- `formal_runs/group1/g1_claude_c2b_combined_20260504/reports/claude_c2_batched_vs_original_and_gpt54_summary.md`
- `formal_runs/group1/g1_claude_c2b_combined_20260504/reports/claude_c2_batched_vs_original_and_gpt54_summary.json`

## Freeze-Level Reports

Included:

- `reports/freeze/group1_c2_method_effect_and_model_effect_20260504.md`
- `reports/freeze/group1_c2_method_effect_table_20260504.csv`
- `reports/freeze/group1_c2_rerun_artifact_manifest_20260505.md`

## Excluded From The Score PR

The following were not included in the original score/bootstrap PR:

- `raw_responses/`
- `raw_text/`
- `qa_json/`
- `qa_json_batched/`
- `qa_validation/`
- `logs/`

As of the raw-response supplement, the `raw_responses/` directories are now tracked separately for API-level audit. The remaining extracted text, parser intermediates, diagnostics, and logs are still excluded because they are not required for formal bootstrap or for reproducing the reported field-level scores from the score JSON files.
