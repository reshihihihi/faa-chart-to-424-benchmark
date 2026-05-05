# 实验组1增加 SFT 方法的详细实验方案

日期：2026-05-03
仓库：`https://github.com/reshihihihi/faa-chart-to-424-benchmark.git`
分支：`group1-sft-extension-plan-20260503`
当前 commit：`57d5c86`
当前执行原则：先把全部 SFT 拓展方法一起跑通 smoke，再进入全量实验；不要只把某一个方法单独做完后再临时补其他方法。

## 1. 实验组1原来的任务是什么

实验组1的核心任务是：

```text
输入 FAA 航图图片
输出 missed approach 的结构化 canonical JSON
再用统一 target 和统一 scoring policy 做评分
```

这次新增 SFT 方法，是为了在同一个实验组1评测框架里，比较端到端微调、未微调对照、证据抽取、证据到语义、自动两阶段系统这几类方法。

## 2. 这次增加的内容是什么

这次不是只增加一个方法，而是增加一组 SFT 相关方法：

1. `D_BASE_SAME_BACKBONE`
2. `D1`
3. `CHART_TO_EVIDENCE_SFT`
4. `EVIDENCE_TO_SEMANTICS_SFT`
5. `TWO_STAGE_AUTO_SFT`

它们应该作为同一个实验批次来准备：

```text
先让五种方法都能在 5 条样本 smoke 上跑通
再让五种方法进入同一批全量实验
最后统一比较结果
```

不要把 `D_BASE_SAME_BACKBONE` 和 `D1` 单独跑成完整结论后，再另外补其他方法。这样会导致实验批次、环境、输入、评分口径不一致。

## 3. 五种方法分别是什么、为了什么

## 3.1 `D_BASE_SAME_BACKBONE`

中文名称：同底座未微调对照。

### 它做什么

```text
航图图片 -> 未微调 Qwen2-VL 底座 -> canonical JSON
```

### 它的目的

它是对照组，用来判断 Qwen2-VL 底座模型本身在不微调时能做到什么水平。

如果没有这个方法，就无法判断 D1 的效果到底来自 SFT，还是来自底座模型本身。

### 输入

允许输入：

```text
航图图片
prompt
输出 JSON schema
Qwen2-VL 底座模型
```

禁止输入：

```text
target JSON
score 文件
raw 424 / CIFP
其他方法预测结果
人工答案
```

### 输出

```text
canonical JSON
```

后处理结果包括：

```text
raw_text
canonical_json
validation/schema 结果
summary_report.json
```

## 3.2 `D1`

中文名称：当前端到端 SFT 方法。

### 它做什么

```text
航图图片 -> Qwen2-VL 底座 + D1 LoRA/checkpoint -> canonical JSON
```

### 它的目的

它是当前已有的端到端 SFT baseline，用来判断经过 D1 微调后，模型是否比同底座未微调对照更好。

### 输入

允许输入：

```text
航图图片
prompt
输出 JSON schema
Qwen2-VL 底座模型
D1 LoRA/checkpoint
```

禁止输入：

```text
target JSON
score 文件
raw 424 / CIFP
其他方法预测结果
人工答案
```

### 输出

```text
canonical JSON
```

## 3.3 `CHART_TO_EVIDENCE_SFT`

中文名称：航图到图上证据 SFT 方法。

### 它做什么

```text
航图图片 -> 图上证据记录
```

它不直接输出最终 `canonical JSON`，而是先输出模型在图上看到的 missed approach 相关证据。

### 它的目的

它用来检查模型是否能先把图上的关键信息找出来。

如果端到端 D1 出错，错误可能来自两种地方：

1. 模型没找到图上证据。
2. 模型找到了证据，但没有正确组织成程序语义。

`CHART_TO_EVIDENCE_SFT` 专门检查第一件事。

### 输入

允许输入：

```text
航图图片
图上证据抽取 prompt
evidence_record schema
对应 SFT 模型或 checkpoint
```

禁止输入：

```text
target JSON
score 文件
raw 424 / CIFP
最终 canonical answer
其他方法预测结果
```

### 输出

```text
evidence record
```

证据记录应包括图上可见的复飞相关信息，例如：

```text
复飞文本
fix 名称
高度限制
转弯方向
course / radial
holding 相关可见信息
```

## 3.4 `EVIDENCE_TO_SEMANTICS_SFT`

中文名称：图上证据到程序语义 SFT 方法。

