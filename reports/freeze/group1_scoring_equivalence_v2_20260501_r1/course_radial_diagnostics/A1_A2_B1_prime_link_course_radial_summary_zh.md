# A1 / A2 / B1_prime_link 航向-航迹-径向识别诊断

本报告只抽取 `Q4_course_or_radial` 与 `Q5_hold_params.inbound_course_deg` 相关字段，用于解释为什么 scoring-equivalence v2 对 A1、A2、B1_prime_link 的增量为 0。

## A1

| scope | correct | total | accuracy |
|---|---:|---:|---:|
| Q4_course_or_radial | 98 | 642 | 15.26% |
| Q5_hold_params.inbound_course_deg | 0 | 401 | 0.00% |
| Q4 + Q5 inbound course | 98 | 1043 | 9.40% |
| degree_display_rounding | 4 | 380 | 1.05% |
| exact_status_value | 94 | 663 | 14.18% |

主要错误类型：

| error_type | count | 解释 |
|---|---:|---|
| missing_leg_or_field | 296 | 预测缺少对应航段或字段 |
| status_not_applicable | 204 | 把应为 present 的字段判成不适用 |
| target_not_present_but_pred_present | 204 | target 不要求该字段，但预测给了 present |
| status_unknown | 139 | 字段存在但判成 unknown |
| missing_inbound_course_deg | 59 | hold 字段里缺少 inbound_course_deg |
| type_mismatch:direct->course_deg | 40 | 把 course_deg 类型误判为 direct |

## A2

| scope | correct | total | accuracy |
|---|---:|---:|---:|
| Q4_course_or_radial | 80 | 642 | 12.46% |
| Q5_hold_params.inbound_course_deg | 0 | 371 | 0.00% |
| Q4 + Q5 inbound course | 80 | 1013 | 7.90% |
| degree_display_rounding | 2 | 380 | 0.53% |
| exact_status_value | 78 | 633 | 12.32% |

主要错误类型：

| error_type | count | 解释 |
|---|---:|---|
| missing_leg_or_field | 383 | 预测缺少对应航段或字段 |
| target_not_present_but_pred_present | 175 | target 不要求该字段，但预测给了 present |
| status_not_applicable | 174 | 把应为 present 的字段判成不适用 |
| status_unknown | 105 | 字段存在但判成 unknown |
| missing_inbound_course_deg | 61 | hold 字段里缺少 inbound_course_deg |
| type_mismatch:direct->course_deg | 32 | 把 course_deg 类型误判为 direct |

## B1_prime_link

| scope | correct | total | accuracy |
|---|---:|---:|---:|
| Q4_course_or_radial | 5 | 583 | 0.86% |
| Q5_hold_params.inbound_course_deg | 0 | 204 | 0.00% |
| Q4 + Q5 inbound course | 5 | 787 | 0.64% |
| degree_display_rounding | 0 | 354 | 0.00% |
| exact_status_value | 5 | 433 | 1.15% |

主要错误类型：

| error_type | count | 解释 |
|---|---:|---|
| missing_leg_or_field | 306 | 预测缺少对应航段或字段 |
| status_unknown | 248 | 字段存在但判成 unknown |
| status_not_observable | 158 | 字段被判成图上不可观察 |
| status_not_applicable | 42 | 把应为 present 的字段判成不适用 |
| target_not_present_but_pred_present | 21 | target 不要求该字段，但预测给了 present |
| missing_inbound_course_deg | 3 | hold 字段里缺少 inbound_course_deg |
| inbound_degree_numeric_mismatch | 2 | inbound course 数值明显不一致 |

## 结论

A1、A2、B1_prime_link 的航向/航迹/径向识别结果可以找到。它们不是完全没有识别 Q4/Q5，而是几乎没有落入 v2 能修正的“424 小数 vs 图面整数”错误类型。

A1 和 A2 的主要问题是 OCR + Rules 抽取覆盖不足、航段结构不稳定、Q4 类型判断不稳、Q5 holding inbound course 几乎没有正确抽出。

B1_prime_link 的问题更明显：field-to-leg linking 后大量 Q4/Q5 字段缺失，或被判成 unknown / not_observable / not_applicable，所以 v2 的整数显示等价规则救不回来。

## 输出文件

- 明细 CSV: `reports/freeze/group1_scoring_equivalence_v2_20260501_r1/course_radial_diagnostics\A1_A2_B1_prime_link_course_radial_rows.csv`
- 汇总 CSV: `reports/freeze/group1_scoring_equivalence_v2_20260501_r1/course_radial_diagnostics\A1_A2_B1_prime_link_course_radial_summary.csv`
