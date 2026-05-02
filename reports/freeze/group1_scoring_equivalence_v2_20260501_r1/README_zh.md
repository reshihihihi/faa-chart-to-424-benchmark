# Group 1 scoring-equivalence v2 完整结果包

本目录记录 Group 1 formal200 已完成预测在 scoring-equivalence v2 下的重评分结果，并补入 D1 对 D-SFT raw output 的固定 canonical JSON 输出接口结果。

本次 v2 不重跑 A1/A2/B1/B1_prime/B1_prime_link/C1/C2/C3/C4 的模型或规则，不修改这些方法已有 prediction JSON，不修改 canonical schema。它只在评分 target / scorer 层处理两类已确认的 chart-display equivalence：

1. Fix / navaid 名称显示形式差异。
2. Course / track / radial / hold inbound course 的 424 小数角度与航图整数显示差异。

以下内容仍保持严格比较：高度、turn、holding time、DME / distance、terminator、leg alignment、自动 reciprocal course/radial、Q_terminator。

## 关键结果

| method | strict accuracy | v2 accuracy | delta | schema valid / files |
|---|---:|---:|---:|---:|
| A1 | 29.22% | 29.22% | +0.00% | 200 / 200 |
| A2 | 22.61% | 22.61% | +0.00% | 200 / 200 |
| B1 | 27.25% | 27.39% | +0.15% | 200 / 200 |
| B1_prime | 32.16% | 32.28% | +0.12% | 200 / 200 |
| B1_prime_link | 19.49% | 19.49% | +0.00% | 185 / 200 |
| C1 | 37.09% | 39.39% | +2.30% | 200 / 200 |
| C2 | 23.94% | 26.51% | +2.57% | 200 / 200 |
| C3 | 38.28% | 40.07% | +1.79% | 196 / 198 |
| C4 | 40.08% | 40.42% | +0.35% | 200 / 200 |
| D_SFT | 73.55% | 78.14% | +4.59% | 184 / 196 |
| D1 | 73.35% | 77.94% | +4.59% | 200 / 200 |

说明：`D_SFT` 是原始 SFT 方法在已有 canonical prediction 文件上的重评分；`D1` 是把 D-SFT raw output 规范为固定 canonical JSON 输出接口后的结果。D1 不使用 target、score、424 raw、OCR 文本、field candidates 或其他方法输出来修正字段答案；它只解决输出格式/外壳合法性问题，因此 D1 的分母是完整 200 张、4052 个字段。

所有 v2 changed rows 都是 old false -> new true；没有 old true -> new false。

## D1 输出接口补齐结果

- run_id: `group1_formal200_D1_20260502_r4`
- policy_id: `d1_output_canonicalization_20260502_r4`
- raw output 找到: 200/200
- canonical JSON 写出: 200/200
- schema-valid: 200/200
- schema-invalid: 0/200
- D1 v2 field-level score: 3158 / 4052 = 77.94%

## 文件位置

### 方案文档

- `docs/group1_scoring_equivalence_experiment_plan_zh.md`
- `docs/group1_scoring_equivalence_detailed_execution_plan_zh.md`
- `docs/d1_method_card_zh.md`
- `docs/d1_output_canonicalization_policy_zh.md`

### 脚本

- `scripts/build_group1_scoring_equivalence_v2_targets.py`
- `scripts/scorers/group1_canonical_field_scorer_v2.py`
- `scripts/rescore_group1_scoring_equivalence_v2.py`
- `scripts/run_d1_output_canonicalizer.py`

### v2 target / policy

- `benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/canonical_proxy_gt_chart_display_v2.json`
- `benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/field_targets_chart_display_v2.jsonl`
- `benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/comparison_policy_v2.jsonl`
- `benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/target_v1_to_v2_diff.jsonl`
- `benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/risk_field_inventory.jsonl`
- `benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/target_v2_summary.md`

### formal200 重评分结果

- `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/reports/old_vs_new_score_delta.csv`
- `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/reports/scoring_equivalence_audit.md`
- `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/reports/*_summary_v2.json`
- `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/reports/*_changed_rows_v2.jsonl`
- `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/scores/`

### D1 完整产物

- `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/D1/`
- `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/D1/reports/D1_summary.json`
- `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/D1/reports/D1_per_sample.jsonl`

### 诊断报告

- `reports/freeze/group1_scoring_equivalence_v2_20260501_r1/group1_scoring_equivalence_v2_run_report_zh.md`
- `reports/freeze/group1_scoring_equivalence_v2_20260501_r1/d1_result_zh.md`
- `reports/freeze/group1_scoring_equivalence_v2_20260501_r1/scoring_equivalence_smoke_report.md`
- `reports/freeze/group1_scoring_equivalence_v2_20260501_r1/course_radial_diagnostics/`
- `reports/freeze/group1_scoring_equivalence_v2_20260501_r1/smoke/`

## 诊断结论

A1、A2、B1_prime_link 在 v2 下没有增量，原因不是 v2 规则未生效，而是它们很少稳定输出可比较的角度数值。对 A1/A2 的专项审查显示：

- A1 实际输出数字角度 8 个，其中 3 个对应 raw 424 小数 target。
- A2 实际输出数字角度 6 个，其中 2 个对应 raw 424 小数 target。
- 这些小数 target 案例仍未被 v2 救回，因为同时存在 direction、navaid、字段适用性或结构不匹配。

D_SFT 与 D1 的提升主要来自 degree-display rounding。D1 同时把 D-SFT raw output 的 200 张全部恢复为合法 canonical JSON，使 D 方法可以按固定接口进入正式对比。