### 它做什么

```text
图上证据记录 -> 程序语义 / questionnaire JSON / canonical JSON
```

它不负责看完整航图，而是根据已经给定的图上证据组织程序语义。

### 它的目的

它用来检查模型在“证据已经给定”的情况下，是否能正确生成 missed approach 的结构化语义。

它专门检查第二件事：

```text
模型是否能把证据组织成正确程序语义
```

### 输入

允许输入：

```text
图上证据记录
evidence-to-semantics prompt
evidence_questionnaire schema 或 canonical JSON schema
对应 SFT 模型或 checkpoint
```

禁止输入：

```text
target JSON
score 文件
raw 424 / CIFP
其他方法预测结果
```

### 输出

可以是：

```text
questionnaire JSON
```

也可以进一步转换成：

```text
canonical JSON
```

如果输入是人工确认的图上证据，这个方法必须标注为诊断实验或上界实验，不能和端到端方法直接公平排名。

## 3.5 `TWO_STAGE_AUTO_SFT`

中文名称：自动两阶段 SFT 方法。

### 它做什么

```text
航图图片 -> 自动图上证据记录 -> canonical JSON
```

它把前两种拆解方法串起来：

1. 先运行 `CHART_TO_EVIDENCE_SFT`，从航图自动生成 evidence record。
2. 再把自动 evidence record 输入 `EVIDENCE_TO_SEMANTICS_SFT`，生成最终结构化结果。

### 它的目的

它用来判断：

```text
显式拆成“先找证据，再组织语义”是否比端到端 D1 更好
```

### 输入

第一阶段允许输入：

```text
航图图片
```

第二阶段允许输入：

```text
第一阶段自动生成的 evidence record
```

禁止输入：

```text
人工确认的证据
target JSON
score 文件
raw 424 / CIFP
其他方法预测结果
```

### 输出

```text
canonical JSON
```

## 4. 五种方法之间的关系

可以把五种方法理解成两个层次：

### 第一层：端到端方法

```text
D_BASE_SAME_BACKBONE:
航图图片 -> 未微调模型 -> canonical JSON

D1:
航图图片 -> 微调模型 -> canonical JSON
```

这一层回答：

```text
SFT 是否比同底座未微调更好
```

### 第二层：拆解式方法

```text
CHART_TO_EVIDENCE_SFT:
航图图片 -> 图上证据记录

EVIDENCE_TO_SEMANTICS_SFT:
图上证据记录 -> 程序语义 / canonical JSON

TWO_STAGE_AUTO_SFT:
航图图片 -> 自动图上证据记录 -> canonical JSON
```

这一层回答：

```text
先抽证据再组织语义，是否比端到端更稳定
```

## 5. 总体实验思路

正确实验思路是：

```text
五种方法一起准备
五种方法一起 smoke
五种方法一起进入全量实验
最后统一比较
```

这里的“一起”不是说所有命令必须在同一秒启动，而是说它们属于同一批实验设计，使用同一套样本、同一套 target、同一套评分口径和同一套运行记录。

其中 `TWO_STAGE_AUTO_SFT` 有依赖关系，不能在 `CHART_TO_EVIDENCE_SFT` 输出之前完成。
所以它的执行方式应是：

```text
并行准备所有方法
先并行跑没有依赖的端到端方法和第一阶段方法
等 CHART_TO_EVIDENCE_SFT 产出 evidence record
再启动 TWO_STAGE_AUTO_SFT 的第二阶段
最后统一评分和汇总
```

## 6. 数据、target 和评分设置

### 数据来源

使用实验组1 formal 数据：

```text
benchmark_exports/derived/v2/formal300/manifest.json
formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1/formal_run_manifest.json
formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1/scoring_manifest.jsonl
```

### 图片来源

图片在本机路径：

```text
<repo-worktree>\benchmark_exports\derived\v2\formal300\images
```

图片不提交到 Git。

### 评分 target

必须优先使用：

```text
benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/canonical_proxy_gt_chart_display_v2.json
benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/comparison_policy_v2.jsonl
benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/field_targets_chart_display_v2.jsonl
```

当前 run package 已经确认可以使用 `scoring_equivalence_v2` 和 `comparison_policy_v2`。

## 7. 输入输出和泄漏控制

### 推理阶段允许读取

按方法不同，允许读取：

```text
航图图片
方法 prompt
输出 schema
模型底座
对应 LoRA/checkpoint
自动生成的 evidence record
```

