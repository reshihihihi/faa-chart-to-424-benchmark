# 实验组1 D 方法补充方案：D1 继续训练增加图上证据框监督

日期：2026-05-04

## 1. 本轮目标

本轮只保留三种 D 方法，目的是把“没有 SFT、已有 D1、在 D1 基础上增加找证据能力”放在同一批 200 张正式评估样本上对比。

三种方法分别是：

1. `D_BASE_SAME_BACKBONE`
   - 作用：同底座未微调对照。
   - 输入：完整航图图片。
   - 输出：原始 missed approach canonical JSON。
   - 是否训练：不训练。
   - 用途：说明同一个 Qwen2-VL 底座不经过 D1 SFT 时，直接输出 canonical JSON 的能力如何。

2. `D1`
   - 作用：实验组1已有端到端 SFT baseline。
   - 输入：完整航图图片。
   - 输出：原始 missed approach canonical JSON。
   - 是否训练：已经有旧 D1 checkpoint，不在本轮重新训练。
   - 用途：作为当前主要 baseline，代表“完整航图直接到最终 canonical JSON”的端到端学习效果。

3. `D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL`
   - 作用：在旧 D1 checkpoint 基础上继续训练，让模型显式学习“先找图上证据，再给最终答案”。
   - 输入：完整航图图片。
   - 原始诊断输出：`evidence_boxes`、`answer_grounding`、`canonical_prediction`。
   - 正式评分输出：只抽取 `canonical_prediction`，保持和旧 D1 完全相同的 missed approach canonical JSON 形状。
   - 是否训练：需要训练，从旧 D1 checkpoint 继续训，不从 base model 重新训。
   - 用途：测试增加图上证据框监督后，是否能改善最终 canonical JSON，同时不改变评分接口。

## 2. 数据来源

训练数据只来自标注后台已经有的人工审核关系，不要求额外补新标注。

后台导出能提供以下信息：

- `regions`：图上框、bbox、region type、可见文字、框来源。
- `accepted_mappings`：框和航段、字段之间的人工接受关系。
- `candidate_mappings_reviewed` 和 `source_field_name`：后台已经保存的细框候选字段关系，用来补足 `CLIMB_ARROW`、`FIX_SYMBOL`、`RADIAL_TEXT`、`NAVAID_TEXT` 等细框监督；这些关系只在 development 50 内用于训练，不进入 evaluation 输入。
- `field_reviews`：字段级最终答案、字段对应证据 region id、support mode、review status。
- 最终字段答案：每个 missed approach leg 下的 `Q_terminator`、`Q1_fix_ident`、`Q2_altitude_constraint`、`Q3_turn`、`Q4_course_or_radial`、`Q5_hold_params`。

脚本只做转换：

- 把后台框转换成模型训练用的 `evidence_boxes`。
- 把后台字段和证据关系转换成 `answer_grounding`。
- 把后台已有的细框候选关系纳入 `evidence_boxes`，避免只训练三个粗框。
- 把后台字段答案转换成 `canonical_prediction`。
- 把后台内部 region id 留在审计逻辑里，不要求模型输出后台 id。

## 3. 固定 split

继续使用 formal300 的固定 50+200+50：

- development 50：本轮新增训练唯一可用的人工标签来源。
- evaluation 200：正式评估样本，只生成无 assistant 标签的输入，不在推理前读取 target、score、raw 424/CIFP 或其他方法预测。
- probe 50：本轮不使用。

当前脚本默认把 development 50 切成：

- train 40：进入优化器训练。
- dev 10：只用于训练过程中的 loss 监控和 checkpoint 选择。

这 40/10 都来自第一个 50，不会碰 evaluation 200。若后续决定用完整 50 做最终训练，需要单独记录 run id，并说明 dev 监控策略，不要悄悄改变。

## 4. 新方法的训练起点

`D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL` 必须从旧 D1 checkpoint 继续训练：

```text
d1_lora_or_checkpoint_dir
```

