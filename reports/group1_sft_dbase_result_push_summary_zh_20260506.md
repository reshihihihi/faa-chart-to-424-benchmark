# 实验组1 D-base 结果汇总与提交说明

日期：2026-05-06

## 方法定义

`D_BASE_SAME_BACKBONE` 是实验组1 SFT 补充实验中的同底座未微调对照方法。

- 输入：完整航图图片。
- 模型：Qwen2-VL-2B-Instruct base。
- adapter/checkpoint：不加载任何 SFT adapter。
- prompt/schema/scorer：与 D1 对照保持一致。
- 评分：预测完成后使用 `scoring_equivalence_v2` target 和 `comparison_policy_v2`。

该方法的目的不是作为强方法，而是回答一个控制变量问题：在相同底座、相同样本、相同 prompt、相同 schema、相同评分器下，不经过 SFT 的模型能不能直接完成 missed approach canonical JSON 任务。

## 50 样本结果

本次已完成 `D_BASE_SAME_BACKBONE` 在 formal evaluation 前 50 张航图上的测试。

| 项目 | 结果 |
|---|---:|
| 样本数 | 50 |
| raw output | 50/50 |
| raw strict JSON parse ok | 8/50 |
| raw 可直接评分 | 0/50 |
| raw failure_count | 50/50 |
| canonicalized JSON written | 50/50 |
| canonicalized schema_valid | 50/50 |
| canonicalized samples_scored | 50/50 |
| 正式 field-level score | 0 / 1022 = 0.0000 |
| 诊断性 salvage score | 7 / 1022 = 0.006849 |

## 与 D1 的同 50 张对照

同一批 50 张航图上，D1 已经跑过并完成评分：

| 方法 | raw strict JSON parse ok | raw samples scored | canonicalized samples scored | field-level score |
|---|---:|---:|---:|---:|
| D_BASE_SAME_BACKBONE | 8/50 | 0/50 | 50/50 | 0/1022 = 0.0000 |
| D1 | 49/50 | 46/50 | 50/50 | 727/1022 = 0.7114 |

这个对照说明：D-base 的失败不是单纯的格式问题。即使经过与 D1 一致的保守 canonicalization，让 50 条全部变成合法 schema 并进入评分，D-base 仍然得到 0 分。D1 的提升主要来自 SFT 后对输出结构和字段语义的学习。

## raw 输出表现

D-base raw 输出常见问题包括：

- 输出不是完整 JSON，出现未闭合字符串、缺逗号、对象截断等 parse failure。
- 只输出航图元信息，例如机场名、进近名、chart name，没有 missed approach 语义结构。
- 字段层级错误，例如把 `Q_terminator`、`Q1_fix_ident`、`Q2_altitude_constraint` 等字段塞进 `missed_approach.leg_count`，而不是放在 `missed_approach.legs[n].answers`。
- `chart_id`、`procedure.airport` 等外壳字段经常不符合 canonical schema。

正式 canonicalization 只做机械外壳修复和 schema 合法化，不使用 target JSON、score、raw 424/CIFP、OCR、人工答案或其他方法预测来修正字段答案。

## 已提交到仓库的文件

以下文件用于在 GitHub 上记录 D-base 结果和对照结论：

- `reports/group1_sft_dbase50_execution_report_zh_20260504.md`
- `reports/group1_sft_dbase_vs_d1_eval_first50_comparison_zh_20260504.md`
- `reports/group1_sft_dbase_result_push_summary_zh_20260506.md`

## 未提交内容

以下内容仍保留在本机实验目录，不提交到 Git：

- `local_paths.local.json`
- 模型权重和 Hugging Face cache
- LoRA/checkpoint
- PNG 航图图片
- raw model outputs
- 每样本大体积 score 输出
- 本机绝对路径配置

## 结论

D-base 已经完成 50 样本跑通和评分，但结果基本为零。它适合作为实验组1新增 SFT 方法的低基线对照：同底座未微调模型无法直接完成 missed approach canonical JSON 任务，而 D1 在同样 50 张上有明显提升。
