# Superseded Diagnostic Run

Run: `group1_formal_eval_20260430_r1`

Status:
- Superseded for formal paper conclusions.
- Retained as diagnostic evidence only.

Reason:
- The run used the earlier materialized `formal300` split with 75 evaluation samples.
- That 75-sample evaluation subset produced unexpectedly high D-SFT accuracy compared with prior pilot100 evidence.
- A score-blind 50/200/50 split candidate has now been generated to make the main evaluation larger and less sensitive to a small subset.

Use policy:
- Do not report this run as the final Group 1 formal result.
- Do not use its method scores, failures, or per-sample outcomes to choose the new split.
- It may be cited internally as evidence that split-size/distribution audit was needed.

Next formal evaluation should use:
- Candidate split id: `formal300_50_200_50_seed20260437`
- Main evaluation size: 200 samples
