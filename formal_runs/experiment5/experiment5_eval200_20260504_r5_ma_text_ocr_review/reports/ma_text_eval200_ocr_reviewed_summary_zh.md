# Experiment 5 eval200 MA_TEXT OCR reviewed input

Generated: 2026-05-04T03:10:26.479195+00:00

## 结论

`gold_ma_text_eval200_ocr_reviewed.jsonl` 已生成。所有行都以 `MISSED APPROACH:` 开头，且不使用最终答案、canonical_answer 或 scoring target。

8 条原先可疑的 OCR 已按图片/人工检查文本覆盖；其余行来自 auto-cleaned v2 且没有 suspicious flag。

## 计数

- `auto_cleaned_v2_accept_no_suspicious_flags`: 192
- `reviewed_accept_image_or_manual_inspected`: 8

## no-leakage scan

- status: `PASS`
- rows: 200
- forbidden key hits: 0
- non-MISSED-APPROACH prefix rows: 0

## 图片/人工检查覆盖的 8 条

- `KAAS_R05`: MISSED APPROACH: Climb to 3000 direct DOODA and hold.
- `KAIK_R07`: MISSED APPROACH: Climb to 2500 direct OXAXE and hold.
- `KAIK_R25`: MISSED APPROACH: Climb to 3000 direct VIXLY and hold.
- `KANB_R23`: MISSED APPROACH: Climb to 3400 direct LINTZ and hold.
- `KAQX_R35`: MISSED APPROACH: Climb to 2100 direct APTIF and hold.
- `KAXV_R26`: MISSED APPROACH: Climb to 3000 direct ZUKEC and hold.
- `KBFD_R14`: MISSED APPROACH: Climb to 4500 direct NIMEE and hold.
- `KCDS_R36`: MISSED APPROACH: Climb to 2400 then climbing right turn to 4000 direct JAPUX and hold.
