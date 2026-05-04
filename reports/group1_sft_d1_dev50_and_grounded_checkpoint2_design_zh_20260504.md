# 实验组1 D1_DEV50_ONLY 与 D1 grounding checkpoint-2 设计

日期：2026-05-04

## 1. 数据源

本轮训练前数据准备以标注后台的完整人工审核导出为准。后台在 2026-05-04 显示 formal300 已全部正式提交：

- formal300 总数：300
- final JSON：300
- submission snapshot：439
- 最新导出：`shujuji_annotation_export_2026-05-04T08-11-57-148Z.json`

导出文件本身不提交 Git。训练集构造脚本只读取导出中的人工审核关系：

- `regions`：人工框、bbox、region type、可见文字。
- `accepted_mappings`：框与航段/字段的人工接受关系。
- `field_reviews`：字段答案、字段证据 region id、support mode、review status。

## 2. 固定 split

沿用 formal300 的固定 50+200+50：

- development 50：只用于训练、dev、smoke 和格式调试。
- evaluation 200：只生成无 assistant 标签输入，用于正式评测。
- probe 50：本轮不使用。

本轮训练 JSONL 使用 development 50 内部的 40/10：

- train：40
- dev：10

## 3. D1_DEV50_ONLY checkpoint-2

方法名：`D1_DEV50_ONLY`

run id 建议：

```text
d1_dev50_only_20260504_r2
```

checkpoint 配置键：

```text
d1_dev50_lora_or_checkpoint_dir
```

训练起点：

```text
Qwen2-VL base model
```

不从旧的 500 样本 D1 checkpoint 继续训练。这样可以隔离“只用第一个 50 张 development 样本训练 D1”这件事，避免把旧 500 样本的 holding 分布记忆带进新 baseline。

输入：

```text
完整航图图片
canonical-only prompt
```

输出：

```text
missed approach canonical JSON
```

标签来源：

```text
field_reviews[].canonical_answer
```

用途：

1. 作为“只用 development 第一个 50 张训练”的 D1 controlled baseline。
2. 作为下一步 grounding 模型的初始化 adapter。

推荐训练命令：

```powershell
python scripts\group1_sft\train_qwen2vl_group1_sft_lora.py `
  --method D1_DEV50_ONLY `
  --paths training\group1_sft\configs\local_paths.local.json `
  --run-id d1_dev50_only_20260504_r2 `
  --epochs 1 `
  --learning-rate 2e-4 `
  --max-seq-length 4096
```

## 4. D1-2 grounding checkpoint-2

方法名：

```text
D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL
```

这里的 D1-2 指第二阶段的 D1 grounding 续训，不是两模型串联。它仍然是单模型完整航图输入，只是输出多了证据框和字段 grounding。

run id 建议：

```text
d1_chart_to_evidence_boxes_grounded_dev50_20260504_r2
```

checkpoint 配置键：

```text
d1_evidence_boxes_lora_or_checkpoint_dir
```

训练起点：

```text
D1_DEV50_ONLY checkpoint-final
```

也就是先训练 `D1_DEV50_ONLY`，再从 `d1_dev50_lora_or_checkpoint_dir` 继续训练 grounding 输出。训练脚本已经把该方法的 `initial_adapter_key` 改成 `d1_dev50_lora_or_checkpoint_dir`。

输入：

```text
完整航图图片
fine evidence boxes + grounding + canonical prompt
```

输出 wrapper：

```json
{
  "evidence_boxes": [],
  "answer_grounding": [],
  "canonical_prediction": {}
}
```

其中：

- `evidence_boxes` 使用稳定编号 `box_001`、`box_002`，避免学习 chart-specific id。
- 每个 box 只保留训练必要字段：`box_id`、`source_region_id`、`bbox`、`region_type`、`visible_text`、`field_names`。
- `answer_grounding` 负责把 `leg_index + field_name` 连到 `evidence_box_ids`，并记录 `support_mode`。
- `canonical_prediction` 是正式评分唯一使用的 canonical JSON。

推荐训练命令：

```powershell
python scripts\group1_sft\train_qwen2vl_group1_sft_lora.py `
  --method D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL `
  --paths training\group1_sft\configs\local_paths.local.json `
  --run-id d1_chart_to_evidence_boxes_grounded_dev50_20260504_r2 `
  --epochs 1 `
  --learning-rate 5e-5 `
  --max-seq-length 4096
```

## 5. 当前训练前构建结果

已用后台最新导出重建 JSONL：

- `D1_DEV50_ONLY` train：40
- `D1_DEV50_ONLY` dev：10
- `D1_DEV50_ONLY` evaluation input：200，无 assistant 标签
- `D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL` train：40
- `D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL` dev：10
- `D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL` evaluation input：200，无 assistant 标签

构建审计：

- schema errors：0
- evaluation input violations：0
- JSONL 图片路径缺失：0
- evidence box 数量：最少 3，最多 6，平均 4.4
- `Q5_hold_params` grounding：50/50 当前仍指向 `PLAN_VIEW`

因此当前数据已经可用于训练流程 smoke；但如果实验结论要声称“holding 参数被细框定位”，还需要后台导出里出现 holding 的更细 region。当前脚本会把这个缺口写入审计报告，并将 `ready_for_fine_holding_training_goal` 标为 false。

## 6. 本次提交内容边界

提交 Git：

- 细粒度 wrapper schema。
- grounding prompt。
- 从后台导出构建 D1 dev50 与 D1 grounding JSONL 的脚本。
- 训练脚本中的 `D1_DEV50_ONLY` 方法和 grounding 初始化逻辑。
- `local_paths.template.json` 的 checkpoint-2 路径键。
- `.gitignore` 对本地 formal300 图片/PDF 的保护。
- 本设计文档。

不提交 Git：

- `training/group1_sft/configs/local_paths.local.json`
- 后台导出原始 JSON
- train/dev/eval JSONL
- PNG/PDF 图片
- LoRA/checkpoint
- raw outputs
- 带 token 的 URL
