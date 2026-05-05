# 实验组5 dev50 r6 严格 reviewed 输入运行报告

- run_id: `experiment5_dev50_20260504_r6_strict_reviewed_runs`
- 时间: 2026-05-04
- 样本: dev50，50/50
- 本轮目标: 用后台人工框/关系派生的合法可见输入，加上用户校正后的 MA_TEXT 可见文字，把实验组5 dev50 跑通；禁止把 `target`、`score`、`canonical_answer`、`canonical_leg_index`、`Q_terminator`、`leg_type`、`field_review_v2` 作为 blind 方法输入。

## 本轮输入来源

| 方法 | 输入 | 说明 |
| --- | --- | --- |
| `A3_GoldText_Rules` | `formal_runs/experiment5/experiment5_dev50_20260504_r5_ma_text_ocr_review/inputs/gold_ma_text_dev50_ocr_reviewed.jsonl` | MA_TEXT 框内文字，经 OCR/用户人工校正，全部以 `MISSED APPROACH:` 开头；规则解析。 |
| `B2a_GoldText_LLM` | 同 A3 的 reviewed MA prose | 只给 LLM 正式 MA 文字，不给字段候选。 |
| `B2b_GoldText_FieldCandidates_LLM` | reviewed MA prose + 从同一 prose 自动 regex 派生的候选 | 候选不是答案侧字段，不读后台 final/canonical。 |
| `B3_T` | `roi_ocr_candidate_input_manifest_dev50_reviewed_strict.jsonl` 中 T profile | 只给 `[MISSED_APPROACH_TEXT]` reviewed 文字和区域候选。 |
| `B3_PD` | 同 manifest 中 PD profile | 只给 `[PLAN_VIEW]` + `[MISSED_APPROACH_DETAIL_AREA]` 的后台可见框/label/candidate；刻意不提供 MA_TEXT。 |
| `B3_TPD` | 同 manifest 中 TPD profile | MA_TEXT + PLAN_VIEW + detail area 合并输入。 |
| `B4_TPD` | 同 B3_TPD | 不调用模型，用确定性规则。 |
| `G3_LLM_Rules` | `formal_runs/experiment5/experiment5_dev50_20260504_r3_strict_no_leak/inputs/g_visible_observables_dev50_strict.jsonl` | answer-stripped 后台 observable；admin gold 只用于评分。 |

本轮没有把 `G0_Direct` / `G1_Rules` 混进 blind 结果表。它们是 oracle 诊断，会刻意使用后台答案侧 field-review 关系，不能和 A/B/G3 这类 blind 方法混同解释。

## 结果汇总

| 方法 | schema valid | scored | strict score | accuracy | failures |
| --- | ---: | ---: | ---: | ---: | ---: |
| `A3_GoldText_Rules` | 50/50 | 50 | 670/1010 | 66.34% | 0 |
| `B2a_GoldText_LLM` | 50/50 | 50 | 237/1010 | 23.47% | 0 |
| `B2b_GoldText_FieldCandidates_LLM` | 50/50 | 50 | 294/1010 | 29.11% | 0 |
| `B3_T` | 50/50 | 50 | 286/1010 | 28.32% | 0 |
| `B3_PD` | 50/50 | 50 | 17/1010 | 1.68% | 0 |
| `B3_TPD` | 50/50 | 50 | 273/1010 | 27.03% | 0 |
| `B4_TPD` | 50/50 | 50 | 664/1010 | 65.74% | 0 |
| `G3_LLM_Rules` | 50/50 | 50 | 56/1010 | 5.54% | 0 |

`score_v2` 与 `score_strict` 本轮相同。

## 主要结论

1. `A3` 和 `B4_TPD` 最高，说明在已有合法 MA_TEXT 文字的情况下，当前确定性规则能稳定吃到大部分信息。`B4_TPD` 只比 `A3` 低 0.60 个百分点。
2. `B3_PD` 几乎失效，说明只靠 plan/detail area 的可见框和 label，不足以重建完整 missed approach 指令；MA_TEXT 仍是关键证据源。
3. `B3_T` / `B3_TPD` 明显低于 `A3/B4`，不是输入缺失导致，而是当前 LLM prompt/schema 转换能力弱于规则解析。加入 PD 后没有提升，说明 PD 当前候选还没有被 LLM 有效利用。
4. `B2b` 比 `B2a` 好，说明从 reviewed MA prose 派生的候选对 LLM 有帮助，但仍远低于规则方法。
5. `G3` 很低，说明 answer-stripped observable 虽然无泄漏，但它现在更像后台框/关系摘要，不足以让 LLM 直接恢复 canonical missed approach。

