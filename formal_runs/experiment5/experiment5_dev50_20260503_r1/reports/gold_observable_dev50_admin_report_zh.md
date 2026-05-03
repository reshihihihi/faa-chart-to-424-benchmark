# 实验组5 dev50 admin 框标注处理报告

- 生成时间 UTC: `2026-05-03T10:12:41.803032+00:00`
- dev50 charts: 50
- admin region rows: 393
- observable rows: 50
- observable fact rows: 396
- forbidden key hits: 0
- hard leakage detected: `False`

## 输出

- gold observable: `formal_runs/experiment5/experiment5_dev50_20260503_r1/inputs/gold_observable_dev50_admin.jsonl`
- flat facts: `formal_runs/experiment5/experiment5_dev50_20260503_r1/reports/gold_observable_dev50_admin_facts.jsonl`
- admin box overlay contact sheet: `formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/dev50_admin_box_overlays_contact_sheet.png`
- per-chart overlays: `formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_box_overlays`

## 说明

- 这里处理的是 admin 里的框标注，不再使用 PDF text-layer 抽 MA prose 作为主要来源。
- 输出只来自 `region_type`、`label`、`bbox`、`review_action`、`annotation_scope` 等可观察标注字段。
- 已在上游 sanitized 文件中去掉 accepted/candidate mappings、field review 结构和答案侧字段。