不再走 `D1_DEV50_ONLY`。原因是本轮问题不是重新证明“只用 50 张能否训出 D1”，而是要在已经有效的 D1 能力上增加找证据能力。

这样做的好处：

- 保留旧 D1 从 500 样本训练中学到的 canonical 输出能力。
- 新的 development 50 只负责补充图上证据框和字段证据关系。
- 避免把“从零只训 50 张的模型能力不足”和“证据监督是否有效”混在一起。

## 5. 新方法的训练目标

训练样本的 assistant label 是一个诊断 wrapper：

```json
{
  "evidence_boxes": [],
  "answer_grounding": [],
  "canonical_prediction": {}
}
```

但正式评分只使用：

```json
canonical_prediction
```

也就是说，canonical JSON 本身没有改 schema。证据框只是让模型在生成最终答案前显式学习“证据在哪里、字段靠什么支持”。

## 6. evidence_boxes 细节

`evidence_boxes` 应该尽量使用后台已有细框，不再只用三个大框。

每个 box 包含：

- `box_id`：训练时重新编号，如 `box_001`、`box_002`，避免模型学习后台内部 id。
- `bbox`：归一化 `[x_center, y_center, width, height]`。
- `region_type`：来自后台 region type。
- `visible_text`：框内可见文字；纯图形符号可为 null。
- `field_names`：该框支持的 canonical 字段列表。
- `evidence_role`：该框的作用，例如 fix、altitude、course/radial、turn/path、holding 参数、missed approach context。

优先使用的细框类型包括：

- `FIX_TEXT`
- `ALTITUDE_TEXT`
- `RADIAL_TEXT`
- `TRACK_OR_RADIAL_TEXT`
- `HEADING_TEXT`
- `NAVAID_TEXT`
- `FIX_SYMBOL`
- `CLIMB_ARROW`
- `PATH_SEGMENT`
- `OUTBOUND_INBOUND_MARK`
- `HOLD_SYMBOL`
- `HOLD_INBOUND_COURSE_TEXT`
- `HOLD_DISTANCE_TEXT`
- `HOLD_TIME_TEXT`
- `HOLD_TURN_DIRECTION_TEXT`

`PLAN_VIEW`、`MISSED_APPROACH_TEXT`、`MISSED_APPROACH_DETAIL_AREA` 只能作为兜底上下文框使用，不应该成为主要训练目标。

## 7. answer_grounding 细节

`answer_grounding` 的作用是解释每个字段答案从哪些证据框来。

每条 grounding 包含：

- `leg_index`：航段编号。
- `field_name`：字段名，如 `Q1_fix_ident`。
- `answer_path`：字段在 canonical JSON 中的位置。
- `support_mode`：证据支持方式。
- `evidence_box_ids`：引用 `evidence_boxes` 中的 `box_id`。
- `evidence_summary`：用 `box_id` 和可见内容简要说明证据来自图上哪里。

允许的 `support_mode`：

- `direct_visible_text`
- `direct_visible_symbol`
- `direct_visible_region`
- `inferred_from_visible_evidence`
- `rule_default_not_directly_visible`
- `insufficient_for_encoding`
- `not_grounded`

如果某字段来自规则默认值，不能伪装成直接可见；如果证据不足，也要明确标成不足或未 grounding。

## 8. canonical_prediction 细节

`canonical_prediction` 必须保持旧 D1 的 canonical JSON：

```json
{
  "chart_id": "...",
  "procedure": {
    "airport": "...",
    "approach_ident": "...",
    "chart_name": "..."
  },
  "missed_approach": {
    "leg_count": {"status": "...", "value": ...},
    "legs": []
  }
}
```

正式评分时，runner 会：

1. 保存模型原始 wrapper 到 `parsed_json/`。
2. 从 wrapper 抽出 `canonical_prediction`。
3. 把抽出的 canonical JSON 保存到 `canonical_json/`。
4. 只用 `canonical_json/` 进入 scorer。

