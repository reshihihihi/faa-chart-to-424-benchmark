# 实验组1补充方法最终方案：D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL

日期：2026-05-04

## 一、本轮只做什么

本轮只做一个新增方法：

```text
D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL
```

旧 `D1` 只作为继续训练的起点 checkpoint，不是本轮要重新跑的新增方法。`D_BASE_SAME_BACKBONE`、普通 `D1` 复跑、`D1_DEV50_ONLY`、两阶段方法都不在当前执行范围内。

## 二、核心目的

这个方法的目的不是改变最终答案格式，也不是把证据框拿去评分。

真正目的只有一个：

```text
在旧 D1 已经会输出最终 canonical JSON 的基础上，
继续训练它学会先找到图上证据来源，
再根据这些证据组织最终 canonical JSON。
```

最终评分仍然是：

```text
模型最终 canonical JSON
vs
424/CIFP 派生出来的 scoring_equivalence_v2 目标 JSON
```

新增的证据框和字段证据关系只用于训练约束和错误分析，不直接参与最终分数。

## 三、最终输出和评分边界

训练和原始推理时，模型会先输出一个诊断外壳：

```json
{
  "evidence_boxes": [],
  "answer_grounding": [],
  "canonical_prediction": {}
}
```

这三个部分的含义是：

- `evidence_boxes`：模型认为图上哪些区域是复飞相关证据。
- `answer_grounding`：每个航段、每个字段的答案由哪些证据框支持。
- `canonical_prediction`：旧 D1 形状的最终 missed approach canonical JSON。

正式评分时不把整个外壳交给 scorer。推理脚本会保存两类文件：

1. 诊断文件：保留完整外壳，用于看证据框和字段证据关系。
2. 正式预测文件：只抽出 `canonical_prediction`，保存成旧 D1 的 canonical JSON。

scorer 只读取第二类正式预测文件。因此最终用于评分的 JSON 仍然是旧格式：

```json
{
  "chart_id": "...",
  "procedure": {
    "airport": "...",
    "approach_ident": "...",
    "chart_name": "..."
  },
  "missed_approach": {
    "leg_count": {"status": "...", "value": "..."},
    "legs": []
  }
}
```

所以本方法满足这个约束：

```text
最终 canonical JSON 仍按照之前 D1 的格式；
只是训练和诊断中额外要求模型找到证据来源。
```

## 四、训练数据来源

训练数据只来自标注后台已经有的人工审核关系，不新增人工工作。

后台导出中使用的信息包括：

- 图上框：每个框的位置、类型、可见文字。
- 框和航段关系：这个框对应哪个复飞航段。
- 框和字段关系：这个框支持哪个字段。
- 字段和证据关系：某个字段答案由哪些框支持。
- 最终字段答案：人工审核后的标准字段答案。

脚本读取的后台字段主要包括：

- `regions`
- `accepted_mappings`
- `candidate_mappings_reviewed`
- `source_field_name`
- `field_reviews`
- `field_reviews[].canonical_answer`

其中 `candidate_mappings_reviewed` 和 `source_field_name` 是为了利用后台已经保存的细框候选关系，例如爬升箭头、修正点符号、径向文字、导航台文字等。这样不需要额外标注，也不会退化成只训练几个大框。

## 五、固定数据划分

继续使用 formal300 固定的 50+200+50：

- 第一个 50 张：用于构建本方法训练集和开发验证集。
- 中间 200 张：正式评估输入，只能推理和评分。
- 最后 50 张：本轮不用。

当前构建方式：

- 40 张训练。
- 10 张开发验证。
- 200 张正式评估输入。

这 40/10 都来自第一个 50。中间 200 张不会有 assistant 标签，不会包含最终答案。

## 六、每条训练样本的输入

每条训练样本的模型输入只有两部分：

1. 完整航图图片。
2. 本方法专用提示词。

禁止输入：

- 目标 JSON。
- 分数。
- raw 424。
- CIFP。
- 其他方法预测。
- 人工答案文件。
- 后台答案路径。

## 七、每条训练样本的输出

每条训练样本的 assistant 标签由三部分组成。

第一部分是 `evidence_boxes`，表示图上证据框。

第二部分是 `answer_grounding`，表示每个航段、每个字段和证据框之间的关系。

第三部分是 `canonical_prediction`，表示旧 D1 形状的最终答案。

训练时让模型同时学习这三部分，是为了让模型不要只记最终答案，而是学习：

```text
图上哪里有证据
哪个字段依赖哪些证据
最终标准答案应该是什么
```

## 八、证据框怎么构建

证据框来自后台已有的 `regions`。

证据框不是只有细框，也不是只有大框，而是：

```text
必要大框 + 字段细框
```

大框包括：

- 平面图区域。
- 复飞文字说明区域。
- 下方复飞细节区域。

大框的作用是提供整体上下文，尤其是航段结构、复飞语义、holding 或图形关系。

细框包括：

- 修正点文字框。
- 高度文字框。
- 爬升箭头框。
- 修正点符号框。
- 径向文字框。
- 导航台文字框。
- 航向文字框。
- 路径线段框。
- 出航/入航标记框。

细框的作用是支持具体字段，例如修正点、高度、航向/径向、转弯方向等。

脚本会优先保留和字段有关系的细框，同时保留必要大框作为上下文。这样既不丢掉大范围语义，也不会退化成只看三个粗框。

## 九、一个航段可以对应多个框

这个方案明确支持：

```text
一个航段的一个字段，对应多个证据框。
```

