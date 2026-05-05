# 实验组5 eval200 r6 strict reviewed 执行报告

- run_id: `experiment5_eval200_20260504_r6_strict_reviewed_runs`
- 日期: 2026-05-04
- 样本: eval200，200/200
- 本轮核心约束: 不重新 OCR、不重新准备 eval200 MA_TEXT；A3/B2 以及 B3/B4 中需要 MA_TEXT 的位置，统一使用 `formal_runs/experiment5/experiment5_eval200_20260504_r5_ma_text_ocr_review/inputs/gold_ma_text_eval200_ocr_reviewed.jsonl` 的 `gold_ma_prose`。

## 输入来源

| 方法 | 输入 | 方法含义 |
| --- | --- | --- |
| `A3_GoldText_Rules` | reviewed MA_TEXT `gold_ma_prose` | 只给正式 missed approach 文本，确定性规则解析。 |
| `B2a_GoldText_LLM` | reviewed MA_TEXT `gold_ma_prose` | 只给正式 missed approach 文本，让 LLM 输出 canonical JSON。 |
| `B2b_GoldText_FieldCandidates_LLM` | reviewed MA_TEXT + 从同一文本 regex 派生的候选 | 候选来自文本本身，不读取后台最终答案。 |
| `B3_T` | `roi_ocr_candidate_input_manifest_eval200_reviewed_strict.jsonl` 的 T profile | 只给 `[MISSED_APPROACH_TEXT]`，文本来自 reviewed MA_TEXT，并给区域内候选。 |
| `B3_PD` | 同一 manifest 的 PD profile | 只给 `[PLAN_VIEW]` + `[MISSED_APPROACH_DETAIL_AREA]` 的后台可见框、label 左半边、图形标记；不给 MA_TEXT。 |
| `B3_TPD` | 同一 manifest 的 TPD profile | reviewed MA_TEXT + PLAN/DETAIL 可见候选合并给 LLM。 |
| `B4_TPD` | 同 B3_TPD | 不调 LLM，使用确定性规则解析 TPD 输入。 |
| `G3_LLM_Rules` | `g_visible_observables_eval200_strict.jsonl` | answer-stripped 后台可见事实摘要；`admin_gold_answer` 只用于评分。 |

关键输入文件：

- MA_TEXT formal gold prose: `formal_runs/experiment5/experiment5_eval200_20260504_r5_ma_text_ocr_review/inputs/gold_ma_text_eval200_ocr_reviewed.jsonl`
- strict visible 输入目录: `formal_runs/experiment5/experiment5_eval200_20260504_r6_strict_visible_inputs`
- B3/B4 manifest: `formal_runs/experiment5/experiment5_eval200_20260504_r6_strict_reviewed_runs/manifests/roi_ocr_candidate_input_manifest_eval200_reviewed_strict.jsonl`
- G3 observable: `formal_runs/experiment5/experiment5_eval200_20260504_r6_strict_visible_inputs/inputs/g_visible_observables_eval200_strict.jsonl`

## 结果汇总

| 方法 | schema valid | scored | v2 正确/总数 | accuracy | schema retry | failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `A3_GoldText_Rules` | 200/200 | 200 | 2752/4052 | 67.92% | 0 | 0 |
| `B2a_GoldText_LLM` | 200/200 | 200 | 970/4052 | 23.94% | 17 | 0 |
| `B2b_GoldText_FieldCandidates_LLM` | 200/200 | 200 | 1100/4052 | 27.15% | 0 | 0 |
| `B3_T` | 200/200 | 200 | 1227/4052 | 30.28% | 3 | 0 |
| `B3_PD` | 200/200 | 200 | 84/4052 | 2.07% | 0 | 0 |
| `B3_TPD` | 200/200 | 200 | 1170/4052 | 28.87% | 1 | 0 |
| `B4_TPD` | 200/200 | 200 | 2718/4052 | 67.08% | 0 | 0 |
| `G3_LLM_Rules` | 200/200 | 200 | 265/4052 | 6.54% | 176 | 0 |

说明: 除 G3 外，v2 与 strict 分数相同；G3 strict 是 264/4052 = 6.52%。

## No-leakage 审查

- reviewed MA_TEXT: `PASS`，200 rows，forbidden key hits 0。
- strict visible inputs: `PASS`，2400 rows，forbidden key hits 0，forbidden value hits 0，interpreted `->` suffix hits 0。
- B3/B4 reviewed ROI manifest: `PASS`，600 rows，forbidden key hits 0。
- A3: `hard_leakage_detected=false`。
- B2: `hard_leakage_detected=false`。
- G3: `g3_uses_admin_gold_answer_for_prediction=false`，`g3_uses_field_review_for_prediction=false`，`g3_method_input_forbidden_key_hits=0`。

本轮没有把 `target`、`score`、`canonical_answer`、`canonical_leg_index`、`Q_terminator`、`leg_type`、`field_review_v2` 作为方法输入。

## 错误与问题

运行错误层面没有失败：A3/B2/B3/B4/G3 全部 `failure_count=0`，三个长任务日志 `stderr` 均为空。

需要注意的不是运行失败，而是方法表现：

1. `A3` 和 `B4_TPD` 都在 67% 左右，说明 reviewed MA_TEXT 足够支撑规则法恢复大部分字段，文本输入本身不是当前主要瓶颈。
2. `B2a/B2b/B3_T/B3_TPD` 明显低于规则法，说明当前 LLM prompt/schema 转换能力弱于规则解析；加文本候选能略微帮助 B2，但幅度有限。
3. `B3_PD` 只有 2.07%，这不是程序错误，而是 PD profile 不给 MA_TEXT，只靠 plan/detail 可见框和 label 很难恢复完整 missed approach。
4. `B3_TPD` 比 `B3_T` 还低一点，说明当前 prompt 下额外 PD 可见候选没有被 LLM 有效利用，甚至可能增加干扰。
5. `G3` 很低且 schema retry 很多；它的输入是稀疏的后台可见事实摘要，不是完整答案关系，所以 LLM 第一轮经常输出 schema 不合规，但 retry 后 200 个样本都成功评分。

## 已完成

1. 确认 eval200 reviewed MA_TEXT 文件存在、200 行、无 forbidden key，且全部以 `MISSED APPROACH:` 开头。
2. 用 `admin_regions_eval200.jsonl` 生成 strict visible 输入，供 PD/G3 使用。
3. 用 reviewed MA_TEXT + strict PD visible 输入生成 B3/B4 eval200 manifest。
4. 完整跑完 A3、B2a、B2b、B3_T、B3_PD、B3_TPD、B4_TPD、G3。
5. 记录 openai-oauth 可用入口为 `http://127.0.0.1:10531/v1`，本轮 LLM 方法均使用 `gpt-5.4`。

## 下一步

1. 做 eval200 错误归因，不在 eval200 上调参，优先看 `Q2_altitude_constraint`、`Q4_course_or_radial`、`Q_terminator`。
2. 对比 dev50 r6 与 eval200 r6，判断 dev50 观察是否泛化。
3. 如需论文表格，汇总 dev50/eval200 的 A3/B2/B3/B4/G3，并单独标注 G0/G1 是 oracle，不混入 blind 方法。
4. 如果继续优化，只能回到 dev50 改 prompt/规则；eval200 结果应作为锁定后的评估，不应用来反复调参。
