# 实验组 5 dev50 admin-relation 运行状态

更新时间：2026-05-03

## 输入状态

本轮使用已经生成的 dev50 admin-relation 输入：

- A3/B2 gold text：`inputs/gold_ma_text_dev50_admin_relation.jsonl`
- B3/B4 manifest：`manifests/roi_admin_relation_candidate_input_manifest_dev50.jsonl`
- 输入分类：`admin_relation_oracle_textualized_inputs`
- charts：50
- B3/B4 profile rows：150
- field_candidates schema validation errors：0
- serialized method payload forbidden key hits：0

注意：这条线是后台完整人工审核关系图派生输入，不是 blind OCR 线。

## 已运行结果

| 方法 | 状态 | schema-valid | v2 正确/总数 | accuracy | failure_count | 说明 |
|---|---|---:|---:|---:|---:|---|
| A3_GoldText_Rules | completed | 50/50 | 303/1010 | 30.00% | 0 | deterministic rules over admin-relation textualized gold prose |
| B2a_GoldText_LLM | blocked | 0/50 | 0/0 | NA | 50 | local model proxy returned invalidated OAuth token |
| B2b_GoldText_FieldCandidates_LLM | blocked | 0/50 | 0/0 | NA | 50 | local model proxy returned invalidated OAuth token |
| B4_TPD | completed | 50/50 | 303/1010 | 30.00% | 0 | deterministic rules over T+P+D field candidates |
| B3_T | not_run | NA | NA | NA | NA | depends on same broken LLM chat endpoint |
| B3_PD | not_run | NA | NA | NA | NA | depends on same broken LLM chat endpoint |
| B3_TPD | not_run | NA | NA | NA | NA | depends on same broken LLM chat endpoint |

## G 系列参考结果

G 系列已在 `experiment5_dev50_20260503_r1` 跑完，可作为同一 dev50 样本的后台关系参考：

| 方法 | schema-valid | v2 正确/总数 | accuracy | failure_count | 边界 |
|---|---:|---:|---:|---:|---|
| G0_Direct | 50/50 | 274/1010 | 27.13% | 0 | admin field-review direct_visible oracle replay |
| G1_Rules | 50/50 | 600/1010 | 59.41% | 0 | admin field-review direct_visible + rule_default_completion oracle replay |
| G3_LLM_Rules | 50/50 | 76/1010 | 7.52% | 0 | no-leak gold observable facts + LLM |

## 当前错误

B2 运行时，本地模型服务的 `/models` endpoint 能返回模型列表，但 `/chat/completions` 返回：

```text
HTTP 500
Encountered invalidated oauth token for user, failing request
```

这不是输入、schema、runner 的错误。它阻塞所有需要 LLM chat completions 的方法：

- B2a_GoldText_LLM
- B2b_GoldText_FieldCandidates_LLM
- B3_T
- B3_PD
- B3_TPD

已落盘的 B2 错误文件：

- `reports/b2_gold_text_summary.json`
- `reports/b2_gold_text_failures.jsonl`
- `logs/b2_run_stdout.log`
- `logs/b2_run_stderr.log`

## 已执行命令

```powershell
python scripts/experiment5/run_experiment5_gold_text_a3.py `
  --run-dir formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation `
  --gold-text formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation/inputs/gold_ma_text_dev50_admin_relation.jsonl `
  --limit 50 `
  --force

python scripts/experiment5/run_experiment5_gold_text_b2.py `
  --run-dir formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation `
  --gold-text formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation/inputs/gold_ma_text_dev50_admin_relation.jsonl `
  --methods B2a_GoldText_LLM,B2b_GoldText_FieldCandidates_LLM `
  --model gpt-5.4 `
  --base-url http://127.0.0.1:8080/v1 `
  --limit 50 `
  --max-workers 4 `
  --request-timeout 240 `
  --schema-retry-count 1 `
  --resume-existing `
  --force

python scripts/experiment5/run_experiment5_smoke_b3_b4.py `
  --run-dir formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation `
  --input-manifest formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation/manifests/roi_admin_relation_candidate_input_manifest_dev50.jsonl `
  --sample-scope experiment5_dev50_admin_relation `
  --methods B4_TPD `
  --limit 50 `
  --text-model gpt-5.4 `
  --openai-base-url http://127.0.0.1:8080/v1 `
  --schema-retry-count 1
```

## 下一步

1. 修复或刷新本地模型代理的 OAuth 状态。
2. 先用一个最小 `/chat/completions` 探针确认模型调用恢复。
3. 重跑 B2：

```powershell
python scripts/experiment5/run_experiment5_gold_text_b2.py `
  --run-dir formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation `
  --gold-text formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation/inputs/gold_ma_text_dev50_admin_relation.jsonl `
  --methods B2a_GoldText_LLM,B2b_GoldText_FieldCandidates_LLM `
  --model gpt-5.4 `
  --base-url http://127.0.0.1:8080/v1 `
  --limit 50 `
  --max-workers 4 `
  --request-timeout 240 `
  --schema-retry-count 1 `
  --resume-existing `
  --force
```

4. 再跑 B3：

```powershell
python scripts/experiment5/run_experiment5_smoke_b3_b4.py `
  --run-dir formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation `
  --input-manifest formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation/manifests/roi_admin_relation_candidate_input_manifest_dev50.jsonl `
  --sample-scope experiment5_dev50_admin_relation `
  --methods B3_T,B3_PD,B3_TPD `
  --limit 50 `
  --text-model gpt-5.4 `
  --openai-base-url http://127.0.0.1:8080/v1 `
  --schema-retry-count 1
```

5. 最后把 A3/B2/B3/B4/G 全方法合并成正式结果表。

