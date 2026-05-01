# Group 1 scoring-equivalence v2 完整结果包

本目录记录 Group 1 formal200 已完成预测在 scoring-equivalence v2 下的重评分结果。

本次 v2 不重跑任何 Group 1 方法，不修改已有 prediction JSON，不修改 canonical schema。它只在评分 target / scorer 层处理两类已确认的 chart-display equivalence：

1. Fix / navaid 名称显示形式差异。
2. Course / track / radial / hold inbound course 的 424 小数角度与航图整数显示差异。

以下内容仍保持严格比较：高度、turn、holding time、DME / distance、terminator、leg alignment、自动 reciprocal course/radial、Q_terminator。

## 关键结果

| method | strict accuracy | v2 accuracy | delta |
|---|---:|---:|---:|
| A1 | 29.22% | 29.22% | +0.00% |
| A2 | 22.61% | 22.61% | +0.00% |
| B1 | 27.25% | 27.39% | +0.15% |
| B1_prime | 32.16% | 32.28% | +0.12% |
| B1_prime_link | 19.49% | 19.49% | +0.00% |
| C1 | 37.09% | 39.39% | +2.30% |
| C2 | 23.94% | 26.51% | +2.57% |
| C3 | 38.28% | 40.07% | +1.79% |
| C4 | 40.08% | 40.42% | +0.35% |
| D_SFT | 73.55% | 78.14% | +4.59% |

所有 v2 changed rows 都是 old false -> new true；没有 old true -> new false。

## 文件位置

### 方案文档

- `docs/group1_scoring_equivalence_experiment_plan_zh.md`
- `docs/group1_scoring_equivalence_detailed_execution_plan_zh.md`

### 脚本

- `scripts/build_group1_scoring_equivalence_v2_targets.py`
- `scripts/scorers/group1_canonical_field_scorer_v2.py`
- `scripts/rescore_group1_scoring_equivalence_v2.py`

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

### 诊断报告

- `reports/freeze/group1_scoring_equivalence_v2_20260501_r1/group1_scoring_equivalence_v2_run_report_zh.md`
- `reports/freeze/group1_scoring_equivalence_v2_20260501_r1/scoring_equivalence_smoke_report.md`
- `reports/freeze/group1_scoring_equivalence_v2_20260501_r1/course_radial_diagnostics/`
- `reports/freeze/group1_scoring_equivalence_v2_20260501_r1/smoke/`

## 诊断结论

A1、A2、B1_prime_link 在 v2 下没有增量，原因不是 v2 规则未生效，而是它们很少稳定输出可比较的角度数值。对 A1/A2 的专项审查显示：

- A1 实际输出数字角度 8 个，其中 3 个对应 raw 424 小数 target。
- A2 实际输出数字角度 6 个，其中 2 个对应 raw 424 小数 target。
- 这些小数 target 案例仍未被 v2 救回，因为同时存在 direction、navaid、字段适用性或结构不匹配。

D_SFT 的提升主要来自 degree-display rounding：171 个 changed rows 中，151 个属于 `Q4_course_or_radial`，20 个属于 `Q5_hold_params.inbound_course_deg`。
