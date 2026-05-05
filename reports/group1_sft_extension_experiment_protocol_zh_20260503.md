# 实验组1 SFT 拓展实验方案

日期：2026-05-03
仓库：`https://github.com/reshihihihi/faa-chart-to-424-benchmark.git`
分支：`group1-sft-extension-plan-20260503`
当前 commit：`57d5c86`
当前阶段：先跑 5 条样本 smoke，只验证能不能跑通，不跑全量。

## 1. 这次实验要解决什么问题

实验组1的任务是：给模型一张 FAA 航图，让模型输出 missed approach 的结构化 `canonical JSON`，然后用统一评分器和统一 target 做评分。

现在要在实验组1里增加和 SFT 有关的方法。这里的 SFT 方法不是一个单独方法，而是一组方法，用来回答几个问题：

1. 已经微调过的 D1 到底有没有比同底座未微调模型更好。
2. 如果 D1 更好，这个提升是不是来自 SFT，而不是来自别的因素。
3. 除了端到端从航图直接生成 `canonical JSON`，能不能把任务拆成两步：先从航图抽取图上证据，再根据证据生成程序语义。
4. 所有这些方法能不能在不读取标准答案、不读取 424/CIFP、不读取其他方法预测的前提下运行和评分。

当前第一步只做最小验证：5 条样本，只跑两个方法：

1. `D_BASE_SAME_BACKBONE`
2. `D1`

后面的几个新 SFT 方法先写进方案，但当前不直接跑。

## 2. 这次一共有哪几种方法

仓库里的 SFT 拓展方案一共有 5 种方法。下面按“现在要跑”和“后面才跑”分开说。

## 3. 当前第一轮要跑的两种方法

### 3.1 `D_BASE_SAME_BACKBONE`

中文含义：同底座未微调对照。

它做什么：

给模型输入一张完整航图图片，让模型直接输出 missed approach 的 `canonical JSON`。

它用什么模型：

使用和 D1 相同的 Qwen2-VL 底座模型，但是不加载 D1 的 LoRA 或 checkpoint。

它的输入是什么：

- 航图图片
- 同一个 prompt
- 同一个输出 JSON schema

它的输出是什么：

- `canonical JSON`

它不能读取什么：

- 不能读取 target JSON
- 不能读取 score
- 不能读取 raw 424 / CIFP
- 不能读取其他方法的预测结果

为什么要有这个方法：

这个方法是为了做公平对照。
如果只跑 D1，我们不知道 D1 的表现是来自 SFT，还是因为 Qwen2-VL 底座本身就能做到。
所以必须先跑一个“同底座但未微调”的版本。

它回答的问题是：

同一个底座模型，在不微调的情况下能做到什么水平？

它在本轮中的状态：

本轮必须先跑它。
它跑成功以后，才能跑 D1。

### 3.2 `D1`

中文含义：当前端到端 SFT 方法。

它做什么：

给模型输入一张完整航图图片，让模型直接输出 missed approach 的 `canonical JSON`。

它用什么模型：

使用和 `D_BASE_SAME_BACKBONE` 相同的 Qwen2-VL 底座模型，并额外加载 D1 的 LoRA 或 checkpoint。

它的输入是什么：

- 航图图片
- 同一个 prompt
- 同一个输出 JSON schema
- D1 LoRA/checkpoint

它的输出是什么：

- `canonical JSON`

它不能读取什么：

- 不能读取 target JSON
- 不能读取 score
- 不能读取 raw 424 / CIFP
- 不能读取其他方法的预测结果

为什么要有这个方法：

这是实验组1当前已有的主要 SFT baseline。
它代表“端到端微调模型”的效果。

它回答的问题是：

D1 在同样图片、同样 prompt、同样 schema、同样评分器下，是否比同底座未微调模型更好？

它在本轮中的状态：

本轮必须跑。
但必须在 `D_BASE_SAME_BACKBONE` 成功之后跑。

## 4. 后续才跑的三种方法

下面三种方法也是 SFT 拓展的一部分，但不是当前第一轮要跑的内容。它们需要额外数据或额外 checkpoint，所以当前不能和 D1 一起直接得出结论。

### 4.1 `CHART_TO_EVIDENCE_SFT`

中文含义：航图到图上证据的 SFT 方法。

它做什么：

给模型输入一张完整航图图片，让模型不要直接输出最终 `canonical JSON`，而是先输出“图上证据记录”。

这里的图上证据指的是：

- 图上能看到的 missed approach 文本
- fix 名称
- 转弯方向
- 高度限制
- 航迹、径向线、course、radial 等可见信息
- holding 相关的可见描述

它的输入是什么：

- 航图图片
- 图上证据抽取 prompt
- 图上证据 schema

它的输出是什么：

- evidence record，也就是图上证据记录

它不能读取什么：

- 不能读取 target JSON
- 不能读取 raw 424 / CIFP
- 不能读取 score
- 不能读取最终 canonical answer
- 不能读取其他方法预测