## 本轮问题与处理

- 旧的 `http://127.0.0.1:8080/v1` 服务返回 `Your authentication token has been invalidated`。这不是实验输入错误。已改用 `openai-oauth-runtime` 暴露的 `http://127.0.0.1:10531/v1`，最小 chat 请求验证通过，随后 B2/B3/G3 均成功运行。
- `G3` 第一次有 2 个 schema 错误，都是模型把 `Q4_course_or_radial` 的 navaid radial 字段写成 schema 不接受的键。已用 `--resume-existing --schema-retry-count 3` 只重跑失败样本，最终 failure_count 为 0。
- B2 runner 原先 run_manifest 里残留 `sample_scope: experiment5_smoke20_gold_ma_prose` 的旧命名。本轮已给 runner 增加 `--sample-scope` 并重写为 `experiment5_dev50_strict_reviewed_ma_text`。

## No-leakage 审查

- reviewed MA text: `ma_text_ocr_reviewed_no_leakage_report.json`，`PASS`，50 rows，forbidden key hits 0。
- reviewed ROI manifest: `roi_reviewed_input_no_leakage_report.json`，`PASS`，150 rows，forbidden key hits 0。
- A3: `hard_leakage_detected=false`，forbidden key hits `{}`。
- B2: `hard_leakage_detected=false`，forbidden key hits `{}`。
- G3: `g3_uses_admin_gold_answer_for_prediction=false`，`g3_uses_field_review_for_prediction=false`，`g3_method_input_forbidden_key_hits=0`。
- B3/B4 的 run manifest 记录 `target_used_for_prediction=false`、`score_used_for_prediction=false`、`gold_observable_used_for_prediction=false`，并且 `reviewed_ma_text_used_for_prediction=true`。

## 已完成

1. 确认 r5 reviewed MA_TEXT 输入可用并无泄漏。
2. 从 reviewed MA_TEXT + r3 strict PD visible inputs 生成 r6 B3/B4 ROI candidate manifest。
3. 跑完 A3/B2/B3/B4/G3 dev50。
4. 修复 `openai-oauth` 使用端口，从坏的 8080 切到可用的 10531。
5. 修复 G3 schema 残留错误。
6. 修复 B2 manifest 的 dev50 sample_scope 命名。

## 下一步

1. 固定 dev50 输入策略：MA_TEXT 必须来自后台 MA_TEXT 框的可见文字 OCR/人工校正；PD 输入只允许后台可见框/label/candidate，不允许答案侧字段。
2. 做 dev50 错误归因：优先看 `Q2_altitude_constraint`、`Q_terminator`、`Q4_course_or_radial`，以及 `B3_PD` 为什么几乎不能恢复有效 leg。
3. 如果 dev50 输入策略确认，按同一规则准备 eval200：200 个样本也要生成 reviewed MA_TEXT、PD visible candidates、TPD manifest 和 no-leakage 报告。
4. eval200 只在 dev50 策略固定后运行；不能用 eval200 调 prompt 或改规则。
5. 如需 oracle 诊断，可单独跑 `G0_Direct/G1_Rules` 并明确标注它们使用答案侧人工审核关系，不能作为 blind 方法效果。

## 给下一个对话的指令

```text
请继续实验组5 eval200 准备与运行。

repo: https://github.com/reshihihihi/faa-chart-to-424-benchmark.git
branch: experiment5-diagnostic-20260503

先读取：
formal_runs/experiment5/experiment5_dev50_20260504_r6_strict_reviewed_runs/reports/experiment5_dev50_r6_strict_reviewed_execution_report_zh.md

dev50 已完成严格 reviewed 输入运行：
- A3/B2/B3/B4/G3 均已跑完，failure_count 0。
- openai-oauth 可用 base URL 是 http://127.0.0.1:10531/v1，不要用旧的 8080。
- blind 方法严禁使用 target、score、canonical_answer、canonical_leg_index、Q_terminator、leg_type、field_review_v2、accepted_mappings.final_value、annotation_pr28_json 作为输入。

下一步先准备 eval200 的同构输入，不要直接调参：
1. 从 shujuji admin 后台框/关系导出 eval200 的 visible artifacts。
2. 对 eval200 MA_TEXT 框内文字做 OCR/人工校正，生成 reviewed gold_ma_text eval200 jsonl。
3. 从 reviewed MA_TEXT + strict PD visible candidates 生成 eval200 ROI candidate manifest。
4. 跑 no-leakage 审查。
5. 按 dev50 已固定方法运行 A3/B2/B3/B4/G3 eval200。
6. G0/G1 只作为 oracle 诊断单独报告，不能混入 blind 方法效果。
```
