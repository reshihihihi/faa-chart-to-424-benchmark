# 实验组 1 C2 半改方法补充报告

- 生成日期：2026-05-04
- 数据集划分：`formal300_50_200_50_seed20260437`
- 评估子集：evaluation 200 条
- 目的：把 C2 的“半改方法”收益和模型差异拆开，避免把 Claude 原始 C2 与 GPT-5.4 半改 C2 直接混为方法结论。

## 结论

C2 的半改方法确实有效，但它不能解释全部提升。

在同一模型 Claude Sonnet 4.5 下，C2 从原始逐字段 QA 改成“每条 leg 一次性输出 6 个 QA 字段”后，准确率从 `23.94%` 提升到 `34.48%`，提升 `+10.54 pp`，多对 `427` 个字段。这是可归因于方法变化的部分。

在同一半改方法下，GPT-5.4 的 C2 准确率是 `46.50%`，比 Claude 半改 C2 高 `+12.02 pp`，多对 `487` 个字段。这是同方法下的模型差异。

因此，GPT-5.4 半改 C2 相对旧 Claude 原始 C2 的总提升 `+22.56 pp` 不能全部归因于方法；其中约 `+10.54 pp` 来自方法，约 `+12.02 pp` 来自模型。

## 公平比较表 1：Claude 同模型方法比较

这个表只比较方法变化，模型固定为 Claude Sonnet 4.5。

| 方法版本 | 模型 | 样本 | Schema valid | Scored | Correct/Total | Accuracy | 备注 |
|---|---|---:|---:|---:|---:|---:|---|
| C1 原始 | Claude Sonnet 4.5 | 200 | 200 | 200 | 1503/4052 | 37.09% | 图像直接到 canonical JSON |
| C2 原始 | Claude Sonnet 4.5 | 200 | 200 | 200 | 970/4052 | 23.94% | q0 + 每个 leg 的 6 个 QA 字段分别调用 |
| C2 半改 | Claude Sonnet 4.5 | 200 | 200 | 200 | 1397/4052 | 34.48% | q0 + 每个 leg 一次性输出 6 个 QA 字段 |
| C3 原始 | Claude Sonnet 4.5 | 200 | 196 | 196 | 1522/3976 | 38.28% | questionnaire-style VLM extraction |
| C4 原始 | Claude Sonnet 4.5 | 200 | 200 | 200 | 1624/4052 | 40.08% | 图像 + OCR-1 到 canonical JSON |

Claude 内部的 C2 方法结论：

| 对比 | Accuracy 差值 | Correct 差值 | 解释 |
|---|---:|---:|---|
| C2 半改 - C2 原始 | +10.54 pp | +427 | 方法变化本身带来明显收益 |
| C2 半改 - C4 原始 | -5.60 pp | -227 | 半改 C2 仍低于 Claude 的图像+OCR 直接抽取 C4 |
| C2 半改 - C1 原始 | -2.62 pp | -106 | 半改后接近 C1，但还没有超过 |

## 公平比较表 2：GPT-5.4 同模型方法比较

这个表只比较 GPT-5.4 下的 C-family 方法。C2 使用同一个半改方法。

| 方法版本 | 模型 | 样本 | Schema valid | Scored | Correct/Total | Accuracy | 备注 |
|---|---|---:|---:|---:|---:|---:|---|
| C1_GPT54 | GPT-5.4 | 200 | 200 | 200 | 1201/4052 | 29.64% | 图像直接到 canonical JSON |
| C2_GPT54_batched_leg | GPT-5.4 | 200 | 200 | 200 | 1884/4052 | 46.50% | q0 + 每个 leg 一次性输出 6 个 QA 字段 |
| C3_GPT54 | GPT-5.4 | 200 | 200 | 200 | 1218/4052 | 30.06% | questionnaire-style VLM extraction |
| C4_GPT54 | GPT-5.4 | 200 | 200 | 200 | 1757/4052 | 43.36% | 图像 + OCR-1 到 canonical JSON |

GPT-5.4 内部的 C2 方法位置：

| 对比 | Accuracy 差值 | Correct 差值 | 解释 |
|---|---:|---:|---|
| C2 半改 - C1 | +16.86 pp | +683 | 半改 C2 明显优于直接图像到 JSON |
| C2 半改 - C3 | +16.44 pp | +666 | 半改 C2 明显优于问卷式抽取 |
| C2 半改 - C4 | +3.13 pp | +127 | 半改 C2 小幅超过图像+OCR 直接抽取 |

