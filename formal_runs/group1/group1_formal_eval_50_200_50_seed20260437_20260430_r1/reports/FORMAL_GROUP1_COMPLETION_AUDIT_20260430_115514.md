# Group 1 Formal Completion Audit

- Created at: `2026-04-30T11:55:18.495295+00:00`
- Base run id: `group1_formal_eval_50_200_50_seed20260437_20260430_r1`
- Expected evaluation samples per method: `200`
- Decision: `formal_group1_outputs_complete_for_reporting_with_method_failures_counted`
- Hard blocker count: `0`

## Method Table

| method | status | total | schema_valid | scored | method_failures | correct | score_total | accuracy | retries | qa_retries |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A1 | complete | 200 | 200 | 200 | 0 | 1184 | 4052 | 0.292201 | 0 | None |
| A2 | complete | 200 | 200 | 200 | 0 | 916 | 4052 | 0.226061 | 0 | None |
| B1 | complete | 200 | 200 | 200 | 0 | 1104 | 4052 | 0.272458 | 10 | None |
| B1_prime | complete | 200 | 200 | 200 | 0 | 1303 | 4052 | 0.321570 | 16 | None |
| B1_prime_link | complete_with_method_failures | 200 | 185 | 185 | 15 | 718 | 3683 | 0.194950 | 51 | None |
| C1 | complete | 200 | 200 | 200 | 0 | 1503 | 4052 | 0.370928 | 16 | None |
| C2 | complete | 200 | 200 | 200 | 0 | 970 | 4052 | 0.239388 | None | 18 |
| C3 | complete_with_method_failures | 200 | 196 | 196 | 4 | 1522 | 3976 | 0.382797 | 27 | None |
| C4 | complete | 200 | 200 | 200 | 0 | 1624 | 4052 | 0.400790 | 3 | None |
| D_SFT | complete_with_method_failures | 200 | 184 | 184 | 16 | 2739 | 3724 | 0.735499 | None | None |

## Interpretation Notes

- Accuracy is the field-level scorer's `correct / total` over schema-valid scored samples.
- Parse/schema/API failures are retained as method failures; they are not silently repaired or counted as correct.
- C2 is combined from the interrupted source C2 slice plus all C2 continuation chunks.
- The source C2 slice has no `method_summary.json`; its 14 scored samples are reconstructed from saved score and validation artifacts.
- A hard blocker means the run package is structurally incomplete, for example missing summaries, missing score totals, duplicated sample ids, or wrong sample count.

## Failure Counts

- `A1`: 0
- `A2`: 0
- `B1`: 0
- `B1_prime`: 0
- `B1_prime_link`: 15
- `C1`: 0
- `C2`: 0
- `C3`: 4
- `C4`: 0
- `D_SFT`: 16
