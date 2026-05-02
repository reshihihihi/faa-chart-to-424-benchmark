# 实验组 1 scoring-equivalence v2 收窄版执行计划

版本：v0.2  
日期：2026-05-01

## 1. 范围

只执行两类修正：

1. Fix / navaid 名称显示形式差异，使用 `normalized_string`。
2. 航向 / 航迹 / 径向的小数与整数显示差异，使用 `degree_display_rounding`。

其他字段全部保持 strict status/value 比较。

## 2. 执行步骤

### 步骤 1：生成输入 manifest

记录以下文件路径和 hash：

- `canonical_proxy_gt_combined.json`
- `field_targets.jsonl`
- `evidence_provenance.jsonl`
- `missed_approach_leg.schema.json`
- 当前 scorer v2 脚本

### 步骤 2：生成 comparison policy

为每个 field target 生成一条 policy：

- `Q1_fix_ident` -> `normalized_string`
- `Q4_course_or_radial` 中包含 `course_deg` / `radial_deg` -> `degree_display_rounding`
- `Q5_hold_params.inbound_course_deg` -> `degree_display_rounding`
- 其他字段 -> `exact_status_value`

### 步骤 3：生成 chart-display target v2

只修改明确属于度数字段小数/整数显示差异的值：

- `63.3 -> 63`
- `243.1 -> 243`
- `234.6 -> 235`

不修改：

- altitude
- turn
- holding time
- holding distance
- Q_terminator
- leg_count
- leg segmentation

### 步骤 4：schema validation

验证：

- `canonical_proxy_gt_chart_display_v2.json`
- `field_targets_chart_display_v2.jsonl`

必须保持 schema-valid。

### 步骤 5：smoke test

至少验证：

- display-equivalent degree 输出能从 wrong 变 correct。
- 明显错误角度，例如 `245` vs `243`，仍然 wrong。
- fix/navaid normalization 不做 fuzzy matching。

### 步骤 6：formal200 rescore

读取已有实验组 1 prediction JSON，重新评分：

- 不重跑 OCR。
- 不重跑 LLM。
- 不重跑 VLM。
- 不重跑 D-SFT。
- 不修改原 prediction。

输出：

- old strict score
- narrowed v2 score
- old-vs-new delta
- changed rows report

### 步骤 7：审计

审计内容：

- 变化是否只来自 `normalized_string` 或 `degree_display_rounding`。
- 是否存在 old true -> new false。
- 是否存在 altitude / turn / distance / holding time 等多余标准混入。
- 是否有 prediction 泄漏或按方法选择性改规则。

## 3. 通过标准

收窄版可进入冻结候选的条件：

1. policy 覆盖全部 field rows。
2. target v2 300/300 schema-valid。
3. v1 -> v2 diff 只发生在 degree display rounding 字段。
4. formal200 changed rows 只来自允许的两类 policy。
5. 没有 old true -> new false。
6. 报告明确说明本版不处理其他 424/chart-display 差异。