例如第 2 个航段的修正点，可能同时依赖：

- 修正点文字框。
- 修正点符号框。
- 复飞文字说明区域。
- 平面图上下文区域。

因此 `answer_grounding` 里使用数组：

```json
{
  "leg_index": 2,
  "field_name": "Q1_fix_ident",
  "answer_path": "missed_approach.legs[1].answers.Q1_fix_ident",
  "support_mode": "direct_visible_text",
  "evidence_box_ids": ["box_001", "box_003", "box_005"],
  "evidence_summary": "第2段修正点由 box_001 的修正点文字、box_003 的修正点符号和 box_005 的上下文支持"
}
```

这里不是“一个航段一个框”，而是“字段到多个证据框”的关系。

## 十、证据框字段

每个证据框包含：

- `box_id`：训练时重新编号，如 `box_001`。
- `bbox`：归一化框坐标。
- `region_type`：框类型。
- `visible_text`：框内可见文字；纯符号框可以是 null。
- `field_names`：这个框支持哪些字段。
- `evidence_role`：这个框的作用。

模型输出里不要求后台内部 region id。后台 id 只留在脚本内部用于映射和审计。

## 十一、字段证据关系

每条字段证据关系包含：

- `leg_index`：航段编号。
- `field_name`：字段名。
- `answer_path`：字段在最终 canonical JSON 中的位置。
- `support_mode`：证据支持方式。
- `evidence_box_ids`：支持该字段的一个或多个证据框。
- `evidence_summary`：用证据框编号和可见内容说明证据来源。

如果字段是规则默认补全，不能伪装成直接从图上可见。若证据不足，也要明确记录。

## 十二、最终答案怎么构建

最终答案来自后台人工审核过的字段答案，也就是 `field_reviews[].canonical_answer`。

脚本会把这些字段答案组装成旧 D1 的 canonical JSON：

- 路径终止符。
- 修正点。
- 高度限制。
- 转弯方向。
- 航向或径向。
- holding 参数。

这个最终答案放入训练标签的 `canonical_prediction` 里。

正式评分时，再从原始诊断输出中抽出它，作为最终预测文件。

## 十三、正式评估输入如何防泄漏

evaluation 200 只生成输入，不生成 assistant 标签。

正式评估输入不包含：

- 最终答案。
- 字段答案。
- 评分结果。
- raw 424。
- CIFP。
- 其他方法预测。
- 后台答案路径。

`scoring_manifest` 只能在预测完成后用于评分。

## 十四、当前构建审计状态

当前本地已经用后台最新导出构建过一次本方法数据集，构建检查结果为：

- 训练样本：40。
- 开发验证样本：10。
- 正式评估输入：200。
- schema errors：0。
- eval input violations：0。
- 评估输入 assistant 标签：0。
- 评估输入答案泄漏：0。

已经纳入训练标签的框类型包括：

- 平面图大框。
- 复飞文字说明大框。
- 修正点文字框。
- 高度文字框。
- 爬升箭头框。
- 修正点符号框。
- 径向文字框。
- 导航台文字框。
- 航向文字框。
- 路径线段框。

需要注意的限制：

当前后台导出里，`Q5_hold_params` 的证据关系仍然主要连到平面图大框，没有完整的 holding 专用细框。因此本实验不能声称 holding 参数细框监督已经完全解决，只能如实说明这个字段目前主要依赖上下文大框。

## 十五、执行步骤

1. 校验路径：

```powershell
python scripts\group1_sft\validate_group1_sft_workspace.py --paths training\group1_sft\configs\local_paths.local.json
```

2. 用后台导出构建本方法 JSONL：

```powershell
python scripts\group1_sft\build_d1_evidence_boxes_canonical_jsonl_from_annotations.py `
  --export-json <本地后台导出JSON路径> `
  --paths training\group1_sft\configs\local_paths.local.json `
  --train-target 40 `
  --max-boxes 24
```

3. 检查构建报告：

```text
<reports_dir>/d1_evidence_boxes_canonical_jsonl_build_report.json
```

重点检查：

- `schema_errors` 是否为 0。
- `eval_input_violations` 是否为 0。
- evaluation 200 是否没有 assistant 标签。
- 是否同时保留必要大框和字段细框。
- `canonical_schema_changed` 是否为 false。

4. 从旧 D1 checkpoint 继续训练：

```powershell
python scripts\group1_sft\train_qwen2vl_group1_sft_lora.py `
  --method D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL `
  --paths training\group1_sft\configs\local_paths.local.json `
  --run-id d1_chart_to_evidence_boxes_and_canonical_d1_continue_dev50_20260504_r2 `
  --epochs 1 `
  --learning-rate 5e-5 `
  --max-seq-length 4096
```

5. 训练后只为本方法生成 smoke 包：

```powershell
python scripts\group1_sft\prepare_group1_sft_run_package.py `
  --paths training\group1_sft\configs\local_paths.local.json `
  --limit 5 `
  --methods D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL `
  --run-id group1_sft_d1_evidence_smoke5
```

6. smoke 通过后，只跑本方法的 evaluation 200。

## 十六、Git 提交边界

可以提交：

- 方案文档。
- 构建脚本。
- 训练脚本的方法配置。
- run package 脚本的方法默认范围。
- prompt。
- schema。
- 路径模板。
- 方法集合配置。

不能提交：

- `local_paths.local.json`。
- 后台导出 JSON。
- train/dev/eval JSONL。
- 图片/PDF。
- checkpoint。
- raw outputs。
- summary results。
- 带 token 的 URL。
