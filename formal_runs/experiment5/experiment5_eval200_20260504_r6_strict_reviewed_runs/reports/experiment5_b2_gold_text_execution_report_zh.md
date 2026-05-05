# 实验组5 B2 gold text smoke 运行报告

- run_id: `experiment5_eval200_20260504_r6_strict_reviewed_runs`
- 模型: `gpt-5.4`
- base_url: `http://127.0.0.1:10531/v1`
- 方法: `B2a_GoldText_LLM`, `B2b_GoldText_FieldCandidates_LLM`
- 样本数: 200
- target/score 使用: 只在 prediction 写盘后评分使用，不进入方法输入

## B2 结果

| 方法 | schema-valid | retry | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---:|---:|---:|---:|---:|
| `B2a_GoldText_LLM` | 200/200 | 17 | 970/4052 | 23.94% | 23.94% |
| `B2b_GoldText_FieldCandidates_LLM` | 200/200 | 0 | 1100/4052 | 27.15% | 27.15% |

## 字段族表现

### `B2a_GoldText_LLM`

| 字段 | 正确/总数 | accuracy |
|---|---:|---:|
| `Q1_fix_ident` | 281/642 | 43.77% |
| `Q2_altitude_constraint` | 3/642 | 0.47% |
| `Q3_turn` | 279/642 | 43.46% |
| `Q4_course_or_radial` | 73/642 | 11.37% |
| `Q5_hold_params` | 252/642 | 39.25% |
| `Q_terminator` | 60/642 | 9.35% |
| `leg_count` | 22/200 | 11.00% |

### `B2b_GoldText_FieldCandidates_LLM`

| 字段 | 正确/总数 | accuracy |
|---|---:|---:|
| `Q1_fix_ident` | 301/642 | 46.88% |
| `Q2_altitude_constraint` | 5/642 | 0.78% |
| `Q3_turn` | 330/642 | 51.40% |
| `Q4_course_or_radial` | 85/642 | 13.24% |
| `Q5_hold_params` | 270/642 | 42.06% |
| `Q_terminator` | 73/642 | 11.37% |
| `leg_count` | 36/200 | 18.00% |

## No-leakage 审查

- hard_leakage_detected: `False`
- forbidden_key_hits: `{}`
- target_used_for_prediction: `False`
- score_used_for_prediction: `False`
- field_review_v2_used_for_prediction: `False`

## 解释边界

- 这是 smoke20 诊断结果，不是 formal200 结论。
- B2a 只使用 gold MA prose；B2b 使用 gold MA prose 和从同一 prose 自动生成的候选。
- 未使用 field_review_v2、canonical target、score、CIFP/ARINC 424 或 gold observable 作为方法输入。
