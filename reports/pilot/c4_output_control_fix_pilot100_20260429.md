# C4 Output-Control Fix Pilot100 - 2026-04-29

Status: **validated candidate, not formal frozen**

## What Changed

- Changed only `scripts/model_clients.py` transport/tool-use handling.
- The C4 method boundary did not change: full chart image + OCR-1 text -> Claude VLM/MLLM -> canonical JSON.
- No target, scorer, CIFP, field_candidates, or field-to-leg links were added to C4 inference.
- No mechanical unwrap policy was enabled.

## Result

| Run | Schema-valid | Schema retry | Parser repair | Score | Note |
|---|---:|---:|---:|---:|---|
| old C4 pilot100 | 100/100 | 51 | 0 | 1265/2344 = 0.539676 | previous high retry baseline |
| new main run | 99/100 | 0 | 0 | 1237/2325 = 0.532043 | one API 524 network failure, no schema retry |
| API recovery sample | 1/1 | 0 | 0 | 11/19 = 0.578947 | KAFO_R16 only, transport recovery |
| combined after API recovery | 100/100 | 0 | 0 | 1248/2344 = 0.532423 | pilot100 feasibility only |

## Wrapper Audit

- Wrapper-like final outputs: 0
- This means no observed `$PARAMETER_NAME` / `chart` outer wrapper in the final outputs after the fix.

## Decision

The previous C4 high-retry blocker is resolved for pilot100. Keep this as the current C4 output-control candidate. Do not enable mechanical unwrap unless future larger/formal runs show the wrapper problem again, and if enabled it must be pre-registered before formal evaluation.

This is still not a formal300 result.
