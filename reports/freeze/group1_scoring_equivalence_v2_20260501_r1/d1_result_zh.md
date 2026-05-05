# 实验组1 D1 输出格式规范化结果

- run_id: `group1_formal200_D1_20260502_r4`
- method: `D1`
- policy_id: `d1_output_canonicalization_20260502_r4`
- 样本范围: formal200，共 200 张航图
- 输入来源: D-SFT raw output，仅用于恢复/约束固定 canonical JSON 输出接口
- 禁止项: 不使用 target JSON、424/CIFP raw、score 文件、人工答案、OCR 文本、field candidates 或其他方法预测来修正字段答案
- canonical JSON 写出: 200/200
- schema-valid: 200/200
- schema-invalid: 0/200
- strict field-level score: 2972 / 4052 = 73.35%
- v2 field-level score: 3158 / 4052 = 77.94%
- raw chart_id mismatch 审计数量: 54
- final chart_id mismatch 数量: 0

## 解释

D1 不是为了提高识别分数而修答案，而是把 D-SFT 的模型原始输出强制整理为和 424/CIFP-derived canonical target 相同的固定层级 JSON 接口。模型把字段识别错仍然计错；D1 只解决输出格式不合法、外壳字段错位、短格式输出、额外字段等接口问题。

本次结果说明：D-SFT 的 200 份 raw output 已经可以通过 D1 统一转成合法 canonical JSON，因此实验组1里的 D 方法可以按固定 JSON 接口进入正式评分与论文表格。

## 仓库内结果位置

- D1 完整产物: `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/D1`
- per-sample 报告: `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/D1/reports/D1_per_sample.jsonl`
- summary JSON: `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/D1/reports/D1_summary.json`
