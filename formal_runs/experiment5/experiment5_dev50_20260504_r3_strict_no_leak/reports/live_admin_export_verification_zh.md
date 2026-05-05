# Experiment 5 dev50 live admin export verification

日期：2026-05-04

## 结论

本轮 strict 输入使用的框不是重新人工框出来的，也不是脚本自行生成的框；来源是后台导出的人工审核框数据。

为确认这一点，已从后台 live 重新下载 latest complete `formal300` export，并重新导出 dev50 的 `admin_regions / admin_field_review / admin_evidence_links / admin_gold_answer`。重新导出的 artifact 与 `experiment5_dev50_20260503_r1/admin_artifacts` 完全一致。

## live export

- selected export file: `shujuji_annotation_export_2026-05-03T08-34-13-795Z.json`
- selected export created_at: `2026-05-03T08:34:13.795Z`
- export sha256: `52082332ff922132a83bca087d250f08571f77709f716e360439daafee313574`
- formal300 final_json_count: `300`
- formal300 submission_json_count: `439`

## dev50 artifact 对比

以下 SHA256 均为 r1 artifact 与 live 重新导出 artifact 的对比结果；每一项两边相同。

- `admin_regions_dev50.jsonl`: `AE09BFBDC9E9C33A37309FD57D97884B23868975C8F3994FCCD9992931AE8AB5`
- `admin_field_review_dev50.jsonl`: `C4B577A1EA80FD6B0FF21F8F366C57A2567BF9CC4CB9C54BA46E6605E8D8C636`
- `admin_evidence_links_dev50.jsonl`: `3BE23167DEACB51E1FF56FAAF8AD1509D3C5B715C48977B118293783C66298BB`
- `admin_gold_answer_dev50.jsonl`: `34147B5120712D2AE20079004DB740B6E4F1F82A3FB0831FBFD89A307040DFA7`

## live 导出计数

- charts: `50`
- region rows: `393`
- field review rows: `542`
- evidence link rows: `542`
- gold answer rows: `50`
- missing submission chart ids: `0`
- gold answer schema error charts: `0`

## 对 strict 输入的影响

因为 live 导出的后台框与 r1 artifact 完全一致，`experiment5_dev50_20260504_r3_strict_no_leak` 中的 strict 输入仍然有效，不需要因为框来源重新生成。

当前限制仍然是：后台框数据中 `MISSED_APPROACH_TEXT` 的 `ocr_text` 为空，所以 A3/B2/B3_T 的 strict 文本侧不能用最终答案补，只能等待合法 OCR 或人工抄录文本；B3_PD 和 G-visible-observable 可以使用后台框、可见 label literal 和图元关系继续。
