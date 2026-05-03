# 实验组 5 计划、当前状态与下一步

更新时间：2026-05-03

## 1. 核心更正

实验组 5 的权威输入源不是 OCR 本身，而是 shujuji 后台导出的人工审核关系图。这个后台能提供一套完整关系：

- region/box：MA_TEXT、PLAN_VIEW、DETAIL、FIX_TEXT、ALTITUDE_TEXT、HEADING_TEXT、RADIAL_TEXT、NAVAID_TEXT 等框。
- evidence relation：字段、证据框、来源范围之间的关系。
- field review：每个字段的人工审核结果、support_mode、evidence_region_ids。
- final answer：每个 chart 的最终 canonical PR28 JSON。

因此，实验组 5 应分清两条线：

- blind/no-leak 方法线：方法输入里不能出现 target、score、canonical_answer、canonical_leg_index、Q_terminator、leg_type、field_review_v2 等答案侧字段。
- admin-relation diagnostic/oracle 线：允许从后台完整人工审核关系图派生输入，用于诊断“如果框、航段、字段、证据关系、最终字段答案已经审核完成，方法能否正确消费这些关系”。这条线必须明确标记为 `admin_relation_oracle_textualized_inputs`，不能误称为 blind OCR。

## 2. 实验组 5 方法分组

当前计划按 50 样本先跑通，再扩展 200 evaluation 样本。

| 方法 | 输入 | 当前用途 |
|---|---|---|
| A3_GoldText_Rules | gold MA prose | 规则解析 gold missed-approach 文本 |
| B2a_GoldText_LLM | gold MA prose | LLM 从 gold 文本生成 canonical JSON |
| B2b_GoldText_FieldCandidates_LLM | gold MA prose + 从同一 prose 生成的 candidates | LLM 使用弱候选辅助 |
| B3_T | MISSED_APPROACH_TEXT ROI + candidates | LLM 只看 MA text 区域 |
| B3_PD | PLAN_VIEW + DETAIL ROI + candidates | LLM 不看 MA text，只看图面/细节区 |
| B3_TPD | T + P + D 合并输入 | LLM 综合三个区域 |
| B4_TPD | T + P + D candidates | deterministic rule baseline |
| G0_Direct | admin field_review 中 direct_visible 字段 | 后台关系 oracle replay |
| G1_Rules | direct_visible + rule_default_completion | 后台关系 oracle replay |
| G3_LLM_Rules | 去答案字段后的 gold_observable facts + LLM | no-leak observable diagnostic |

## 3. 已完成内容

### 3.1 后台导出与脚本

新增脚本：

- `scripts/experiment5/download_shujuji_admin_export.py`
  - 通过环境变量 `SHUJUJI_ADMIN_TOKEN` 下载后台 export。
  - 不把 token 写入仓库。
  - 原始下载放在 `downloads/`，该目录不提交。

修改脚本：

- `scripts/experiment5/export_admin_dev50_artifacts.py`
  - 支持 `--chart-manifest` alias。
  - 支持 `--artifact-label`，可导出 dev50/eval200 不同标签。

- `scripts/experiment5/build_experiment5_dev50_admin_observables.py`
  - 支持 `--chart-manifest` 和 `--artifact-label`。
  - 支持没有 overlay PNG 时仍生成 observable artifacts。

- `scripts/experiment5/run_experiment5_smoke_b3_b4.py`
  - 新增 `--input-manifest`，不再硬编码 smoke20 manifest。
  - 新增 `--sample-scope`。
  - `--limit 0` 表示使用 manifest 中全部 chart。

新增脚本：

- `scripts/experiment5/build_experiment5_admin_relation_method_inputs.py`
  - 将后台 `admin_gold_answer/admin_field_review/admin_regions` 转成：
    - A3/B2 的 `gold_ma_prose` JSONL。
    - B3/B4 的 ROI 文本。
    - B3/B4 的 field_candidates JSON。
    - B3/B4 的 input manifest。
  - 当前生成的序列化方法 payload 禁用键命中数为 0。
  - 该输入分类为 `admin_relation_oracle_textualized_inputs`。

