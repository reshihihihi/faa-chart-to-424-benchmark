# 实验组5 eval200 admin-relation 运行状态

更新时间：2026-05-03

## 输入状态

本轮使用 `experiment5_eval200_20260503_r1` 中已经导出的 shujuji 后台人工审核关系，生成新的 eval200 admin-relation 方法输入：

- 运行目录：`formal_runs/experiment5/experiment5_eval200_20260503_r2_admin_relation`
- A3/B2 gold text：`inputs/gold_ma_text_eval200_admin_relation.jsonl`
- B3/B4 manifest：`manifests/roi_admin_relation_candidate_input_manifest_eval200.jsonl`
- 输入分类：`admin_relation_oracle_textualized_inputs`
- chart 数：200
- B3/B4 profile 行数：600
- field candidate schema validation errors：0
- serialized method payload forbidden key hits：0

说明：这条线来自后台完整人工审核关系图，包括框、航段、字段、证据关系和最终字段答案；不是 blind OCR 输入线。序列化后的方法输入没有使用禁用 key 名称：`target`、`score`、`canonical_answer`、`canonical_leg_index`、`Q_terminator`、`leg_type`、`field_review_v2`。

## 已运行结果

| 方法 | 状态 | schema-valid | v2 正确/总数 | accuracy | failure_count | 说明 |
|---|---|---:|---:|---:|---:|---|
| A3_GoldText_Rules | completed | 200/200 | 1245/4052 | 30.73% | 0 | deterministic rules over admin-relation textualized gold prose |
| B4_TPD | completed | 200/200 | 1245/4052 | 30.73% | 0 | deterministic rules over T+P+D field candidates |
| B2a_GoldText_LLM | not_run | NA | NA | NA | NA | local model proxy OAuth blocked |
| B2b_GoldText_FieldCandidates_LLM | not_run | NA | NA | NA | NA | local model proxy OAuth blocked |
| B3_T | not_run | NA | NA | NA | NA | depends on same broken LLM chat endpoint |
| B3_PD | not_run | NA | NA | NA | NA | depends on same broken LLM chat endpoint |
| B3_TPD | not_run | NA | NA | NA | NA | depends on same broken LLM chat endpoint |

## G 系列参考结果

G 系列已经在 `experiment5_eval200_20260503_r1` 跑完，可作为同一 eval200 样本的后台关系参考：

| 方法 | schema-valid | v2 正确/总数 | accuracy | failure_count | 边界 |
|---|---:|---:|---:|---:|---|
| G0_Direct | 200/200 | 1079/4052 | 26.63% | 0 | admin field-review direct_visible oracle replay |
| G1_Rules | 200/200 | 2380/4052 | 58.74% | 0 | admin field-review direct_visible + rule_default_completion oracle replay |
| G3_LLM_Rules | 200/200 | 284/4052 | 7.01% | 0 | no-leak gold observable facts + LLM |

## 当前阻塞

本地模型服务 `/v1/models` 可以返回模型列表，但 `/v1/chat/completions` 最小探针返回：

```text
HTTP 500
Encountered invalidated oauth token for user, failing request
```

因此所有需要 LLM chat completions 的方法仍然阻塞：

- B2a_GoldText_LLM
- B2b_GoldText_FieldCandidates_LLM
- B3_T
- B3_PD
- B3_TPD

这不是 eval200 admin-relation 输入、schema 或 deterministic runner 的错误。

## 已执行命令

```powershell
python scripts/experiment5/build_experiment5_admin_relation_method_inputs.py `
  --run-dir formal_runs/experiment5/experiment5_eval200_20260503_r1 `
  --output-dir formal_runs/experiment5/experiment5_eval200_20260503_r2_admin_relation `
  --artifact-label eval200

python scripts/experiment5/run_experiment5_gold_text_a3.py `
  --run-dir formal_runs/experiment5/experiment5_eval200_20260503_r2_admin_relation `
  --gold-text formal_runs/experiment5/experiment5_eval200_20260503_r2_admin_relation/inputs/gold_ma_text_eval200_admin_relation.jsonl `
  --limit 200 `
  --force

python scripts/experiment5/run_experiment5_smoke_b3_b4.py `
  --run-dir formal_runs/experiment5/experiment5_eval200_20260503_r2_admin_relation `
  --input-manifest formal_runs/experiment5/experiment5_eval200_20260503_r2_admin_relation/manifests/roi_admin_relation_candidate_input_manifest_eval200.jsonl `
  --sample-scope experiment5_eval200_admin_relation `
  --methods B4_TPD `
  --limit 200 `
  --text-model gpt-5.4 `
  --openai-base-url http://127.0.0.1:8080/v1 `
  --schema-retry-count 1
```

## 下一步

1. 修复或刷新本地模型代理的 OAuth 状态。
2. 先用最小 `/v1/chat/completions` 探针确认模型调用恢复。
3. 回到 dev50，补跑 B2a/B2b/B3_T/B3_PD/B3_TPD。
4. dev50 全部完成后，再补跑 eval200 的 B2a/B2b/B3_T/B3_PD/B3_TPD。
5. 汇总 dev50 与 eval200 全部方法，形成最终实验组5结果表。
