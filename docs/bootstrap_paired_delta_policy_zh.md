# Bootstrap 与 paired-delta 统计处理政策

本文档固定 paper-v2 各实验组正式结果的统计处理口径。它只用于**预测完成、评分完成之后**的结果汇总，不能参与训练、推理、提示词选择、样本筛选或评分规则修改。

核心原则很简单：先分清“最终主结果”和“诊断/开发结果”，再做 bootstrap 和 paired-delta。不能因为某个目录里有结果文件，就把它自动放进正式论文结论。

## 1. 统计目的

正式实验只有有限数量的航图。单个方法的 accuracy 只是这批样本上的点估计，所以需要：

- 给每个正式方法报告 95% confidence interval；
- 给两个正式方法的差值报告 paired-delta 95% confidence interval；
- 避免把很小的点估计差距过度解释；
- 保留 parse failure、schema failure、method failure 对结果的影响；
- 防止只在成功样本上比较方法。

默认统计量为：

```text
metric = sum(score_numerator) / sum(score_denominator)
```

默认重采样单位为：

```text
chart_id
```

原因是同一张航图内的字段、证据行、反事实 case 不是相互独立样本。按字段行或 case 行独立抽样会人为缩小置信区间。

## 2. 固定随机性

第一版冻结配置为：

```text
bootstrap_iterations = 10000
seed = 20260504
confidence_level = 0.95
interval_method = percentile
resampling_unit = chart_id
paired_delta = metric(method_a) - metric(method_b)
```

正式报告必须记录：配置文件路径、配置 sha256、统计脚本路径、脚本 sha256、输入 score/per-sample 文件路径与 sha256、随机种子、重采样次数和输出目录。

## 3. 预测阶段边界

任何方法 runner 在预测阶段都禁止读取：

- target JSON；
- scorer 输出；
- raw 424/CIFP；
- 其他方法预测；
- answer key；
- 只允许评分阶段使用的 scoring manifest 字段。

Bootstrap 脚本只能读取已经完成的 score/per-sample 结果。它不能被方法 runner 调用，不能生成或修补预测。

## 4. 各实验组最终口径

### 4.1 实验组1

正式主结果是：

```text
formal200 evaluation split
scoring_equivalence_v2 / comparison_policy_v2
```

正式主方法为：

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

- `D1` 是正式 SFT 结果口径。它把 D-SFT raw output 规范化成固定 canonical JSON 接口，200/200 schema-valid。
- `D_SFT` raw output 只能作为历史/诊断/附录结果，不能替代 `D1` 进入主表。
- 旧 formal75、pilot10、pilot100、smoke、dev 结果都不是实验组1主结论。
- 当前新增的 `D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL` 是实验组1 SFT 补充方向，只有完成 formal200 预测、评分和 no-leakage 审计后，才能进入后续正式统计。

实验组1需要 bootstrap 和 paired-delta，因为它是多方法同一 formal200 样本上的主 leaderboard。

#### 实验组1 C 系列补充对照

实验组1还有一条单独的 C 系列模型/方法补充对照，不能直接混入上述主 leaderboard。

已确认的补充结果来自：

```text
origin/group1-c2-method-effect-20260504
```

它包含两类信息：

1. GPT-5.4 对 C1/C2/C3/C4 的补充 rerun summary。
2. C2 的桥接对照：Claude 原始 C2、Claude batched C2、GPT-5.4 batched C2。

解释边界：

- 原始实验组1主表中的 C1/C2/C3/C4 仍是冻结 formal run 的 Claude 版本。
- GPT-5.4 C1/C2/C3/C4 都已经跑过，并且都有 200/200 的 combined summary。combined summary 的 artifact checks 还记录了 C1/C2/C3/C4 均为 `scores=200`，说明运行时产生过 score 工件。当前限制不是“没跑”，而是 C1/C3/C4 的逐 chart score 文件没有在当前 Git tree/PR 文件列表中作为 Git blob 提交；因此可以报告 point estimate 和 artifact status，但不能从 summary-only 文件计算正式 chart-level bootstrap CI。
- C2 的三个版本可以单独作为 `group1_c2_model_method_effect_20260504` 进行 bootstrap，因为 Claude batched C2 和 GPT-5.4 batched C2 的 `method_summary.json` 含有 200 条逐 chart `results`，原始 Claude C2 也有正式 per-sample score。

