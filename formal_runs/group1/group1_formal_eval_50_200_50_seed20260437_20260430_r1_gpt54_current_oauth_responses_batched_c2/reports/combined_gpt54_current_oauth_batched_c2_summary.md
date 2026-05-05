# Group 1 GPT-5.4 Current OAuth Rerun Summary

Created: 2026-05-04T05:02:53.741111+00:00

Source split: `formal300_50_200_50_seed20260437/evaluation`; samples: `200`.
Model/transport: `gpt-5.4` through streaming Responses API tool calls.

| Method | Schema valid | Scored | Correct/Total | Accuracy | Extra |
|---|---:|---:|---:|---:|---|
| `C1_GPT54` | 200/200 | 200 | 1201/4052 | 0.296397 | schema retries 1 |
| `C2_GPT54_batched_leg` | 200/200 | 200 | 1884/4052 | 0.464956 | QA calls saved 809; fields 3854 |
| `C3_GPT54` | 200/200 | 200 | 1218/4052 | 0.300592 | schema retries 0 |
| `C4_GPT54` | 200/200 | 200 | 1757/4052 | 0.433613 | schema retries 0 |

Artifact checks:
- `C1_GPT54`: canonical=200, scores=200, parse_errors=0, qa_errors=0, qa_invalid=0
- `C2_GPT54_batched_leg`: canonical=200, scores=200, parse_errors=0, qa_errors=0, qa_invalid=0
- `C3_GPT54`: canonical=200, scores=200, parse_errors=0, qa_errors=0, qa_invalid=0
- `C4_GPT54`: canonical=200, scores=200, parse_errors=0, qa_errors=0, qa_invalid=0

Main run dir: `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_gpt54_current_oauth_responses_batched_c2`
C2 run dir: `formal_runs/group1/g1_gpt54_oauth_c2b_20260504`
