# Group 1 scoring-equivalence v2 target build summary

- Run ID: `group1_scoring_equivalence_v2_20260501_r1`
- Charts: 300
- Field target rows: 6084
- Policy rows: 6084
- Risk rows: 1225
- v1 -> v2 changed rows: 513
- Manual review required rows: 0
- Schema valid charts: 300
- Schema invalid charts: 0

## Policy Counts

- `degree_display_rounding`: 566
- `exact_status_value`: 4554
- `normalized_string`: 964

## Diff By Question Field

- `Q4_course_or_radial`: 280
- `Q5_hold_params`: 233

## Risk Type Counts

- `degree_decimal_display_rounding`: 566
- `fix_navaid_format_normalization`: 659

## Notes

This build does not read model predictions and does not rerun OCR/LLM/VLM methods.
It only derives chart-display-aware targets and comparison policies from the existing formal300 target files.
