# Bootstrap / paired-delta 执行记录

执行日期：2026-05-04；实验组4补充 bootstrap：2026-05-05

配置文件：

```text
configs/bootstrap_paired_delta_policy.json
```

统计脚本：

```text
scripts/scorers/compute_bootstrap_paired_delta.py
```

统一设置：

- bootstrap 次数：10000
- confidence interval：95%
- 重采样单位：`chart_id`
- paired delta 定义：`metric(method_a) - metric(method_b)`
- 统计输入：只读取已经完成的 score / per-sample / method_summary 结果

## 1. 执行结果总览

| analysis set | smoke | formal 10000 | 输出目录 | 备注 |
|---|---|---|---|---|
| `group1_scoring_equivalence_v2` | 通过 | 已完成 | `reports/statistics/group1_scoring_equivalence_v2/` | 有缺失样本按预注册规则补 0，详见下方 |
| `group1_c2_model_method_effect_20260504` | 通过 | 已完成 | `reports/statistics/group1_c2_model_method_effect_20260504/` | 无 warning |
| `experiment4_source_ablation_formal200_main_6x3` | 通过 | 已完成 | `reports/statistics/experiment4_source_ablation_formal200_main_6x3/` | V1-V5 逐 chart CSV 已补齐，warning 为空 |
| `experiment5_eval200_r6_strict_reviewed` | 通过 | 已完成 | `reports/statistics/experiment5_eval200_r6_strict_reviewed/` | 已把 G3 的真实逐样本来源接入配置 |
| `experiment6_v11_pr25_d1_counterfactual` | 通过 | 已完成 | `reports/statistics/experiment6_v11_pr25_d1_counterfactual/` | 无 warning |

## 2. 实验组1主表

输出：

```text
reports/statistics/group1_scoring_equivalence_v2/
```

warning：

- `D_SFT` 被排除，因为它不是正式主榜方法。
- `B1_prime_link` 缺 15 个 chart，按 `zero_correct_with_unit_total` 补 0。
- `C3` 缺 4 个 chart，按 `zero_correct_with_unit_total` 补 0。

point estimate：

| 方法 | Correct/Total | Accuracy | 95% CI |
|---|---:|---:|---:|
| `A1` | 1184/4052 | 29.22% | 26.83% - 31.68% |
| `A2` | 916/4052 | 22.61% | 20.00% - 25.27% |
| `B1` | 1110/4052 | 27.39% | 25.36% - 29.50% |
| `B1_prime` | 1308/4052 | 32.28% | 30.31% - 34.26% |
| `B1_prime_link` | 718/4052 | 17.72% | 15.81% - 19.69% |
| `C1` | 1596/4052 | 39.39% | 37.79% - 41.01% |
| `C2` | 1074/4052 | 26.51% | 25.09% - 27.96% |
| `C3` | 1593/4052 | 39.31% | 37.33% - 41.30% |
| `C4` | 1638/4052 | 40.42% | 37.54% - 43.40% |
| `D1` | 3158/4052 | 77.94% | 75.06% - 80.73% |

## 3. 实验组1 GPT-5.4 C2 桥接分析

输出：

```text
reports/statistics/group1_c2_model_method_effect_20260504/
```

point estimate：

| 方法 | Correct/Total | Accuracy | 95% CI |
|---|---:|---:|---:|
| `C2_CLAUDE_original` | 1074/4052 | 26.51% | 25.09% - 27.96% |
| `C2_CLAUDE_batched_leg` | 1397/4052 | 34.48% | 33.04% - 35.92% |
| `C2_GPT54_batched_leg` | 1884/4052 | 46.50% | 44.61% - 48.37% |

paired delta：

| 比较 | delta | 95% CI | 含义 |
|---|---:|---:|---|
| `C2_CLAUDE_batched_leg - C2_CLAUDE_original` | +7.97 pp | +6.18 pp - +9.78 pp | 固定 Claude，测 batched-leg 结构效应 |
| `C2_GPT54_batched_leg - C2_CLAUDE_batched_leg` | +12.02 pp | +9.58 pp - +14.40 pp | 固定 batched-leg，测 GPT-5.4 模型效应 |
| `C2_GPT54_batched_leg - C2_CLAUDE_original` | +19.99 pp | +18.01 pp - +22.03 pp | 结构变化 + 模型变化的混合差异 |

## 4. 实验组4

输出：

```text
reports/statistics/experiment4_source_ablation_formal200_main_6x3/
```

本次修正：

- 已补齐实验组4 V1-V5 的逐 chart CSV：`formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1/scores/v2/<variant>/<method>/per_sample_scores.csv`。
- 已把实验组4 bootstrap 配置改为读取这些逐 chart CSV，而不是旧的 `runs/formal_eval200/*/<method>/scores_v2/*.json` 路径。
- smoke 通过，正式 10000 次 bootstrap 已完成。
- `bootstrap_run_manifest.json` 中 `warnings=[]`，`n_units=200`，方法数为 18，paired delta 行数为 153。

point estimate：

