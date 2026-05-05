# 实验组1 D_BASE_SAME_BACKBONE 50 样本执行记录

## 运行对象

- 方法：`D_BASE_SAME_BACKBONE`
- 含义：同底座未微调对照
- 输入：完整航图图片
- 模型：Qwen2-VL-2B-Instruct base
- adapter/checkpoint：不使用
- 样本数：50
- run package：`<group1_sft-artifact-root>\runs\group1_sft_dbase50_20260504_r1`
- preflight blocker：0

## raw 推理结果

- raw summary：`<group1_sft-artifact-root>\runs\group1_sft_dbase50_20260504_r1\D_BASE_SAME_BACKBONE\summary_report.json`
- raw prediction run id：`group1_sft_dbase50_20260504_r1_D_BASE_SAME_BACKBONE_raw`
- raw output：50/50
- strict JSON parse ok：8/50
- raw runner samples_scored：0/50
- raw runner failure_count：50/50

raw 阶段失败主要是模型输出 JSON 不闭合、字段形状不符合 canonical schema，或者只输出了类似 chart metadata 的对象。

## canonicalized 评分结果

- canonicalized summary：`<group1_sft-artifact-root>\runs\group1_sft_dbase50_20260504_r1\D_BASE_SAME_BACKBONE_CANONICALIZED\reports\D_BASE_SAME_BACKBONE_summary.json`
- canonicalized run id：`group1_sft_dbase50_20260504_r1_D_BASE_SAME_BACKBONE_CANONICALIZED`
- canonical JSON written：50/50
- schema_valid：50/50
- schema_invalid：0/50
- samples_scored：50/50
- score：0 / 1022 = 0.0
- raw_chart_id_mismatch_count：1
- final_chart_id_mismatch_count：0

## 后处理边界

本次后处理复用 D1 的机械 canonicalization 策略，只解决输出外壳和 schema 合法性问题：

- 允许使用 input manifest 固定 `chart_id` 和 `procedure` 外壳。
- 允许删除 canonical 顶层之外的额外字段。
- 允许把不可解析或不可转换的 missed-approach 内容降级为空 legs / unknown 合法结构。
- 不使用 target JSON、score、raw 424/CIFP、OCR、人工答案或其他方法预测来修改字段答案。
- target 和 comparison policy 只在 canonical JSON 写出之后用于评分。

## 结论

50 样本流程已经跑通：D_base 可以稳定产出可评分 canonical JSON。

但 D_base 的任务能力基本为 0：后处理虽然让 50 条全部进入评分，最终字段得分仍是 0/1022。这个结果说明未微调同底座模型无法直接完成实验组1的 missed approach canonical JSON 任务，后续与 D1 或 D1 加找框监督方法对比时，D_base 可作为有效低基线对照。

## 诊断性错层级 salvage 检查

为了判断 D_base raw output 中是否存在被保守 canonicalization 丢掉的可用信息，额外运行了一次诊断性 salvage：

- diagnostic summary：`<group1_sft-artifact-root>\runs\group1_sft_dbase50_20260504_r1\D_BASE_SAME_BACKBONE_CANONICALIZED_DIAGNOSTIC_SALVAGE\reports\D_BASE_SAME_BACKBONE_summary.json`
- diagnostic policy id：`dbase_output_canonicalization_diagnostic_misnested_salvage`
- schema_valid：50/50
- samples_scored：50/50
- score：7 / 1022 = 0.006849

诊断性 salvage 只搬运 raw output 自身的错层级字段，例如：

- `procedure.missed_approach` -> 顶层 `missed_approach`
- `procedure.legs` -> `missed_approach.legs`
- 把误塞进 `leg_count` 的 Q 字段转成第 1 条 leg 的 answers

该诊断仍不使用 target JSON、score、raw 424/CIFP、OCR、人工答案或其他方法预测来修改字段答案。

诊断结论：

- 50 条 raw output 中，只有极少量可抢救字段。
- 7 个正确字段主要来自浅层结构或常见字段，例如 `Q_terminator=CA`、`leg_count=3`、少量 `not_applicable`。
- 未救出稳定的 fix、altitude、course/radial 或 hold 参数。
- 因此正式 D_base 对照仍应使用保守 canonicalization 结果，诊断版只作为错误分析参考。