为什么要有这个方法：

D1 是端到端方法，从航图直接到 `canonical JSON`。
如果 D1 错了，我们很难知道它是没看懂图，还是看到了证据但语义组织错了。
`CHART_TO_EVIDENCE_SFT` 把第一步单独拆出来，用来检查模型能不能先把图上的关键信息找出来。

它回答的问题是：

模型能不能可靠地从航图中抽取 missed approach 相关的可见证据？

它在本轮中的状态：

当前不跑。
原因是这一步需要对应的 SFT checkpoint 或明确的证据抽取运行配置。当前 smoke 先只验证 D_BASE 和 D1。

### 4.2 `EVIDENCE_TO_SEMANTICS_SFT`

中文含义：图上证据到程序语义的 SFT 方法。

它做什么：

给模型输入已经整理好的图上证据，让模型根据这些证据生成 questionnaire 或最终结构化语义。

简单说，它不看完整航图图片，而是看“已经确认的图上证据”。

它的输入是什么：

- 图上证据记录
- evidence-to-semantics prompt
- 对应输出 schema

它的输出是什么：

- questionnaire JSON，或进一步转成 `canonical JSON` 的结构化结果

它不能读取什么：

- 不能读取 target JSON
- 不能读取 raw 424 / CIFP
- 不能读取 score
- 不能读取其他方法预测

为什么要有这个方法：

它用来检查第二步：
如果图上证据已经给定，模型能不能把证据正确组织成 missed approach 的程序语义？

这能帮助区分两类错误：

1. 第一类错误：模型没有从图上找到正确证据。
2. 第二类错误：模型找到了证据，但把程序语义组织错了。

它回答的问题是：

在证据已经给定的情况下，模型的语义组织能力有多强？

它在本轮中的状态：

当前不跑。
原因是当前本机缺少这个方法需要的 evidence eval JSONL：

```text
<group1_sft-artifact-root>\eval_jsonl\evidence_to_semantics_formal200.jsonl
```

注意：如果这个方法使用人工确认的证据，它必须在报告里标为诊断实验或上界实验，不能和端到端方法直接公平排名。

### 4.3 `TWO_STAGE_AUTO_SFT`

中文含义：自动两阶段 SFT 系统。

它做什么：

它把前面两个步骤串起来：

第一步：航图图片输入 `CHART_TO_EVIDENCE_SFT`，自动生成图上证据记录。
第二步：把自动生成的证据输入 `EVIDENCE_TO_SEMANTICS_SFT`，生成最终语义或 `canonical JSON`。

它的输入是什么：

- 航图图片
- 第一阶段自动生成的 evidence record

它的输出是什么：

- 最终 `canonical JSON`

它不能读取什么：

- 不能读取人工确认的证据
- 不能读取 target JSON
- 不能读取 raw 424 / CIFP
- 不能读取 score
- 不能读取其他方法预测

为什么要有这个方法：

它用来测试“显式拆成两步”是否比 D1 端到端更好。

D1 是：

```text
航图图片 -> canonical JSON
```

`TWO_STAGE_AUTO_SFT` 是：

```text
航图图片 -> 图上证据记录 -> canonical JSON
```

它回答的问题是：

把任务拆成“先找证据，再组织语义”是否能减少错误？

它在本轮中的状态：

当前不跑。
原因是它必须先有 `CHART_TO_EVIDENCE_SFT` 的自动输出，不能凭空直接运行第二阶段。

## 5. 五种方法之间的关系

可以这样理解：

```text
方法 1：D_BASE_SAME_BACKBONE
航图图片 -> 未微调 Qwen2-VL -> canonical JSON

方法 2：D1
航图图片 -> D1 微调模型 -> canonical JSON

方法 3：CHART_TO_EVIDENCE_SFT
航图图片 -> SFT 模型 -> 图上证据记录

方法 4：EVIDENCE_TO_SEMANTICS_SFT
图上证据记录 -> SFT 模型 -> 程序语义 / canonical JSON

方法 5：TWO_STAGE_AUTO_SFT
航图图片 -> 自动图上证据记录 -> 程序语义 / canonical JSON
```

当前最重要的比较是：

```text
D_BASE_SAME_BACKBONE vs D1
```

这个比较是为了回答：

```text
D1 的微调到底有没有带来收益？
```

后续更复杂的比较是：

```text
D1 vs TWO_STAGE_AUTO_SFT
```

这个比较是为了回答：

```text
端到端方法好，还是拆成“证据抽取 + 语义组织”两步更好？
```

## 6. 当前为什么只跑两个方法

因为当前第一步目标不是完成所有 SFT 拓展，而是先确认最基础链路能跑通：

