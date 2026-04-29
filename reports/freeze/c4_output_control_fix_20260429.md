# C4 Output Control Fix - 2026-04-29

Status: **c4_output_control_fix_recorded_not_formal300_run**

C4 pilot100 retries were mainly caused by provider/tool transport wrappers, not by method-boundary violations. The parser now permits only narrow transport-wrapper normalization for `{ "$PARAMETER_NAME": <canonical object> }` and `{ "chart": <canonical object> }`, guarded by the presence of top-level `chart_id`, `procedure`, and `missed_approach`.

This does not change field values, does not add missing fields, does not move `status/value`, and does not use target/scorer/CIFP. Formal300 has not been run.
