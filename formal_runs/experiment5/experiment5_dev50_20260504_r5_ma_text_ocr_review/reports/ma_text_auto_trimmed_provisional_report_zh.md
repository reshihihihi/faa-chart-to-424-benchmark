# Experiment 5 MA_TEXT auto-trimmed input report

Generated: 2026-05-04T02:38:09.080934+00:00

## 说明

本文件把 OCR 候选统一裁剪到 `MISSED APPROACH:` 开头，删除此前的灯光、minima、温度等前缀污染。

这一步只能降低前缀污染，不能保证 OCR 后半句完全正确。因此当前状态是 provisional，不等于人工 reviewed gold。

## 汇总

- rows: 50
- suspicious rows: 6

## 需要重点抽查

- `KACT_R01` flags=['contains_lpv_or_lnav_minima_text', 'contains_common_ocr_garbage']

```text
MISSED APPROACH: LPV DA to 792 feet Climb to 3000 direct As AO feet and LNAV CHRUS and hold.
```

- `KACT_R32` flags=['contains_common_ocr_garbage']

```text
MISSED APPROACH: rease Climb to 4000 direct -ircling EVVIS and hold, NAV continue climb-in-hold 1g Mc Gregor to 4000.
```

- `KAEX_R18` flags=['contains_common_ocr_garbage']

```text
MISSED APPROACH: Climb F). to 4000 direct HIPKU and via 105° track to MUSHE and hola.
```

- `KAEX_R32` flags=['contains_common_ocr_garbage']

```text
MISSED APPROACH: Climb to 3000 direct EBYAJ WP and hola.
```

- `KAND_R17` flags=['missing_terminal_punctuation']

```text
MISSED APPROACH: Climb ity Amie. to 2500 direct ZAROM and ter visibility Lold
```

- `KAPN_R01` flags=['missing_terminal_punctuation']

```text
MISSED APPROACH: ill Cats visibility Climb to 3500 direct 36 SM. When © = | HIMVO and on track > 1029 feet and &) 307° to RABBO and hold. ) feet. For inop —)
```

