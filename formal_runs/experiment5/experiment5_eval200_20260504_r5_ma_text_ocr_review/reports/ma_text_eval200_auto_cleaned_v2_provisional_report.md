# Experiment 5 MA_TEXT auto-cleaned v2 provisional input report

Generated: 2026-05-04T03:07:33.029920+00:00

This v2 file applies extra OCR cleanup after trimming to MISSED APPROACH.
It removes noisy prefixes before the first Climb/Climbing phrase, fixes common OCR hold/degree errors,
and repairs six rows that were flagged by the first provisional pass.

The source is still chart crop OCR/PDF text-layer candidates only; final answers are not used.
Status remains provisional until human spotcheck or acceptance.

- rows: 200
- suspicious rows: 8

## Remaining rows to inspect

- `KAAS_R05` flags=['contains_weather_or_visibility_note']

```text
MISSED APPROACH: Climb to 3000 direct Baro-VNAV DOODA and hold.
```

- `KAIK_R07` flags=['contains_common_ocr_garbage']

```text
MISSED APPROACH: not received, use Augusta Climb to 2500 direct OXAXE and hold. increase all MDAs 120 feet Rwy 1, 19 NA at night.
```

- `KAIK_R25` flags=['missing_climb_keyword']

```text
MISSED APPROACH:.
```

- `KANB_R23` flags=['contains_common_ocr_garbage']

```text
MISSED APPROACH: received, use Climb to 3400 direct increase all LINTZ and hold. VDP NA.
```

- `KAQX_R35` flags=['contains_common_ocr_garbage']

```text
MISSED APPROACH: and increase Climb to 2100 direct 38 mile. APTIF and hold.
```

- `KAXV_R26` flags=['contains_common_ocr_garbage']

```text
MISSED APPROACH: Lima Climb to 3000 direct Increase ZUKEC and hold. 60 feet.
```

- `KBFD_R14` flags=['contains_common_ocr_garbage']

```text
MISSED APPROACH: not received, use Climb to 4500 direct NIMEE and hold. Circling Cat C.
```

- `KCDS_R36` flags=['contains_lpv_or_lnav_minima_text', 'contains_weather_or_visibility_note']

```text
MISSED APPROACH: setting not received, Climb to 2400 then MDA 200 feet and climbing right turn to Cats C and D 4000 direct JAPUX Baro-VNAV and and hold.
```

