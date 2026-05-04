# 实验组 1 补充方法完整方案：D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL

日期：2026-05-04

## 1. 当前只新增哪一个方法

当前实验组 1 的补充内容只新增一个方法：

```text
D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL
```

这个方法保留旧 `D1`，但不把旧 `D1` 当作本轮新方法重新发明。旧 `D1` 的作用是提供继续训练的起点 checkpoint。

本方法要回答的问题是：

```text
在旧 D1 已经会从完整航图直接输出 missed approach canonical JSON 的基础上，
如果继续用人工审核的图上证据框、航段、字段、证据关系训练它，
模型最终输出 canonical JSON 的能力是否会提升。
```

因此，这个方法不是两阶段方法，也不是人工证据上限方法。它仍然是完整航图输入，只是在训练时额外要求模型学习“答案来自图上哪里”。

## 2. 和旧 D1 的关系

旧 `D1`：

- 输入：完整航图图片；
- 输出：missed approach canonical JSON；
- 训练目标：端到端从图到最终答案。

`D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL`：

- 初始化：从旧 `D1` checkpoint 继续训练；
- 输入：完整航图图片；
- 训练输出：证据框、字段证据关系、最终 canonical JSON；
- 正式评分输出：仍然是旧 `D1` 形状的 canonical JSON。

这样设计是为了避免“训练找框以后忘掉 D1 原来已经学会的 canonical 答案组织能力”。继续训练从旧 `D1` checkpoint 开始，而不是从 base model 开始。

## 3. 为什么正式输出不改 schema

用户明确要求：

```text
最终输出 canonical JSON 还按之前 D1 的格式，只是增加一个要求它找到证据的功能。
```

所以本方法分成两个层面。

训练层面，assistant 标签包含：

```json
{
  "evidence_boxes": [],
  "answer_grounding": [],
  "canonical_prediction": {}
}
```

正式评分层面，只使用旧 D1 canonical JSON：

```json
{
  "chart_id": "...",
  "procedure": {
    "airport": "...",
    "approach_ident": "...",
    "chart_name": "..."
  },
  "missed_approach": {
    "leg_count": {"status": "present", "value": 3},
    "legs": []
  }
}
```

原因：

- scorer 已经固定接受旧 D1 canonical JSON；
- 如果把证据框塞进正式 JSON，会让评分和旧 D1 不可比；
- 证据框和字段证据关系用于训练约束和诊断分析，不直接参与最终分数；
- 最终分数只比较 canonical JSON 和 `scoring_equivalence_v2` target。

## 4. 训练数据从哪里来

训练数据来自后台人工审核导出。后台已经提供完整关系，不需要新增人工标注。

后台导出可提供的信息包括：

- 图上框的位置；
- 图上框的类型；
- 框内可见文字或图形线索；
- 框和复飞航段的对应关系；
- 框和具体字段的对应关系；
- 字段和证据框的支持关系；
- 人工审核后的最终字段答案。

构建脚本读取这些关系后，生成本方法专用 JSONL。

固定使用 formal300 的 50+200+50 划分：

- 第一个 50 张：本方法训练和开发验证；
- 中间 200 张：正式评估；
- 最后 50 张：本轮不用。

当前训练划分：

- train：40 张；
- dev：10 张；
- evaluation input：200 张。

evaluation input 只包含图片输入和必要 manifest 信息，不包含 assistant 标签，不包含最终答案，不包含 target JSON。

## 5. 训练样本输入

每条训练样本的输入只有：

- 完整航图图片；
- 本方法专用训练 prompt。

禁止把下面内容放入模型输入：

- target JSON；
- score；
- raw 424；
- CIFP；
- 其他方法预测；
- 人工答案文件；
- 后台答案路径。

## 6. 训练样本输出

每条训练样本的 assistant 标签包含三部分。

第一部分：`evidence_boxes`

表示模型应在图上找到哪些证据区域。证据框包括必要大框和字段细框。

第二部分：`answer_grounding`

表示每个航段、每个字段由哪些证据框支持。一个字段可以对应多个证据框。

第三部分：`canonical_prediction`

表示旧 D1 形状的最终 missed approach canonical JSON。

训练时让模型同时学习这三件事，是为了让模型形成这个链条：

```text
先看图上哪里有证据，
再判断每个字段依赖哪些证据，
最后组织成 canonical JSON。
```

## 7. 证据框设计细节

证据框不能只用几个大框。框设计必须包含：

- 必要上下文大框；
- 和字段有直接关系的细框。

必要上下文大框包括：

- plan view 区域；
- missed approach text 区域；
- profile/detail 区域。

字段细框包括：

- 修正点文字；
- 修正点符号；
- 高度文字；
- 爬升箭头；
- 航向文字；
- 径向文字；
- 导航台文字；
- 路径线段；
- 出航/入航标记。

