# 下一个 Codex 对话可直接输入的指令

请继续实验组 5。先不要重新理解成 OCR 任务：实验组 5 当前的权威输入源是 shujuji 后台人工审核关系图。后台提供完整的框、航段、字段、证据关系和最终字段答案关系；当前已经把这些关系派生成 dev50 admin-relation 方法输入。

repo:

```text
https://github.com/reshihihihi/faa-chart-to-424-benchmark.git
```

branch:

```text
experiment5-diagnostic-20260503
```

请先执行：

```powershell
git clone https://github.com/reshihihihi/faa-chart-to-424-benchmark.git
cd faa-chart-to-424-benchmark
git checkout experiment5-diagnostic-20260503
git pull
git log -1 --oneline
```

然后读取：

```text
formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation/reports/experiment5_plan_status_and_next_steps_zh.md
formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation/reports/admin_relation_method_inputs_dev50_summary.json
formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation/inputs/gold_ma_text_dev50_admin_relation.jsonl
formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation/manifests/roi_admin_relation_candidate_input_manifest_dev50.jsonl
```

当前已完成：

- dev50 后台 artifacts 导出：50 charts、542 field reviews、393 regions、542 evidence links、50 gold answers。
- dev50 G 系列已跑：
  - G0_Direct：274/1010 = 27.13%，0 failures。
  - G1_Rules：600/1010 = 59.41%，0 failures。
  - G3_LLM_Rules：76/1010 = 7.52%，0 failures。
- eval200 G 系列已跑：
  - G0_Direct：1079/4052 = 26.63%，0 failures。
  - G1_Rules：2380/4052 = 58.74%，0 failures。
  - G3_LLM_Rules：284/4052 = 7.01%，0 failures。
- dev50 admin-relation 方法输入已生成：
  - A3/B2：`inputs/gold_ma_text_dev50_admin_relation.jsonl`
  - B3/B4 manifest：`manifests/roi_admin_relation_candidate_input_manifest_dev50.jsonl`
  - field_candidates schema validation errors：0
  - serialized method payload forbidden key hits：0
- dev50 admin-relation 可运行部分已跑：
  - A3_GoldText_Rules：303/1010 = 30.00%，50/50 schema-valid，0 failures。
  - B4_TPD：303/1010 = 30.00%，50/50 schema-valid，0 failures。
- dev50 B2/B3 的 LLM 方法被本地模型代理 OAuth 失效阻塞：
  - `/models` 能返回模型列表。
  - `/chat/completions` 返回 HTTP 500：`Encountered invalidated oauth token for user, failing request`。
  - B2a/B2b 已记录 100 个 proxy failures。
  - B3_T/B3_PD/B3_TPD 尚未运行，以免把同一个代理错误刷满结果目录。

非常重要：

- 不要把这条线误称为 blind OCR。
- 当前 dev50 admin-relation 输入分类是 `admin_relation_oracle_textualized_inputs`。
- 方法输入文件本身没有 `target`、`score`、`canonical_answer`、`canonical_leg_index`、`Q_terminator`、`leg_type`、`field_review_v2` 这些禁用键。
- 但这些输入是从后台完整人工审核关系图派生出来的，包含最终字段答案关系的文本化结果，所以它是 admin-relation diagnostic/oracle lane。

下一步先修复/刷新本地模型代理 OAuth。确认 `/chat/completions` 能成功后，继续运行 dev50 B2/B3：

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

跑完后请输出：

- A3/B2/B3/B4/G 的统一结果表。
- 每个方法的 schema-valid、accuracy、failure_count。
- 哪些方法是 blind/no-leak，哪些方法是 admin-relation oracle diagnostic。
- 若有错误，列出具体 chart_id、方法、错误文件路径。
