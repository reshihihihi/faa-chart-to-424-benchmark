# 实验组1 scoring-equivalence v2 运行报告

Run ID: `group1_scoring_equivalence_v2_20260501_r1` / `group1_rescore_scoring_equivalence_v2_20260501_r1`

本次只处理两类等价显示问题：

1. Fix / navaid 名称显示形式差异。
2. 航向 / 航迹 / 径向 / holding inbound course 的 424 小数角度与航图整数显示差异。

没有重跑 OCR、LLM、VLM 或 D-SFT；没有修改 A/B/C 系列已有 prediction JSON。D1 是额外的输出接口规范化步骤，用于把 D-SFT raw output 固定成合法 canonical JSON。

## 1. 明确不放宽的内容

以下内容在 v2 中仍然严格比较：

- altitude 约束内容。
- turn 方向。
- holding time / distance。
- DME / distance 数值。
- reciprocal course/radial 自动换算。
- `Q_terminator` 标签。
- `compound_hold_params` 整体字段。

## 2. target/policy 构建结果

| 项目 | 数量 |
|---|---:|
| charts | 300 |
| field rows | 6084 |
| policy rows | 6084 |
| risk rows | 1225 |
| v1->v2 changed rows | 513 |
| manual review required | 0 |
| schema valid charts | 300 |
| schema invalid charts | 0 |

policy 分布：

| policy | count |
|---|---:|
| `degree_display_rounding` | 566 |
| `exact_status_value` | 4554 |
| `normalized_string` | 964 |

v1 -> v2 的字段变化集中在：

| question field | changed rows |
|---|---:|
| `Q4_course_or_radial` | 280 |
| `Q5_hold_params` | 233 |

说明：`Q5_hold_params` 中只改变 `inbound_course_deg` 的显示等价，不改变 holding time、distance 或 turn。

## 3. smoke test

| case | result |
|---|---|
| strict v1 vs display-equivalent prediction | 16/19，通过失败定位确认 strict 会扣小数显示差异 |
| narrowed v2 vs display-equivalent prediction | 19/19，确认两类等价显示被接受 |
| narrowed v2 vs bad radial prediction | 18/19，确认错误径向 `245` 不会被放宽 |

## 4. formal200 结果

| method | strict accuracy | v2 accuracy | delta | schema valid / files |
|---|---:|---:|---:|---:|
| A1 | 29.22% | 29.22% | +0.00% | 200 / 200 |
| A2 | 22.61% | 22.61% | +0.00% | 200 / 200 |
| B1 | 27.25% | 27.39% | +0.15% | 200 / 200 |
| B1_prime | 32.16% | 32.28% | +0.12% | 200 / 200 |
| B1_prime_link | 19.49% | 19.49% | +0.00% | 185 / 200 |
| C1 | 37.09% | 39.39% | +2.30% | 200 / 200 |
| C2 | 23.94% | 26.51% | +2.57% | 200 / 200 |
| C3 | 38.28% | 40.07% | +1.79% | 196 / 198 |
| C4 | 40.08% | 40.42% | +0.35% | 200 / 200 |
| D_SFT | 73.55% | 78.14% | +4.59% | 184 / 196 |
| D1 | 73.35% | 77.94% | +4.59% | 200 / 200 |

## 5. changed rows 审计

全部 changed rows 都是 old false -> new true，没有 old true -> new false。D1 的 changed rows 为 186，来自 D1 输出在 strict target 与 chart-display v2 target 之间的等价显示差异。

## 6. D1 结果

D1 将 D-SFT raw output 转成固定 canonical JSON 接口：

- raw output 找到: 200/200
- canonical JSON 写出: 200/200
- schema-valid: 200/200
- schema-invalid: 0/200
- strict score: 2972 / 4052 = 73.35%
- v2 score: 3158 / 4052 = 77.94%

D1 不使用 target、score、424 raw、OCR 文本、field candidates 或其他方法输出修字段答案。它只保证输出接口合法，字段识别错误仍按错误计入评分。

## 7. 结论

v2 的修改范围保持在已确认的图表显示等价上。实验组1 formal200 现在包含 A1、A2、B1、B1_prime、B1_prime_link、C1、C2、C3、C4、D_SFT、D1 的结果文件、summary、per-sample 报告和 changed-row 审计。
