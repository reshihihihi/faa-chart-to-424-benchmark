# Group 1 Final Pre-Freeze Optimization Report

Created: 2026-04-29

Status: final pre-freeze method-mechanism hardening completed; not formal freeze.

## Scope

This pass addresses remaining mechanism-level issues before preparing the formal freeze package for Experiment Group 1. It does not tune prompts or rules against pilot100 scores, does not add target/scorer/CIFP information, and does not change method boundaries.

In scope:

- B1/C1/C3/C4/B1_prime output stability and status/value hardening.
- C4 schema-output stability.
- A1/A2 source-agnostic schema-safety rule hardening.
- C2 QA/aggregator audit.
- B1_prime final candidate decision.

Out of scope:

- Formal300 sample/target freeze.
- Formal model/provider/max-token freeze.
- D-SFT r2 training.
- Any sample-specific repair or target-driven score optimization.

## Changes Made

### Prompt Output Stability

Updated candidate prompts:

- `prompts/paper_v2/b1_ocr_to_canonical_pilot10.zh_v1_candidate.md`
- `prompts/paper_v2/b1_prime_ocr_field_candidates_to_canonical_pilot10.zh_v0_candidate.md`
- `prompts/paper_v2/c1_image_to_canonical_pilot10.zh_v1_candidate.md`
- `prompts/paper_v2/c3_questionnaire_pilot10.zh_v1_candidate.md`
- `prompts/paper_v2/c4_image_ocr_to_canonical_pilot10.zh_v1_candidate.md`

Added source-agnostic hardening:

- copy `chart_id`, `airport`, `approach_ident`, and `chart_name` exactly from input metadata;
- keep aviation values out of `status`;
- require non-present answers to have `value = null`;
- require present answers to have schema-valid values;
- enforce Q1 fix ident length/facility-word guard;
- enforce degree range `0.0` through `359.9`, including `360 -> 359.9`;
- enforce `leg_count` consistency and one-based `leg_index`.

### Output-Control Policy

Updated:

- `configs/output_control_policy.md`
- `configs/parser_repair_policy.md`

Added the Anthropic-compatible tool-use candidate policy for C1/C2/C3/C4. This records the actual candidate output path used by recent C-family validation:

- C1/C4: `emit_canonical_json` with `schemas/missed_approach_leg.schema.json`
- C3: `emit_questionnaire_json` with `schemas/c3_questionnaire.schema.candidate.json`
- C2: one `emit_qa_answer` tool call per fixed QA question

Parser repair remains forbidden.

### A1/A2 Rules

Updated:

- `scripts/run_a1_a2_rules_pilot10.py`
- `docs/group1_a1_a2_rules_candidate_v1.md`

Added a schema-safe degree helper:

- OCR degree `360` becomes `359.9`;
- other out-of-range degree values are not forced into schema-valid values;
- A1 and A2 still use the same rule runner and differ only by OCR source.

### C2 QA/Aggregator

Updated:

- `docs/group1_c2_qa_aggregator_candidate_v1.md`

No target-aware prompt or aggregator changes were made. The current candidate already enforces:

- image-only QA calls;
- q0 controls follow-up leg questions;
- one fixed question per model call;
- tool-use output control;
- deterministic aggregation by copying saved QA JSON;
- malformed/missing QA answers become `unknown/null`;
- no OCR, target, scorer, CIFP, or field candidates.

### B1_prime

Updated:

- `reports/pilot/b1prime_method_decision_20260428.md`
- `docs/method_registry.md`

No new matcher repair was added. B1_prime remains candidate / pre-freeze only. Field-to-leg linking stays assigned to B1_link / Experiment Group 5.

## Validation

### Static Checks

Passed:

- Python compile:
  - `scripts/run_a1_a2_rules_pilot10.py`
  - `scripts/run_group1_pilot10_gpt54.py`
  - `scripts/run_c2_qa_pilot10.py`
  - `scripts/aggregate_c2_qa_candidate.py`
  - `scripts/model_clients.py`
  - `scripts/c3_questionnaire_to_canonical.py`