### 推理阶段禁止读取

所有方法都禁止读取：

```text
target JSON
score 文件
raw 424 / CIFP
其他方法预测结果
人工答案
```

`TWO_STAGE_AUTO_SFT` 还禁止读取人工确认的 evidence record，只能使用 `CHART_TO_EVIDENCE_SFT` 自动生成的 evidence record。

### scoring manifest 使用边界

`scoring_manifest.jsonl` 只能在预测完成后用于评分。
它不能被放进 prompt，也不能作为模型输入。

## 8. 具体实验计划

## 8.1 阶段一：仓库和文件检查

运行：

```powershell
git status --short --branch
git pull
git rev-parse --short HEAD
```

确认当前 commit：

```text
57d5c86
```

确认以下文件存在：

```text
scripts/group1_sft/prepare_group1_sft_run_package.py
scripts/group1_sft/run_qwen2vl_group1_sft_inference.py
training/group1_sft/manifests/evidence_record.schema.json
training/group1_sft/manifests/evidence_questionnaire.schema.json
```

## 8.2 阶段二：本地路径检查

本地路径文件：

```text
training/group1_sft/configs/local_paths.local.json
```

检查命令：

```powershell
python scripts\group1_sft\validate_group1_sft_workspace.py --paths training\group1_sft\configs\local_paths.local.json
```

通过条件：

```text
required 路径全部存在
ready = true
```

当前已经通过。

## 8.3 阶段三：补齐五种方法的运行前置条件

要把五种方法一起跑通，必须补齐以下前置条件。

### 已经具备

```text
D_BASE_SAME_BACKBONE 的底座模型路径
D1 的底座模型路径
D1 LoRA/checkpoint 路径
formal 图片路径
scoring_equivalence_v2 target
comparison_policy_v2
```

### 还需要确认或补齐

`CHART_TO_EVIDENCE_SFT` 需要：

```text
chart-to-evidence 的 SFT checkpoint
或明确决定先用同一底座/现有 checkpoint 做 smoke
```

`EVIDENCE_TO_SEMANTICS_SFT` 需要：

```text
evidence_to_semantics_eval_jsonl
evidence-to-semantics 的 SFT checkpoint
运行入口或转换脚本
```

当前缺少的已知文件是：

```text
<group1_sft-artifact-root>\eval_jsonl\evidence_to_semantics_formal200.jsonl
```

`TWO_STAGE_AUTO_SFT` 需要：

```text
CHART_TO_EVIDENCE_SFT 的自动 evidence record 输出
第二阶段 evidence-to-semantics 推理入口
最终 canonical JSON 转换和评分流程
```

## 8.4 阶段四：生成五方法 5 样本 smoke package

前置条件补齐后，生成包含全部方法的 smoke package：

```powershell
python scripts\group1_sft\prepare_group1_sft_run_package.py `
  --paths training\group1_sft\configs\local_paths.local.json `
  --limit 5 `
  --run-id group1_sft_smoke5 `
  --overwrite
```

不要用只包含两个方法的 package 作为最终 smoke。
五种方法都要进入同一个 smoke package。

检查：

```text
<group1_sft-artifact-root>\runs\group1_sft_smoke5\reports\preflight_report_zh.md
<group1_sft-artifact-root>\runs\group1_sft_smoke5\RUN_COMMANDS.md
```

通过条件：

```text
blockers = 0
五种方法的输入 manifest 都存在
每种方法 rows = 5
图片方法 missing images = 0
图片方法 image sha256 mismatch = 0
scoring target source = scoring_equivalence_v2
comparison_policy_v2 exists = true
```

## 8.5 阶段五：五方法 smoke 执行计划

五方法 smoke 的执行不应该被理解为一个一个长期串行完成，而应该按依赖关系并行推进。

### 可以并行启动的方法

这些方法互不依赖，可以同时准备和运行：

```text
D_BASE_SAME_BACKBONE
D1
CHART_TO_EVIDENCE_SFT
EVIDENCE_TO_SEMANTICS_SFT
```

注意：是否能真的同时启动，取决于本机 GPU 显存。
如果显存不足，可以在同一批实验中排队运行，但实验设计仍然是同一批次。

### 有依赖的方法

`TWO_STAGE_AUTO_SFT` 依赖：

```text
CHART_TO_EVIDENCE_SFT 的自动 evidence record 输出
```

所以它不能在第一阶段输出产生之前完成。
正确执行顺序是：

