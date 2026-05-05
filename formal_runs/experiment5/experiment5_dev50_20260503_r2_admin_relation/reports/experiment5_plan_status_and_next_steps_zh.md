# 实验组5计划、状态和下一步

更新时间：2026-05-03

## 实验方案理解

实验组5是 backend/admin-relation diagnostic lane。输入来自 shujuji 后台完整人工审核关系图，包括框、航段、字段、证据关系和最终字段答案。它不是 blind OCR lane。

核心方法：

- A3_GoldText_Rules：admin-relation textualized gold text + deterministic rules
- B2a_GoldText_LLM：admin-relation textualized gold text + LLM
- B2b_GoldText_FieldCandidates_LLM：admin-relation textualized gold text + field candidates + LLM
- B3_T：T profile candidates + LLM
- B3_PD：PD profile candidates + LLM
- B3_TPD：T+PD candidates + LLM
- B4_TPD：T+PD candidates + deterministic rules
- G0/G1/G3：后台关系参考线，已在 r1 目录完成

序列化方法输入不得包含禁用 key 名称：`target`、`score`、`canonical_answer`、`canonical_leg_index`、`Q_terminator`、`leg_type`、`field_review_v2`。

## 已完成

已使用 `openai-oauth` 将本机 Codex OAuth 包装成 OpenAI-compatible API：

- base URL：`http://127.0.0.1:10531/v1`
- model：`gpt-5.4`
- 最小 chat probe 已成功返回 `pong`

dev50 已经跑齐 A3/B2/B3/B4/G。

eval200 也已经跑齐 A3/B2/B3/B4/G。B2b 曾在 23/200 后遇到 transient usage-limit 错误，后续已用 `--resume-existing` 补完；最终汇总中 A/B/G 全部方法 `failure_count = 0`。

## 当前结果

### dev50

| 方法 | v2 正确/总数 | accuracy | failure_count |
|---|---:|---:|---:|
| A3_GoldText_Rules | 303/1010 | 30.00% | 0 |
| B2a_GoldText_LLM | 606/1010 | 60.00% | 0 |
| B2b_GoldText_FieldCandidates_LLM | 509/1010 | 50.40% | 0 |
| B3_T | 722/1010 | 71.49% | 0 |
| B3_PD | 171/1010 | 16.93% | 0 |
| B3_TPD | 660/1010 | 65.35% | 0 |
| B4_TPD | 303/1010 | 30.00% | 0 |
| G0_Direct | 274/1010 | 27.13% | 0 |
| G1_Rules | 600/1010 | 59.41% | 0 |
| G3_LLM_Rules | 76/1010 | 7.52% | 0 |

### eval200

| 方法 | 状态 | v2 正确/总数 | accuracy | failure_count |
|---|---|---:|---:|---:|
| A3_GoldText_Rules | completed | 1245/4052 | 30.73% | 0 |
| B2a_GoldText_LLM | completed | 2552/4052 | 62.98% | 0 |
| B2b_GoldText_FieldCandidates_LLM | completed | 1963/4052 | 48.45% | 0 |
| B3_T | completed | 2930/4052 | 72.31% | 0 |
| B3_PD | completed | 719/4052 | 17.74% | 0 |
| B3_TPD | completed | 2657/4052 | 65.57% | 0 |
| B4_TPD | completed | 1245/4052 | 30.73% | 0 |
| G0_Direct | completed | 1079/4052 | 26.63% | 0 |
| G1_Rules | completed | 2380/4052 | 58.74% | 0 |
| G3_LLM_Rules | completed | 284/4052 | 7.01% | 0 |

## 当前结论

200 样本 eval200 上，B3_T 是当前最强方法：`2930/4052 = 72.31%`。B3_TPD 次高：`2657/4052 = 65.57%`。B2a 为 `2552/4052 = 62.98%`。B2b 低于 B2a：`1963/4052 = 48.45%`。A3 与 B4_TPD 持平：`1245/4052 = 30.73%`。

## 下一步

1. 做最终 no-leakage 与敏感信息扫描。
2. 确认 dev50/eval200 reports 与 combined summary 一致。
3. git 提交并推送。
4. 后续再基于结果写正式分析，不需要再补跑实验组5核心方法。
