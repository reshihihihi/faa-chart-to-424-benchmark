# D1 输出格式规范化结果

- run_id: `experiment4_V2_full_minus_ma_prose_D1_20260502_r2`
- policy_id: `d1_output_canonicalization_20260502_r4`
- 总样本: 200
- raw output 找到: 200
- canonical JSON 写出: 200
- schema-valid: 200/200
- schema-invalid: 0
- raw chart_id mismatch 审计数量: 51
- final chart_id mismatch 数量: 0

本运行用 manifest 只固定 prediction 外壳；missed-approach 字段仍来自模型 raw output。非法字段值统一降级为合法 unknown/null，不使用 target、score 或 424 raw 修答案。

## 仍然 schema-invalid 的样本

| expected_chart_id | output_chart_id | 首个错误 |
|---|---|---|
