# 实验组5 A3 gold text smoke 运行报告

- run_id: `experiment5_eval200_20260503_r2_admin_relation`
- 方法: `A3_GoldText_Rules`
- 样本数: 200
- 输入: adjudicated `gold_ma_prose` only
- 规则注册表状态: `candidate_for_smoke_diagnostic_not_formal_reviewed`
- target/score 使用: 只在 prediction 写盘后评分使用，不进入方法输入

## A3 结果

| 方法 | schema-valid | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---:|---:|---:|---:|
| `A3_GoldText_Rules` | 200/200 | 1245/4052 | 30.73% | 30.73% |

## 字段族表现

| 字段 | 正确/总数 | accuracy |
|---|---:|---:|
| `Q1_fix_ident` | 372/642 | 57.94% |
| `Q2_altitude_constraint` | 88/642 | 13.71% |
| `Q3_turn` | 321/642 | 50.00% |
| `Q4_course_or_radial` | 17/642 | 2.65% |
| `Q5_hold_params` | 219/642 | 34.11% |
| `Q_terminator` | 217/642 | 33.80% |
| `leg_count` | 11/200 | 5.50% |

## No-leakage 审查

- target_used_for_prediction: `False`
- score_used_for_prediction: `False`
- cifp_or_arinc_424_used_for_prediction: `False`
- field_review_v2_used_for_prediction: `False`
- hard_leakage_detected: `False`
- forbidden_key_hits: `{}`

## B2/B3 后续状态

- B2a/B2b/B3/B4/G 已在同一 eval200 admin-relation 线中跑齐。
- 本文件只记录 A3 单方法结果；完整汇总见 `experiment5_eval200_admin_relation_combined_summary.json`。

## 解释边界

- 这是 eval200 admin-relation 诊断结果。
- A3 消除了 MA prose OCR 错误，但仍不提供图形区 gold observable，也不提供 target 字段答案。
- rule_registry 尚未完成正式审查，因此该结果可以用于诊断下一步，不宜直接作为论文 formal claim。