```text
先完成 CHART_TO_EVIDENCE_SFT 的 evidence record
再运行 TWO_STAGE_AUTO_SFT 的第二阶段
```

## 8.6 阶段六：五方法 smoke 结果汇总

每种方法都要生成自己的 summary report。
最终汇总应包括：

```text
method_id
summary_report.json 路径
输入样本数
完成推理数
parse failure 数量
schema failure 数量
score
是否读取了禁止输入
是否使用 scoring_equivalence_v2
```

只有五种方法 smoke 全部通过，才进入全量实验。

## 8.7 阶段七：五方法全量实验

全量实验原则：

```text
五种方法使用同一 formal split
五种方法使用同一 scoring_equivalence_v2 target
五种方法使用同一 comparison_policy_v2
五种方法统一记录环境、commit、路径 hash、输入清单 hash、输出 summary
```

可并行运行的方法：

```text
D_BASE_SAME_BACKBONE
D1
CHART_TO_EVIDENCE_SFT
EVIDENCE_TO_SEMANTICS_SFT
```

依赖后运行的方法：

```text
TWO_STAGE_AUTO_SFT
```

它必须等待 `CHART_TO_EVIDENCE_SFT` 的全量 evidence record 输出。

最终全量比较表至少包括：

```text
D_BASE_SAME_BACKBONE score
D1 score
CHART_TO_EVIDENCE_SFT evidence-level 指标
EVIDENCE_TO_SEMANTICS_SFT semantic/canonical 指标
TWO_STAGE_AUTO_SFT score
parse failure 数量
schema failure 数量
每个字段类别的错误统计
```

## 9. 当前已经做了什么

已经完成：

1. 仓库已拉到最新 commit：`57d5c86`。
2. 4 个 run-package 脚本/schema 已确认存在。
3. 已创建并填写本地路径配置：

```text
training/group1_sft/configs/local_paths.local.json
```

4. 已运行路径检查，required 路径全部存在。
5. 已生成过一次默认 5 方法 smoke package：

```text
<group1_sft-artifact-root>\runs\group1_sft_smoke5
```

6. 已确认该 package 使用：

```text
scoring_equivalence_v2
comparison_policy_v2
```

## 10. 当前出现了什么问题

默认 5 方法 smoke package 出现了 2 个 blocker：

### blocker 1

方法：

```text
EVIDENCE_TO_SEMANTICS_SFT
```

问题：

```text
缺少 evidence_to_semantics_formal200.jsonl
```

缺少文件：

```text
<group1_sft-artifact-root>\eval_jsonl\evidence_to_semantics_formal200.jsonl
```

### blocker 2

方法：

```text
TWO_STAGE_AUTO_SFT
```

问题：

```text
requires_chart_to_evidence_outputs_before_stage2
```

含义：

`TWO_STAGE_AUTO_SFT` 必须等待 `CHART_TO_EVIDENCE_SFT` 生成自动 evidence record 后，才能进入第二阶段。

### 对问题的重新解释

这两个 blocker 不应该通过“只跑 D_BASE 和 D1”来绕开。
如果目标是五种方法同时跑通，那么这两个 blocker 就是当前必须解决的前置条件。

正确处理是：

```text
补齐 evidence_to_semantics_eval_jsonl
确认 chart-to-evidence checkpoint 或 smoke 替代设置
明确 two-stage 的第一阶段输出到第二阶段输入的路径
重新生成五方法 smoke package
直到 blockers = 0
```

## 11. 下一步应该做什么

下一步不是直接跑全量，也不是只跑两个方法。
下一步应该是补齐五方法 smoke 的前置条件。

具体顺序：

1. 找到或生成 `EVIDENCE_TO_SEMANTICS_SFT` 需要的 eval JSONL。
2. 确认 `CHART_TO_EVIDENCE_SFT` 使用哪个 checkpoint。
3. 确认 `EVIDENCE_TO_SEMANTICS_SFT` 使用哪个 checkpoint 或运行入口。
4. 明确 `CHART_TO_EVIDENCE_SFT` 输出 evidence record 的目录。
5. 明确 `TWO_STAGE_AUTO_SFT` 如何读取这些自动 evidence record。
6. 重新生成默认五方法 smoke package。
7. preflight blocker 清零后，按依赖关系运行五方法 smoke。
8. 五方法 smoke 全部成功后，再进入五方法全量实验。

## 12. 当前不应该做什么

