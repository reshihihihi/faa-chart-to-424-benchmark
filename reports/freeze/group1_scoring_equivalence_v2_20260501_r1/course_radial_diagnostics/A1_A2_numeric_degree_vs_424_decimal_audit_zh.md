# A1 / A2 数字角度预测 vs raw 424 小数审查

目的：审查 A1/A2 所有实际输出了数字角度的字段，检查其对应 raw 424 target 是否存在小数，证明或修正“v2 没有提升是因为它们没有落入 424 小数 vs 图面整数差异”的解释。

审查口径：只纳入预测输出中实际出现数字角度的字段，包括 `course_deg`、`radial_deg`、`inbound_course_deg`。然后检查对应 raw 424 target 是否也有角度值，以及该 target 是否有小数。

## 总结

| method | numeric predictions | target has degree | target degree has decimal | target degree integer | target no degree | round-equivalent to target | exact-equal target |
|---|---:|---:|---:|---:|---:|---:|---:|
| A1 | 8 | 7 | 3 | 4 | 1 | 7 | 4 |
| A2 | 6 | 5 | 2 | 3 | 1 | 5 | 3 |

## 按字段范围拆分

| method | target_scope | numeric predictions | target decimal | target integer | target no degree | round-equivalent |
|---|---|---:|---:|---:|---:|---:|
| A1 | Q4_angle | 7 | 3 | 4 | 0 | 7 |
| A1 | Q4_not_applicable | 1 | 0 | 0 | 1 | 0 |
| A2 | Q4_angle | 5 | 2 | 3 | 0 | 5 |
| A2 | Q4_not_applicable | 1 | 0 | 0 | 1 | 0 |

## 全量明细

| method | chart_id | field | pred | raw 424 target | target_has_decimal | round_equivalent | error_type |
|---|---|---|---:|---:|---|---|---|
| A1 | KABE_I06 | `leg_2.Q4_course_or_radial` | radial_deg=243.0 | radial_deg=243.1 | True | True | `round_equivalent_but_other_mismatch` |
| A1 | KALS_I02 | `leg_3.Q4_course_or_radial` | radial_deg=296.0 | no target degree |  |  | `target_not_present_but_pred_present` |
| A1 | KAMA_I04 | `leg_2.Q4_course_or_radial` | radial_deg=118.0 | radial_deg=118.3 | True | True | `round_equivalent_but_other_mismatch` |
| A1 | KATL_I09R | `leg_1.Q4_course_or_radial` | course_deg=100.0 | course_deg=100.0 | False | True | `correct` |
| A1 | KAUS_I18L | `leg_2.Q4_course_or_radial` | course_deg=40.0 | course_deg=40.0 | False | True | `correct` |
| A1 | KBUR_L08-Z | `leg_2.Q4_course_or_radial` | course_deg=210.0 | course_deg=210.0 | False | True | `correct` |
| A1 | KBWI_L15L | `leg_2.Q4_course_or_radial` | radial_deg=153.0 | radial_deg=152.9 | True | True | `round_equivalent_but_other_mismatch` |
| A1 | KCJR_L04 | `leg_2.Q4_course_or_radial` | course_deg=180.0 | course_deg=180.0 | False | True | `correct` |
| A2 | KABE_I06 | `leg_2.Q4_course_or_radial` | radial_deg=243.0 | radial_deg=243.1 | True | True | `round_equivalent_but_other_mismatch` |
| A2 | KATL_I09R | `leg_1.Q4_course_or_radial` | course_deg=100.0 | course_deg=100.0 | False | True | `correct` |
| A2 | KATL_I09R | `leg_3.Q4_course_or_radial` | radial_deg=235.0 | no target degree |  |  | `target_not_present_but_pred_present` |
| A2 | KAWM_L17 | `leg_2.Q4_course_or_radial` | radial_deg=147.0 | radial_deg=147.0 | False | True | `round_equivalent_but_other_mismatch` |
| A2 | KBWI_L15L | `leg_2.Q4_course_or_radial` | radial_deg=153.0 | radial_deg=152.9 | True | True | `round_equivalent_but_other_mismatch` |
| A2 | KCJR_L04 | `leg_2.Q4_course_or_radial` | course_deg=180.0 | course_deg=180.0 | False | True | `correct` |

## 结论

1. A1/A2 真正输出数字角度的次数非常少：A1 只有 8 个，A2 只有 6 个。
2. 在这些数字预测里，确实有一部分对应 raw 424 小数：A1 为 3 个，A2 为 2 个。
3. 但是这些 raw 424 小数案例并没有被 v2 救回来，因为它们不是单纯的小数/整数差异，还存在 direction、navaid、或字段适用性等其他不匹配。
4. 因此更准确的解释是：A1/A2 的低分和 v2 增量为 0，主要不是因为 424 小数显示差异，而是因为它们几乎没有稳定抽出数字角度；少数抽出的数字角度也常常伴随其他结构错误。

## 输出文件

- 全量 CSV: `reports/freeze/group1_scoring_equivalence_v2_20260501_r1/course_radial_diagnostics\A1_A2_numeric_degree_vs_424_decimal_audit.csv`