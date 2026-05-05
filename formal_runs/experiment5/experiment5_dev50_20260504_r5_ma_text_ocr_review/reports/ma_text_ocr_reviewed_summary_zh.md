# Experiment 5 dev50 MA_TEXT OCR reviewed input

Generated: 2026-05-04T02:49:30.816128+00:00

## 结论

`gold_ma_text_dev50_ocr_reviewed.jsonl` 已生成。50 条都以 `MISSED APPROACH:` 开头，且不使用最终答案、canonical_answer 或 scoring target。

6 条原先可疑的 OCR 已按用户提供的图片文本覆盖；其余 44 条来自 auto-cleaned v2 且没有 suspicious flag。

## 计数

- `auto_cleaned_v2_accept_no_suspicious_flags`: 44
- `reviewed_accept_user_image_confirmed`: 6

## no-leakage scan

- status: `PASS`
- rows: 50
- forbidden key hits: 0
- non-MISSED-APPROACH prefix rows: 0

## 用户图片确认覆盖的 6 条

- `KACT_R01`: MISSED APPROACH: Climb to 3000 direct CHRUS and hold.
- `KACT_R32`: MISSED APPROACH: Climb to 4000 direct EVVIS and hold, continue climb-in-hold to 4000.
- `KAEX_R18`: MISSED APPROACH: Climb to 4000 direct HIPKU and via 105° track to MUSHE and hold.
- `KAEX_R32`: MISSED APPROACH: Climb to 3000 direct EBYAJ WP and hold.
- `KAND_R17`: MISSED APPROACH: Climb to 2500 direct ZAROM and hold.
- `KAPN_R01`: MISSED APPROACH: Climb to 3500 direct HIMVO and on track 307° to RABBO and hold.
