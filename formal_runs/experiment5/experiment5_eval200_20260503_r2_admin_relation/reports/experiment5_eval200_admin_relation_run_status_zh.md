# 实验组5 eval200 admin-relation 运行状态

更新时间：2026-05-03

## 输入状态

本轮使用 `experiment5_eval200_20260503_r1` 中已经导出的 shujuji 后台人工审核关系，生成新的 eval200 admin-relation 方法输入：

- 运行目录：`formal_runs/experiment5/experiment5_eval200_20260503_r2_admin_relation`
- A3/B2 gold text：`inputs/gold_ma_text_eval200_admin_relation.jsonl`
- B3/B4 manifest：`manifests/roi_admin_relation_candidate_input_manifest_eval200.jsonl`
- 输入分类：`admin_relation_oracle_textualized_inputs`
- charts：200
- B3/B4 profile rows：600
- field candidate schema validation errors：0
- serialized method payload forbidden key hits：0

说明：这条线来自 shujuji 后台完整人工审核关系图，包括框、航段、字段、证据关系和最终字段答案；不是 blind OCR 输入线。序列化方法输入没有使用禁用 key 名称：`target`、`score`、`canonical_answer`、`canonical_leg_index`、`Q_terminator`、`leg_type`、`field_review_v2`。

## LLM endpoint

已使用 `openai-oauth` 把本机 Codex OAuth 包装成 OpenAI-compatible API：

- base URL：`http://127.0.0.1:10531/v1`
- model：`gpt-5.4`
- 最小 chat probe 已成功返回 `pong`

原来的 `http://127.0.0.1:8080/v1` 不再作为本轮 LLM 方法入口。

## 已运行结果

| 方法 | 状态 | schema-valid | v2 正确/总数 | accuracy | failure_count | 说明 |
|---|---|---:|---:|---:|---:|---|
| A3_GoldText_Rules | completed | 200/200 | 1245/4052 | 30.73% | 0 | deterministic rules over admin-relation textualized gold prose |
| B2a_GoldText_LLM | completed | 200/200 | 2552/4052 | 62.98% | 0 | gold text + LLM |
| B2b_GoldText_FieldCandidates_LLM | completed | 200/200 | 1963/4052 | 48.45% | 0 | gold text + field candidates + LLM |
| B3_T | completed | 200/200 | 2930/4052 | 72.31% | 0 | T profile candidates + LLM |
| B3_PD | completed | 200/200 | 719/4052 | 17.74% | 0 | PD profile candidates + LLM |
| B3_TPD | completed | 200/200 | 2657/4052 | 65.57% | 0 | T+PD candidates + LLM |
| B4_TPD | completed | 200/200 | 1245/4052 | 30.73% | 0 | deterministic rules over T+P+D field candidates |

## G 系列参考结果

G 系列已经在 `experiment5_eval200_20260503_r1` 跑完，可作为同一 eval200 样本的后台关系参考：

| 方法 | schema-valid | v2 正确/总数 | accuracy | failure_count | 边界 |
|---|---:|---:|---:|---:|---|
| G0_Direct | 200/200 | 1079/4052 | 26.63% | 0 | admin field-review direct_visible oracle replay |
| G1_Rules | 200/200 | 2380/4052 | 58.74% | 0 | admin field-review direct_visible + rule_default_completion oracle replay |
| G3_LLM_Rules | 200/200 | 284/4052 | 7.01% | 0 | no-leak gold observable facts + LLM |

## 过程记录

B2b 在第一次 eval200 运行中跑到 23/200 后遇到上游 usage-limit 错误。随后确认 `openai-oauth` 恢复，用 `--resume-existing` 继续补跑，避免重跑已成功样本；B2b、B3_T、B3_PD、B3_TPD 最终全部完成。当前最终结果中 A/B/G 全部方法 `failure_count = 0`。

## 当前结论

eval200 的实验组5 admin-relation 线已经跑齐。B3_T 最高：`2930/4052 = 72.31%`。B3_TPD 次高：`2657/4052 = 65.57%`。B2a 为 `2552/4052 = 62.98%`，高于 B2b 的 `1963/4052 = 48.45%`。A3 和 B4_TPD 均为 `1245/4052 = 30.73%`。

下一步应进入最终审阅：确认方法输入无泄漏、汇总 dev50/eval200 表格、提交并推送 git。