当前不应该：

```text
不要直接跑全量
不要只把 D_BASE_SAME_BACKBONE 和 D1 当作最终 smoke
不要跳过 EVIDENCE_TO_SEMANTICS_SFT 的缺失数据问题
不要跳过 TWO_STAGE_AUTO_SFT 的阶段依赖问题
不要把 target JSON 输入推理
不要把 raw 424 / CIFP 输入推理
不要把 score 文件输入推理
不要把其他方法预测输入推理
不要提交 local_paths.local.json
不要提交模型、checkpoint、PNG、raw outputs、大结果
```

## 13. 最终全量实验完成后要汇报什么

最终报告至少包括：

```text
git commit hash
运行机器和 GPU 信息
local_paths.local.json 关键路径存在性
五种方法的 run package manifest 路径
preflight blocker 数量
每种方法的 summary_report.json 路径
每种方法的 score 或对应指标
每种方法的 parse failure 数量
每种方法的 schema failure 数量
是否使用 scoring_equivalence_v2
是否使用 comparison_policy_v2
是否发现任何泄漏风险
是否有任何代码改动
```

## 14. 一句话总结

实验思路应改为：

```text
五种 SFT 相关方法作为同一批实验一起打包、一起 smoke、一起进入全量。
```

当前真正的问题是：

```text
五方法 package 还缺 EVIDENCE_TO_SEMANTICS_SFT 的 eval JSONL，
并且 TWO_STAGE_AUTO_SFT 的第一阶段到第二阶段衔接还没有跑通。
```

下一步应该解决这两个前置条件，而不是把实验缩小成只跑 `D_BASE_SAME_BACKBONE` 和 `D1`。

## 15. 五种方法是否需要训练、训练集从哪里来

这一节专门说明训练问题。前面说的是“推理方法”，但 SFT 方法必须先有训练数据和 checkpoint，否则只能生成 run package，不能真正完成实验。

## 15.1 总表

| 方法 | 是否需要训练 | 当前状态 | 训练输入 | 训练标签 | 推理输入 | 推理输出 |
|---|---|---|---|---|---|---|
| `D_BASE_SAME_BACKBONE` | 不需要训练 | 已具备 | 无 | 无 | 航图图片 | `canonical JSON` |
| `D1` | 需要训练 | 已有冻结训练和 checkpoint | 航图图片 | `canonical JSON` | 航图图片 | `canonical JSON` |
| `CHART_TO_EVIDENCE_SFT` | 需要训练 | 目前只有 prompt/schema，训练集和 checkpoint 还要补 | 航图图片 | 图上证据记录 | 航图图片 | 图上证据记录 |
| `EVIDENCE_TO_SEMANTICS_SFT` | 需要训练 | 目前只有 prompt/schema，训练集、checkpoint、text runner 还要补 | 图上证据记录 | questionnaire 或 `canonical JSON` | 图上证据记录 | questionnaire 或 `canonical JSON` |
| `TWO_STAGE_AUTO_SFT` | 本身不一定单独训练 | 依赖前两个子模型 | 使用两个子模型的训练集 | 使用两个子模型的标签 | 航图图片，再接自动证据 | `canonical JSON` |

## 15.2 `D_BASE_SAME_BACKBONE` 的训练说明

`D_BASE_SAME_BACKBONE` 不训练。

它直接使用和 D1 相同的 Qwen2-VL 底座模型，但不加载 LoRA/checkpoint。

它存在的目的不是得到最强模型，而是做对照：

```text
如果 D1 高于 D_BASE_SAME_BACKBONE，说明微调可能带来收益。
如果 D1 不高于 D_BASE_SAME_BACKBONE，说明当前 SFT 训练未必有效，或者 smoke 样本太小需要扩大验证。
```

它没有训练集，也没有训练标签。

## 15.3 `D1` 的训练说明

`D1` 是已经训练过的端到端 SFT 方法。

### 训练任务

```text
输入：完整航图图片
输出：missed approach canonical JSON
```

训练样本格式是 chat JSONL。每一行大致是：

```json
{
  "sample_id": "d_sft_train_0001",
  "split": "train",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "image", "image": "训练图片路径"},
        {"type": "text", "text": "D-SFT prompt"}
      ]
    },
    {
      "role": "assistant",
      "content": "{...canonical JSON...}"
    }
  ]
}
```

### 训练集来源

当前冻结配置记录的 D1 训练集是：

```text
d_sft_train500_dev100
```

