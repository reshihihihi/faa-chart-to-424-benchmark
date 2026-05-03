# 实验组2二机运行说明

本分支只通过 Git 同步实验组2代码和说明文件。正式数据、人工标注后台导出、实验组1全量结果通常较大或可能包含敏感信息，不建议直接提交到 Git。

## 另一台电脑需要准备的输入

建议保持和当前机器相同的根目录：

```text
E:\experiment3
```

至少需要准备：

```text
E:\experiment3\github_work\faa-chart-to-424-benchmark
E:\experiment3\group2_annotation_status_YYYYMMDD_HHMM
E:\experiment3\github_work\faa-chart-to-424-benchmark\formal_runs\group1\group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2
E:\experiment3\github_work\faa-chart-to-424-benchmark\benchmark_exports\derived\v2\formal300\targets\scoring_equivalence_v2\field_targets_chart_display_v2.jsonl
```

如果另一台电脑不用 `E:\experiment3`，需要先把脚本里的本地路径改成新机器路径，或者后续改造成命令行参数。

## 已同步到 Git 的关键文件

```text
scripts\group2\run_group2_group3_direct_q4_fix.py
docs\group2\group2_new_window_handoff_zh.md
docs\group2\direct_q4_fix_20260503_report_zh.md
docs\group2\direct_q4_fix_20260503_audit.json
```

## 正式全量前的判断

如果人工标注仍是 `296/300`，不要把结果写成 formal300 正式结论。

如果已完成 `300/300`，应先生成新的后台导出，再基于新导出迁移 direct Q4 修复逻辑并跑正式实验组2。
