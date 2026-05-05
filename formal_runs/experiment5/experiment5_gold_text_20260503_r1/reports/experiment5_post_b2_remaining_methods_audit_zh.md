# 实验组5剩余方法输入合规审计

- 生成时间 UTC: `2026-05-03T07:51:46.790853+00:00`
- smoke20 样本数: 20
- 标注导出: `external_artifact://E/experiment3\group2_annotation_status_20260503\shujuji_annotation_export_2026-05-03T02-07-42-455Z.json`

## 结论

- 已经可以合法执行并已跑通：`B3_T`、`B3_TPD`、`B3_PD`、`B4_TPD`。`A3_GoldText_Rules` 也已完成 smoke20 candidate run。`B2a_GoldText_LLM` / `B2b_GoldText_FieldCandidates_LLM` 也已完成 smoke20 run。
- 现在不能直接执行：`G0`、`G1`、`G2`、`G3`。
- 原因不是没有标注文件，而是现有标注导出属于字段级 evidence review，里面混有 `canonical_answer`、`canonical_leg_index`、`Q_terminator/leg_type`、`support_mode` 等方法输入禁用项。
- 因此不能把这些字段审查记录直接当作 gold MA text 或 gold observable 输入；否则会把答案结构带给方法，破坏实验组5的 oracle 诊断边界。

## Gold Text 状态

- 模板行数: 20
- 已填写: 20
- 未填写: 0
- A3/B2 只允许输入人工校正后的 `gold_ma_prose`，不能输入 field review、leg type、Q_terminator 或 canonical answer。

## Gold Observable 状态

- 模板行数: 20
- 已填写: 0
- 未填写: 20
- G 系列只允许输入人工确认的图上事实、显式缺失、证据区域和 checked scopes。
- G 系列禁止输入 canonical target、Q_terminator 答案、canonical leg index、final canonical JSON 和 score。

## 标注导出中发现了什么

- annotation audit status: `blocked_missing_annotation_export`
- smoke20 中有最新 submission 的样本: 0 / 20
- 字段审查记录总数: unknown_missing_export
- 非空 region OCR 数量: unknown_missing_export
- 如果直接作为方法输入会命中的禁用字段: `{}`

这说明标注导出对实验组2/3分析很有价值，但不能原样喂给实验组5的 A3/B2/G 方法。若 annotation export 缺失，本节只保留方法边界判断，不能复现字段审查计数。

## 方法 readiness

| 方法 | 状态 | 需要输入 | 当前原因 |
|---|---|---|---|
| `A3_GoldText_Rules` | `completed_smoke20_candidate_rules_formal_claim_needs_rule_review` | adjudicated gold_ma_prose only | A3 smoke run completed; rule_registry still requires formal review before formal claim |
| `B2a_GoldText_LLM` | `completed_smoke20` | adjudicated gold_ma_prose only | B2a smoke run completed |
| `B2b_GoldText_FieldCandidates_LLM` | `completed_smoke20` | adjudicated gold_ma_prose + automatic field candidates | B2b smoke run completed |
| `B3_T` | `completed_smoke20_r4` | MA_TEXT ROI OCR + automatic candidates |  |
| `B3_TPD` | `completed_smoke20_r4` | T/P/D ROI OCR + automatic candidates |  |
| `B3_PD` | `completed_smoke20_r4` | P/D ROI OCR + automatic candidates |  |
| `B4_TPD` | `completed_smoke20_r4` | T/P/D ROI OCR + automatic candidates + frozen rules |  |
| `G0_Direct` | `blocked` | adjudicated gold observable facts, explicit absence, source evidence ids | gold_observable template is not completed |
| `G1_Rules` | `blocked` | adjudicated gold observable facts + frozen rules | gold_observable template is not completed |
| `G2_LLM` | `optional_blocked` | adjudicated gold observable facts | optional method; gold_observable template is not completed |
| `G3_LLM_Rules` | `blocked` | adjudicated gold observable facts + frozen rule descriptions | gold_observable template is not completed |

## 下一步

1. `gold_ma_text_smoke20_template.jsonl` 已填写；A3/B2 已跑通。
2. 单独建立符合 schema 的 `gold_observable_smoke20.jsonl`，只写可观察事实和显式缺失，不写 canonical answer 或 target leg index；完成后再跑 G0/G1/G3。
3. 在跑 G1/G3 前审查并冻结 `rule_registry.yaml`，明确哪些规则属于 direct fill、convention default、424-derived 程序语义。
4. 已跑通的 B3/B4 层可以先用于 smoke 诊断报告，但正式结论仍需要扩展到 formal200 或冻结的 diagnostic subset。
