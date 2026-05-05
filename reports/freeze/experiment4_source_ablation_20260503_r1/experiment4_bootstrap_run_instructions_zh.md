# 实验组4 bootstrap 运行说明

本文件只说明如何运行统计步骤；不包含已经运行出的 bootstrap 结果。

## 已补齐的输入材料

- V1-V5 的逐航图分数 CSV：
  `formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1/scores/v2/<variant>/<method>/per_sample_scores.csv`
- 覆盖的方法包括 `B1`、`C4`、`D1`、`D_SFT`。正式 bootstrap 主矩阵只使用 `B1`、`C4`、`D1`。
- V0 baseline 仍复用实验组1冻结结果：
  `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/reports/*_per_sample_v2.jsonl`
- 统计配置：
  `configs/bootstrap_paired_delta_policy.json`
- 统计脚本：
  `scripts/scorers/compute_bootstrap_paired_delta.py`

## 正式 analysis set

```text
experiment4_source_ablation_formal200_main_6x3
```

该 analysis set 覆盖 6 个 source-view variant × 3 个主方法，共 18 个方法：

```text
V0_full_chart__B1/C4/D1
V1_ma_text_only__B1/C4/D1
V2_full_minus_ma_prose__B1/C4/D1
V3_plan_view_only__B1/C4/D1
V4_icon_detail_only__B1/C4/D1
V5_plan_detail_no_ma__B1/C4/D1
```

重采样单位固定为 `chart_id`，随机种子固定为 `20260504`，正式次数为 `10000`。

## 建议运行命令

先跑 smoke：

```powershell
python scripts\scorers\compute_bootstrap_paired_delta.py `
  --analysis-set experiment4_source_ablation_formal200_main_6x3 `
  --iterations 100 `
  --seed 20260504 `
  --output-dir reports\statistics\experiment4_source_ablation_formal200_main_6x3_smoke
```

确认 smoke 无误后跑正式 10000 次：

```powershell
python scripts\scorers\compute_bootstrap_paired_delta.py `
  --analysis-set experiment4_source_ablation_formal200_main_6x3 `
  --iterations 10000 `
  --seed 20260504 `
  --output-dir reports\statistics\experiment4_source_ablation_formal200_main_6x3
```

## 运行后检查

运行完成后应检查：

- `bootstrap_run_manifest.json` 里的 `warnings` 为空数组。
- `bootstrap_run_manifest.json` 里的 `n_units` 为 `200`。
- `point_estimates.csv` 有 18 行方法结果。
- `paired_deltas.csv` 有 153 行两两差值结果。
- `point_estimates.csv` 中每个方法的 `score_numerator`、`score_denominator`、`point_estimate` 与 `experiment4_final_metrics_table.csv` 中对应 `chart_display_aware_v2` 行一致。

如果缺少 CSV，脚本应在 strict policy 下失败，不能用 summary-only 表替代 chart-level bootstrap。