规模：

```text
train = 500
dev = 100
```

训练数据不是 formal evaluation 样本。
数据准备脚本会从外部候选航图中选样，然后做以下处理：

1. 下载或定位 FAA D-TPP 2604 PDF。
2. 渲染第一页为完整航图 PNG。
3. 从 CIFP 文件中抽取该 procedure 的 raw CIFP 记录。
4. 用投影脚本把 CIFP/procedure 投影成当前 `canonical JSON` proxy label。
5. 用 `schemas/missed_approach_leg.schema.json` 校验标签。
6. 写出 train/dev manifest 和训练 JSONL。

标签来源在冻结配置里写为：

```text
CIFP_260416_FAACIFP18_to_current_canonical_proxy_projection
```

也就是说，D1 的训练标签不是人工直接写的最终答案，而是由 CIFP/procedure 投影到当前 canonical schema 的 proxy label。

### 防泄漏规则

D1 训练数据准备时排除了：

```text
formal300
pilot10_external
pilot100_external_heldout_feasibility
```

排除检查包括：

```text
chart_id
pdf_name
exact airport/procedure key
procedure family key
image_path
target_path
```

冻结报告记录：

```text
hard_leakage = false
forbidden overlap counts = 0
```

### 训练配置

D1 使用：

```text
base model: Qwen/Qwen2-VL-2B-Instruct
training: QLoRA
r = 8
lora_alpha = 16
lora_dropout = 0.05
target modules = q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
epochs = 1
train samples = 500
dev samples = 100
max_seq_length = 4096
assistant_prefill = "{"
strict JSON only
no parser repair
```

当前本机 D1 checkpoint：

```text
<d_sft-artifact-root>\checkpoints\d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1\checkpoint-final
```

## 15.4 `CHART_TO_EVIDENCE_SFT` 的训练说明

`CHART_TO_EVIDENCE_SFT` 需要训练。
目前仓库里已经有它的 prompt 和 schema，但还没有确认好的训练 JSONL 和 checkpoint。

### 训练任务

```text
输入：完整航图图片
输出：图上证据记录 evidence record
```

它不应该输出 `canonical JSON`。
它只负责说“图上看到了什么证据”。

### 训练样本格式

每一行训练 JSONL 应该类似：

```json
{
  "sample_id": "chart_to_evidence_train_0001",
  "split": "train",
  "chart_id": "KAAA_R03",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "image", "image": "训练航图图片路径"},
        {"type": "text", "text": "chart_to_evidence.zh.md 的 prompt"}
      ]
    },
    {
      "role": "assistant",
      "content": "{\"chart_id\":\"KAAA_R03\",\"evidence_items\":[...]}"
    }
  ]
}
```

assistant 的内容必须符合：

```text
training/group1_sft/manifests/evidence_record.schema.json
```

### 训练标签从哪里来

训练标签应该来自“图上可见证据”的标注，而不是来自最终 target。

推荐来源：

```text
人工标注的 missed approach 文本区域
人工标注的 plan view / profile view / missed approach detail area
人工确认的 fix 文本
人工确认的高度文本
人工确认的 course/radial 文本
人工确认的 holding pattern
人工确认的转弯箭头或方向
人工确认的 DME/navaid 文本
```

也可以辅助使用 OCR，但 OCR 只能作为“图上可见文本”的候选来源，不能把最终答案字段塞进去。

可以作为 evidence label 的内容：

```text
图上文字："CLIMB TO 3000 DIRECT ABCDE AND HOLD"
图上 fix 文本："ABCDE"
图上高度文本："3000"
图上 course/radial 文本："233"
图上 holding pattern 可见
图上右转箭头可见
```

不可以作为 evidence label 的内容：

```text
Q_terminator = HM
leg_2.fix_ident = ABCDE
expected canonical answer = ...
score = ...
raw CIFP says ...
this field is 424_derived
```

原因是这些属于最终语义或 424-derived 信息，不是图上证据本身。

### 训练集怎么划分

必须和 formal evaluation 隔离。

建议：

```text
train：非 formal evaluation 的人工证据标注样本
dev：非 formal evaluation 的人工证据标注样本，用于 checkpoint 选择
eval/smoke：formal split 中的 5 条或 formal eval 样本，只在推理时给图片，不给标签
```

如果要在 formal 样本上做 evidence-level 评分，则 evidence target 只能在评分阶段使用，不能进入推理 prompt。