- JSON load checks:
  - `configs/prompt_manifest.json`
  - `configs/model_config_manifest.json`
  - `configs/frozen_experiment_manifest.json`
  - `configs/ocr_source_manifest.json`
  - registered schemas

### A1/A2 Pilot100 Deterministic Recheck

Run:

```text
E:\experiment3\try_B1_B1'\predictions\pilot100_group1_a1_a2_rules_prefreeze_final_20260429_r1
```

Result:

| Method | Schema-valid | Parser repair | Failure | Score |
|---|---:|---:|---:|---:|
| A1 | 100/100 | 0 | 0 | 741/2344 = 0.316126 |
| A2 | 100/100 | 0 | 0 | 521/2344 = 0.222270 |

Interpretation: the schema-safety rule hardening did not change the aggregate A1/A2 pilot100 result and did not introduce schema failures.

### B1 Pilot100 Recheck

Initial 100-run command was interrupted by command timeout after saving 86 completed samples. Remaining 14 were run under a separate run id. Combined summary:

```text
E:\experiment3\try_B1_B1'\reports\pilot100_group1_b1_prefreeze_final_20260429_combined_summary.json
```

Combined result:

| Method | Schema-valid | Parser repair | Schema retries | Score |
|---|---:|---:|---:|---:|
| B1 | 100/100 | 0 | 9 | 728/2344 = 0.310580 |

Run roots:

```text
E:\experiment3\try_B1_B1'\predictions\pilot100_group1_b1_gpt54_prefreeze_final_20260429_r1
E:\experiment3\try_B1_B1'\predictions\pilot100_group1_b1_gpt54_prefreeze_final_20260429_remaining14_r1
```

Interpretation: B1 remains mechanically runnable and schema-valid under OpenAI-compatible forced tool call. Score is not used for further prompt tuning.

### C4 Focused Smoke

Run:

```text
E:\experiment3\try_B1_B1'\predictions\pilot5_group1_c4_claude_prefreeze_final_20260429_r1
```

Result:

| Method | Schema-valid | Parser repair | Schema retries | Score |
|---|---:|---:|---:|---:|
| C4 | 5/5 | 0 | 2 | 52/101 = 0.514851 |

Interpretation: C4 remains schema-valid with Anthropic tool-use output control. Retry has not disappeared, so C4's formal rerun policy must still explicitly allow at most one schema-only retry or accept failures without retry.

### C1/C3 Focused Smoke

Run:

```text
E:\experiment3\try_B1_B1'\predictions\pilot3_group1_c1_c3_claude_prefreeze_final_20260429_r1
```

Result:

| Method | Schema-valid | Parser repair | Schema retries | Score |
|---|---:|---:|---:|---:|
| C1 | 3/3 | 0 | 0 | 25/63 = 0.396825 |
| C3 | 3/3 | 0 | 0 | 23/63 = 0.365079 |

Interpretation: the image-only direct canonical path and questionnaire path were not broken by prompt hardening.

### Interrupted C1/C3/C4 Pilot20 Attempt

Run root:

```text
E:\experiment3\try_B1_B1'\predictions\pilot20_group1_c1_c3_c4_claude_prefreeze_final_20260429_r1
```

This command timed out before summary generation. Partial artifacts were retained but are not used as a primary validation result:

- C1 canonical outputs: 3
- C3 canonical outputs: 2
- C4 canonical outputs: 2

## Remaining Before Formal Freeze

The final optimization pass is complete, but these are still not frozen:

- formal300 sample manifest and targets;
- formal scorer implementation and hash;
- final model/provider/max-token settings;
- final OCR artifact policy and formal OCR run paths;
- final prompt freeze decision and hashes;
- formal retry/rerun policy;
- C4 decision on whether one schema-only retry is allowed;
- C2 full formal-run feasibility cost policy;
- B1_prime inclusion decision.

Recommended freeze decision:

- Freeze A1, A2, B1, C1, C2, C3, C4 method mechanisms if the formal freeze accepts the current retry policy.
- Keep B1_prime out of the formal main leaderboard unless the paper explicitly labels it candidate/diagnostic.
- Do not run further pilot100-driven prompt tuning after this report.
