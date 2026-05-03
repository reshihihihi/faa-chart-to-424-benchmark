# 实验组5 dev50 后台审核工件导出报告

- 生成时间 UTC: `2026-05-03T11:33:42.110086+00:00`
- charts: 200
- gold answers: 200
- gold answer schema error charts: 0
- field reviews: 2149
- regions: 1585
- evidence links: 2149
- observable accept facts: 883
- observable accept+pending facts: 1578
- method-safe accept forbidden key hits: 0
- method-safe accept+pending forbidden key hits: 0

## 输出文件

- `admin_gold_answer`: `formal_runs/experiment5/experiment5_eval200_20260503_r1/admin_artifacts/admin_gold_answer_eval200.jsonl`
- `admin_field_review`: `formal_runs/experiment5/experiment5_eval200_20260503_r1/admin_artifacts/admin_field_review_eval200.jsonl`
- `admin_regions`: `formal_runs/experiment5/experiment5_eval200_20260503_r1/admin_artifacts/admin_regions_eval200.jsonl`
- `admin_evidence_links`: `formal_runs/experiment5/experiment5_eval200_20260503_r1/admin_artifacts/admin_evidence_links_eval200.jsonl`
- `gold_observable_accept`: `formal_runs/experiment5/experiment5_eval200_20260503_r1/inputs/gold_observable_eval200_accept.jsonl`
- `gold_observable_accept_pending`: `formal_runs/experiment5/experiment5_eval200_20260503_r1/inputs/gold_observable_eval200_accept_pending.jsonl`

## 用法

- `admin_gold_answer_dev50.jsonl` 是最终人工答案，只用于评分或审计。
- `admin_field_review_dev50.jsonl` 和 `admin_evidence_links_dev50.jsonl` 是完整审核关系，用于 oracle 诊断和错误归因。
- `gold_observable_dev50_accept*.jsonl` 是去答案字段后的方法输入，可给 G 系列使用。
