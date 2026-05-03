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
```

其中 `benchmark_exports\derived\v2\formal300\targets\scoring_equivalence_v2` 已放入本分支。

如果另一台电脑不用 `E:\experiment3`，需要先把脚本里的本地路径改成新机器路径，或者后续改造成命令行参数。

## 已同步到 Git 的关键文件

```text
scripts\group2\run_group2_group3_pilot30.py
scripts\group2\run_group2_group3_complete19_v3.py
scripts\group2\run_group2_group3_direct_q4_fix.py
scripts\group2\run_group2_formal_submitted_v1.py
docs\group2\group2_new_window_handoff_zh.md
docs\group2\direct_q4_fix_20260503_report_zh.md
docs\group2\direct_q4_fix_20260503_audit.json
```

这三个脚本默认读取和写入 `E:\experiment3` 下的路径。如果新机器路径不同，可以设置：

```powershell
$env:EXPERIMENT3_ROOT = "D:\experiment3"
$env:FAA_BENCH_REPO = "D:\experiment3\github_work\faa-chart-to-424-benchmark"
$env:GROUP23_ROOT = "D:\experiment3\zu2+3"
$env:GROUP2_EXPORT_PATH = "D:\experiment3\group2_annotation_status_YYYYMMDD_HHMM\shujuji_annotation_export_xxx.json"
$env:GROUP2_OVERVIEW_PATH = "D:\experiment3\group2_annotation_status_YYYYMMDD_HHMM\admin_overview_formal300.json"
$env:GROUP1_RUN = "D:\experiment3\github_work\faa-chart-to-424-benchmark\formal_runs\group1\group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2"
```

如果新机器仍使用 `E:\experiment3`，通常只需要设置最新人工导出的两个路径：

```powershell
$env:GROUP2_EXPORT_PATH = "E:\experiment3\group2_annotation_status_YYYYMMDD_HHMM\shujuji_annotation_export_xxx.json"
$env:GROUP2_OVERVIEW_PATH = "E:\experiment3\group2_annotation_status_YYYYMMDD_HHMM\admin_overview_formal300.json"
```

## 正式全量前的判断

如果人工标注仍是 `296/300`，不要把结果写成 formal300 正式结论。

如果已完成 `300/300`，应先生成新的后台导出，再基于新导出迁移 direct Q4 修复逻辑并跑正式实验组2。

## 正式/已提交标注运行命令

本分支已新增正式 runner：

```text
scripts\group2\run_group2_formal_submitted_v1.py
```

它会做以下事情：

```text
读取最新人工标注导出
读取 admin overview
读取 Group1 scoring-equivalence v2 字段分数
读取 scoring-equivalence v2 target/policy
选择全部 submitted/final 且 Group1 分数完整的航图
迁移 direct-Q4 同航段补证据规则
输出正类证据来源主表、不适用字段负类表、异常审计和中文报告
```

如果 300 张已经全部提交，推荐命令：

```powershell
$env:GROUP2_EXPORT_PATH = "E:\experiment3\group2_annotation_status_YYYYMMDD_HHMM\shujuji_annotation_export_xxx.json"
$env:GROUP2_OVERVIEW_PATH = "E:\experiment3\group2_annotation_status_YYYYMMDD_HHMM\admin_overview_formal300.json"
$env:GROUP2_OUTPUT_ROOT = "E:\experiment3\zu2+3\group2_formal\group2_formal300_v1_YYYYMMDD_HHMM"
python scripts\group2\run_group2_formal_submitted_v1.py
```

如果明确只跑 296 张已提交子集，不能冒充 formal300，命令必须显式写：

```powershell
$env:GROUP2_RUN_ID = "group2_formal_submitted296_v1_YYYYMMDD_HHMM"
$env:GROUP2_OUTPUT_ROOT = "E:\experiment3\zu2+3\group2_formal\group2_formal_submitted296_v1_YYYYMMDD_HHMM"
python scripts\group2\run_group2_formal_submitted_v1.py --allow-submitted-subset
```

跑完后先看：

```text
group2\group2_formal_submitted_v1_audit.json
group2\reports\group2_formal_submitted_v1_report_zh.md
reports\run_summary.json
```

只有 `ready_for_group2_main_claim = true`，且以下数量都合理，才进入论文结论：

```text
positive_question_fallback_rows = 0
unmatched_present_rows = 0
submitted_annotation_count = 300  （除非明确写 submitted 子集）
analysis_chart_count 符合预期
```
