# 实验组 1 SFT 补充方法正式 200 结果汇总

日期：2026-05-05

## 1. 本次 PR 覆盖的新增方法

本次实验组 1 补充内容只新增一个 SFT 方法：

```text
D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL
```

这个方法不是重新定义 D1，也不是两阶段方法。它从既有 D1 checkpoint 继续训练，训练时额外加入后台人工审核得到的图上证据框、字段证据关系和最终 canonical 答案。

核心问题是：

```text
在旧 D1 已经能从完整航图输出 missed approach canonical JSON 的基础上，
继续训练“图上证据来源”和“字段证据绑定”是否能提高最终 canonical JSON 得分。
```

## 2. 数据和训练来源

数据使用 formal300 固定的 50+200+50 划分：

- 第一个 50 张：用于开发训练和验证；
- 中间 200 张：用于正式评估；
- 最后 50 张：本轮不用。

本方法继续训练的数据来自第一个 50 张中的 40/10 划分：

- train：40 张；
- dev：10 张；
- formal evaluation input：200 张。

训练标签来自后台人工审核导出，包含：

- 图上框的位置、类型和可见文字/图形线索；
- 框和复飞航段的关系；
- 框和字段的关系；
- 字段和证据框的支持关系；
- 人工审核后的最终字段答案。

本轮没有新增人工标注，也没有把 target JSON、score、raw 424/CIFP 或其他方法预测放入推理输入。

## 3. 训练目标和正式评分目标

训练时，assistant 标签包含三部分：

```json
{
  "evidence_boxes": [],
  "answer_grounding": [],
  "canonical_prediction": {}
}
```

含义：

- `evidence_boxes`：图上复飞相关证据区域；
- `answer_grounding`：每个航段字段由哪些证据框支持；
- `canonical_prediction`：旧 D1 格式的最终 missed approach canonical JSON。

正式评分时不把整个 wrapper 交给 scorer。正式评分仍然只使用旧 D1 canonical JSON 形状：

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

这样做是为了保持和旧 D1 的评分接口完全一致。证据框和字段证据关系只作为训练约束和诊断材料，不进入正式 scorer。

## 4. 推理和评分边界

正式推理阶段：

- 输入完整航图图片；
- 使用旧 D1 canonical prompt；
- 使用旧 D1 canonical schema；
- 使用继续训练后的 `D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL` checkpoint；
- 不读取 target JSON；
- 不读取 score；
- 不读取 raw 424/CIFP；
- 不读取其他方法预测。

预测完成后，才运行 canonicalize+score：

- 使用与 D1 相同的机械 canonicalization policy；
- 使用 `scoring_equivalence_v2` target；
- 使用 `comparison_policy_v2`；
- 不用 target 或 score 修改答案值。

canonicalizer 只允许做格式层面的机械处理，例如：

- 从 raw output 中提取 JSON 对象；
- 合并模型自己输出的 header/body；
- 用 manifest 修正 JSON 外壳中的 `chart_id`；
- 把 schema 不允许的字段形状降级为合法 unknown/null；
- 输出 validation、scores 和 summary。

## 5. 5 张 smoke 和 50 张 dev 验证

5 张 smoke 的作用是确认正式评分不再依赖长 wrapper 输出，而是走 canonical JSON 路径。

5 张 smoke 结果：

- raw outputs found：5/5；
- canonical JSON written：5/5；
- schema valid：5/5；
- samples scored：5/5；
- score：54/101；
- accuracy：0.5347；
- final chart_id mismatch：0。

50 张 dev 验证结果：

- raw outputs：50/50；
- canonical JSON：50/50；
- schema valid：50/50；
- samples scored：50/50；
- score：700/1010；
- accuracy：0.6931；
- final chart_id mismatch：0。

50 张验证说明该方法已经可以端到端跑通，但 raw 输出中仍存在少量 JSON 外壳和 schema 形状问题，需要由 D1 mechanical canonicalizer 统一处理。

## 6. 正式 200 结果

正式 200 run id：

```text
group1_sft_d1_evidence_formal200_canonical
```

raw 推理阶段：

- samples_total：200；
- raw_text：200/200；
- parsed_json：198/200；
- raw inference strict/schema failure：24；
- inference 阶段未读取 scoring manifest；
- inference 阶段未读取 target。

canonicalize+score 阶段：

- raw_outputs_found：200；
- canonical_json_written：200；
- schema_valid：200；
- schema_invalid：0；
- samples_scored：200；
- final_chart_id_mismatch_count：0；
- failures：0。

正式 200 field-level v2 score：

```text
2901 / 4052 = 0.7159427443
```

主要 canonicalizer action counts：

- `parse_entire_raw_as_json_object`：192；
- `set_manifest_chart_id_envelope`：52；
- `raw_object_not_convertible_to_canonical_shape`：11；
- `fallback_missing_legs`：11；
- `fallback_missing_missed_approach`：11；
- `fallback_invalid_fix_ident`：12；
- `merge_raw_internal_metadata_and_body`：5；
- `extract_json_object_candidates:2`：5；
- `fallback_no_parseable_json_to_empty_canonical`：1。

这些 action 表明新方法 raw 输出比旧 D1 更容易出现 JSON 外壳、chart_id、短格式和非法 fix_ident 问题。所有动作均为 D1 mechanical canonicalizer 的格式规范化，不使用 target 或 score 修改答案。

## 7. 与旧 D1 的正式 200 对比

旧 D1 formal200 v2 score：

```text
3158 / 4052 = 0.7793682132
```

新增方法 formal200 v2 score：

```text
2901 / 4052 = 0.7159427443
```

差异：

- correct 字段数：-257；
- accuracy：-0.0634254689；
- 约下降 6.34 percentage points。

结论：

```text
D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL 已完整跑通正式 200，
但最终 canonical JSON 得分低于旧 D1。
```

## 8. 结果解释

本结果应记录为负结果，而不是性能提升结果。

最可能原因：

- 继续训练样本只有 40 张，数据量太小；
- 训练目标从单一 canonical JSON 变成 evidence wrapper + grounding + canonical prediction，复杂度明显增加；
- 继续训练可能造成旧 D1 canonical 输出能力部分遗忘；
- 训练时学习 wrapper，正式推理时输出 canonical JSON，存在目标分布切换；
- 证据监督没有稳定转化为最终 canonical JSON 提升。

因此，该方法目前可以说明：

```text
简单地在旧 D1 上用少量证据框/字段证据关系继续 SFT，
不能保证提升最终 missed approach canonical JSON，
当前实现反而降低了 formal200 得分。
```

## 9. PR 中提交和不提交的材料

本 PR 应提交：

- 方法定义；
- prompt 和 schema；
- run package 生成代码；
- 推理脚本 canonical output mode；
- JSON object candidate extraction 的机械解析选项；
- 训练 JSONL 构建脚本；
- 训练 runner；
- 中文实验方案；
- 50 张 dev 验证结论；
- 正式 200 汇总结论；
- bootstrap paired-delta 统计代码和轻量结果表。

本 PR 不提交：

- `local_paths.local.json`；
- 后台导出 JSON；
- 训练 JSONL；
- 图片/PDF；
- checkpoint；
- raw outputs；
- canonicalized 大结果目录；
- scores 大结果目录；
- 本地绝对路径配置。

正式 200 的 raw outputs 和 per-sample scores 保留在本机实验目录，用于审计，不进入 Git。
