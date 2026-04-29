# Group 1 non-B1prime audit-fix pilot10 report

Created: 2026-04-28

Scope: A1, A2, B1, C1, C2, C3, C4 only. B1prime was intentionally not modified or rerun in this report.

## What changed

1. B1/C1/C3/C4 prompts now include stricter schema-bound output rules:
   - no nested JSON as strings;
   - no concrete value in `status`;
   - no string `unknown` in `value`; use `status=unknown`, `value=null`;
   - leg count must agree with leg array length when present.
2. A1/A2 rules spec now requires per-sample OCR text hashes, OCR artifact manifest hashes, and the same rule runner/spec for both methods.
3. A1/A2 runner now writes method-boundary metadata, OCR artifact manifest hashes, and per-sample OCR text hashes into `run_manifest.json`.
4. B1/C1/C3/C4 runner now writes method-boundary metadata and per-sample image/OCR input hashes into `run_manifest.json`.
5. C2 QA runner/aggregator spec now explicitly records q0-first leg-count policy, no target/scorer/OCR/field-candidate use, QA artifact layout, and missing-answer handling.
6. C2 runner now writes per-sample image hashes and QA artifact layout into `run_manifest.json`.
7. C2 aggregator diagnostics now record no semantic repair and no target/scorer use.

## Pilot10 runs

| Method | Run id | Schema-valid | Scored | Accuracy | Retry / repair | Failures |
|---|---|---:|---:|---:|---:|---:|
| A1 | `pilot10_group1_a1_a2_rules_auditfix_20260428_r2` | 10/10 | 10/10 | 0.281818 | n/a | 0 |
| A2 | `pilot10_group1_a1_a2_rules_auditfix_20260428_r2` | 10/10 | 10/10 | 0.200000 | n/a | 0 |
| B1 | `pilot10_group1_b1_gpt54_toolcall_auditfix_ordinary_ocr_20260428_r4` | 10/10 | 10/10 | 0.368182 | 0 schema retry, 0 parser repair | 0 |
| C1 | `pilot10_group1_c1_c3_c4_claude_tooluse_auditfix_ordinary_ocr_20260428_r3` | 10/10 | 10/10 | 0.495455 | 0 schema retry, 0 parser repair | 0 |
| C3 | `pilot10_group1_c1_c3_c4_claude_tooluse_auditfix_ordinary_ocr_20260428_r3` | 10/10 | 10/10 | 0.427273 | 1 schema retry, 0 parser repair | 0 |
| C4 | `pilot10_group1_c1_c3_c4_claude_tooluse_auditfix_ordinary_ocr_20260428_r3` | 10/10 | 10/10 | 0.531818 | 6 schema retries, 0 parser repair | 0 |
| C2 | `pilot10_group1_c2_claude_tooluse_qa_auditfix_ordinary_ocr_20260428_r4` | 10/10 | 10/10 | 0.281818 | 1 QA schema retry, 0 parser repair | 0 |

## Interpretation

All non-B1prime methods ran through pilot10 with schema-valid final outputs and no parser repair. This confirms the corrected output-control and artifact-recording path is operational.

The remaining issue is not runability but freeze readiness:

- A1/A2 rules are still candidate rules, not formal frozen.
- B1 is stable on pilot10 after stronger prompt/tool-call output control.
- C1/C3/C4 are stable on pilot10, but C4 still required 6 schema-only retries and should be checked on pilot100 before formal freeze.
- C2 is operational and now auditable, but it remains the heaviest method: 232 QA calls for 10 charts.

## Artifact roots

- `predictions/pilot10_external/pilot10_group1_a1_a2_rules_auditfix_20260428_r2`
- `predictions/pilot10_external/pilot10_group1_b1_gpt54_toolcall_auditfix_ordinary_ocr_20260428_r4`
- `predictions/pilot10_external/pilot10_group1_c1_c3_c4_claude_tooluse_auditfix_ordinary_ocr_20260428_r3`
- `predictions/pilot10_external/pilot10_group1_c2_claude_tooluse_qa_auditfix_ordinary_ocr_20260428_r4`
