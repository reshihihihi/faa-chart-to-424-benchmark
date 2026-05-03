# 实验组5 B2 gold text smoke 运行报告

- run_id: `experiment5_eval200_20260503_r2_admin_relation`
- 模型: `gpt-5.4`
- base_url: `http://127.0.0.1:10531/v1`
- 方法: `B2a_GoldText_LLM`, `B2b_GoldText_FieldCandidates_LLM`
- 样本数: 200
- target/score 使用: 只在 prediction 写盘后评分使用，不进入方法输入

## B2 结果

| 方法 | schema-valid | retry | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---:|---:|---:|---:|---:|
| `B2a_GoldText_LLM` | 200/200 | 0 | 2552/4052 | 62.98% | 55.08% |
| `B2b_GoldText_FieldCandidates_LLM` | 200/200 | 0 | 1963/4052 | 48.45% | 42.94% |

## 字段族表现

### `B2a_GoldText_LLM`

| 字段 | 正确/总数 | accuracy |
|---|---:|---:|
| `Q1_fix_ident` | 593/642 | 92.37% |
| `Q2_altitude_constraint` | 13/642 | 2.02% |
| `Q3_turn` | 598/642 | 93.15% |
| `Q4_course_or_radial` | 434/642 | 67.60% |
| `Q5_hold_params` | 612/642 | 95.33% |
| `Q_terminator` | 117/642 | 18.22% |
| `leg_count` | 185/200 | 92.50% |

### `B2b_GoldText_FieldCandidates_LLM`

| 字段 | 正确/总数 | accuracy |
|---|---:|---:|
| `Q1_fix_ident` | 454/642 | 70.72% |
| `Q2_altitude_constraint` | 34/642 | 5.30% |
| `Q3_turn` | 522/642 | 81.31% |
| `Q4_course_or_radial` | 292/642 | 45.48% |
| `Q5_hold_params` | 452/642 | 70.40% |
| `Q_terminator` | 104/642 | 16.20% |
| `leg_count` | 105/200 | 52.50% |

## No-leakage 审查

- hard_leakage_detected: `False`
- forbidden_key_hits: `{}`
- target_used_for_prediction: `False`
- score_used_for_prediction: `False`
- field_review_v2_used_for_prediction: `False`

## 解释边界

- 这是 eval200 admin-relation 诊断结果。
- B2a 只使用 gold MA prose；B2b 使用 gold MA prose 和从同一 prose 自动生成的候选。
- 未使用 field_review_v2、canonical target、score、CIFP/ARINC 424 或 gold observable 作为方法输入。
