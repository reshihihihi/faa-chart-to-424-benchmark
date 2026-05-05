# 实验组5 smoke20 r4 执行与审查报告

- run_id: `experiment5_smoke_20260503_r4_available_methods`
- 样本数: 20
- 范围: smoke20 流程验证，不是 formal200 正式结论
- 模型: `gpt-5.4`，temperature = 0，max_tokens = 4096，schema retry 上限 = 1
- 主评分: PR #25 narrowed scoring-equivalence v2；同时保存 strict score

## 已执行方法

| 方法 | 输入 | 输出 | schema-valid | retry | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---|---|---:|---:|---:|---:|---:|
| `B3_T` | MA_TEXT ROI OCR + 自动 field candidates + LLM | canonical JSON | 20/20 | 0 | 138/470 | 29.36% | 29.36% |
| `B3_TPD` | MA_TEXT + PLAN_VIEW + DETAIL ROI OCR + 自动 field candidates + LLM | canonical JSON | 20/20 | 0 | 126/470 | 26.81% | 26.81% |
| `B3_PD` | PLAN_VIEW + DETAIL ROI OCR + 自动 field candidates + LLM；不含 MA_TEXT | canonical JSON | 20/20 | 0 | 8/470 | 1.70% | 1.70% |
| `B4_TPD` | MA_TEXT + PLAN_VIEW + DETAIL ROI OCR + 自动 field candidates + deterministic rules | canonical JSON | 20/20 | 0 | 310/470 | 65.96% | 65.96% |

## 结果解释

- `B4_TPD` 明显最高，说明当 T/P/D ROI OCR 与自动候选已经给定时，当前规则系统在 smoke20 上很有效。这个结论只说明“候选已知条件下规则强”，不代表端到端视觉问题已经解决。
- `B3_T` 高于 `B3_TPD`，说明把 P/D OCR 直接加给 LLM 未必有帮助。额外区域文本可能引入噪声，或让 LLM 错误绑定字段。
- `B3_PD` 接近 0，说明没有上方 missed approach prose 时，仅靠平面图和细节区 OCR 很难恢复完整程序结构。这与实验组4的 source-view 消融问题相呼应。
- v2 与 strict 在本次四个方法中相同，说明这批方法的差异不是由 PR #25 的两类显示等价造成。

## 字段族表现

下表用于看每个方法主要错在哪些 canonical 字段。

| 方法 | 字段 | 正确/总数 | accuracy |
|---|---|---:|---:|
| `B3_T` | `Q1_fix_ident` | 28/75 | 37.33% |
| `B3_T` | `Q2_altitude_constraint` | 4/75 | 5.33% |
| `B3_T` | `Q3_turn` | 51/75 | 68.00% |
| `B3_T` | `Q4_course_or_radial` | 6/75 | 8.00% |
| `B3_T` | `Q5_hold_params` | 36/75 | 48.00% |
| `B3_T` | `Q_terminator` | 12/75 | 16.00% |
| `B3_T` | `leg_count` | 1/20 | 5.00% |
| `B3_TPD` | `Q1_fix_ident` | 25/75 | 33.33% |
| `B3_TPD` | `Q2_altitude_constraint` | 6/75 | 8.00% |
| `B3_TPD` | `Q3_turn` | 49/75 | 65.33% |
| `B3_TPD` | `Q4_course_or_radial` | 4/75 | 5.33% |
| `B3_TPD` | `Q5_hold_params` | 34/75 | 45.33% |
| `B3_TPD` | `Q_terminator` | 8/75 | 10.67% |
| `B3_TPD` | `leg_count` | 0/20 | 0.00% |
| `B3_PD` | `Q1_fix_ident` | 0/75 | 0.00% |
| `B3_PD` | `Q2_altitude_constraint` | 0/75 | 0.00% |
| `B3_PD` | `Q3_turn` | 1/75 | 1.33% |
| `B3_PD` | `Q4_course_or_radial` | 0/75 | 0.00% |
| `B3_PD` | `Q5_hold_params` | 7/75 | 9.33% |
| `B3_PD` | `Q_terminator` | 0/75 | 0.00% |
| `B3_PD` | `leg_count` | 0/20 | 0.00% |
| `B4_TPD` | `Q1_fix_ident` | 64/75 | 85.33% |
| `B4_TPD` | `Q2_altitude_constraint` | 19/75 | 25.33% |
| `B4_TPD` | `Q3_turn` | 63/75 | 84.00% |
| `B4_TPD` | `Q4_course_or_radial` | 38/75 | 50.67% |
| `B4_TPD` | `Q5_hold_params` | 49/75 | 65.33% |
| `B4_TPD` | `Q_terminator` | 62/75 | 82.67% |
| `B4_TPD` | `leg_count` | 15/20 | 75.00% |

## No-leakage 审查

- target_used_for_prediction: `False`
- score_used_for_prediction: `False`
- cifp_or_arinc_424_used_for_prediction: `False`
- gold_observable_used_for_prediction: `False`
- gold_ma_text_used_for_prediction: `False`
- hard_leakage_detected: `False`
- candidate validation error rows: 0
- cross-region snippet count: 0
- unknown source_section count: 0

## 剩余方法状态

| 方法 | 状态 | 原因 |
|---|---|---|
| `A3_GoldText_Rules` | `blocked` | `gold_ma_text_smoke20_template.jsonl` 还没有填写 |
| `B2a_GoldText_LLM` | `blocked` | `gold_ma_text_smoke20_template.jsonl` 还没有填写 |
| `B2b_GoldText_FieldCandidates_LLM` | `blocked` | `gold_ma_text_smoke20_template.jsonl` 还没有填写 |
| `G0_Direct` | `blocked` | `gold_observable_smoke20_template.jsonl` 还没有填写 |
| `G1_Rules` | `blocked` | `gold_observable_smoke20_template.jsonl` 还没有填写 |
| `G2_LLM` | `optional_blocked` | 可选方法；`gold_observable_smoke20_template.jsonl` 还没有填写 |
| `G3_LLM_Rules` | `blocked` | `gold_observable_smoke20_template.jsonl` 还没有填写 |

## 下一步

1. 人工填写 `gold_ma_text_smoke20_template.jsonl` 为纯 MA prose；完成后跑 A3/B2a/B2b。
2. 按 Gold observable schema 制作不含 target、canonical leg index、Q_terminator 答案的 `gold_observable_smoke20.jsonl`；完成后跑 G0/G1/G3。
3. 审查 `rule_registry.yaml`，明确哪些规则允许用于 B4/G1/G3 的 formal claim。
4. smoke20 全部方法跑通后，再扩展到 formal200 或冻结 diagnostic subset。