大框的作用是提供上下文，不能替代细框。细框的作用是告诉模型字段值具体来自图上的哪个可见区域。

## 8. 字段证据关系设计

`answer_grounding` 记录字段到证据框的关系。

每条关系应说明：

- `leg_index`：第几个复飞航段；
- `field_name`：哪个字段；
- `answer_path`：字段在 canonical JSON 中的位置；
- `support_mode`：证据支持方式；
- `evidence_box_ids`：一个或多个证据框；
- `evidence_summary`：证据来自哪里。

一个字段可以依赖多个框。例如一个修正点字段可能同时依赖：

- 修正点文字框；
- 修正点符号框；
- plan view 上下文大框；
- missed approach text 区域。

如果字段是规则默认值，不能伪装成直接可见证据。证据不足时，也要在诊断输出中如实表示。

## 9. 推理和评分流程

正式推理不使用 wrapper prompt。正式推理使用旧 D1 canonical prompt 和旧 D1 canonical schema。

正式流程：

1. 用继续训练后的 checkpoint 对完整航图生成旧 D1 canonical JSON；
2. 保存 raw output；
3. 用 D1 相同的 mechanical canonicalizer 规范 JSON 外壳和 schema 形状；
4. canonical JSON 写出后，才读取 target 和 comparison policy 评分。

正式推理命令由 `RUN_COMMANDS.md` 生成，核心参数是：

```text
--method D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL
--prompt training\d_sft\prompts\d_sft_image_to_canonical.v2.md
--json-schema schemas\missed_approach_leg.schema.json
--output-mode canonical
--allow-json-object-candidate-extraction
--max-new-tokens 1024
--repetition-penalty 1.08
```

`--output-mode canonical` 表示正式输出按旧 D1 canonical JSON 来解析和保存。

`--allow-json-object-candidate-extraction` 只处理模型输出中出现多个 JSON 对象或包络混乱的机械格式问题。它不读取 target，不读取 score，不读取 raw 424/CIFP，不读取其他方法预测，也不改答案值。

## 10. 泄漏控制

推理阶段禁止读取：

- target JSON；
- score；
- raw 424；
- CIFP；
- 其他方法预测；
- 人工答案。

`scoring_manifest` 只能在预测完成后用于评分。

正式评分必须使用：

- `scoring_equivalence_v2` target；
- `comparison_policy_v2`。

canonicalizer 只允许做机械格式规范化，例如：

- 去掉外层空白；
- 从 raw output 中提取 JSON 对象；
- 合并模型自己输出的 header/body；
- 用 manifest 补 JSON 外壳中的 `chart_id`；
- 把非法字段降级为合法 unknown/null；
- 修正 schema 形状。

canonicalizer 不允许用 target 或 score 修改答案值。

## 11. 相关代码位置

核心代码：

- `scripts/group1_sft/build_d1_evidence_boxes_canonical_jsonl_from_annotations.py`
  - 从后台导出构建训练 JSONL；
  - 生成 `evidence_boxes`、`answer_grounding`、`canonical_prediction`；
  - 确保 evaluation input 不含 assistant 标签和答案。

- `scripts/group1_sft/train_qwen2vl_group1_sft_lora.py`
  - 从旧 D1 checkpoint 继续训练；
  - 当前方法 id 为 `D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL`。

- `scripts/group1_sft/run_qwen2vl_group1_sft_inference.py`
  - 新增 `--output-mode canonical`；
  - 新增 `--allow-json-object-candidate-extraction`；
  - 支持本方法正式评分时输出旧 D1 canonical JSON。

- `scripts/group1_sft/prepare_group1_sft_run_package.py`
  - 生成本方法 run package；
  - 生成正式推理命令；
  - 生成 canonicalize+score 命令；
  - 默认只跑 `D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL`。

- `scripts/run_d1_output_canonicalizer.py`
  - 使用和 D1 相同的机械 canonicalization policy；
  - 在预测完成后输出 canonical JSON、validation、score、summary。

配置和定义：

- `training/group1_sft/configs/group1_sft_method_set.json`
- `training/group1_sft/configs/local_paths.template.json`
- `training/group1_sft/manifests/d1_chart_to_evidence_boxes_and_canonical.schema.json`
- `training/group1_sft/prompts/d1_chart_to_evidence_boxes_and_canonical.zh.md`

## 12. 当前已经完成的工作

已经完成：

- 从后台导出构建本方法 JSONL；
- train 40、dev 10、eval input 200；
- schema errors 为 0；
- eval input leakage 为 0；
- 从旧 D1 checkpoint 继续训练 r2；
- r2 训练无截断；
- r2 best dev loss 约为 0.266；
- wrapper 正式输出 smoke 失败，原因是输出过长、证据框重复、JSON wrapper 不稳定；
- 正式评分流程已调整为 canonical JSON 输出；
- 代码和方案已 push 到远端分支。