### 当前缺什么

当前缺：

```text
chart_to_evidence_train_jsonl
chart_to_evidence_dev_jsonl
chart_to_evidence_eval_jsonl
chart-to-evidence checkpoint
evidence-level scorer 或人工审查指标
```

`local_paths.local.json` 里已经有这些路径字段，但本机目前没有对应 JSONL 文件。

## 15.5 `EVIDENCE_TO_SEMANTICS_SFT` 的训练说明

`EVIDENCE_TO_SEMANTICS_SFT` 也需要训练。
目前仓库里有 prompt 和 schema，但还没有完整训练 JSONL、checkpoint 和正式 text-only runner。

### 训练任务

```text
输入：图上证据记录 evidence record
输出：questionnaire JSON 或 canonical JSON
```

推荐先输出 questionnaire JSON，因为它比完整 canonical JSON 更容易控制，也更适合诊断第二阶段能力。

questionnaire schema 是：

```text
training/group1_sft/manifests/evidence_questionnaire.schema.json
```

### 训练样本格式

每一行训练 JSONL 应该类似：

```json
{
  "sample_id": "evidence_to_semantics_train_0001",
  "split": "train",
  "chart_id": "KAAA_R03",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "prompt + evidence record JSON"
        }
      ]
    },
    {
      "role": "assistant",
      "content": "{\"leg_count\":1,\"legs\":[...]}"
    }
  ]
}
```

如果选择直接输出 canonical JSON，assistant label 就是 canonical JSON。
如果选择 questionnaire，后面还需要一个 deterministic converter，把 questionnaire 转成 canonical JSON 后再评分。

### 训练输入从哪里来

训练输入是 evidence record。来源有两种：

第一种：人工确认 evidence record。

```text
人工从航图上确认 visible evidence
只包含图上可见证据
不包含 target answer
不包含 424/CIFP
```

这种适合训练和诊断第二阶段能力。
但如果在 formal eval 上使用人工证据，它是诊断/上界实验，不是端到端公平方法。

第二种：自动 evidence record。

```text
由 CHART_TO_EVIDENCE_SFT 在训练集或 dev 集上自动生成
再作为第二阶段输入
```

这种更接近 `TWO_STAGE_AUTO_SFT` 的真实使用场景。
但要注意，不能用同一条样本的 target 来修正自动 evidence 后再输入模型。

### 训练标签从哪里来

训练标签可以来自训练集的 canonical proxy label，再转换成 questionnaire label。

合法训练标签来源：

```text
训练 split 的 canonical proxy label
训练 split 的人工确认 questionnaire label
训练 split 的 CIFP projection label
```

非法训练标签来源：

```text
formal evaluation target JSON
formal evaluation scoring target
raw 424/CIFP 在推理阶段直接输入
score 文件
其他方法预测结果
```

注意：训练阶段可以使用训练 split 的标签；推理阶段绝对不能读取 eval target。

### 当前缺什么

当前已知缺：

```text
<group1_sft-artifact-root>\eval_jsonl\evidence_to_semantics_formal200.jsonl
```

同时还缺：

```text
evidence_to_semantics_train_jsonl
evidence_to_semantics_dev_jsonl
evidence-to-semantics checkpoint
text-only inference runner
questionnaire -> canonical JSON converter
```

当前 `scripts/group1_sft/run_qwen2vl_group1_sft_inference.py` 主要支持图片输入方法，命令行 choices 目前包括：

```text
D_BASE_SAME_BACKBONE
D1
CHART_TO_EVIDENCE_SFT
```

所以 `EVIDENCE_TO_SEMANTICS_SFT` 还需要补 text-only 推理入口，或者扩展现有 runner。

## 15.6 `TWO_STAGE_AUTO_SFT` 的训练说明

`TWO_STAGE_AUTO_SFT` 本身可以不单独训练一个新模型。
它通常是把两个已经训练好的模型串起来：

```text
CHART_TO_EVIDENCE_SFT 模型
EVIDENCE_TO_SEMANTICS_SFT 模型
```

### 它的执行流程

第一阶段：

```text
航图图片 -> CHART_TO_EVIDENCE_SFT -> 自动 evidence record
```

第二阶段：

```text
自动 evidence record -> EVIDENCE_TO_SEMANTICS_SFT -> questionnaire 或 canonical JSON
```

如果第二阶段输出 questionnaire，还要再做：

```text
questionnaire -> deterministic converter -> canonical JSON
```