### 3.2 dev50 后台 artifacts

路径：

- `formal_runs/experiment5/experiment5_dev50_20260503_r1/admin_artifacts/`

结果：

- charts：50
- field reviews：542
- regions：393
- evidence links：542
- gold answers：50
- schema errors：0

### 3.3 dev50 G 系列已运行

路径：

- `formal_runs/experiment5/experiment5_dev50_20260503_r1/reports/g_admin_summary.json`

结果：

| 方法 | 样本 | schema-valid | v2 正确/总数 | accuracy | failures |
|---|---:|---:|---:|---:|---:|
| G0_Direct | 50 | 50/50 | 274/1010 | 27.13% | 0 |
| G1_Rules | 50 | 50/50 | 600/1010 | 59.41% | 0 |
| G3_LLM_Rules | 50 | 50/50 | 76/1010 | 7.52% | 0 |

边界说明：

- G0/G1 是 admin field-review oracle replay，不是 blind predictor。
- G3 的方法输入禁用答案侧字段命中为 0。

### 3.4 eval200 G 系列已运行

路径：

- `formal_runs/experiment5/experiment5_eval200_20260503_r1/`

eval200 manifest：

- `formal_runs/experiment5/experiment5_eval200_20260503_r1/manifests/eval200_chart_manifest.jsonl`
- 数量：200
- 注意：此前误把 `previous_dataset_split` 也算入，得到 224；已修正为严格 `dataset_split == "evaluation"`。

eval200 admin artifacts：

- gold answers：200
- field reviews：2149
- regions：1585
- evidence links：2149

G 系列结果：

| 方法 | 样本 | schema-valid | v2 正确/总数 | accuracy | failures |
|---|---:|---:|---:|---:|---:|
| G0_Direct | 200 | 200/200 | 1079/4052 | 26.63% | 0 |
| G1_Rules | 200 | 200/200 | 2380/4052 | 58.74% | 0 |
| G3_LLM_Rules | 200 | 200/200 | 284/4052 | 7.01% | 0 |

备注：

- G3 曾有两个临时 schema failure，已通过 retry 修复。
- 最终 `failure_count=0`。

### 3.5 dev50 admin-relation 方法输入已生成

路径：

- `formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation/`

关键文件：

- A3/B2 gold text：
  - `inputs/gold_ma_text_dev50_admin_relation.jsonl`
- B3/B4 input manifest：
  - `manifests/roi_admin_relation_candidate_input_manifest_dev50.jsonl`
- B3/B4 ROI text：
  - `inputs/B3_T/*.txt`
  - `inputs/B3_PD/*.txt`
  - `inputs/B3_TPD/*.txt`
- B3/B4 candidates：
  - `field_candidates/B3_T/*.json`
  - `field_candidates/B3_PD/*.json`
  - `field_candidates/B3_TPD/*.json`
- summary：
  - `reports/admin_relation_method_inputs_dev50_summary.json`

生成结果：

- charts：50
- profile rows：150
- field_candidates schema validation errors：0
- serialized method payload forbidden key hits：0
- classification：`admin_relation_oracle_textualized_inputs`

已修正的问题：

- 对 `RADIAL_TEXT: R-045 -> type=navaid_radial, navaid=FQF, radial_deg=225.2, direction=inbound` 这类后台 label，候选优先采用右侧审核关系值 `225.2`，不误把左侧显示文本 `045` 当最终 radial candidate。

### 3.6 图片检查材料

已生成后台 MA_TEXT 框裁剪总览：

- `formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/`

包括：

- `dev50_admin_ma_text_crops_v2_sheet_1.png`
- `dev50_admin_ma_text_crops_v2_sheet_2.png`
- `dev50_admin_ma_text_crops_v2_sheet_3.png`
- `dev50_admin_ma_text_crops_v2_sheet_4.png`
- `dev50_admin_ma_text_crops_v2_sheet_5.png`