1. 图片路径能找到。
2. Qwen2-VL 底座能加载。
3. D1 LoRA/checkpoint 能加载。
4. 推理脚本能输出。
5. 输出能解析成 JSON。
6. 输出能通过 schema 检查。
7. 评分能使用 `scoring_equivalence_v2` 完成。

如果这两个最基础方法都没跑通，后面三种方法没有必要直接上。

## 7. 当前已经做了什么

已经完成：

1. 拉取最新分支。
2. 确认当前 commit 是 `57d5c86`。
3. 确认 SFT run-package 脚本和 schema 已经存在。
4. 创建并填写本机路径配置：

```text
training/group1_sft/configs/local_paths.local.json
```

5. 路径检查通过。
6. 生成过一次 5 样本 run package。

第一次 package 出现 2 个 blocker，不是因为 D_BASE 或 D1 失败，而是因为默认把后续三种方法也包含进来了。

## 8. 当前出现的 blocker 是什么

第一次生成 package 时默认包含了 5 种方法。
其中两个后续方法产生 blocker：

### blocker 1

方法：

```text
EVIDENCE_TO_SEMANTICS_SFT
```

问题：

```text
缺少 evidence_to_semantics_formal200.jsonl
```

这说明第二阶段证据到语义的方法还没有准备好本机 eval JSONL。

### blocker 2

方法：

```text
TWO_STAGE_AUTO_SFT
```

问题：

```text
它需要先运行 CHART_TO_EVIDENCE_SFT，拿到自动生成的证据记录
```

这说明自动两阶段系统不能直接从第二阶段开始跑。

### 这两个 blocker 对当前第一轮意味着什么

它们不影响当前要跑的两个方法：

```text
D_BASE_SAME_BACKBONE
D1
```

所以当前正确做法不是临时补造数据，也不是修改实验定义，而是重新生成一个只包含这两个方法的 5 样本 package。

## 9. 当前下一步怎么做

重新生成只包含两个方法的 package：

```powershell
python scripts\group1_sft\prepare_group1_sft_run_package.py `
  --paths training\group1_sft\configs\local_paths.local.json `
  --limit 5 `
  --run-id group1_sft_smoke5 `
  --methods D_BASE_SAME_BACKBONE,D1 `
  --overwrite
```

然后打开：

```text
<group1_sft-artifact-root>\runs\group1_sft_smoke5\reports\preflight_report_zh.md
<group1_sft-artifact-root>\runs\group1_sft_smoke5\RUN_COMMANDS.md
```

确认：

```text
blockers = 0
D_BASE_SAME_BACKBONE rows = 5
D1 rows = 5
missing images = 0
image sha256 mismatch = 0
```

确认无 blocker 后，先跑：

```text
D_BASE_SAME_BACKBONE
```

成功后再跑：

```text
D1
```

## 10. 评分和结果怎么汇报

两个方法跑完后，读取：

```text
<group1_sft-artifact-root>\runs\group1_sft_smoke5\D_BASE_SAME_BACKBONE\summary_report.json
<group1_sft-artifact-root>\runs\group1_sft_smoke5\D1\summary_report.json
```

最终汇报必须包括：

1. 当前 commit hash。
2. 本机关键路径是否存在。
3. preflight blocker 数量。
4. `D_BASE_SAME_BACKBONE` 的 summary report 路径。
5. `D_BASE_SAME_BACKBONE` 的 score。
6. `D1` 的 summary report 路径。
7. `D1` 的 score。
8. 两个方法各自的 parse failure 数量。
9. 两个方法各自的 schema failure 数量。
10. 是否有任何代码改动。

## 11. 哪些东西绝对不能提交到 Git

不能提交：

```text
training/group1_sft/configs/local_paths.local.json
模型目录
LoRA/checkpoint
PNG 图片
raw outputs
parsed predictions 大结果
正式大结果目录
API token
本机绝对路径配置
```

可以提交：

```text
实验方案 md
不含本机隐私路径的大纲说明
脚本修复
schema 修复
小型摘要报告
```

## 12. 最简结论

当前一共有 5 种方法：

1. `D_BASE_SAME_BACKBONE`：未微调同底座对照，用来判断底座本身能力。
2. `D1`：当前端到端 SFT 方法，用来判断 SFT 是否带来提升。
3. `CHART_TO_EVIDENCE_SFT`：航图到图上证据，用来检查模型能不能先找证据。
4. `EVIDENCE_TO_SEMANTICS_SFT`：证据到程序语义，用来检查模型能不能把证据组织成语义。
5. `TWO_STAGE_AUTO_SFT`：自动两阶段系统，用来检查“先找证据再组织语义”是否优于端到端。

当前马上应该做的是：

```text
只跑 D_BASE_SAME_BACKBONE 和 D1 的 5 条样本 smoke。
```

当前不应该做的是：

```text
不要跑全量。
不要临时造 evidence eval JSONL。
不要把后续三种方法混进第一轮 smoke。
不要把 target、424/CIFP、score 或其他方法预测传给推理阶段。
```
