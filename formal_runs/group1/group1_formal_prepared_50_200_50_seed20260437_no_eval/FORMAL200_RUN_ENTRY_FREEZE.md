# Group 1 Formal200 Run Entry Freeze

Status: prepared, not run.

This package freezes the entry point for the next Group 1 formal evaluation decision. It does not contain model predictions or formal scores.

Frozen entry:
- split_candidate_id: `formal300_50_200_50_seed20260437`
- split role: `evaluation`
- evaluation sample count: 200
- run_id: `group1_formal_prepared_50_200_50_seed20260437_no_eval`
- methods: `A1`, `A2`, `B1`, `B1_prime`, `B1_prime_link`, `C1`, `C2`, `C3`, `C4`, `D_SFT`

Frozen files:
- split manifest: `benchmark_exports/derived/v2/formal300/split_candidates/split_50_200_50_seed20260437/sample_manifest_50_200_50_seed20260437.jsonl`
- split policy: `benchmark_exports/derived/v2/formal300/split_candidates/split_50_200_50_seed20260437/SPLIT_POLICY_50_200_50_seed20260437.md`
- run plan: `formal_runs/group1/group1_formal_prepared_50_200_50_seed20260437_no_eval/run_plan.json`
- scoring manifest: `formal_runs/group1/group1_formal_prepared_50_200_50_seed20260437_no_eval/scoring_manifest.jsonl`
- readiness audit: `formal_runs/group1/group1_formal_prepared_50_200_50_seed20260437_no_eval/reports/formal200_manifest_readiness_audit.json`

Hashes:
- split manifest sha256: `d15f0ab36a223dd60705f2231643254925dbb1783295f686d21146c57a6ee468`
- split policy sha256: `d1a927e1e76e5be788b5f67b68749bcf89b0b6e977296d73327cbf80346aede7`
- run plan sha256: `8c1230cf641ae320b9a3cfd7c1a4b7a19e215f54fefaa501197d20ffbde2f621`
- scoring manifest sha256: `4eb885e60ae2188360fecc05ce3e018599a01e201ff8616e9e750746042a9ce1`
- readiness audit sha256: `a12547543d0f897103c9fb49d2464e154ba99de35ec3129a0cf477da30b8d81a`

Readiness result:
- `ready_for_user_decision_to_run`: true
- audit error count: 0
- formal evaluation has not been run.

Use policy:
- Use this run package only after the user explicitly decides to run the formal evaluation.
- Do not use the superseded 75-sample run as a final paper result.
- Do not modify the evaluation sample set based on method scores or failures.
