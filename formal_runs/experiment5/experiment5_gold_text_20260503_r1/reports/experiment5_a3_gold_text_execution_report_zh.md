# 实验组5 A3 gold text smoke 运行报告

- run_id: `experiment5_gold_text_20260503_r1`
- 方法: `A3_GoldText_Rules`
- 样本数: 20
- 输入: adjudicated `gold_ma_prose` only
- 规则注册表状态: `candidate_for_smoke_diagnostic_not_formal_reviewed`
- target/score 使用: 只在 prediction 写盘后评分使用，不进入方法输入

## A3 结果

| 方法 | schema-valid | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---:|---:|---:|---:|
| `A3_GoldText_Rules` | 20/20 | 342/470 | 72.77% | 72.77% |

## 字段族表现

| 字段 | 正确/总数 | accuracy |
|---|---:|---:|
| `Q1_fix_ident` | 73/75 | 97.33% |
| `Q2_altitude_constraint` | 19/75 | 25.33% |
| `Q3_turn` | 68/75 | 90.67% |
| `Q4_course_or_radial` | 38/75 | 50.67% |
| `Q5_hold_params` | 54/75 | 72.00% |
| `Q_terminator` | 71/75 | 94.67% |
| `leg_count` | 19/20 | 95.00% |

## No-leakage 审查

- target_used_for_prediction: `False`
- score_used_for_prediction: `False`
- cifp_or_arinc_424_used_for_prediction: `False`
- field_review_v2_used_for_prediction: `False`
- hard_leakage_detected: `False`
- forbidden_key_hits: `{}`

## B2 当前状态

- B2a/B2b: `not_run_pending_model_server`
- 原因: B2a/B2b require an OpenAI-compatible model server. No successful model-server call is recorded by run_experiment5_gold_text_a3.py; run B2 only after service readiness is confirmed.

## 解释边界

- 这是 smoke20 诊断结果，不是 formal200 结论。
- A3 消除了 MA prose OCR 错误，但仍不提供图形区 gold observable，也不提供 target 字段答案。
- rule_registry 尚未完成正式审查，因此该结果可以用于诊断下一步，不宜直接作为论文 formal claim。
