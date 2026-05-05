# 实验组 1：D 相关三种方法的补充实验方案与当前状态

## 1. 本轮只整理和比较这三种方法

本轮实验组 1 的 SFT 补充内容只保留三种 D 相关方法：

| 方法 | 是否训练 | 输入 | 输出 | 主要目的 |
|---|---:|---|---|---|
| 同底座未微调对照 | 否 | 完整航图图片 | missed approach canonical JSON | 判断同一个视觉语言模型底座在不做实验组 1 SFT 时的原始能力 |
| D1 | 是，已有 | 完整航图图片 | missed approach canonical JSON | 保留实验组 1 已有端到端 SFT baseline |
| D1 基础上增加图上证据框监督 | 是，本轮新增 | 完整航图图片 | 先输出 `evidence_boxes`，再输出 `canonical_prediction` | 检验显式学习复飞证据区域/框是否能改善最终 canonical JSON |

本轮不再继续推进以下三个旧方向：

- 完整航图到图上证据记录的单独模型。
- 人工证据到语义的单独模型。
- 两个模型串联的自动两阶段方法。

原因：当前目标是用最短路径验证一个清楚的对照问题：**D1 已经能端到端答题时，额外加入图上证据框监督，是否能提升最终 canonical JSON。**

## 2. 三种方法的输入、输出和评分边界

### 2.1 同底座未微调对照

- 输入：完整航图图片。
- 训练：不使用实验组 1 的 SFT checkpoint。
- 推理输出：missed approach canonical JSON。
- 评分：使用原有 missed approach canonical schema、`scoring_equivalence_v2` target 和 `comparison_policy_v2`。
- 用途：作为同底座模型原始能力对照。

### 2.2 D1

- 输入：完整航图图片。
- 训练：使用已有 D1 LoRA/checkpoint。
- 推理输出：missed approach canonical JSON。
- 评分：使用原有 missed approach canonical schema、`scoring_equivalence_v2` target 和 `comparison_policy_v2`。
- 用途：作为实验组 1 当前端到端 SFT baseline。

### 2.3 D1 基础上增加图上证据框监督

新增方法不是单独训练“找框模型”，也不是两个模型串联。它是从 D1 checkpoint 继续训练的单模型联合输出：

```text
完整航图图片
→ evidence_boxes
→ canonical_prediction
```

推理输出顶层结构固定为：

```json
{
  "evidence_boxes": [],
  "canonical_prediction": {}
}
```

评分时只抽取 `canonical_prediction`，再交给原 canonical scorer。`evidence_boxes` 只用于诊断分析，不进入正式 canonical score。

## 3. 新增方法的训练集来源

实验组 1 沿用既有 300 张航图划分：

- 第一个 50 张：允许用于训练、开发验证、prompt 和格式调试。
- 中间 200 张：正式评测，只能在预测完成后评分。
- 最后 50 张：保留，不参与本轮训练和正式分数。

新增方法只使用第一个 50 张，并切成：

- 40 张训练。
- 10 张开发验证。

训练标签来自人工标注导出中的三类信息：

- `regions`：人工框、框坐标、区域类型、框内可见文字或区域标签。
- `accepted_mappings`：框与复飞航段、canonical 字段之间的对应关系。
- `field_reviews`：第一个 50 张内部允许使用的 canonical 答案标签。

正式 evaluation 200 的输入 JSONL 只包含图片和 prompt，没有 assistant 标签，没有 target JSON，没有 score，没有 raw 424/CIFP。

## 4. evidence_boxes 的设计

每张图最多输出 12 个复飞相关证据框。bbox 统一使用归一化格式：

```json
[x_center, y_center, width, height]
```

每个证据框格式：

```json
{
  "box_id": "box_or_region_id",
  "bbox": [0.7962, 0.1492, 0.3135, 0.0771],
  "region_type": "MISSED_APPROACH_TEXT",
  "visible_text": null,
  "candidate_bindings": [
    {
      "leg_index": 3,
      "candidate_leg_id": "candidate_leg_identifier",
      "field_name": "Q1_fix_ident",
      "evidence_role": "supports_field",
      "human_confidence": "medium"
    }
  ]
}
```

重要边界：

- `evidence_boxes` 不放 `final_value`。
- `evidence_boxes` 不放 `canonical_answer`。
- `evidence_boxes` 不放 target JSON、score、raw 424/CIFP 或其他方法预测。
- 最终答案只放在 `canonical_prediction`。

## 5. 已完成的代码和配置整理

本次整理新增或修改了以下可提交内容：

- 新增训练数据构造脚本：`scripts/group1_sft/build_d1_evidence_boxes_canonical_jsonl_from_annotations.py`
- 修改训练脚本：`scripts/group1_sft/train_qwen2vl_group1_sft_lora.py`
  - 支持新增方法。
  - 支持从 D1 adapter 继续训练，而不是重新初始化。
- 修改推理脚本：`scripts/group1_sft/run_qwen2vl_group1_sft_inference.py`
  - 支持 wrapper 输出。
  - 支持抽取 `canonical_prediction` 进行评分。
  - 支持记录 repetition penalty。
- 修改 run package 脚本：`scripts/group1_sft/prepare_group1_sft_run_package.py`
  - 默认方法集改为三种 D 相关方法。
  - run package 优先使用 `scoring_equivalence_v2` target 和 `comparison_policy_v2`。
