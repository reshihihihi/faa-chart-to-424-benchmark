# 实验组5 B2 gold text smoke 运行报告

- run_id: `experiment5_dev50_20260503_r1`
- 模型: `gpt-5.4`
- base_url: `http://127.0.0.1:8080/v1`
- 方法: `B2a_GoldText_LLM`, `B2b_GoldText_FieldCandidates_LLM`
- 样本数: 50
- target/score 使用: 只在 prediction 写盘后评分使用，不进入方法输入

## B2 结果

| 方法 | schema-valid | retry | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---:|---:|---:|---:|---:|
| `B2a_GoldText_LLM` | 50/50 | 5 | 261/1010 | 25.84% | 25.84% |
| `B2b_GoldText_FieldCandidates_LLM` | 50/50 | 1 | 275/1010 | 27.23% | 27.23% |

## 字段族表现

### `B2a_GoldText_LLM`

| 字段 | 正确/总数 | accuracy |
|---|---:|---:|
| `Q1_fix_ident` | 71/160 | 44.38% |
| `Q2_altitude_constraint` | 4/160 | 2.50% |
| `Q3_turn` | 84/160 | 52.50% |
| `Q4_course_or_radial` | 13/160 | 8.12% |
| `Q5_hold_params` | 66/160 | 41.25% |
| `Q_terminator` | 11/160 | 6.88% |
| `leg_count` | 12/50 | 24.00% |

### `B2b_GoldText_FieldCandidates_LLM`

| 字段 | 正确/总数 | accuracy |
|---|---:|---:|
| `Q1_fix_ident` | 75/160 | 46.88% |
| `Q2_altitude_constraint` | 0/160 | 0.00% |
| `Q3_turn` | 81/160 | 50.62% |
| `Q4_course_or_radial` | 24/160 | 15.00% |
| `Q5_hold_params` | 69/160 | 43.12% |
| `Q_terminator` | 15/160 | 9.38% |
| `leg_count` | 11/50 | 22.00% |

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