最后评分：

```text
canonical JSON -> scoring_equivalence_v2 scorer -> score
```

### 它需要哪些训练数据

它不一定需要第三套训练数据，但它需要前两套训练完成：

```text
CHART_TO_EVIDENCE_SFT 的训练集和 checkpoint
EVIDENCE_TO_SEMANTICS_SFT 的训练集和 checkpoint
```

为了让第二阶段适应自动 evidence，建议额外准备一种训练/开发数据：

```text
训练 split 航图
-> 用 CHART_TO_EVIDENCE_SFT 自动生成 evidence record
-> 用训练 split 标签生成 questionnaire/canonical label
-> 训练或微调第二阶段模型适应自动 evidence 的噪声
```

这一步必须只在训练 split 或 dev split 上做，不能用 formal eval target 修正自动 evidence。

### 当前缺什么

当前缺：

```text
CHART_TO_EVIDENCE_SFT 自动输出目录规范
自动 evidence record -> EVIDENCE_TO_SEMANTICS_SFT 输入 JSONL 的转换脚本
EVIDENCE_TO_SEMANTICS_SFT text runner
questionnaire -> canonical JSON converter
two-stage summary_report.json 汇总逻辑
```

## 16. 五方法一起跑通前必须补齐的训练/数据清单

要真正做到“五种方法同时 smoke，再同时全量”，必须补齐下面这些东西：

### 已经有的

```text
D_BASE_SAME_BACKBONE 底座模型
D1 checkpoint
D1 训练冻结报告
D1 训练配置
formal 图片
scoring_equivalence_v2 target
comparison_policy_v2
run package 脚本
图片方法推理 runner
```

### 还没有或还未确认的

```text
CHART_TO_EVIDENCE_SFT train JSONL
CHART_TO_EVIDENCE_SFT dev JSONL
CHART_TO_EVIDENCE_SFT eval/smoke input JSONL
CHART_TO_EVIDENCE_SFT checkpoint
CHART_TO_EVIDENCE_SFT evidence-level scorer

EVIDENCE_TO_SEMANTICS_SFT train JSONL
EVIDENCE_TO_SEMANTICS_SFT dev JSONL
EVIDENCE_TO_SEMANTICS_SFT eval/smoke input JSONL
EVIDENCE_TO_SEMANTICS_SFT checkpoint
EVIDENCE_TO_SEMANTICS_SFT text-only runner
questionnaire -> canonical JSON converter

TWO_STAGE_AUTO_SFT bridge script:
CHART_TO_EVIDENCE_SFT output -> EVIDENCE_TO_SEMANTICS_SFT input

TWO_STAGE_AUTO_SFT final canonical output and scoring summary
```

## 17. 现在 blocker 的真实含义

之前 package 里出现的 2 个 blocker，本质上不是路径小问题，而是训练/数据链路没有补齐：

### `EVIDENCE_TO_SEMANTICS_SFT` blocker

缺：

```text
evidence_to_semantics_formal200.jsonl
```

这说明第二阶段方法还没有可运行的 eval input manifest。
进一步说，它的 train/dev JSONL、checkpoint、runner 也需要确认。

### `TWO_STAGE_AUTO_SFT` blocker

缺：

```text
CHART_TO_EVIDENCE_SFT 的自动 evidence 输出
```

这说明两阶段流水线还没接起来。
必须先让第一阶段生成 evidence record，再把 evidence record 转成第二阶段输入。

## 18. 更新后的下一步

下一步应该按训练链路补齐，而不是直接全量：

1. 盘点本机是否已有 chart-to-evidence 的人工证据标注 JSONL。
2. 如果没有，先定义 evidence record 标注来源和转换脚本。
3. 生成 `chart_to_evidence_train_jsonl` 和 `chart_to_evidence_dev_jsonl`。
4. 训练 `CHART_TO_EVIDENCE_SFT` checkpoint。
5. 盘点或生成 evidence-to-semantics 的 train/dev JSONL。
6. 明确第二阶段输出 questionnaire 还是 canonical JSON。
7. 如果输出 questionnaire，先实现 questionnaire 到 canonical JSON 的确定性转换。
8. 训练 `EVIDENCE_TO_SEMANTICS_SFT` checkpoint。
9. 实现或扩展 text-only runner。
10. 实现 two-stage bridge。
11. 重新生成五方法 smoke package。
12. 五方法 smoke 全部通过后，再一起全量。
