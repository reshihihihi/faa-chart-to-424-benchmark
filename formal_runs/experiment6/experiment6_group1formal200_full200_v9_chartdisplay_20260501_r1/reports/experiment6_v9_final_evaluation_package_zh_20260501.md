# 实验组6 v9 最终评估整理报告

## 1. 评估口径

本轮使用 v9 chart-display candidate。PR #25 的显示值等价功能已经作为前置规范被消除，不再作为实验组6的新方法。

本报告补齐了 control/oracle、自检审计、retry 汇总和分层统计。

## 2. 主结果与 control/oracle

| method | total | valid | invalid | binary acc | balanced acc | positive accept | false alarm | negative reject | miss rate | norm field overlap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| control_all_accept | 400 | 400 | 0 | 50.0% | 50.0% | 100.0% | 0.0% | 0.0% | 100.0% | 0.0% |
| control_all_reject | 400 | 400 | 0 | 50.0% | 50.0% | 0.0% | 100.0% | 100.0% | 0.0% | 18.0% |
| control_oracle_label | 400 | 400 | 0 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 0.0% | 100.0% |
| control_v0_candidate_integrity | 400 | 400 | 0 | 50.0% | 50.0% | 100.0% | 0.0% | 0.0% | 100.0% | 0.0% |
| V1_OCR_text_chartdisplay_v2 | 400 | 400 | 0 | 49.0% | 49.0% | 69.5% | 30.5% | 28.5% | 71.5% | 16.5% |
| V2_direct_image_policyv3_chartdisplay_v2 | 400 | 400 | 0 | 56.8% | 56.8% | 40.5% | 59.5% | 73.0% | 27.0% | 25.0% |
| V3_C4_group1v2_neutralized | 400 | 400 | 0 | 50.0% | 50.0% | 0.0% | 100.0% | 100.0% | 0.0% | 41.5% |
| V3_D_SFT_group1v2_neutralized | 400 | 370 | 30 | 48.2% | 51.9% | 3.8% | 96.2% | 100.0% | 0.0% | 81.2% |
| V4_C4_tolerant_chartdisplay_v2 | 400 | 400 | 0 | 50.5% | 50.5% | 61.5% | 38.5% | 39.5% | 60.5% | 20.0% |
| V4_D_SFT_tolerant_chartdisplay_v2 | 400 | 370 | 30 | 52.0% | 56.2% | 57.6% | 42.4% | 54.8% | 45.2% | 48.4% |

## 3. 完整性审计

| method | rows | missing | duplicate | unexpected | parse fail | api error | disallowed fields | malformed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V1_OCR_text_chartdisplay_v2 | 400 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| V2_direct_image_policyv3_chartdisplay_v2 | 400 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| V3_C4_group1v2_neutralized | 400 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| V3_D_SFT_group1v2_neutralized | 400 | 0 | 0 | 0 | 30 | 0 | 0 | 30 |
| V4_C4_tolerant_chartdisplay_v2 | 400 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| V4_D_SFT_tolerant_chartdisplay_v2 | 400 | 0 | 0 | 0 | 30 | 0 | 0 | 30 |
| control_all_accept | 400 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| control_all_reject | 400 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| control_oracle_label | 400 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| control_v0_candidate_integrity | 400 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## 4. No-leakage 审计

| input | checked | findings | status |
|---|---:|---:|---|
| V1_text_only | 400 | 0 | pass |
| V2_direct_image | 400 | 0 | pass |
| V3_extract_then_compare | 400 | 0 | pass |

## 5. Retry / attempt 汇总

| method | rows | retry rows | max attempts | api errors | parse fails | attempt distribution |
|---|---:|---:|---:|---:|---:|---|
| V1_OCR_text_chartdisplay_v2 | 400 | 0 | 1 | 0 | 0 | `{"1": 400}` |
| V2_direct_image_policyv3_chartdisplay_v2 | 400 | 0 | 1 | 0 | 0 | `{"1": 400}` |
| V3_C4_group1v2_neutralized | 400 | 0 | 0 | 0 | 0 | `{"0": 400}` |
| V3_D_SFT_group1v2_neutralized | 400 | 0 | 0 | 0 | 30 | `{"0": 400}` |
| V4_C4_tolerant_chartdisplay_v2 | 400 | 0 | 0 | 0 | 0 | `{"0": 400}` |
| V4_D_SFT_tolerant_chartdisplay_v2 | 400 | 0 | 0 | 0 | 30 | `{"0": 400}` |
| control_all_accept | 400 | 0 | 0 | 0 | 0 | `{"0": 400}` |
| control_all_reject | 400 | 0 | 0 | 0 | 0 | `{"0": 400}` |
| control_oracle_label | 400 | 0 | 0 | 0 | 0 | `{"0": 400}` |
| control_v0_candidate_integrity | 400 | 0 | 0 | 0 | 0 | `{"0": 400}` |

## 6. 分层统计文件

- `experiment6_v9_stratified_by_counterfactual_type.csv`
- `experiment6_v9_stratified_by_procedure_type.csv`
- `experiment6_v9_stratified_by_sample_type.csv`
- `experiment6_v9_stratified_by_leg_count.csv`
- `experiment6_v9_stratified_by_field_category.csv`

## 7. 结论

v9 的核心实验运行和最终评估整理已经完成。旧 v8 应只作为 pre-fix 诊断记录；实验组6当前主口径应使用本 v9 package。
