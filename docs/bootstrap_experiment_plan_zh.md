# Bootstrap / paired-delta 详细实验方案

## 1. 这一步到底要做什么

现在要做的不是重新跑模型，也不是重新生成预测，而是对已经完成评分的实验结果做统计不确定性分析。

具体来说，对每个方法已有的逐样本评分结果进行 bootstrap 重采样，输出：

1. 每个方法的 point estimate，也就是原始准确率。
2. 每个方法准确率的 95% bootstrap confidence interval。
3. 同一批样本上两个方法之间的 paired delta，也就是方法 A 减方法 B 的准确率差。
4. paired delta 的 95% bootstrap confidence interval。

这里的 paired-delta 很重要，因为实验组 1、4、5、6 的很多方法是在同一批 chart 上比较的。直接比较两个独立置信区间不够准确，应该按同一张 chart 聚类后成对重采样。

## 2. 统计边界

Bootstrap 脚本只允许读取已经完成的 score / per-sample / method_summary 结果。

禁止做的事情：

- 不能读取 target JSON 来重新判分。
- 不能读取 raw 424/CIFP。
- 不能读取其他方法预测来修补当前方法。
- 不能删除失败样本。
- 不能因为某方法缺逐样本工件，就用 summary 结果伪造逐样本分布。
- 不能把 dev/smoke/admin/oracle 结果混进正式主结论。

允许做的事情：

- 读取已经提交的 scorer 输出。
- 读取每个 chart 的 correct / total。
- 按 chart_id 聚类重采样。
- 对同一 chart 上的两个方法计算 paired delta。
- 报告缺失工件导致不能 bootstrap 的方法。

## 3. Bootstrap 设计

### 3.1 重采样单位

统一按 `chart_id` 聚类重采样。

原因是同一张航图内部有多个字段，字段之间不是独立样本。如果按字段直接重采样，会低估不确定性。

每次 bootstrap：

1. 从 formal evaluation chart 集合中有放回抽取 N 张 chart。
2. 对抽到的 chart 汇总 correct / total。
3. 得到该方法本次 bootstrap 的 accuracy。
4. 对方法对，计算同一批抽样 chart 下的 accuracy delta。

### 3.2 重采样次数

正式结果使用：

```text
10000 次 bootstrap
```

开发检查可以先用：

```text
100 次 bootstrap
```

只要 100 次 smoke 能跑通，再跑 10000 次正式版本。

### 3.3 随机种子

随机种子固定在配置文件中，保证可复现。

配置文件：

```text
configs/bootstrap_paired_delta_policy.json
```

## 4. 哪些实验组需要 bootstrap

第一批需要做的是：

```text
实验组1
实验组4
实验组5
实验组6
```

实验组2、实验组3暂时不作为第一批主 bootstrap 对象。

原因：

- 实验组2主要是 evidence / paired input 的分析，只有当论文要对某个 evidence 子集做显著性声明时才需要 bootstrap。
- 实验组3主要是 challenge tag / difficulty tag 分层说明，不是新的方法 leaderboard。

## 5. 实验组1 bootstrap 方案

### 5.1 实验组1主表

实验组1主表比较的是同一 formal200 evaluation split 上的一组方法。

主表方法包括：

```text
A1
A2
B1
B1_prime
B1_prime_link
C1
C2
C3
C4
D1
```

其中：

- `C1/C2/C3/C4` 是原始 Claude 版本。
- `D1` 是 D-SFT 最终 canonical 输出接口。
- 旧的 `D_SFT` raw run 只作为历史/诊断工件，不进入主表 bootstrap。

输入：

```text
formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/
```

输出：

```text
reports/statistics/group1_scoring_equivalence_v2/
```

需要输出：

- `point_estimates.csv`
- `paired_deltas.csv`
- `bootstrap_samples.csv` 或等价的可追溯统计结果
- `summary.md`

### 5.2 实验组1 GPT-5.4 C 系列补充分析

这部分不是替代主表，而是补充回答：

1. GPT-5.4 跑 C1/C2/C3/C4 的结果是什么。
2. C2 的结构变化和模型变化分别带来多少提升。

已经确认 GPT-5.4 C1/C2/C3/C4 都跑过，结果在：

```text
formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_gpt54_current_oauth_responses_batched_c2/reports/combined_gpt54_current_oauth_batched_c2_summary.json
```

878856d5 已补齐 GPT-5.4 C1/C2/C3/C4 的逐 chart bootstrap score 表：

```text
reports/freeze/group1_gpt54_cfamily_per_chart_scores_for_bootstrap_20260505.csv
```

四个 GPT-5.4 C 系列结果现在都可以做 chart-level bootstrap：