C2 的结论必须拆开说：

```text
方法结构效应 = Claude batched C2 - Claude original C2
模型效应 = GPT-5.4 batched C2 - Claude batched C2
混合差异 = GPT-5.4 batched C2 - Claude original C2
```

其中“混合差异”不能被解释成纯模型差异，因为它同时改变了 C2 调用结构和底座模型。

### 4.2 实验组2

正式口径是：

```text
300 张人工标注已提交
其中 200 张与实验组1 formal200 成对
用于字段证据来源和方法正确性的连接分析
```

实验组2不是重新跑模型，也不是独立 leaderboard。它回答的是：实验组1字段正确/错误与人工证据来源有什么关系。

实验组2在第一批统一统计中不作为必跑对象。只有当论文里要声称“某方法在某类证据来源上显著更强”时，才需要按 `chart_id` 聚类做 bootstrap 或 paired-delta。描述性证据分布表本身不需要 paired-delta。

### 4.3 实验组3

当前仓库内实验组3主要体现为 formal300 challenge tags / 难度标签。它用于分层解释样本，而不是新的方法结果。

实验组3不进入第一批主方法 paired-delta。若要报告某标签子集上的方法差异，也必须按 `chart_id` 聚类，并明确这是 subgroup diagnostic，不是新的主 leaderboard。

### 4.4 实验组4

正式主结果是 source-view ablation，样本为实验组1 formal200 的 200 张 evaluation charts。

正式主矩阵是：

```text
6 个 source-view variant × 3 个主方法
```

6 个 variant：

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

重要边界：

- `V0_full_chart` 复用实验组1整图 baseline，不重跑。
- `D1` 是正式 SFT 比较口径。
- `D_SFT` raw output 只能作诊断或附录，因为它在若干 source-view 下存在严重 coverage/schema failure。不能把 D_SFT raw 的 valid-only 高分当作实验组4主结论。
- 实验组4正式统计必须覆盖 6×3 主矩阵。只跑 D1 或只跑 V0 都不完整。
- V1-V5 的 B1/C4/D1 必须使用已提交的逐航图 CSV：`formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1/scores/v2/<variant>/<method>/per_sample_scores.csv`。不能只用最终 summary 表反推 bootstrap。

实验组4需要 bootstrap 和 paired-delta。主要比较包括：

- 同一方法在不同 source-view 下的差异；
- 同一 source-view 下 B1、C4、D1 的差异；
- D1 在 `V0_full_chart`、`V2_full_minus_ma_prose`、`V3_plan_view_only`、`V5_plan_detail_no_ma` 之间的证据来源变化。

### 4.5 实验组5

实验组5是诊断实验，不是与实验组1完全公平的端到端 leaderboard。

正式主诊断结果是：

```text
experiment5_eval200_20260504_r6_strict_reviewed_runs
eval200
strict reviewed inputs
```

正式主诊断方法为：

```text
A3_GoldText_Rules
B2a_GoldText_LLM
B2b_GoldText_FieldCandidates_LLM
B3_T
B3_PD
B3_TPD
B4_TPD
G3_LLM_Rules
```

这些方法回答的问题是失败来自哪里：

- reviewed MA_TEXT 是否足够；
- LLM 是否能把文本转成 canonical JSON；
- 文本候选是否帮助 LLM；
- plan/detail 区域是否能替代 MA_TEXT；
- rule parser 和 LLM canonical structuring 的差异；
- answer-stripped 后台可见事实摘要能提供多少信息。

不能混入主诊断结果的内容：

- dev50；
- smoke20；
- admin_relation/oracle textualized inputs；
- G0/G1 oracle 或历史 r1/r2 结果；
- MA_TEXT OCR review 的中间产物本身。

admin_relation/oracle 结果可以作为单独 oracle diagnostic appendix，但必须与 r6 strict reviewed 主诊断表分开。

实验组5需要 bootstrap 和 paired-delta，但解释时必须写明这是 diagnostic/oracle-style analysis，不是端到端公平排名。

### 4.6 实验组6

正式主结果是：

```text
experiment6_group1formal200_full200_v11_pr25_d1_20260502_r1
```

