# C-Family Pilot100 Evidence - 2026-04-29

Status: **pilot100_evidence_available_not_formal_freeze_ready**

| Method | Schema-valid | Score | Accuracy | Retry | Failure note |
|---|---:|---:|---:|---:|---|
| `C1` | 99/100 | 902/2313 | 0.389970 | 7 | KMCW_I36 schema_validation_failed |
| `C2` | 100/100 | 457/2344 | 0.194966 | 9 | none |
| `C3` | 99/100 | 874/2313 | 0.377864 | 5 | KMCW_I36 schema_validation_failed |
| `C4` old | 100/100 | 1265/2344 | 0.539676 | 51 | superseded by output-control fix |
| `C4` current | 100/100 | 1248/2344 | 0.532423 | 0 | after API 524 recovery; no wrapper-like final outputs |

## Interpretation
- C1_C3_failure: Both C1 and C3 fail on KMCW_I36 because Q4_course_or_radial contains course_deg=360, while the canonical schema currently accepts degree values below 360. This is a schema/output-control boundary issue, not a target/scorer issue.
- C4_retry: The previous C4 high-retry issue was reduced from 51 schema retries to 0 after Anthropic-compatible tool transport hardening. See `reports/pilot/c4_output_control_fix_pilot100_20260429.md`. Mechanical unwrap remains disabled.
- C2: C2 is 100/100 schema-valid but low accuracy is method performance, not a freeze blocker by itself.
- formal_decision: C-family has enough evidence for pilot100 feasibility, but not enough for formal freeze until model/tool/retry policy and invalid-output scoring are finalized.

This is external pilot100 feasibility evidence only. It is not formal300 evidence.
