# 实验组5 smoke20 r2 输入准备报告

- run_id: `experiment5_smoke_20260503_r4_available_methods`
- 生成时间 UTC: `2026-05-03T05:34:10.251156+00:00`
- smoke20 样本数: 20
- source-view hash 是否闭合: True
- candidate schema: `E:\experiment3\github_work\faa-chart-to-424-benchmark-experiment5\schemas\experiment5_roi_field_candidates.schema.v1.json`
- candidate validation error rows: 0
- unknown source_section 数量: 0
- cross-region snippet 数量: 0
- B3/B4 smoke 前置是否就绪: True

## 已准备的 region profiles

| profile | 含义 | 行数 | 可用于 |
|---|---|---:|---|
| `T` | 只使用 MISSED_APPROACH_TEXT ROI OCR | 20 | B3-T |
| `TPD` | 使用 MISSED_APPROACH_TEXT + PLAN_VIEW + DETAIL_AREA ROI OCR | 20 | B3-TPD, B4-TPD |
| `PD` | 使用 PLAN_VIEW + DETAIL_AREA ROI OCR，不含复飞文字 | 20 | B3-PD optional |

## 说明

- r2 通过 Experiment 5 当前 source-view summary snapshot 闭合 provenance。
- r2 candidates 按区域独立生成后再合并，候选片段不得跨越区域标签。
- A3/B2/G 系列仍需要人工 gold text / gold observable 后才能执行。
