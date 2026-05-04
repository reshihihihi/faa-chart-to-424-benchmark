# 实验组 1 补充方法执行方案：D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL

日期：2026-05-04

## 1. 当前只做哪一个新增方法

当前只继续执行一个新增方法：

```text
D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL
```

这里的 `D1` 是已经训练过的端到端 SFT checkpoint，用作继续训练起点；本轮新增内容不是重新发明 D1，也不是同时跑两阶段方法。

这个方法的目的：

```text
在旧 D1 已经会从完整航图输出 missed approach canonical JSON 的基础上，
继续用第一个 50 张里的人工审核框、航段、字段、证据关系进行训练，
让模型额外学习“答案来自图上哪些证据”。
```

## 2. 为什么正式输出仍然保持旧 D1 canonical JSON

正式评分器只接受旧 D1 形状的 canonical JSON。如果把证据框、证据关系一起塞进正式输出，评分链路会变复杂，也会和原 D1 不可比。

所以本方法分成两个层面：

训练层面：

```json
{
  "evidence_boxes": [],
  "answer_grounding": [],
  "canonical_prediction": {}
}
```

正式评分层面：

```json
{
  "chart_id": "...",
  "procedure": {
    "airport": "...",
    "approach_ident": "...",
    "chart_name": "..."
  },
  "missed_approach": {
    "leg_count": {"status": "present", "value": 0},
    "legs": []
  }
}
```

也就是说，训练时让模型学习找证据；正式推理评分时仍然让它输出旧 D1 的 canonical JSON。这样可以观察“额外证据监督”是否改善最终答案，同时不改变评分 JSON。

## 3. 训练集从哪里来

训练数据来自后台人工审核导出。后台已经提供：

- 图上框的位置和类型；
- 框里的可见文字或图形线索；
- 框和复飞航段的关系；
- 框和字段的关系；
- 字段和证据框的关系；
- 最终人工审核字段答案。

不需要新增人工标注，也不需要额外构造目标答案。

固定使用 formal300 的 50+200+50 划分：

- 第一个 50 张：用于本方法训练和开发验证；
- 中间 200 张：正式评估，只能做推理和评分；
- 最后 50 张：本轮不用。

当前构建方式：

- train：40 张；
- dev：10 张；
- eval input：200 张，只包含图像输入，不包含答案。

## 4. 每条训练样本的输入输出

训练输入：

- 完整航图图片；
- 本方法专用训练 prompt。

训练输出：

- `evidence_boxes`：模型要找出的图上证据区域，包括必要大框和字段细框；
- `answer_grounding`：每个航段字段由哪些证据框支持；
- `canonical_prediction`：旧 D1 形状的最终 canonical JSON。

证据框要求：

- 不能只保留几个大框；
- 要优先保留和字段有关系的细框，例如修正点文字、修正点符号、高度文字、爬升箭头、航向/径向文字、导航台文字、路径线段、出航/入航标记；
- 大框只作为上下文，不替代细框。

## 5. 推理和评分边界

推理阶段禁止读取：

- target JSON；
- score；
- raw 424/CIFP；
- 其他方法预测；
- 人工答案文件。

`scoring_manifest` 只能在预测完成后用于评分。

正式评分流程：

1. 用继续训练后的 checkpoint 对航图生成旧 D1 canonical JSON；
2. 保存 raw output；
3. 用与 D1 相同的机械 canonicalizer 修 JSON 外壳和 schema 形状；
4. canonical JSON 写出后，才读取 `scoring_equivalence_v2` target 和 `comparison_policy_v2` 评分。

canonicalizer 的作用只限于格式规范化，例如补 `chart_id` 外壳、合并模型自己输出的 header/body JSON、把非法外壳转成合法 schema。它不能使用 target、score、raw 424/CIFP 或其他方法预测来改答案值。

## 6. 目前已经完成什么

已经完成：

- 从后台导出构建了本方法 JSONL；
- train 40、dev 10、eval input 200；
- schema errors 为 0；
- eval input 标签泄漏为 0；
- 从旧 D1 checkpoint 继续训练了 r2；
- r2 训练无截断，best dev loss 约为 0.266；
- wrapper 形式的正式推理 smoke 失败，原因是输出太长且容易重复证据框；
- 已改为正式评分输出 canonical JSON，证据 wrapper 保留为训练和诊断目标。

5 张 smoke 当前结果：

- raw outputs found：5/5；
- canonical JSON written：5/5；
- schema valid：5/5；
- samples scored：5/5；
- score：54/101，accuracy 0.535；
- final chart_id mismatch：0。

## 7. 现在的执行顺序

先做 50 张跑通样本：

```powershell
python scripts\group1_sft\prepare_group1_sft_run_package.py `
  --paths training\group1_sft\configs\local_paths.local.json `
  --limit 50 `
  --methods D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL `
  --run-id group1_sft_d1_evidence_dev50_canonical
```

然后按生成的 `RUN_COMMANDS.md` 执行本方法正式推理和 canonicalize+score。

50 张确认：

- raw outputs 是否为 50/50；
- canonical JSON 是否为 50/50；
- schema invalid 是否为 0；
- final chart_id mismatch 是否为 0；
- parse/schema failure 是否清零或只剩可解释的机械格式问题；
- score 是否正常写入。

50 张跑通后，再跑中间 200 张正式评估：

```powershell
python scripts\group1_sft\prepare_group1_sft_run_package.py `
  --paths training\group1_sft\configs\local_paths.local.json `
  --split-subset evaluation `
  --methods D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL `
  --run-id group1_sft_d1_evidence_formal200_canonical
```

正式 200 的报告以 canonicalizer 输出为准。

## 8. 加速原则

可以加速的地方：

- 正式评分推理使用旧 D1 canonical prompt，不使用大 wrapper prompt；
- `max-new-tokens` 使用 1024，足够覆盖 canonical JSON；
- 推理不在中途读取 target；
- 推理结束后一次性 canonicalize+score；
- 不并发启动多个模型进程抢同一张 GPU。

不为了加速而改变的地方：

- 不降低图片输入质量；
- 不改 checkpoint；
- 不改训练/评估 split；
- 不改 target；
- 不改 comparison policy；
- 不用 target 修答案；
- 不删除失败样本。

## 9. Git 提交边界

可以提交：

- 代码；
- prompt；
- schema；
- 路径模板；
- 设计文档；
- `.gitignore`。

不能提交：

- `local_paths.local.json`；
- 后台导出 JSON；
- 训练 JSONL；
- 图片、PDF；
- checkpoint；
- raw outputs；
- 大结果目录。