| 方法 | Correct/Total | Accuracy | 95% CI | 当前统计状态 |
|---|---:|---:|---:|---|
| `C1_GPT54` | 1201/4052 | 29.64% | 27.30% - 32.10% | 已完成 10000 次 bootstrap |
| `C2_GPT54_batched_leg` | 1884/4052 | 46.50% | 44.61% - 48.37% | 已完成 10000 次 bootstrap |
| `C3_GPT54` | 1218/4052 | 30.06% | 27.71% - 32.49% | 已完成 10000 次 bootstrap |
| `C4_GPT54` | 1757/4052 | 43.36% | 40.59% - 46.09% | 已完成 10000 次 bootstrap |

输出位置：

```text
reports/statistics/group1_gpt54_cfamily_per_chart_20260505/
```

另外，C2 桥接对照仍然单独保留：

```text
C2_CLAUDE_original
C2_CLAUDE_batched_leg
C2_GPT54_batched_leg
```

这个对照要拆成三层解释：

| 比较 | 含义 |
|---|---|
| `C2_CLAUDE_batched_leg - C2_CLAUDE_original` | 固定模型为 Claude，测 C2 调用结构改成 batched-leg 后的结构效应 |
| `C2_GPT54_batched_leg - C2_CLAUDE_batched_leg` | 固定 batched-leg 结构，测 GPT-5.4 相对 Claude 的模型效应 |
| `C2_GPT54_batched_leg - C2_CLAUDE_original` | 结构变化 + 模型变化的混合差异，不能解释成纯模型效应 |

当前已经跑出的正式 10000 次 bootstrap 结果位置：

```text
reports/statistics/group1_c2_model_method_effect_20260504/
```

## 6. 实验组4 bootstrap 方案

实验组4是 source-view ablation，也就是看不同输入信息源对方法效果的影响。

主实验矩阵是：

```text
6 个 source-view variant × 3 个主方法
```

6 个 source-view variant：

```text
V0_full_chart
V1_ma_text_only
V2_full_minus_ma_prose
V3_plan_view_only
V4_icon_detail_only
V5_plan_detail_no_ma
```

3 个主方法：

```text
B1
C4
D1
```

bootstrap 目标：

1. 每个 variant × method 的准确率和 95% CI。
2. 同一 method 下，不同 variant 相对 `V0_full_chart` 的 paired delta。
3. 同一 variant 下，不同 method 之间的 paired delta。

解释重点：

- `V0_full_chart` 是完整航图基线。
- `V1_ma_text_only` 测 missed approach prose 文字本身的信息量。
- `V2_full_minus_ma_prose` 测删除复飞文字后，仅凭图形/其他区域还能保留多少能力。
- `V3/V4/V5` 分别测 plan view、icon/detail、组合视图的贡献。

当前执行状态：

- V1-V5 的 B1/C4/D1 逐 chart score 已补齐，输入为 `formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1/scores/v2/<variant>/<method>/per_sample_scores.csv`。
- V0_full_chart 复用实验组1整图 baseline 的逐 chart score。
- 已完成 `experiment4_source_ablation_formal200_main_6x3` 的正式 10000 次 bootstrap。
- 输出在 `reports/statistics/experiment4_source_ablation_formal200_main_6x3/`。
- `bootstrap_run_manifest.json` 中 `warnings=[]`，`n_units=200`，point estimate 方法数为 18，paired delta 行数为 153。

注意事项：

- 不能只对 D1 做 bootstrap，否则会把实验组4错误简化成 D1-only。
- 实验组4正式解释必须围绕 6 个 source-view variant × 3 个主方法，也就是 B1、C4、D1 的 18 个结果。
- `D_SFT` raw output 只能作为诊断或附录，不进入实验组4主 6×3 结论。

## 7. 实验组5 bootstrap 方案

实验组5是诊断 / oracle-style 误差归因实验，不是端到端公平主榜。

核心问题是：

```text
如果给模型不同程度的中间信息、人工校正信息、文本信息或规则信息，最终 canonical 输出会提升多少？
```

当前主分析应使用 r6 strict reviewed eval200 结果。

方法集合包括：

```text
A3
B2a
B2b
B3_T
B3_PD
B3_TPD
B4_TPD
G3
```

bootstrap 目标：

1. 每个方法的准确率和 95% CI。
2. 相对基础输入方法的 paired delta。
3. 分析不同额外信息来源带来的边际收益。

解释边界：

- 这是诊断实验，不是完全公平的端到端方法排名。
- 如果某方法使用人工 reviewed text 或 oracle-style relation，必须在论文中明确说明。
- 不能把它和实验组1主榜放在同一个公平 leaderboard 里解释。

当前执行状态：

- `G3` 的 r6 eval200 逐样本结果已经确认，不在 `G3_LLM_Rules/scores_v2/*.json`。
- 实际来源是 `formal_runs/experiment5/experiment5_eval200_20260504_r6_strict_reviewed_runs/reports/g_admin_results.jsonl`。
- 该 JSONL 每行包含 `score.v2.correct` 和 `score.v2.total`，已经接入 `configs/bootstrap_paired_delta_policy.json`。
- 评分阶段可以读取 scoring manifest；预测阶段不能读取 target。

