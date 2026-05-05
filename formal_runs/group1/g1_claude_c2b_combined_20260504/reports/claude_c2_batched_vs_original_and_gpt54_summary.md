# Group 1 C2 Claude Batched Rerun Summary

- Created UTC: 2026-05-04T06:28:13.375323+00:00
- Split: formal300_50_200_50_seed20260437 evaluation, 200 samples
- Variant rerun: Claude C2 half-changed method, q0 leg count plus one tool call per leg that emits the six QA fields
- API token values are not recorded in artifacts.

## Results

| Run | Method/model | Scored | Correct/Total | Accuracy | Saved QA calls | Saved QA fields | QA schema retries |
|---|---:|---:|---:|---:|---:|---:|---:|
| Claude original C2 | Claude Sonnet 4.5 | 200/200 | 970/4052 | 23.94% | n/a | n/a | 18 |
| Claude batched C2 | Claude Sonnet 4.5 via Anthropic-compatible API | 200/200 | 1397/4052 | 34.48% | 881 | 4286 | 0 |
| GPT-5.4 batched C2 | gpt-5.4 via current OAuth Responses API | 200/200 | 1884/4052 | 46.50% | 809 | 3854 | 0 |

## Deltas

- Same model / method effect: Claude batched C2 minus Claude original C2 = +10.54 pp (+427 correct fields).
- Same method / model effect: GPT-5.4 batched C2 minus Claude batched C2 = +12.02 pp (+487 correct fields).
- Non-isolated combined difference: GPT-5.4 batched C2 minus Claude original C2 = +22.56 pp (+914 correct fields).

## Integrity

- Combined Claude batched summary: formal_runs/group1/g1_claude_c2b_combined_20260504/C2_CLAUDE_batched_leg/method_summary.json
- Unique chart IDs: 200/200; duplicate chart IDs: []
- Unique sample IDs: 200/200; duplicate sample IDs: []
- Total fields: 4052; matches expected 4052: True
- Front/back overlap: []
