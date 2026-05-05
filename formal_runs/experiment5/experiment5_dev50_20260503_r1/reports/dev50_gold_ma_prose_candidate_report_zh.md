# 实验组5 dev50 gold_ma_prose 候选生成报告

- 生成时间 UTC: `2026-05-03T09:02:01.911996+00:00`
- dev50 rows: 50
- PDF 下载成功: 50/50
- pdftotext 成功: 50/50
- 找到 admin MA_TEXT bbox: 50/50
- 生成 MA prose 候选: 50/50
- layout fallback 次数: 0
- 状态: `complete_candidates_need_review`

## 重要限制

- 这是 dev50 跑通用候选，不是正式人工 adjudicated gold。
- 候选只使用 FAA PDF text layer 和去泄漏 admin MA_TEXT 区域框。
- 没有使用 field review、canonical answer、score、CIFP/ARINC 424 或任何方法输出。

## 输出

- candidate jsonl: `formal_runs/experiment5/experiment5_dev50_20260503_r1/inputs/gold_ma_text_dev50_candidate.jsonl`
- extraction details: `formal_runs/experiment5/experiment5_dev50_20260503_r1/reports/gold_ma_pdf_bbox_extract_candidates_dev50.jsonl`

## 下一步

1. 先用这个 candidate 文件跑 A3/B2 的 dev50 pipeline check。
2. 如果要把 dev50 结果作为正式诊断数字，需人工抽查并改成 adjudicated gold。
