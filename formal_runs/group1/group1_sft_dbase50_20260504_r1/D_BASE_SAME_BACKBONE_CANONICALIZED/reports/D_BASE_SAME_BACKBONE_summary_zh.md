# D1 输出格式规范化结果

- run_id: `group1_sft_dbase50_20260504_r1_D_BASE_SAME_BACKBONE_CANONICALIZED`
- method: `D_BASE_SAME_BACKBONE`
- policy_id: `dbase_output_canonicalization_same_as_d1`
- 总样本: 50
- raw output 找到: 50
- canonical JSON 写出: 50
- schema-valid: 50/50
- schema-invalid: 0
- raw chart_id mismatch 审计数量: 1
- final chart_id mismatch 数量: 0

本运行用 manifest 只固定 prediction 外壳；missed-approach 字段仍来自模型 raw output。非法字段值统一降级为合法 unknown/null，不使用 target、score 或 424 raw 修答案。

## 仍然 schema-invalid 的样本

| expected_chart_id | output_chart_id | 首个错误 |
|---|---|---|
