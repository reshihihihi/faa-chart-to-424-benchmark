# 实验组5 r4 + A3/B2 当前状态

生成日期：2026-05-03

## 仓库状态

- repo: `https://github.com/reshihihihi/faa-chart-to-424-benchmark.git`
- branch: `experiment5-diagnostic-20260503`
- HEAD: `c69c184`
- 本地目录：`external_artifact://C/Users\admin\Documents\New project\faa-chart-to-424-benchmark-c69c184`

## r4 输入工件核对

路径：`formal_runs/experiment5/experiment5_smoke_20260503_r4_available_methods/`

已确认存在：

| 工件 | 状态 |
|---|---:|
| `inputs/` | 递归 60 files |
| `field_candidates/` | 递归 60 files |
| `field_candidates_validation/` | 递归 60 files |
| `B3_T/prompts/` | 20 files |
| `B3_TPD/prompts/` | 20 files |
| `B3_PD/prompts/` | 20 files |
| `B4_TPD/rule_diagnostics/` | 20 files |

r4 报告状态保持不变：

| 方法 | v2 正确/总数 | v2 accuracy |
|---|---:|---:|
| `B3_T` | 138/470 | 29.36% |
| `B3_TPD` | 126/470 | 26.81% |
| `B3_PD` | 8/470 | 1.70% |
| `B4_TPD` | 310/470 | 65.96% |

## r4 manifest SHA 注意事项

`benchmark_exports/derived/v2/experiment5_diagnostic/roi_ocr_candidate_input_manifest_smoke20.jsonl` 中 120 个 input/candidate 工件都存在。

当前 checkout 下原始 byte hash 与 manifest 不一致：`0/120`。把当前 LF 文件按 CRLF 归一化后，hash 与 manifest 一致：`120/120`。

解释：这是 Git checkout 换行归一化造成的 provenance hash 差异，不是工件缺失。正式归档前建议固定 `.gitattributes` 或生成 newline-normalized hash audit。

## gold_ma_prose 状态

文件：`benchmark_exports/derived/v2/experiment5_diagnostic/gold_ma_text_smoke20_template.jsonl`

- 模板行数：20
- 已填写：20
- review_status：`adjudicated`
- 来源：FAA chart PDF text layer + Experiment 5 MA_TEXT ROI OCR cross-check
- 禁用项：未使用 target、score、canonical_answer、canonical_leg_index、Q_terminator、leg_type、field_review_v2

辅助产物：

- `formal_runs/experiment5/experiment5_gold_ma_prose_20260503_r1/reports/gold_ma_prose_adjudication_notes.json`
- `formal_runs/experiment5/experiment5_gold_ma_prose_20260503_r1/reports/experiment5_gold_ma_readiness_audit_zh.md`

## A3 已执行

运行目录：`formal_runs/experiment5/experiment5_gold_text_20260503_r1/`

方法：`A3_GoldText_Rules`

输入边界：只给 `gold_ma_prose`，target/score 只在 prediction 写盘后用于评分。

| 方法 | schema-valid | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---:|---:|---:|---:|
| `A3_GoldText_Rules` | 20/20 | 342/470 | 72.77% | 72.77% |

字段族：

| 字段 | 正确/总数 | accuracy |
|---|---:|---:|
| `Q1_fix_ident` | 73/75 | 97.33% |
| `Q2_altitude_constraint` | 19/75 | 25.33% |
| `Q3_turn` | 68/75 | 90.67% |
| `Q4_course_or_radial` | 38/75 | 50.67% |
| `Q5_hold_params` | 54/75 | 72.00% |
| `Q_terminator` | 71/75 | 94.67% |
| `leg_count` | 19/20 | 95.00% |

No-leakage：

- `target_used_for_prediction`: false
- `score_used_for_prediction`: false
- `cifp_or_arinc_424_used_for_prediction`: false
- `field_review_v2_used_for_prediction`: false
- `hard_leakage_detected`: false
- `forbidden_key_hits`: `{}`

注意：`rule_registry.yaml` 仍是 candidate 状态，A3 结果可用于 smoke 诊断，但不应直接写成 formal claim。

## B2 已执行

运行目录：`formal_runs/experiment5/experiment5_gold_text_20260503_r1/`

模型服务：

- provider: `openai_compatible_via_openai_oauth`
- base_url: `http://127.0.0.1:8080/v1`
- model: `gpt-5.4`
- temperature: `0`
- max_tokens: `4096`
- schema_retry_count: `1`

| 方法 | schema-valid | retry | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---:|---:|---:|---:|---:|
| `B2a_GoldText_LLM` | 20/20 | 5 | 125/470 | 26.60% | 26.60% |
| `B2b_GoldText_FieldCandidates_LLM` | 20/20 | 0 | 137/470 | 29.15% | 29.15% |

No-leakage：

- `target_used_for_prediction`: false
- `score_used_for_prediction`: false
- `cifp_or_arinc_424_used_for_prediction`: false
- `field_review_v2_used_for_prediction`: false
- `hard_leakage_detected`: false
- `forbidden_key_hits`: `{}`

解释：B2b 比 B2a 略高，说明从 gold prose 自动抽出的弱候选对 LLM 有小幅帮助；但两者仍远低于 `A3_GoldText_Rules`，说明在 gold prose 条件下，当前 LLM 主要瓶颈不是 OCR，而是将 prose 稳定翻译成 canonical leg structure / path terminator。

## G 系列当前阻塞

`gold_observable_smoke20_template.jsonl` 仍为 0/20 adjudicated。不能从 field_review_v2 或 canonical target 派生。

下一步应单独制作无泄漏 `gold_observable`，只写可观察事实、显式缺失、source regions 和 evidence ids；禁止写 `Q_terminator`、canonical leg index、target value、score 或 final canonical JSON。

## 下一步

1. 审查并冻结 `rule_registry.yaml`，至少标明 direct fill、convention/default、424-derived rule。
2. 制作无泄漏 `gold_observable`，再跑 `G0_Direct`、`G1_Rules`；`G3_LLM_Rules` 继续使用当前 `openai-oauth` 模型服务。
3. A3/B2/G 完成后生成 smoke20 all-methods 总报告，再决定是否扩展到 formal200 或 diagnostic subset。
4. 后续需要加速时，优先做样本级并行；必须保持同一 model/prompt/temperature/schema retry，不要换成 `gpt-5.4-mini` 或减少输入。