v11 对齐了 PR25 scoring-equivalence v2 与 D1。v8/v9/v10 只能作为历史或过渡版本；pre-D1 D_SFT 是附录诊断，不是主结果。

正式主结果方法包括：

```text
control_all_accept
control_all_reject
control_oracle_label
control_v0_candidate_integrity
V1_OCR_text_chartdisplay_v2
V2_direct_image_policyv3_chartdisplay_v2
V3_C4_group1v2_neutralized
V3_D1_SFT_group1v2_neutralized
V4_C4_tolerant_chartdisplay_v2
V4_D1_SFT_tolerant_chartdisplay_v2
```

边界：

- `V3_D_SFT_pre_D1_group1v2_neutralized` 和 `V4_D_SFT_pre_D1_tolerant` 只作附录诊断。
- `V4` 是实验组6内部的 tolerant symbolic compare，不等于实验组1的 scoring-equivalence v2。
- 实验组6测的是 counterfactual verification，不是 extractor 字段准确率。

实验组6需要 bootstrap。虽然原始对象是 verification case，但重采样必须按 `chart_id` 聚类，把同一张图下的 positive/negative cases 一起抽样。

## 5. 缺失、parse failure 和 schema failure

正式结果不能静默删除失败样本。

推荐做法是：每个正式 `chart_id` 都有一条 per-sample score 记录。失败样本显式记录：

```text
score_numerator = 0
score_denominator = 该 chart 的正式应评分字段数或应判断 case 数
failure_type = parse_failure / schema_failure / method_failure / missing_prediction
```

如果历史结果只保存了成功样本，统计脚本必须采取以下任一策略：

- 使用冻结的 `unit_total_source` 补齐缺失 `chart_id`，补齐样本按 0 正确计；
- 在 strict 模式下报错，要求先生成完整 per-sample score 文件。

禁止只在两个方法的共同成功样本上做正式 paired-delta。共同成功样本分析最多是诊断，不是主结论。

## 6. 对输入工件的要求

Bootstrap/paired-delta 需要逐 chart score，而不是只有最终 summary。

可接受输入：

- post-scoring per-sample JSONL/CSV；
- 每个 chart 一个 score JSON；
- 实验组6 case-level predictions 加 cases，在所有预测完成后生成 chart-cluster score；
- 带 sha256 和 source_ref 的冻结 Git 工件。

不可接受输入：

- 只有总 correct/total 的 summary 表；
- raw predictions；
- raw model outputs；
- PNG；
- checkpoint；
- target JSON；
- 任何会让统计脚本在预测阶段可见答案的文件。

如果某实验组只有最终汇总表，没有逐 chart score 文件，则可以报告 point estimate 已存在，但不能从该汇总表计算正式 chart-level bootstrap CI。

## 7. 第一批要做的 analysis set

第一批只固定并执行：

```text
group1_scoring_equivalence_v2
group1_c2_model_method_effect_20260504
experiment4_source_ablation_formal200_main_6x3
experiment5_eval200_r6_strict_reviewed
experiment6_v11_pr25_d1_counterfactual
```

实验组2、实验组3暂不放入第一批主流程。后续如果论文需要它们的子组差异声明，再单独添加 analysis set。

## 8. 输出要求

统一统计脚本至少输出：

- 每个方法的 point estimate、95% CI、样本覆盖数、补齐失败数；
- 每对方法的 paired delta point estimate、95% CI；
- run manifest，记录配置、输入文件、sha256、随机种子、迭代次数和 warnings；
- CSV 和 JSON 两种机器可读结果。

统计输出可以提交小型汇总表和 manifest。不要提交模型、checkpoint、PNG、raw outputs、raw predictions 或大结果目录。

## 9. 推荐运行

示例：

```powershell
python scripts\scorers\compute_bootstrap_paired_delta.py --config configs\bootstrap_paired_delta_policy.json --analysis-set group1_scoring_equivalence_v2
```

快速自检可以临时减少迭代：

```powershell
python scripts\scorers\compute_bootstrap_paired_delta.py --config configs\bootstrap_paired_delta_policy.json --analysis-set group1_scoring_equivalence_v2 --iterations 100 --output-dir reports\statistics\_smoke_group1_bootstrap
```

正式结果仍必须使用冻结配置中的 10000 次重采样。
