# 实验组5 B2 gold text smoke 运行报告

- run_id: `experiment5_dev50_20260503_r2_admin_relation`
- 模型: `gpt-5.4`
- base_url: `http://127.0.0.1:10531/v1`
- 方法: `B2a_GoldText_LLM`, `B2b_GoldText_FieldCandidates_LLM`
- 样本数: 50
- target/score 使用: 只在 prediction 写盘后评分使用，不进入方法输入

## B2 结果

| 方法 | schema-valid | retry | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---:|---:|---:|---:|---:|
| `B2a_GoldText_LLM` | 50/50 | 12 | 606/1010 | 60.00% | 52.97% |
| `B2b_GoldText_FieldCandidates_LLM` | 50/50 | 5 | 509/1010 | 50.40% | 44.65% |

## 字段族表现

### `B2a_GoldText_LLM`

| 字段 | 正确/总数 | accuracy |
|---|---:|---:|
| `Q1_fix_ident` | 139/160 | 86.88% |
| `Q2_altitude_constraint` | 1/160 | 0.62% |
| `Q3_turn` | 147/160 | 91.88% |
| `Q4_course_or_radial` | 103/160 | 64.38% |
| `Q5_hold_params` | 150/160 | 93.75% |
| `Q_terminator` | 21/160 | 13.12% |
| `leg_count` | 45/50 | 90.00% |

### `B2b_GoldText_FieldCandidates_LLM`

| 字段 | 正确/总数 | accuracy |
|---|---:|---:|
| `Q1_fix_ident` | 119/160 | 74.38% |
| `Q2_altitude_constraint` | 8/160 | 5.00% |
| `Q3_turn` | 132/160 | 82.50% |
| `Q4_course_or_radial` | 73/160 | 45.62% |
| `Q5_hold_params` | 122/160 | 76.25% |
| `Q_terminator` | 24/160 | 15.00% |
| `leg_count` | 31/50 | 62.00% |

## No-leakage 审查

- hard_leakage_detected: `False`
- forbidden_key_hits: `{}`
- target_used_for_prediction: `False`
- score_used_for_prediction: `False`
- field_review_v2_used_for_prediction: `False`

## 解释边界

- 这是 dev50 admin-relation 诊断结果，不是 eval200 最终结论。
- B2a 只使用 gold MA prose；B2b 使用 gold MA prose 和从同一 prose 自动生成的候选。
- 未使用 field_review_v2、canonical target、score、CIFP/ARINC 424 或 gold observable 作为方法输入。