## 8. 实验组6 bootstrap 方案

实验组6是 counterfactual verification。

它的样本不是普通 canonical JSON 生成，而是 verification case：

```text
给定一个 candidate / perturbation，让方法判断是否接受或拒绝。
```

bootstrap 目标：

1. 每个 verification 方法的准确率和 95% CI。
2. 方法之间的 paired delta。
3. 与简单控制策略比较，例如 all_accept、all_reject、oracle_label。

重采样单位仍然是 `chart_id`。

原因是同一张 chart 下可能有多个 positive / negative verification cases，不能把这些 case 当成完全独立样本。

当前可先跑：

```text
experiment6_v11_pr25_d1_counterfactual
```

输出：

```text
reports/statistics/experiment6_v11_pr25_d1_counterfactual/
```

## 9. 执行顺序

### 第一步：配置冻结

确认配置文件存在：

```text
configs/bootstrap_paired_delta_policy.json
```

里面必须冻结：

- bootstrap iterations = 10000
- random seed
- cluster key = chart_id
- 每个 analysis set 的 source ref
- 每个方法的 score 输入路径
- required_methods
- allowed_missing 或 summary_only 的说明

### 第二步：先做 smoke

每个 analysis set 先跑 100 次：

```powershell
python scripts\scorers\compute_bootstrap_paired_delta.py --config configs\bootstrap_paired_delta_policy.json --analysis-set group1_scoring_equivalence_v2 --iterations 100 --output-dir reports\statistics\_smoke_group1_bootstrap
```

然后依次 smoke：

```text
group1_c2_model_method_effect_20260504
experiment4_source_ablation_formal200_main_6x3
experiment5_eval200_r6_strict_reviewed
experiment6_v11_pr25_d1_counterfactual
```

smoke 检查内容：

- 是否所有 required methods 都找到。
- 是否所有方法 chart_id 集合一致。
- 是否有缺样本。
- 是否有 total=0。
- 是否有重复 chart_id。
- 是否 CI 输出正常。

### 第三步：正式 10000 次

smoke 通过后，再跑正式版本：

```powershell
python scripts\scorers\compute_bootstrap_paired_delta.py --config configs\bootstrap_paired_delta_policy.json --analysis-set <analysis_set_name>
```

正式输出统一放到：

```text
reports/statistics/<analysis_set_name>/
```

### 第四步：写 summary

每个 analysis set 输出后，需要写中文 summary，至少包括：

- 输入结果来源。
- 方法列表。
- point estimate。
- 95% CI。
- paired delta。
- paired delta 95% CI。
- 是否有缺失工件。
- 解释边界。

## 10. 当前已完成和未完成

已经完成：

1. 新增 bootstrap/paired-delta 中文政策文档。
2. 新增 bootstrap 配置文件。
3. 新增统一 bootstrap 脚本。
4. `group1_scoring_equivalence_v2` 已经跑过正式 10000 次 bootstrap。
5. `group1_c2_model_method_effect_20260504` 已经跑过正式 10000 次 bootstrap。
6. `experiment4_source_ablation_formal200_main_6x3` 已经跑过正式 10000 次 bootstrap。
7. `experiment5_eval200_r6_strict_reviewed` 已经跑过正式 10000 次 bootstrap。
8. `experiment6_v11_pr25_d1_counterfactual` 已经跑过正式 10000 次 bootstrap。
9. 已导入 `878856d5` 新增的 GPT-5.4 C1/C2/C3/C4 逐 chart score 表。
10. `group1_gpt54_cfamily_per_chart_20260505` 已经跑过正式 10000 次 bootstrap。

当前还需要做：

1. 在论文写作中明确 GPT-5.4 C 系列补充不替代实验组1主榜的冻结 Claude C1/C2/C3/C4。
2. 在论文写作中明确实验组5是 diagnostic/oracle-style，不并入实验组1公平主 leaderboard。
3. 在论文写作中明确实验组6是 counterfactual verification，不和 canonical JSON 生成主榜直接混排。

## 11. 最终论文中应该怎么写

最终论文/报告里不要把所有东西混成一个大表。

建议分成四类：

1. 实验组1主 leaderboard：正式方法主结果，带 CI 和 paired delta。
2. 实验组1 GPT-5.4 C 系列补充：C1/C2/C3/C4 点估计、95% CI、paired delta；C2 桥接对照单独解释结构效应和模型效应。
3. 实验组4 source-view ablation：6×3 ablation 表，带 CI 和 variant delta。
4. 实验组5 diagnostic/oracle-style：诊断表，带 CI，但明确不是端到端公平排名。
5. 实验组6 verification：counterfactual verification 表，按 chart_id 聚类 bootstrap。
