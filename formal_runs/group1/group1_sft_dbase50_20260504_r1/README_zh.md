# 实验组1 D_BASE_SAME_BACKBONE 50 样本结果包

日期：2026-05-06

这个目录保存实验组1补充实验中 `D_BASE_SAME_BACKBONE` 在 50 张 formal evaluation 航图上的可复核结果。该方法是“同底座未微调对照”：输入完整航图图片，使用 Qwen2-VL-2B-Instruct base，不加载 D1 的 SFT adapter，也不加载任何额外 checkpoint；prompt、输出 schema、后处理边界和评分器与 D1 对照保持一致。

## 为什么需要这个结果包

之前 GitHub 上只记录了摘要结论，无法直接复查每个样本的模型输出、规范化结果和逐样本得分。这个目录补齐 50 样本的运行材料，用来说明 D-base 不是只输在 JSON 格式，而是在经过与 D1 相同的保守 canonicalization 后，仍然没有学到 missed approach canonical JSON 的字段语义。

## 目录内容

- `RUN_COMMANDS.md`：本次 run package 对应的验证、构包、推理、canonicalization 和 scoring 命令，路径已脱敏为仓库相对路径或占位符。
- `run_package_manifest.json`：run package 元信息、使用的 scoring equivalence target、comparison policy、方法配置哈希和 preflight 状态。
- `scoring_manifest.jsonl`：50 样本评分清单，只用于预测完成后的 scoring 阶段。
- `reports/preflight_report_zh.md` 和 `reports/preflight_report.json`：构包前检查结果，blocker 为 0。
- `D_BASE_SAME_BACKBONE/input_manifest.jsonl`：推理阶段输入清单，不包含 target JSON、score、raw 424/CIFP、其他方法预测或人工答案。
- `D_BASE_SAME_BACKBONE/summary_report.json`：raw 推理解析摘要，记录 50 条输出、8 条 strict JSON parse ok、0 条 raw 可直接评分。
- `D_BASE_SAME_BACKBONE/predictions/.../raw_text/`：50 个 raw model output 文本文件，用于复查模型原始输出形态。
- `D_BASE_SAME_BACKBONE/predictions/.../parsed_json/`、`errors/`、`parser_logs/`、`validation/`：raw 输出解析和 schema validation 过程记录。
- `D_BASE_SAME_BACKBONE_CANONICALIZED/canonical_json/`：50 个经过保守 canonicalization 后写出的 canonical JSON。
- `D_BASE_SAME_BACKBONE_CANONICALIZED/reports/D_BASE_SAME_BACKBONE_per_sample.jsonl`：逐样本 score 摘要，每行包含 chart_id、schema_valid、canonicalization actions 和该样本 correct/total/accuracy。
- `D_BASE_SAME_BACKBONE_CANONICALIZED/scores/`：50 个逐样本 field-level scoring 明细。
- `D_BASE_SAME_BACKBONE_CANONICALIZED/reports/D_BASE_SAME_BACKBONE_summary.json`：正式 scoring 汇总，50/50 schema valid，50/50 scored，field-level score 为 0/1022 = 0.0。

## 实验边界

推理阶段只读取完整航图图片、prompt 和输出 schema；禁止读取 target JSON、score 文件、raw 424/CIFP、其他方法预测或人工答案。`scoring_manifest.jsonl`、`scoring_equivalence_v2` target 和 `comparison_policy_v2` 只在预测完成并写出 canonical JSON 后用于评分。

canonicalization 只做外壳和 schema 层面的机械修复，例如固定 `chart_id` 外壳、删除 schema 外额外顶层字段、在缺少 missed approach 结构时写出合法空结构；它不使用 target 或其他答案来源来修改字段答案。

## 不在本目录提交的内容

- `training/group1_sft/configs/local_paths.local.json`
- 模型权重、Hugging Face cache、LoRA adapter 或 checkpoint
- PNG 航图图片
- 本机绝对路径配置

## 结论

`D_BASE_SAME_BACKBONE` 在这 50 个样本上的 raw 输出虽然全部生成成功，但 strict JSON parse 只有 8/50，raw 阶段 0/50 可直接评分。经过保守 canonicalization 后，50/50 都能进入评分，最终 field-level score 仍为 0/1022 = 0.0。这说明 D-base 的失败不是单纯格式问题，而是未经过 SFT 的同底座模型没有稳定学到实验组1需要的 missed approach canonical JSON 字段语义。
