# Experiment 5 r2 admin-relation 结果使用边界

日期：2026-05-04

## 结论

`experiment5_dev50_20260503_r2_admin_relation` 和 `experiment5_eval200_20260503_r2_admin_relation` 可以保留为 **oracle 诊断 / 上界分析**，但不能作为 Experiment 5 原计划中的 strict failure-attribution 正式结果。

原因不是运行失败，而是输入来源过强：部分方法输入已经包含了人工最终答案或由最终答案反推出来的内容。这样得到的分数可以说明“如果候选/文本/关系已经接近答案，模型还能不能组织成 424 输出”，但不能回答原问题：错误到底来自 OCR、区域识别、候选生成、证据绑定，还是规则/模型推理。

## 发现的问题

1. `gold_ma_prose` 来自最终答案反推。

   旧脚本 `scripts/experiment5/build_experiment5_admin_relation_method_inputs.py` 的 `gold_prose_from_answer()` 会读取 `annotation_pr28_json`，再把最终人工答案重写成 formal missed approach prose。这不是图上可见文本，也不是 OCR/人工校正文本。

2. field candidates 来自 `canonical_answer`。

   旧脚本中的候选构造逻辑读取 `admin_field_review` 的 `canonical_answer`，把最终字段值塞进候选输入。即使后来删除了字段名或 leg index，候选值本身已经是答案级信息。

3. T/TPD profile 中包含 answer-derived prose。

   B3/B4 的 T 或 TPD 输入里，文本侧使用了上述 `gold_prose`。因此 T/TPD 结果不能解释真实 OCR 文本质量或真实 MA_TEXT 区域文本质量。

4. 旧 no-leakage 检查只做了字段名扫描，不是 provenance 审计。

   r2 报告里 “forbidden key hit = 0” 只能说明输出文件中没有出现若干敏感键名，不能说明值没有从 `canonical_answer` 或 `annotation_pr28_json` 派生。

## 允许如何使用 r2

- 可以作为 oracle 诊断结果：观察在“候选接近人工答案”的条件下，模型输出、绑定和 schema 组织还会出哪些错。
- 可以作为 debugging 参考：定位 prompt、解析器、评测器、输出 schema 的问题。
- 可以保留在仓库中，但报告必须明确标注 “oracle diagnostic, not strict method result”。

## 不能如何使用 r2

- 不能宣称它是 Experiment 5 正式 failure-attribution 结果。
- 不能用它比较 OCR 错误、区域识别错误、候选生成错误的真实贡献。
- 不能把 B3/B4 T/TPD 的分数解释成“给了图上真实 ROI 文本/区域关系后”的效果。

## 下一步 strict 路线

1. 建立 strict 输入契约：每种方法明确允许字段、禁止字段、允许派生方式和 provenance。
2. 对 admin 后台导出的 `regions / evidence_links / field_review / gold_answer` 做来源审计。
3. 只从可见图面证据生成方法输入：
   - MA_TEXT 文本：必须来自图面文本、OCR、人工校正文本，不能来自最终答案。
   - ROI/PD candidates：只能来自框、框类型、可见 label 左侧文本、可见图元关系，不能来自 `canonical_answer`。
   - G inputs：只能是人工审核过的可观察事实，且必须剥离字段名、leg index、terminator、leg_type、最终答案结构。
4. 先生成 dev50 strict 输入和 provenance 审计，抽样给人工确认。
5. 通过输入审计后，再跑 dev50；dev50 跑通后再扩展 eval200。
