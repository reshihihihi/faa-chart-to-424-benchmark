# 实验组5 dev50 admin-relation 运行状态

更新时间：2026-05-03

## 输入状态

本轮使用已经生成的 dev50 admin-relation 输入：

- 运行目录：`formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation`
- A3/B2 gold text：`inputs/gold_ma_text_dev50_admin_relation.jsonl`
- B3/B4 manifest：`manifests/roi_admin_relation_candidate_input_manifest_dev50.jsonl`
- 输入分类：`admin_relation_oracle_textualized_inputs`
- charts：50
- B3/B4 profile rows：150
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
| A3_GoldText_Rules | completed | 50/50 | 303/1010 | 30.00% | 0 | deterministic rules over admin-relation textualized gold prose |
| B2a_GoldText_LLM | completed | 50/50 | 606/1010 | 60.00% | 0 | gold text + LLM |
| B2b_GoldText_FieldCandidates_LLM | completed | 50/50 | 509/1010 | 50.40% | 0 | gold text + field candidates + LLM |
| B3_T | completed | 50/50 | 722/1010 | 71.49% | 0 | T profile candidates + LLM |
| B3_PD | completed | 50/50 | 171/1010 | 16.93% | 0 | PD profile candidates + LLM |
| B3_TPD | completed | 50/50 | 660/1010 | 65.35% | 0 | T+PD candidates + LLM |
| B4_TPD | completed | 50/50 | 303/1010 | 30.00% | 0 | deterministic rules over T+P+D field candidates |

## G 系列参考结果

G 系列已经在 `experiment5_dev50_20260503_r1` 跑完，可作为同一 dev50 样本的后台关系参考：

| 方法 | schema-valid | v2 正确/总数 | accuracy | failure_count | 边界 |
|---|---:|---:|---:|---:|---|
| G0_Direct | 50/50 | 274/1010 | 27.13% | 0 | admin field-review direct_visible oracle replay |
| G1_Rules | 50/50 | 600/1010 | 59.41% | 0 | admin field-review direct_visible + rule_default_completion oracle replay |
| G3_LLM_Rules | 50/50 | 76/1010 | 7.52% | 0 | no-leak gold observable facts + LLM |

## 当前结论

dev50 的实验组5 admin-relation 线已经跑齐。B3_T 在 dev50 上最高：`722/1010 = 71.49%`。B2a 也明显高于 deterministic A3/B4：`606/1010 = 60.00%`。

dev50 后续不需要继续补跑。eval200 的 B2b/B3 也已经在同一 r2 admin-relation 目录中用 `openai-oauth` 和 `--resume-existing` 补齐；下一步是统一审阅 dev50/eval200 汇总并提交 git。
