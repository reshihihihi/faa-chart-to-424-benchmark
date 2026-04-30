# Group 1 Formal Freeze Package

- Package id: `group1_formal_freeze_20260430_r1`
- Created at: `2026-04-30T15:58:28.769300+00:00`
- Formal run id: `group1_formal_eval_50_200_50_seed20260437_20260430_r1`
- Split id: `formal300_50_200_50_seed20260437`
- Evaluation samples: `200`
- Completion decision: `formal_group1_outputs_complete_for_reporting_with_method_failures_counted`
- Hard blockers: `0`

## Freeze Steps

1. **sample and split**: frozen
   - The formal reporting split is fixed to the 200-sample evaluation subset of formal300_50_200_50_seed20260437.
2. **schema target scorer**: frozen
   - Canonical schema, proxy targets, field scorer, and invalid-output scoring policy are fixed by path and sha256.
3. **method boundaries**: frozen
   - Each method's allowed inputs and forbidden leakage sources are fixed for Group 1 reporting.
4. **model and call parameters**: frozen
   - OCR engines, LLM/VLM identities, D-SFT checkpoint role, deterministic settings, and retry policy are fixed for this run.
5. **runner prompt rule aggregator**: frozen
   - Runners, prompts, rules, link builder, QA aggregator, and D-SFT inference prompt are fixed by path and sha256.
6. **results and failure accounting**: frozen
   - Final method table, C2 combination policy, coverage, method failures, and field accuracy are fixed from the timestamped completion audit.
7. **freeze package**: generated
   - This package is the reporting source for Group 1 formal results before moving to later experiment groups.

## Method Boundaries

| method | formal definition | model | runner / logic |
|---|---|---|---|
| `A1` | OCR-1 full-chart text -> deterministic rules -> canonical JSON | none | `scripts/run_group1_formal_manifest.py + docs/group1_a1_a2_rules_candidate_v1.md` |
| `A2` | OCR-2 full-chart text -> deterministic rules -> canonical JSON | none | `scripts/run_group1_formal_manifest.py + docs/group1_a1_a2_rules_candidate_v1.md` |
| `B1` | OCR-1 full-chart text -> LLM -> canonical JSON | gpt-5.4 | `scripts/run_group1_formal_manifest.py` |
| `B1_prime` | OCR-1 full-chart text -> deterministic field candidates -> LLM -> canonical JSON | gpt-5.4 | `scripts/run_group1_formal_manifest.py` |
| `B1_prime_link` | OCR-1 full-chart text -> deterministic field candidates -> deterministic field-to-leg links -> LLM -> canonical JSON | gpt-5.4 | `scripts/run_group1_formal_manifest.py + scripts/build_field_to_leg_links.py` |
| `C1` | full chart image -> VLM -> canonical JSON | claude-sonnet-4-5-20250929 | `scripts/run_group1_formal_manifest.py` |
| `C2` | full chart image -> fixed per-field QA prompts -> deterministic aggregator -> canonical JSON | claude-sonnet-4-5-20250929 | `scripts/run_group1_formal_manifest.py + scripts/aggregate_c2_qa_candidate.py` |
| `C3` | full chart image -> questionnaire-style VLM extraction -> canonical JSON | claude-sonnet-4-5-20250929 | `scripts/run_group1_formal_manifest.py` |
| `C4` | full chart image + OCR-1 full-chart text -> VLM -> canonical JSON | claude-sonnet-4-5-20250929 | `scripts/run_group1_formal_manifest.py` |
| `D_SFT` | full chart image -> SFT VLM checkpoint -> canonical JSON | Qwen/Qwen2-VL-2B-Instruct + QLoRA adapter checkpoint | `scripts/d_sft_infer_qwen2vl_lora.py` |

## Formal Result Table

| method | status | total | schema_valid | scored | failures | correct | score_total | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `A1` | complete | 200 | 200 | 200 | 0 | 1184 | 4052 | 0.292201 |
| `A2` | complete | 200 | 200 | 200 | 0 | 916 | 4052 | 0.226061 |
| `B1` | complete | 200 | 200 | 200 | 0 | 1104 | 4052 | 0.272458 |
| `B1_prime` | complete | 200 | 200 | 200 | 0 | 1303 | 4052 | 0.321570 |
| `B1_prime_link` | complete_with_method_failures | 200 | 185 | 185 | 15 | 718 | 3683 | 0.194950 |
| `C1` | complete | 200 | 200 | 200 | 0 | 1503 | 4052 | 0.370928 |
| `C2` | complete | 200 | 200 | 200 | 0 | 970 | 4052 | 0.239388 |
| `C3` | complete_with_method_failures | 200 | 196 | 196 | 4 | 1522 | 3976 | 0.382797 |
| `C4` | complete | 200 | 200 | 200 | 0 | 1624 | 4052 | 0.400790 |
| `D_SFT` | complete_with_method_failures | 200 | 184 | 184 | 16 | 2739 | 3724 | 0.735499 |

## Interpretation

- Field accuracy is `correct / total` over schema-valid scored samples.
- Parse, schema, API, and missing-prediction failures are retained as method failures and must be reported with coverage.
- C2 is frozen as a combined result from the interrupted source slice plus continuation chunks; the combined audit report is the reporting source of truth.
- D-SFT accuracy is not comparable without its 184/200 scored coverage being reported beside it.
- This package supersedes the 2026-04-29 pre-run freeze manifest for reporting the completed formal Group 1 run.

## Output Files

- `manifest_json`: `reports/freeze/group1_formal_freeze_package_20260430_r1.json`
- `markdown`: `reports/freeze/group1_formal_freeze_package_20260430_r1.md`
- `method_boundary_csv`: `reports/freeze/group1_formal_method_boundaries_20260430_r1.csv`
- `result_table_csv`: `reports/freeze/group1_formal_result_table_20260430_r1.csv`