这些图用于人工确认后台 MA_TEXT 框是否适合派生/核对输入。

## 4. 当前没有完成的内容

### 4.1 2026-05-03 运行更新

在用户要求继续后，已用新版 admin-relation 输入运行了可运行部分：

- `A3_GoldText_Rules`：50/50 schema-valid，303/1010，30.00%，0 failures。
- `B4_TPD`：50/50 schema-valid，303/1010，30.00%，0 failures。
- `B2a_GoldText_LLM`：被本地模型代理 OAuth 失效阻塞，50 failures。
- `B2b_GoldText_FieldCandidates_LLM`：被本地模型代理 OAuth 失效阻塞，50 failures。
- `B3_T/B3_PD/B3_TPD`：同样依赖 `/chat/completions`，因本地模型代理 OAuth 失效暂未运行。

详细状态见：

- `formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation/reports/experiment5_dev50_admin_relation_run_status_zh.md`
- `formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation/reports/experiment5_dev50_admin_relation_combined_summary.json`

模型代理错误：

```text
HTTP 500
Encountered invalidated oauth token for user, failing request
```

### 4.2 B3 和 B2 的 LLM 方法仍未完成

仍待本地模型代理恢复后继续：

- B2a_GoldText_LLM
- B2b_GoldText_FieldCandidates_LLM
- B3_T
- B3_PD
- B3_TPD

### 4.3 eval200 的 A/B/B3/B4 尚未跑

eval200 目前只完成了 admin artifacts、gold observable 和 G 系列。

下一步应该先用 dev50 跑通新版 admin-relation 输入，再扩展 eval200，避免把输入边界错误放大到 200 样本。

## 5. 下一步建议

### 第一步：用户确认输入

重点看：

- `inputs/gold_ma_text_dev50_admin_relation.jsonl`
- `inputs/B3_T/*.txt`
- `inputs/B3_PD/*.txt`
- `inputs/B3_TPD/*.txt`
- `field_candidates/B3_TPD/*.json`
- `visuals/admin_ma_text_crops_v2/*.png`

确认问题：

- 后台框是否正确。
- admin-relation textualized prose 是否可以作为 A3/B2 的输入。
- B3_PD 是否应该只使用 PLAN_VIEW/DETAIL 中的框和关系，还是也允许从 field_review 派生更多文本候选。
- B3_TPD/B4_TPD 是否接受当前 T+P+D 合并方式。

### 第二步：恢复模型代理后运行 dev50 B2/B3

`A3_GoldText_Rules` 和 `B4_TPD` 已完成。模型代理恢复后，建议先重跑 B2，再跑 B3：

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

### 第三步：汇总 dev50 全方法结果

需要新增或生成统一汇总表，至少包含：

- A3/B2/B3/B4/G 全方法 accuracy。
- schema-valid 数量。
- failures。
- 输入边界分类：blind/no-leak 或 admin-relation oracle。
- 哪些方法用了后台 final answer 派生输入。

### 第四步：扩展 eval200

dev50 输入和结果确认后，按同样流程生成 eval200 的 admin-relation A/B/B3/B4 输入，然后运行 eval200。

建议新目录：

- `formal_runs/experiment5/experiment5_eval200_20260503_r2_admin_relation/`

### 第五步：最终 formal claim

最终论文/报告结论必须按输入边界分开写：

- OCR/no-leak 结果。
- gold text 结果。
- admin-relation oracle diagnostic 结果。
- 后台人工审核关系作为上界/诊断，不可混成 blind model performance。

## 6. Git 提交边界

本次应提交：

- 新增/修改脚本。
- dev50 后台 artifacts、observables、G 系列结果。
- eval200 admin artifacts、observables、G 系列结果。
- dev50 admin-relation 方法输入。
- 图片检查材料。
- 本计划与交接文档。

不应提交：

- `downloads/` 下原始后台 export。
- admin token。
- 无关旧临时目录，除非明确需要保留对应 smoke 运行结果。
