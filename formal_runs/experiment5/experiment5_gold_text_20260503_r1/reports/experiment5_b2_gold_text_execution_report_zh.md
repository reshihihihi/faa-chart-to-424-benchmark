# 实验组5 B2 gold text smoke 运行报告

- run_id: `experiment5_gold_text_20260503_r1`
- 模型: `gpt-5.4`
- base_url: `http://127.0.0.1:8080/v1`
- 方法: `B2a_GoldText_LLM`, `B2b_GoldText_FieldCandidates_LLM`
- 样本数: 20
- target/score 使用: 只在 prediction 写盘后评分使用，不进入方法输入

## B2 结果

| 方法 | schema-valid | retry | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---:|---:|---:|---:|---:|
| `B2a_GoldText_LLM` | 20/20 | 5 | 125/470 | 26.60% | 26.60% |
| `B2b_GoldText_FieldCandidates_LLM` | 20/20 | 0 | 137/470 | 29.15% | 29.15% |

## 字段族表现

### `B2a_GoldText_LLM`

| 字段 | 正确/总数 | accuracy |
|---|---:|---:|
| `Q1_fix_ident` | 38/75 | 50.67% |
| `Q2_altitude_constraint` | 0/75 | 0.00% |
| `Q3_turn` | 31/75 | 41.33% |
| `Q4_course_or_radial` | 11/75 | 14.67% |
| `Q5_hold_params` | 34/75 | 45.33% |
| `Q_terminator` | 9/75 | 12.00% |
| `leg_count` | 2/20 | 10.00% |

### `B2b_GoldText_FieldCandidates_LLM`

| 字段 | 正确/总数 | accuracy |
|---|---:|---:|
| `Q1_fix_ident` | 38/75 | 50.67% |
| `Q2_altitude_constraint` | 0/75 | 0.00% |
| `Q3_turn` | 38/75 | 50.67% |
| `Q4_course_or_radial` | 11/75 | 14.67% |
| `Q5_hold_params` | 37/75 | 49.33% |
| `Q_terminator` | 10/75 | 13.33% |
| `leg_count` | 3/20 | 15.00% |

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