- 更新方法集配置：`training/group1_sft/configs/group1_sft_method_set.json`
- 更新路径模板：`training/group1_sft/configs/local_paths.template.json`
- 新增 prompt：`training/group1_sft/prompts/d1_chart_to_evidence_boxes_and_canonical.zh.md`
- 新增 wrapper schema：`training/group1_sft/manifests/d1_chart_to_evidence_boxes_and_canonical.schema.json`

不提交：

- `training/group1_sft/configs/local_paths.local.json`
- 模型和 checkpoint
- PNG
- 训练 JSONL
- raw outputs
- 大结果文件
- 本机绝对路径配置

## 6. 当前已经跑到哪里

### 6.1 训练数据生成

新增方法的 JSONL 已在本机生成：

- train rows：40
- dev rows：10
- evaluation input rows：200
- schema errors：0
- evaluation input violations：0
- 每张图证据框数量：最少 5，最多 12，平均约 7.86
- 训练/开发标签没有截断风险：实际最长序列长度约 3481，训练上限为 4096

### 6.2 新增方法训练

新增方法已从 D1 checkpoint 继续训练一轮：

- run id：`d1_chart_to_evidence_boxes_and_canonical_dev50_20260504_r2`
- 训练样本：40
- 开发验证样本：10
- epoch：1
- learning rate：`5e-5`
- max sequence length：4096
- truncated train samples：0
- dev truncated samples：0
- best dev loss：约 0.4565
- checkpoint：已生成 `checkpoint-final`

这个结果说明训练流程、D1 adapter 续训和标签长度控制已经跑通。

### 6.3 5 样本 smoke package

已生成 5 样本 smoke run package：

- 方法数：3
- 每个方法样本数：5
- preflight blocker：0
- scoring target 来源：`scoring_equivalence_v2`
- comparison policy：`comparison_policy_v2`

### 6.4 5 样本 smoke 结果

同底座未微调对照：

- samples total：5
- samples scored：0
- failure count：5
- score：不可计算
- 失败类型：主要是 parse failure，另有 schema validation failure

D1：

- samples total：5
- samples scored：4
- failure count：1
- score：54 / 82 = 0.6585
- 失败类型：1 个 parse failure

D1 基础上增加图上证据框监督：

- 已先做 1 张关键 smoke 检查。
- 当前未通过。
- 主要问题：模型在 `evidence_boxes` 部分重复生成同一个假框，无法及时关闭数组，导致 JSON 不闭合。
- 已尝试轻量改进：
  - prompt 中加入“不要重复同一框，无法确定就输出更少框”。
  - 推理中加入 repetition penalty。
  - 将 `max_new_tokens` 从 4096 收到 2560。
- 结果：仍出现长输出不闭合，说明问题不是单纯 token 上限，而是证据框输出结构过难、训练样本太少或框字段设计不够稳。

## 7. 当前问题分析

新增方法的问题不在 scoring，也不在 target 泄漏，而在生成阶段：

1. `evidence_boxes` 字段太复杂  
   当前每个框同时要求 bbox、region type、visible text、candidate leg id、field name、evidence role、confidence。40 条训练样本可能不足以让模型稳定学会这个长结构。

2. 证据框输出容易形成重复循环  
   模型第一张 smoke 中反复生成同一个框，说明它还没学会“最多输出若干不同框，然后关闭数组，再进入 canonical_prediction”。

3. 模型把 canonical 概念混入 box 字段  
   失败样例中出现类似把 altitude constraint 语义写进 `region_type` 或 `evidence_role` 的情况。这说明证据框字段和最终答案字段的边界还需要进一步简化。

4. 不能直接跑 50 或 200  
   当前新增方法还没有通过 1 张 smoke，更不能跑 development 50 或 formal 200。继续全量只会扩大失败结果。

## 8. 下一步建议

下一步应该先修新增方法的证据框输出设计，然后重新训练和验证：

1. 简化 `evidence_boxes` 标签
   - 第一版只保留 `box_id`、`bbox`、`region_type`、`field_names`。
   - 暂时去掉 `candidate_leg_id`、`evidence_role`、`human_confidence`。
   - 框 ID 改成 `box_001`、`box_002` 这种稳定编号，避免模型学习复杂 chart-specific id。

2. 降低每张图框数量
   - 从最多 12 个降到最多 6 到 8 个。
   - 优先保留 missed approach 文本块、plan view、detail/profile 区域和少数关键细粒度框。

3. 重新生成 40/10 JSONL
   - 仍然只用第一个 50 张。
   - 仍然不使用 formal 200 的 target。

4. 从 D1 checkpoint 重新续训一个新 run id
   - 保持低学习率。
   - 继续检查截断数量必须为 0。

5. 先跑 1 张 smoke
   - 要求能关闭 `evidence_boxes` 数组。
   - 要求能输出 `canonical_prediction`。

6. 再跑 5 张 smoke
   - parse/schema failure 接近 0 后再进入 50 张 development。

7. 50 张 development 跑通后，才允许跑 200 张 formal evaluation。

## 9. 实验边界

后续所有推理阶段必须继续遵守：

- 不读取 target JSON。
- 不读取 score。
- 不读取 raw 424/CIFP。
- 不读取其他方法预测。
- `scoring_manifest` 只能在预测完成后评分时使用。
- run package 必须继续优先使用 `scoring_equivalence_v2` target 和 `comparison_policy_v2`。

当前结论：三方法框架和代码路径已经整理完成，D1 与同底座对照 smoke 已复现；新增方法的训练流程已跑通，但证据框联合输出还没有跑通，需要先简化框标签再继续验证。
