# Group 1 Raw API Response Artifact Manifest

- Created: 2026-05-06
- Purpose: add the raw API response envelopes for the Group 1 GPT-5.4 and Claude reruns, after the score, summary, and per-chart bootstrap artifacts were submitted separately.
- Split: `formal300_50_200_50_seed20260437` evaluation, 200 formal charts.
- Related score artifact manifest: `reports/freeze/group1_c2_rerun_artifact_manifest_20260505.md`

## Scope

This supplement commits the API response objects that were intentionally left out of the earlier score/bootstrap PR to keep that PR focused on chart-level scoring evidence. These files are low-level traceability evidence for the same reruns:

- GPT-5.4 direct methods `C1_GPT54`, `C3_GPT54`, and `C4_GPT54`
- GPT-5.4 half-modified C2 method `C2_GPT54_batched_leg`
- Claude half-modified C2 method `C2_CLAUDE_batched_leg`

The raw files are not the source of the bootstrap resampling itself. Bootstrap should continue to use the per-chart score tables and score JSON files already tracked for the formal results.

## Included Raw Response Directories

| Provider | Method | Raw response path | Shape | Files | Bytes | Notes |
|---|---|---|---|---:|---:|---|
| GPT-5.4 | `C1_GPT54` | `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_gpt54_current_oauth_responses_batched_c2/C1_GPT54/raw_responses/` | one direct chart-level response per chart plus attempt copies | 401 | 6,449,684 | 200 final files, 201 attempt files; one schema retry is represented by the extra attempt file. |
| GPT-5.4 | `C3_GPT54` | `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_gpt54_current_oauth_responses_batched_c2/C3_GPT54/raw_responses/` | one direct chart-level response per chart plus attempt copies | 400 | 6,231,200 | 200 final files, 200 attempt files. |
| GPT-5.4 | `C4_GPT54` | `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_gpt54_current_oauth_responses_batched_c2/C4_GPT54/raw_responses/` | one direct chart-level response per chart plus attempt copies | 400 | 6,433,600 | 200 final files, 200 attempt files. |
| GPT-5.4 | `C2_GPT54_batched_leg` | `formal_runs/group1/g1_gpt54_oauth_c2b_20260504/C2_GPT54_batched_leg/raw_responses/` | chart subdirectories containing `q0_leg_count` and per-leg `batched_leg_answers` responses | 1,618 | 19,526,906 | 809 final call files and 809 attempt files. The shorter run directory avoids Windows nested path length problems. |
| Claude | `C2_CLAUDE_batched_leg` first shard | `formal_runs/group1/g1_claude_c2b_20260504/C2_CLAUDE_batched_leg/raw_responses/` | chart subdirectories containing `q0_leg_count` and per-leg `batched_leg_answers` responses | 930 | 1,399,714 | 465 final call files and 465 attempt files. This raw directory has 101 chart subdirectories because `KABI_R17L` was also started before the front shard stopped. The front shard `method_summary.json` and `input_manifest.jsonl` track the intended 100 scored rows. |
| Claude | `C2_CLAUDE_batched_leg` second shard | `formal_runs/group1/g1_claude_c2b_100_199_20260504/C2_CLAUDE_batched_leg/raw_responses/` | chart subdirectories containing `q0_leg_count` and per-leg `batched_leg_answers` responses | 840 | 1,250,816 | 420 final call files and 420 attempt files. This shard supplies the formal `KABI_R17L` row and the remaining second-half rows. |

Total raw response files: 4,589 files, 41,291,920 bytes.

## Included Companion Files

The GPT-5.4 method summaries and input manifests were already tracked with the earlier score artifacts. This supplement adds the same minimal companions for the Claude raw-response shard directories, because those shard directories are the only location where the Claude raw API envelopes exist:

- `formal_runs/group1/g1_claude_c2b_20260504/C2_CLAUDE_batched_leg/input_manifest.jsonl`
- `formal_runs/group1/g1_claude_c2b_20260504/C2_CLAUDE_batched_leg/method_summary.json`
- `formal_runs/group1/g1_claude_c2b_100_199_20260504/C2_CLAUDE_batched_leg/input_manifest.jsonl`
- `formal_runs/group1/g1_claude_c2b_100_199_20260504/C2_CLAUDE_batched_leg/method_summary.json`

These four files add 258,174 bytes and document the intended shard membership and shard-level scoring summaries.

## Provider Formats

GPT-5.4 raw files are OpenAI Responses API objects. Sample files expose fields such as `id`, `model`, `output`, `tools`, `reasoning`, `status`, `usage`, and `tool_usage`, with `model` recorded as `gpt-5.4`.

Claude raw files are Anthropic message objects. Sample files expose fields such as `id`, `content`, `model`, `role`, `stop_reason`, `type`, and `usage`, with `model` recorded as `claude-sonnet-4-5-20250929`.

## Reconstruction Notes

For formal scoring and bootstrap, use the already tracked formal outputs:

- GPT-5.4 score JSON: the `scores/*.json` files under each GPT-5.4 method directory.
- Claude score JSON: `formal_runs/group1/g1_claude_c2b_combined_20260504/C2_CLAUDE_batched_leg/scores/*.json`.
- Bootstrap-ready table: `reports/freeze/group1_gpt54_cfamily_per_chart_scores_for_bootstrap_20260505.csv`.

For raw-response audit:

- GPT-5.4 direct methods can be audited directly from their method-level `raw_responses/` directories.
- GPT-5.4 C2 can be audited from the short-path C2 run directory.
- Claude C2 should be audited from the two shard directories above. The combined Claude directory intentionally has the merged formal `canonical_json/`, `validation/`, and `scores/` outputs but no `raw_responses/` directory.
- If a Claude raw chart appears in both shards, prefer the second shard for formal combined reconstruction. The only overlapping raw chart directory found here is `KABI_R17L`.

## Not Included

The following adjacent artifacts remain excluded from this supplement:

- `raw_text/`
- `qa_json/`
- `qa_json_batched/`
- `qa_validation/`
- `aggregation_diagnostics/`
- `qa_call_diagnostics/`
- `logs/`

Those files are extracted text, parser intermediates, diagnostics, or run logs. They are useful for local debugging, but the requested original API envelopes are the `raw_responses/` JSON files committed here.

## Local Integrity Checks

Checks run before commit:

- Raw response count and size: 4,589 files, 41,291,920 bytes.
- Nested-path check: no `raw_responses/raw_responses` directories.
- Claude shard overlap check: one overlapping raw chart directory, `KABI_R17L`.
- Secret scan targets: raw response JSON plus companion shard summaries/manifests.
