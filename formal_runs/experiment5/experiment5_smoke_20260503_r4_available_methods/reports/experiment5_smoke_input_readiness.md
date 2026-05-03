# Experiment 5 smoke20 r2 input readiness

- run_id: `experiment5_smoke_20260503_r4_available_methods`
- created_at_utc: `2026-05-03T05:34:10.251156+00:00`
- smoke20_count: 20
- source_view_hash_matches_summary: True
- candidate_schema: `E:\experiment3\github_work\faa-chart-to-424-benchmark-experiment5\schemas\experiment5_roi_field_candidates.schema.v1.json`
- candidate_validation_error_rows: 0
- candidate_unknown_source_section_count: 0
- candidate_cross_region_snippet_count: 0
- ready_for_smoke_b3_b4: True

## Region profiles prepared

| profile | rows |
|---|---:|
| `PD` | 20 |
| `T` | 20 |
| `TPD` | 20 |

## Notes

- r2 uses a current Experiment 5 source-view summary snapshot to close source-view provenance.
- r2 candidates are generated per region and then merged; snippets must not cross region markers.
- Human gold inputs are still required before A3/B2/G methods.