| 方法 | Correct/Total | Accuracy | 95% CI |
|---|---:|---:|---:|
| `V0_full_chart__B1` | 1110/4052 | 27.39% | 25.36% - 29.50% |
| `V0_full_chart__C4` | 1638/4052 | 40.42% | 37.54% - 43.40% |
| `V0_full_chart__D1` | 3158/4052 | 77.94% | 75.06% - 80.73% |
| `V1_ma_text_only__B1` | 1166/4052 | 28.78% | 26.89% - 30.75% |
| `V1_ma_text_only__C4` | 1948/4052 | 48.08% | 44.98% - 51.12% |
| `V1_ma_text_only__D1` | 79/4052 | 1.95% | 0.60% - 3.62% |
| `V2_full_minus_ma_prose__B1` | 790/4052 | 19.50% | 17.72% - 21.34% |
| `V2_full_minus_ma_prose__C4` | 1574/4052 | 38.85% | 35.87% - 41.71% |
| `V2_full_minus_ma_prose__D1` | 2908/4052 | 71.77% | 68.59% - 74.85% |
| `V3_plan_view_only__B1` | 134/4052 | 3.31% | 2.46% - 4.23% |
| `V3_plan_view_only__C4` | 1341/4052 | 33.09% | 30.39% - 35.76% |
| `V3_plan_view_only__D1` | 2289/4052 | 56.49% | 53.68% - 59.24% |
| `V4_icon_detail_only__B1` | 0/4052 | 0.00% | 0.00% - 0.00% |
| `V4_icon_detail_only__C4` | 35/4052 | 0.86% | 0.17% - 1.76% |
| `V4_icon_detail_only__D1` | 335/4052 | 8.27% | 5.28% - 11.57% |
| `V5_plan_detail_no_ma__B1` | 287/4052 | 7.08% | 5.91% - 8.30% |
| `V5_plan_detail_no_ma__C4` | 1179/4052 | 29.10% | 26.03% - 32.14% |
| `V5_plan_detail_no_ma__D1` | 2583/4052 | 63.75% | 61.02% - 66.53% |

## 5. 实验组5

输出：

```text
reports/statistics/experiment5_eval200_r6_strict_reviewed/
```

本次修正：

- `G3_LLM_Rules` 的逐样本结果不在 `G3_LLM_Rules/scores_v2/*.json`。
- 真实来源是 `reports/g_admin_results.jsonl`。
- 配置已改为读取 `score.v2.correct` 和 `score.v2.total`。

point estimate：

| 方法 | Correct/Total | Accuracy | 95% CI |
|---|---:|---:|---:|
| `A3_GoldText_Rules` | 2752/4052 | 67.92% | 65.69% - 69.92% |
| `B2a_GoldText_LLM` | 970/4052 | 23.94% | 22.05% - 25.91% |
| `B2b_GoldText_FieldCandidates_LLM` | 1100/4052 | 27.15% | 24.95% - 29.44% |
| `B3_PD` | 84/4052 | 2.07% | 1.71% - 2.43% |
| `B3_T` | 1227/4052 | 30.28% | 28.30% - 32.40% |
| `B3_TPD` | 1170/4052 | 28.87% | 26.91% - 30.94% |
| `B4_TPD` | 2718/4052 | 67.08% | 64.82% - 69.12% |
| `G3_LLM_Rules` | 265/4052 | 6.54% | 5.89% - 7.22% |

selected paired delta：

| 比较 | delta | 95% CI |
|---|---:|---:|
| `A3_GoldText_Rules - B4_TPD` | +0.84 pp | +0.20 pp - +1.67 pp |
| `B4_TPD - G3_LLM_Rules` | +60.54 pp | +58.15 pp - +62.69 pp |

解释边界：实验组5是 diagnostic/oracle-style 分析，不应并入实验组1公平主榜。

## 6. 实验组6

输出：

```text
reports/statistics/experiment6_v11_pr25_d1_counterfactual/
```

point estimate：

| 方法 | Correct/Total | Accuracy | 95% CI |
|---|---:|---:|---:|
| `V1_OCR_text_chartdisplay_v2` | 196/400 | 49.00% | 45.39% - 52.73% |
| `V2_direct_image_policyv3_chartdisplay_v2` | 227/400 | 56.75% | 52.90% - 60.49% |
| `V3_C4_group1v2_neutralized` | 200/400 | 50.00% | 46.81% - 52.94% |
| `V3_D1_SFT_group1v2_neutralized` | 208/400 | 52.00% | 48.78% - 54.95% |
| `V4_C4_tolerant_chartdisplay_v2` | 202/400 | 50.50% | 47.38% - 53.73% |
| `V4_D1_SFT_tolerant_chartdisplay_v2` | 223/400 | 55.75% | 52.33% - 59.19% |
| `control_all_accept` | 200/400 | 50.00% | 47.06% - 53.19% |
| `control_all_reject` | 200/400 | 50.00% | 46.81% - 52.94% |
| `control_oracle_label` | 400/400 | 100.00% | 100.00% - 100.00% |
| `control_v0_candidate_integrity` | 200/400 | 50.00% | 47.06% - 53.19% |

selected paired delta：

| 比较 | delta | 95% CI |
|---|---:|---:|
| `V3_C4_group1v2_neutralized - V3_D1_SFT_group1v2_neutralized` | -2.00 pp | -3.49 pp - -0.74 pp |
| `V4_C4_tolerant_chartdisplay_v2 - V4_D1_SFT_tolerant_chartdisplay_v2` | -5.25 pp | -8.83 pp - -1.55 pp |

## 7. 下一步

1. 如果需要给 GPT-5.4 `C1_GPT54/C3_GPT54/C4_GPT54` 做 CI，还要补齐它们的逐 chart score 工件。
2. 论文写作时区分主 leaderboard、source-view ablation、diagnostic/oracle-style、counterfactual verification，避免把不同实验组的可比性边界混在一起。
