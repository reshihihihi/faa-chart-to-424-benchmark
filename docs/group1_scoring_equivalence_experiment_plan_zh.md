# 实验组 1 scoring-equivalence v2 收窄版方案

版本：v0.2  
日期：2026-05-01  
保存目录：`reports/freeze/group1_scoring_equivalence_v2_20260501_r1`

## 1. 本版只处理两类问题

本版不再处理所有潜在 424/chart-display 差异，只处理用户指定的两类：

1. Fix / navaid 名称的显示形式差异。
2. 航向 / 航迹 / 径向的小数与整数显示差异。

除此之外，其他字段保持原 strict status/value 比较。

## 2. 保持不变

以下内容不改：

- 实验组 1 方法定义。
- A1/A2/B1/B1_prime/B1_prime_link/C1/C2/C3/C4/D-SFT 的预测结果。
- canonical JSON schema。
- OCR / LLM / VLM / D-SFT 配置。
- 原始 strict 424 target。
- leg alignment 规则。

## 3. 允许的新 comparison policy

### 3.1 `normalized_string`

只用于 `Q1_fix_ident`。

允许的规范化：

- 大小写。
- 前后空格。
- 局部的 localizer 连字符，例如 `I-ABC` 与 `IABC`。
- 明确的 facility suffix，例如 `ABC VOR`、`ABC VORTAC`、`ABC NDB` 与 `ABC`。

不允许：

- 不同 fix 之间模糊匹配。
- 编辑距离相似就判等。
- 用 target 或 prediction 分数反向改规则。

### 3.2 `degree_display_rounding`

只用于度数字段：

- `Q4_course_or_radial.course_deg`
- `Q4_course_or_radial.radial_deg`
- `Q5_hold_params.inbound_course_deg`

允许：

- 424 小数度数与航图整数显示等价，例如 `243.1 -> 243`。
- `63.3 -> 63`，`234.6 -> 235`。

不允许：

- 自动 reciprocal，例如 `053` 与 `233` 不在本版自动判等。
- 大范围角度容差。
- 改变 course/radial 的 `type` 语义。
- 放宽 turn、altitude、distance、holding time。

## 4. 严格保持的字段

以下字段仍用 `exact_status_value`：

- `leg_count`
- `Q_terminator`
- `Q2_altitude_constraint`
- `Q3_turn`
- `Q5_hold_params.turn`
- `Q5_hold_params.leg_time_min`
- `Q5_hold_params.leg_distance_nm`
- 其他未列入两类问题的字段

也就是说，之前旧宽版中的这些处理已经删除：

- `altitude_exact_ft`
- `exact_semantic_turn`
- `compound_hold_params` 的整体放宽
- `implicit_default_rule`
- `distance_display_rounding`
- `424_derived_exact` 作为新评分标准
- `degree_reciprocal_allowed`
- `derived_altitude_equivalence`

## 5. 输出文件

收窄版仍使用以下文件名，但语义已变为 fix/course-only：

- `targets/comparison_policy_v2.jsonl`
- `targets/canonical_proxy_gt_chart_display_v2.json`
- `targets/field_targets_chart_display_v2.jsonl`
- `targets/target_v1_to_v2_diff.jsonl`
- `reports/target_v2_summary.md`
- `reports/target_v2_summary.json`

## 6. 验收标准

本版通过条件：

1. policy 覆盖全部 `field_targets.jsonl` 行。
2. target v2 仍然 schema-valid。
3. v1 -> v2 diff 只出现在度数字段的小数到整数显示转换。
4. scorer v2 smoke test 中，显示等价值判对，明显错误角度仍判错。
5. formal200 重评分中，不出现 old true -> new false。
6. 结果报告明确说明本版只处理 fix/navaid 与 degree display rounding 两类问题。