因此证据功能不会改变评分 JSON 的 schema。

## 9. 防止忘掉旧 D1 能力

因为新训练只用 development 50，必须控制继续训练强度：

- 起点使用旧 D1 checkpoint。
- 学习率用较小值，建议 `5e-5` 起步。
- 先跑 1 epoch smoke，不直接全量长训。
- assistant label 同时保留完整 `canonical_prediction`，不是只训练框。
- dev 10 监控 wrapper schema、canonical schema、loss 和截断情况。
- 如果 canonical parse/schema failure 上升，要优先降学习率、缩短 epoch 或调低输出复杂度。

## 10. 构建和训练步骤

1. 确认本地路径：

```powershell
python scripts\group1_sft\validate_group1_sft_workspace.py --paths training\group1_sft\configs\local_paths.local.json
```

2. 用后台导出构建训练 JSONL：

```powershell
python scripts\group1_sft\build_d1_evidence_boxes_canonical_jsonl_from_annotations.py `
  --export-json <本地后台导出JSON路径> `
  --paths training\group1_sft\configs\local_paths.local.json `
  --train-target 40 `
  --max-boxes 8
```

3. 检查构建报告：

```text
<reports_dir>/d1_evidence_boxes_canonical_jsonl_build_report.json
```

必须重点看：

- `schema_errors` 是否为 0。
- `eval_input_violations` 是否为 0。
- `box_count` 是否不是三个大框模式。
- `region_type_counts_train_dev` 中细框是否占主导。
- `CLIMB_ARROW`、`FIX_SYMBOL`、`RADIAL_TEXT`、`NAVAID_TEXT`、`PATH_SEGMENT` 等后台细框是否进入训练标签。
- `evidence_boxes` 是否被限制在 8 个以内，避免推理时在框数组里循环而不输出最终 canonical JSON。
- `q5_hold_params_needs_fine_box_count` 是否提示 holding 仍只连到粗框。

4. 从旧 D1 checkpoint 继续训练：

```powershell
python scripts\group1_sft\train_qwen2vl_group1_sft_lora.py `
  --method D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL `
  --paths training\group1_sft\configs\local_paths.local.json `
  --run-id d1_chart_to_evidence_boxes_and_canonical_d1_continue_dev50_20260504_r1 `
  --epochs 1 `
  --learning-rate 5e-5 `
  --max-seq-length 5120
```

5. 生成 run package 并先跑小样本：

```powershell
python scripts\group1_sft\prepare_group1_sft_run_package.py `
  --paths training\group1_sft\configs\local_paths.local.json `
  --limit 5 `
  --run-id group1_sft_smoke5
```

6. 小样本通过后再跑 evaluation 200：

- `D_BASE_SAME_BACKBONE`
- `D1`
- `D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL`

三者使用同一套 evaluation 200 和同一套 scoring manifest。scoring manifest 只能在预测完成后用于评分。

## 11. 不提交到 Git 的内容

以下内容不能提交：

- `training/group1_sft/configs/local_paths.local.json`
- 后台导出 JSON
- train/dev/eval JSONL
- PNG/PDF 图片
- 模型和 checkpoint
- raw outputs
- 大结果文件
- 带 token 的后台 URL

可以提交：

- 脚本
- schema
- prompt
- 路径模板
- `.gitignore`
- 设计文档

## 12. 当前需要执行的下一步

当前应先完成代码层面的定义修正，然后本地构建 JSONL 并读审计报告。

顺序是：

1. 确认 `D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL` 的训练起点已经改成 `d1_lora_or_checkpoint_dir`。
2. 确认模型输出 wrapper 中不要求后台内部 region id。
3. 确认 `canonical_prediction` schema 与旧 D1 canonical JSON 一致。
4. 用后台导出重新构建 train/dev/eval JSONL。
5. 审计 `schema_errors`、`eval_input_violations`、box 细粒度和 holding 字段证据。
6. 审计通过后再训练新方法的 1 epoch smoke。