## 模型效应拆分

这个表固定方法为 C2 半改，只比较模型。

| 方法 | Claude Sonnet 4.5 | GPT-5.4 | 差值 |
|---|---:|---:|---:|
| C2 半改 | 1397/4052 = 34.48% | 1884/4052 = 46.50% | GPT-5.4 +12.02 pp |

这说明：C2 半改方法在 Claude 上能提升，但 GPT-5.4 在同一半改方法下仍明显更强。因此，如果论文或报告想论证“方法有效”，应优先引用 Claude 同模型比较；如果想报告当前最佳 C2 结果，可以引用 GPT-5.4 半改 C2，但需要标注模型已变化。

## 不应作为主结论的混合比较

| 对比 | Accuracy 差值 | Correct 差值 | 是否可作为方法结论 |
|---|---:|---:|---|
| GPT-5.4 半改 C2 - Claude 原始 C2 | +22.56 pp | +914 | 不可单独作为方法结论，因为同时改变了方法和模型 |

这个混合差值只能作为总变化描述。正式方法结论应拆成：

- 方法效应：Claude 半改 C2 - Claude 原始 C2 = `+10.54 pp`
- 模型效应：GPT-5.4 半改 C2 - Claude 半改 C2 = `+12.02 pp`

## 运行与完整性

Claude 半改 C2 重跑使用同一 evaluation 200 条样本，分两片执行后合并：

| 分片 | 样本 | Correct/Total | Accuracy |
|---|---:|---:|---:|
| 前 100 条 | 100 | 760/2152 | 35.32% |
| 后 100 条 | 100 | 637/1900 | 33.53% |
| 合并 | 200 | 1397/4052 | 34.48% |

完整性检查：

- Claude 半改 C2：200/200 schema valid，200/200 scored。
- 合并后 unique chart IDs = 200/200，unique sample IDs = 200/200。
- 合并后字段总数 = 4052，与旧正式评估表一致。
- Claude 半改 C2 的 QA schema retry = 0。
- Claude 半改 C2 保存的 QA 调用数 = 881，保存的 QA 字段数 = 4286。
- GPT-5.4 半改 C2 保存的 QA 调用数 = 809，保存的 QA 字段数 = 3854。
- Bootstrap 所需的逐 chart `scores/*.json` 已补齐：GPT-5.4 的 C1/C2/C3/C4 各 200 个，Claude 半改 C2 合并结果 200 个。

## 数据来源

- 旧 Claude 原始 C-family：`formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1/reports/final_completion_audit_20260430_115514.json`
- 旧冻结报告：`reports/freeze/group1_formal_freeze_package_20260430_r1.md`
- GPT-5.4 C-family 重跑：`formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_gpt54_current_oauth_responses_batched_c2/reports/combined_gpt54_current_oauth_batched_c2_summary.json`
- GPT-5.4 C2 半改：`formal_runs/group1/g1_gpt54_oauth_c2b_20260504/C2_GPT54_batched_leg/method_summary.json`
- Claude C2 半改合并结果：`formal_runs/group1/g1_claude_c2b_combined_20260504/C2_CLAUDE_batched_leg/method_summary.json`
- Claude C2 半改合并报告：`formal_runs/group1/g1_claude_c2b_combined_20260504/reports/claude_c2_batched_vs_original_and_gpt54_summary.md`
- PR artifact manifest：`reports/freeze/group1_c2_rerun_artifact_manifest_20260505.md`

## 推荐写法

在实验组 1 的正式叙述里，建议写成：

> 为了隔离 C2 改法与模型替换的影响，我们额外在 Claude Sonnet 4.5 上重跑 C2 半改方法。结果显示，固定模型时，半改方法将 C2 从 23.94% 提升到 34.48%，带来 +10.54 pp 的方法收益；固定半改方法时，GPT-5.4 进一步达到 46.50%，比 Claude 半改 C2 高 +12.02 pp。因此，GPT-5.4 半改 C2 相对旧 Claude 原始 C2 的 +22.56 pp 总提升应解释为方法收益与模型收益的叠加，而不能全部归因于方法。
