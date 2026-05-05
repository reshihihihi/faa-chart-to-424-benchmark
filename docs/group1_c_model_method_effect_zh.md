# 实验组1 C 系列 Claude / GPT-5.4 补充对照说明

本文档说明实验组1中 C 系列方法的额外模型/方法对照。它不是实验组1原始 formal200 主榜的替代品，而是一个单独的补充分析。

## 1. 为什么要单独说明

实验组1主结果里，C1/C2/C3/C4 的冻结 formal run 使用的是 Claude 系列 VLM/MLLM 配置。后续又在 `origin/group1-c2-method-effect-20260504` 分支上跑了 GPT-5.4 版本，并且对 C2 做了 batched-leg 结构改造。

因此这里有两种变化：

1. **模型变化**：Claude 和 GPT-5.4 的差别。
2. **方法结构变化**：C2 原始逐字段 QA 调用和 C2 batched-leg 调用的差别。

这两者不能混在一起解释。特别是 `C2_GPT54_batched_leg` 不是“只把 Claude 换成 GPT-5.4”，它同时使用了 batched-leg 的 C2 调用结构。

## 2. 输入与边界

样本：

```text
formal300_50_200_50_seed20260437 evaluation split
200 charts
```

主要来源分支：

```text
origin/group1-c2-method-effect-20260504
commit 1b09a5a5625230360e8eeb40ca06e2d1b4963578
```

本补充分析仍遵守实验组1边界：

- 预测阶段不能读取 target JSON；
- 不能读取 score；
- 不能读取 raw 424/CIFP；
- 不能读取其他方法预测；
- scoring manifest 只能在预测完成后用于评分；
- bootstrap 只读取已经完成的 post-scoring 工件。

## 3. 主结果和补充结果的关系

实验组1主 leaderboard 仍使用原 formal run 的方法集合：

```text
A1, A2, B1, B1_prime, B1_prime_link, C1, C2, C3, C4, D1
```

其中 C1/C2/C3/C4 是原始 Claude 版本。GPT-5.4 C 系列不直接替换主榜中的 C 系列，而是作为模型/方法效应补充分析。

## 4. GPT-5.4 C 系列结果

`origin/group1-c2-method-effect-20260504` 中记录了 GPT-5.4 对 C1/C2/C3/C4 的一整套 rerun 结果。这里必须分清三层含义：

- “是否跑过”：C1、C2、C3、C4 都已经跑过，且都有 200/200 的汇总结果。
- “运行时是否产生过 score”：combined summary 的 artifact checks 记录 C1/C2/C3/C4 均为 `scores=200`，说明运行目录里当时存在 score 工件。
- “Git 中是否提交了逐样本 score 文件”：正式置信区间需要逐 chart 或逐字段明细 score；当前 PR 文件列表和 Git tree 中只确认 C2 提交了这种明细工件，C1/C3/C4 的逐 chart score 文件没有作为 Git blob 提交。

四个方法的汇总结果为：

| 方法 | Scored | Correct/Total | Accuracy | 当前统计状态 |
|---|---:|---:|---:|---|
| `C1_GPT54` | 200/200 | 1201/4052 | 29.64% | 已跑完；summary 记录 `scores=200`，但当前 Git tree 未提交逐 chart score |
| `C2_GPT54_batched_leg` | 200/200 | 1884/4052 | 46.50% | 有逐 chart `method_summary.results`，可 bootstrap |
| `C3_GPT54` | 200/200 | 1218/4052 | 30.06% | 已跑完；summary 记录 `scores=200`，但当前 Git tree 未提交逐 chart score |
| `C4_GPT54` | 200/200 | 1757/4052 | 43.36% | 已跑完；summary 记录 `scores=200`，但当前 Git tree 未提交逐 chart score |

因此，这不是“C1/C3/C4 没跑”，而是“它们的逐样本统计输入没有在当前 Git tree/PR 文件列表中提交”。目前只有 C2 batched-leg 可以进入 chart-level bootstrap；C1/C3/C4 可以报告点估计和工件状态，但不能从 summary-only 文件计算正式 CI。

## 5. C2 桥接分析

C2 桥接分析使用三组结果：

| 方法 | 含义 | 逐 chart score 来源 |
|---|---|---|
| `C2_CLAUDE_original` | 原实验组1 Claude C2，按 scoring_equivalence_v2 重新评分 | `C2_per_sample_v2.jsonl` |
| `C2_CLAUDE_batched_leg` | 同为 Claude，但把 C2 改成 batched-leg 调用结构 | `C2_CLAUDE_batched_leg/method_summary.json` |
| `C2_GPT54_batched_leg` | GPT-5.4，使用同样 batched-leg C2 结构 | `C2_GPT54_batched_leg/method_summary.json` |

注意：原始 Claude C2 在旧 strict 报告中是 `970/4052 = 23.94%`；本统计使用实验组1统一的 `scoring_equivalence_v2`，因此原始 Claude C2 为：

```text
1074/4052 = 26.51%
```

## 6. Bootstrap 配置

配置文件：

```text
configs/bootstrap_paired_delta_policy.json
```

analysis set：

```text
group1_c2_model_method_effect_20260504
```

重采样设置：

```text
bootstrap_iterations = 10000
seed = 20260504
resampling_unit = chart_id
confidence_level = 0.95
interval_method = percentile
```

正式输出目录：

```text
reports/statistics/group1_c2_model_method_effect_20260504
```

## 7. 10000 次 bootstrap 结果

点估计：

| 方法 | Correct/Total | Accuracy | 95% CI |
|---|---:|---:|---:|
| `C2_CLAUDE_original` | 1074/4052 | 26.51% | 25.09% - 27.96% |
| `C2_CLAUDE_batched_leg` | 1397/4052 | 34.48% | 33.04% - 35.92% |
| `C2_GPT54_batched_leg` | 1884/4052 | 46.50% | 44.61% - 48.37% |

Paired delta：

| 对比 | 差值 | 95% CI | 解释 |
|---|---:|---:|---|
| `C2_CLAUDE_batched_leg - C2_CLAUDE_original` | +7.97 pp | +6.18 pp 到 +9.78 pp | 同模型下的 C2 方法结构效应 |
| `C2_GPT54_batched_leg - C2_CLAUDE_batched_leg` | +12.02 pp | +9.58 pp 到 +14.40 pp | 同 batched C2 结构下的模型效应 |
| `C2_GPT54_batched_leg - C2_CLAUDE_original` | +19.99 pp | +18.01 pp 到 +22.03 pp | 混合差异，不能解释为纯模型效应 |

## 8. 结论

在 `scoring_equivalence_v2` 口径下，C2 的提升来自两部分：

1. C2 调用结构从原始逐字段 QA 改为 batched-leg 后，同为 Claude 的准确率从 26.51% 提升到 34.48%。
2. 在同样 batched-leg 结构下，GPT-5.4 从 34.48% 进一步提升到 46.50%。

所以可以说：C2 的 GPT-5.4 batched 结果明显优于 Claude batched，也明显优于原始 Claude C2；但不能把 `C2_GPT54_batched_leg - C2_CLAUDE_original` 直接写成纯模型差异。
