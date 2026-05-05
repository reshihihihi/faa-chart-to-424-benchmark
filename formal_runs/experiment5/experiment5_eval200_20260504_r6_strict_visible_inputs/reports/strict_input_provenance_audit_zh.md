# Experiment 5 dev50 strict input provenance audit

Generated: 2026-05-04T03:51:36.040705+00:00

## 输入生成结果

- A3/B2: {'blocked_missing_visible_ma_text': 200}
- B3_T: {'blocked_missing_roi_text': 200}
- B3_PD: {'ready_visible_region_labels': 200}
- B3_TPD/B4_TPD: {'partial_missing_text': 200}
- G: {'ready_visible_observable_no_final_answers': 200}

## no-leakage scan

- status: `PASS`
- scanned rows: 2400
- forbidden key hits: 0
- forbidden value hits: 0
- interpreted `->` suffix hits: 0

## 结论

已生成 dev50 strict 输入工件，但只有 B3_PD 与 G-visible-observable 是完整可用输入。A3/B2/B3_T 仍缺合法 MA_TEXT/ROI 文本，因此 B3_TPD/B4_TPD 目前只能算 partial input，不能正式报告完整 TPD 分数。

下一步应先人工确认 B3_PD/G 的可见 label literal 是否符合预期；如果要跑 A3/B2/B3_T/TPD，则必须补合法图面 OCR 或人工校正 MA_TEXT/ROI 文本。