当前远端分支：

```text
group1-sft-extension-plan-20260503
```

关键提交：

```text
f7b5d28c Use canonical scoring path for D1 evidence method
e5eece67 Clarify D1 evidence formal output notes
```

## 13. 已完成的 5 张 smoke 结果

5 张 smoke 用于确认 canonical 输出路径是否能跑通。

结果：

- raw outputs found：5/5；
- canonical JSON written：5/5；
- schema valid：5/5；
- samples scored：5/5；
- score：54/101；
- accuracy：0.535；
- final chart_id mismatch：0。

这个 smoke 说明正式评分不需要依赖大 wrapper 输出，canonical prompt + canonicalizer 能跑通。

## 14. 已完成的 50 张 dev 跑通验证

50 张 dev run package：

```text
group1_sft_d1_evidence_dev50_canonical
```

raw 推理阶段结果：

- samples_total：50；
- raw_text：50/50；
- direct strict JSON parse ok：47/50；
- raw inference summary failure_count：7；
- inference 阶段未读取 scoring manifest；
- inference 阶段未读取 target。

canonicalize+score 阶段结果：

- samples_total：50；
- raw_outputs_found：50；
- canonical_json_written：50；
- schema_valid：50；
- schema_invalid：0；
- samples_scored：50；
- score：700/1010；
- accuracy：0.693069306930693；
- final_chart_id_mismatch_count：0；
- failures：0。

说明：

- 50 张已经跑通；
- raw 输出中存在少量 JSON 外壳/格式问题；
- 这些问题由 D1 mechanical canonicalizer 在不使用 target 改答案的前提下处理；
- canonicalizer 后 50/50 都能评分。

## 15. 50 张验证中观察到的问题

raw inference 阶段观察到的问题包括：

- 模型有时输出 markdown code fence；
- 模型有时输出截断 JSON；
- 模型有时只输出 header，缺 `procedure` 或 `missed_approach`；
- 模型有时把 `chart_id` 拼错；
- 模型有时输出 schema 不允许的 holding 参数，例如异常 inbound course。

这些问题不改变实验定义。当前处理方式是：

- raw output 全部保留；
- 不删除失败样本；
- 不用 target 修答案；
- 用同 D1 的 canonicalizer 做机械格式规范化；
- canonicalizer 的动作写入 action_counts 和 validation 报告。

## 16. 下一步：正式 200

50 张已经跑通后，下一步是正式 200 张 evaluation。

生成正式 200 run package：

```powershell
python scripts\group1_sft\prepare_group1_sft_run_package.py `
  --paths training\group1_sft\configs\local_paths.local.json `
  --split-subset evaluation `
  --methods D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL `
  --run-id group1_sft_d1_evidence_formal200_canonical `
  --overwrite
```

然后检查：

- preflight blocker 数量是否为 0；
- rows 是否为 200；
- prompt 是否是旧 D1 canonical prompt；
- schema 是否是旧 D1 canonical schema；
- scoring target 是否来自 `scoring_equivalence_v2`；
- comparison policy 是否是 `comparison_policy_v2`。

正式推理阶段执行 `RUN_COMMANDS.md` 第 6 节。这个阶段不能读取 target。

正式评分阶段执行 `RUN_COMMANDS.md` 第 6b 节。这个阶段才读取 target 和 comparison policy。

正式 200 完成后，需要汇报：

- run id；
- raw outputs 数量；
- canonical JSON 数量；
- schema valid 数量；
- samples scored 数量；
- score；
- parse/schema failure 数量；
- canonicalizer action_counts；
- final chart_id mismatch 数量；
- 与旧 D1 200 样本结果的差异。

## 17. 加速原则

可以加速：

- 正式推理使用 canonical prompt，不使用大 wrapper prompt；
- `max-new-tokens` 控制为 1024；
- 推理完成后一次性 canonicalize+score；
- 不中途读取 target；
- 不并发启动多个模型进程抢同一张 GPU。

不能为了加速改变：

- checkpoint；
- split；
- target；
- comparison policy；
- 图片输入；
- scorer；
- canonical schema；
- 失败样本保留策略。

## 18. Git 提交边界

可以提交：

- 代码；
- schema；
- prompt；
- 路径模板；
- 设计文档；
- `.gitignore`。

不能提交：

- `local_paths.local.json`；
- 后台导出 JSON；
- 训练 JSONL；
- 图片；
- PDF；
- checkpoint；
- raw outputs；
- canonicalized 大结果；
- scores 大结果；
- 本机绝对路径配置。
