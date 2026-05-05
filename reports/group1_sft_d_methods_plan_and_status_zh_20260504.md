# 实验组1新增 D 系列方法方案与当前状态

日期：2026-05-04

本文只记录当前确定继续推进的三个 D 系列方法，不再把早期讨论过的人工证据两阶段方法、自动两阶段方法作为本轮默认方法。

## 一、实验目标

实验组1的任务是：

```text
输入 FAA 航图图片
输出 missed approach 的 canonical JSON
使用统一的 scoring_equivalence_v2 target 和 comparison_policy_v2 评分
```

本轮新增内容的目的，是在同一底座和同一评分口径下比较：

1. 未经过 SFT 的同底座模型是否本来就能完成任务。
2. 已有 D1 端到端 SFT 是否显著优于未微调底座。
3. 在 D1 基础上继续加入“从航图中找复飞相关证据框”的监督后，是否能改善最终 canonical JSON，同时额外产生可诊断的证据框输出。

## 二、数据划分

实验组1 formal300 固定为 50+200+50：

```text
development: 50
evaluation: 200
probe: 50
```

使用边界：

- `development` 50 张：允许用于本轮新增 SFT 的训练、开发、smoke 和调试。
- `evaluation` 200 张：用于正式全量评测。
- `probe` 50 张：保留为 holdout，不用于训练或调参。

推理阶段禁止读取 target JSON、score、raw 424/CIFP、其他方法预测或人工答案。`scoring_manifest`、target 和 comparison policy 只能在预测完成后用于评分。

## 三、方法一：D_BASE_SAME_BACKBONE

中文含义：同底座未微调对照。

输入：

```text
完整航图图片
固定 canonical prompt
canonical output schema
Qwen2-VL-2B-Instruct 底座模型
```

不使用：

```text
LoRA adapter
SFT checkpoint
target JSON
score
raw 424/CIFP
其他方法预测
人工答案
```

输出：

```text
missed approach canonical JSON
```

实验目的：

这个方法是低基线，用来回答“如果只给同一个底座模型和同一个 prompt，不经过 D1 任务训练，模型能不能自己完成 canonical JSON 任务”。

当前结果：

- 50 样本 run package 已生成，preflight blocker 为 0。
- raw 推理 50/50 完成。
- raw strict JSON parse ok 为 8/50。
- 保守 canonicalization 后 50/50 都可以进入评分。
- 正式保守结果为 0/1022。
- 额外诊断性错层级 salvage 结果为 7/1022，只用于错误分析，不作为正式 D_base 分数。

结论：

D_base 流程已经跑通，但任务能力基本为 0。它可以作为有效的未微调低基线，不应继续为了提高分数而调 prompt 或引入额外修复，否则会破坏对照意义。

## 四、方法二：D1

中文含义：已有端到端 D-SFT 方法。

输入：

```text
完整航图图片
固定 canonical prompt
canonical output schema
Qwen2-VL-2B-Instruct 底座模型
D1 SFT adapter/checkpoint
```

输出：

```text
missed approach canonical JSON
```

实验目的：

D1 用来回答“同样的底座模型在经过端到端 SFT 后，是否能从完整航图直接生成最终 missed approach canonical JSON”。

与 D_base 的唯一核心能力差异：

```text
D_base 不加载 SFT checkpoint
D1 加载 D1 SFT checkpoint
```

因此 D_base 和 D1 的比较可以衡量 D1 SFT 本身带来的收益。

当前状态：

- D1 checkpoint 本机路径检查已通过。
- 已生成 D1 50 样本 run package，preflight blocker 为 0。
- 当前正在跑 D1 50 样本推理。

下一步：

1. 等 D1 50 样本推理完成。
2. 检查 raw parse、schema valid、samples scored 和 score。
3. 如果 D1 raw 输出存在可机械修复的 envelope/schema 问题，使用与 D_base 相同边界的 D1 canonicalization 策略处理。
4. D1 50 样本确认跑通后，再决定是否复用既有 D1 200 样本结果，或在同一个新 run package 口径下复跑 D1 evaluation 200。

## 五、方法三：D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL

中文含义：D1 基础上继续训练“找复飞证据框并输出最终答案”的方法。

输入：

```text
完整航图图片
D1 checkpoint 作为继续训练起点
证据框监督数据
canonical JSON 监督数据
```

训练数据来源：

`development` 50 张中的人工标注可以提供：

- 航图上复飞相关区域框。
- 框对应的航段或字段关系。
- 可见文字、图形线索和候选字段绑定。
- 对应的 canonical missed approach JSON。

训练目标不是只训练一个检测器，也不是替代 D1，而是在 D1 已经学会端到端 canonical 输出的基础上，继续加入证据框监督，让模型输出：

```json
{
  "chart_id": "...",
  "evidence_boxes": [
    {
      "box_id": "...",
      "bbox": [0.0, 0.0, 1.0, 1.0],
      "evidence_type": "...",
      "visible_text": "...",
      "linked_leg_index": 1,
      "linked_fields": ["..."]
    }
  ],
  "canonical_prediction": {
    "...": "missed approach canonical JSON"
  }
}
```

正式评分只使用：

```text
canonical_prediction
```

`evidence_boxes` 只用于诊断分析，例如：

- 是否找到了复飞文字区域。
- 是否找到了 hold、fix、course、altitude 等相关图上证据。
- 错误样本是“证据没找到”还是“证据找到了但语义组织错了”。

实验目的：

这个方法测试“额外学习找证据框”是否会帮助最终 canonical JSON，而不是把两阶段方法和 D1 混在一起。它仍然是一个完整航图输入的方法，可以和 D_base、D1 在同一个 evaluation 200 上对比。

当前状态：

- prompt 已有：`training/group1_sft/prompts/d1_chart_to_evidence_boxes_and_canonical.zh.md`
- wrapper schema 已有：`training/group1_sft/manifests/d1_chart_to_evidence_boxes_and_canonical.schema.json`
- 训练 JSONL 构造脚本已有：`scripts/group1_sft/build_d1_evidence_boxes_canonical_jsonl_from_annotations.py`
- 推理 runner 已支持 wrapper 输出，并提取 `canonical_prediction` 进行正式评分。
- 本机路径检查显示该方法 checkpoint 已存在。

下一步：

1. D1 50 样本完成后，生成同口径的该方法 50 样本 run package。
2. 跑该方法 50 样本推理。
3. 检查 wrapper schema、canonical schema、parse failure、score。
4. 如果 50 样本跑通，再进入 evaluation 200。

## 六、正式推进顺序

当前顺序：

1. D_base 50：已完成，作为低基线。
2. D1 50：正在运行，用于确认本机新入口和当前 package 口径正常。
3. D1 加证据框 50：D1 50 完成后运行。
4. 三个方法都确认 50 样本可跑通后，进入 evaluation 200。

全量阶段应该使用同一批 evaluation 200、同一套 target v2、同一套 comparison policy v2，并保留每个方法的 raw output、schema validation、parse failure 和 summary report。

## 七、不能提交到 Git 的内容

不得提交：

- `training/group1_sft/configs/local_paths.local.json`
- 模型底座目录
- LoRA/checkpoint 目录
- PNG/PDF 图片数据
- raw prediction outputs
- 大体积逐样本结果目录
- 本机绝对路径
- 带 token 的标注系统 URL

可以提交：

- 方法定义文档
- prompt
- schema
- run package 构造脚本
- 推理 runner
- canonicalization 脚本
- 小体积汇总报告
- 不含本机绝对路径和 token 的实验计划
