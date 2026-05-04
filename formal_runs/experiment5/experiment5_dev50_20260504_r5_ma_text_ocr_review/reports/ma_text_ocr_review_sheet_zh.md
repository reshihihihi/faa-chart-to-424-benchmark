# Experiment 5 dev50 MA_TEXT OCR 人工校验表

说明：这里的 OCR/PDF text-layer 都只是候选。请以图片为准，把确认后的文本填入 review JSONL 的 `reviewed_gold_ma_prose`。

严格规则：确认前不能把这些候选当作正式 A3/B2/B3_T 输入；确认后才可以生成 `gold_ma_text_dev50_ocr_reviewed.jsonl`。

## KACT_R01

![KACT_R01 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KACT_R01_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `88.04`

OCR raw candidate:

```text
> 54°C. Baro-VNAV ion below 34 SM NA. MISSED APPROACH:. LPV DA to 792 feet Climb to 3000 direct As AO feet and LNAV CHRUS and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH:. LPV DA to 792 feet Climb to 3000 direct As AO feet and LNAV CHRUS and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: increase LPV DA to 792 feet Climb to 3000 direct MDAs 40 feet and LNAV CHRUS and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: increase LPV DA to 792 feet Climb to 3000 direct MDAs 40 feet and LNAV CHRUS and hold.
```

## KACT_R19

![KACT_R19 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KACT_R19_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `93.85`

OCR raw candidate:

```text
MALSR MISSED APPROACH: Climb to 4000 direct YAYUC and on track 171° to BOSEL and hold, continue climb-in-hold to 4000.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 4000 direct YAYUC and on track 171° to BOSEL and hold, continue climb-in-hold to 4000.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to above 4000 direct YAYUC and on track 171° to BOSEL and hold, A5 continue climb-in-hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to above 4000 direct YAYUC and on track 171° to BOSEL and hold, A5 continue climb-in-hold.
```

## KACT_R32

![KACT_R32 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KACT_R32_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `87.3`

OCR raw candidate:

```text
Gregor MISSED APPROACH: rease Climb to 4000 direct -ircling EVVIS and hold, NAV continue climb-in-hold 1g Mc Gregor to 4000.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: rease Climb to 4000 direct -ircling EVVIS and hold, NAV continue climb-in-hold 1g Mc Gregor to 4000.
```

PDF text-layer candidate:

```text
MISSED APPROACH: feet; increase Climb to 4000 direct and Circling EVVIS and hold, LNAV/VNAV continue climb-in-hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: feet; increase Climb to 4000 direct and Circling EVVIS and hold, LNAV/VNAV continue climb-in-hold.
```

## KACV_R01

![KACV_R01 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KACV_R01_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `93.73`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 3200 direct HIPGI and on track 295° to CULDU and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3200 direct HIPGI and on track 295° to CULDU and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 3200 direct HIPGI and on track 295° to CULDU and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3200 direct HIPGI and on track 295° to CULDU and hold.
```

## KACV_R14

![KACV_R14 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KACV_R14_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.55`

OCR raw candidate:

```text
MISSED APPROACH: Climbing right turn to 3000 direct SEGVE and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climbing right turn to 3000 direct SEGVE and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: NA. Climbing right turn to 3000 direct SEGVE and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: NA. Climbing right turn to 3000 direct SEGVE and hold.
```

## KACV_R32

![KACV_R32 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KACV_R32_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `95.0`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 3000 direct CULDU and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3000 direct CULDU and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 3000 direct CULDU and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3000 direct CULDU and hold.
```

## KAEX_R14

![KAEX_R14 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAEX_R14_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.6`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 4000 direct EHHIR and on track 106° to MUSHE and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 4000 direct EHHIR and on track 106° to MUSHE and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 4000 direct EHHIR and on track 106° to MUSHE and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 4000 direct EHHIR and on track 106° to MUSHE and hold.
```

## KAEX_R18

![KAEX_R18 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAEX_R18_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `92.0`

OCR raw candidate:

```text
iensated MISSED APPROACH: Climb F). to 4000 direct HIPKU and via 105° track to MUSHE and hola.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb F). to 4000 direct HIPKU and via 105° track to MUSHE and hola.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb (119°F). to 4000 direct HIPKU and via 105° track to MUSHE and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb (119°F). to 4000 direct HIPKU and via 105° track to MUSHE and hold.
```

## KAEX_R32

![KAEX_R32 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAEX_R32_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `91.0`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 3000 direct EBYAJ WP and hola.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3000 direct EBYAJ WP and hola.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 3000 -15°C. direct EBYAJ WP and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3000 -15°C. direct EBYAJ WP and hold.
```

## KAGS_R08-Y

![KAGS_R08-Y MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAGS_R08-Y_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `90.43`

OCR raw candidate:

```text
MISSED APPROACH: meter setting. Climb to 1200 then climbing ase all MDAs right turn to 2000 direct sibility 4 SM. GUKVE and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: meter setting. Climb to 1200 then climbing ase all MDAs right turn to 2000 direct sibility 4 SM. GUKVE and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Fld altimeter setting. Climb to 1200 then climbing increase all MDAs right turn to 2000 direct D visibility 14 SM. GUKVE and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Fld altimeter setting. Climb to 1200 then climbing increase all MDAs right turn to 2000 direct D visibility 14 SM. GUKVE and hold.
```

## KAGS_R08-Z

![KAGS_R08-Z MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAGS_R08-Z_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `93.0`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 1200 then climbing right turn to 2000 direct HEPIG and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 1200 then climbing right turn to 2000 direct HEPIG and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 1200 then climbing right turn to 2000 direct HEPIG and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 1200 then climbing right turn to 2000 direct HEPIG and hold.
```

## KAGS_R26

![KAGS_R26 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAGS_R26_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `90.1`

OCR raw candidate:

```text
MISSED APPROACH: iltimeter setting. Climb to 3000 direct ease all MDAs GONRE and on track 201° to HEPIG and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: iltimeter setting. Climb to 3000 direct ease all MDAs GONRE and on track 201° to HEPIG and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Fld altimeter setting. Climb to 3000 direct increase all MDAs GONRE and on track 201° to HEPIG and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Fld altimeter setting. Climb to 3000 direct increase all MDAs GONRE and on track 201° to HEPIG and hold.
```

## KAJG_R04

![KAJG_R04 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAJG_R04_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.44`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 2500 direct RUOFF and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2500 direct RUOFF and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 2500 direct RUOFF and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2500 direct RUOFF and hold.
```

## KAJG_R22

![KAJG_R22 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAJG_R22_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `95.0`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 2500 direct SURDY and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2500 direct SURDY and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 2500 direct SURDY and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2500 direct SURDY and hold.
```

## KAJG_R31

![KAJG_R31 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAJG_R31_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `93.55`

OCR raw candidate:

```text
MISSED APPROACH: Climbing lett turn to 2500 direct NIYRI and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climbing lett turn to 2500 direct NIYRI and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climbing left turn setting to 2500 direct NIYRI and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climbing left turn setting to 2500 direct NIYRI and hold.
```

## KAND_R05

![KAND_R05 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAND_R05_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `90.29`

OCR raw candidate:

```text
MALSR | MISSED APPROACH: Climb to & -=- | 3000 direct OXTIC and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to & -=- | 3000 direct OXTIC and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to C/D A5 3000 direct OXTIC and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to C/D A5 3000 direct OXTIC and hold.
```

## KAND_R17

![KAND_R17 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAND_R17_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `81.69`

OCR raw candidate:

```text
} imeter setting MISSED APPROACH: Climb ity Amie. to 2500 direct ZAROM and ter visibility Lold
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb ity Amie. to 2500 direct ZAROM and ter visibility Lold
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb helicopter visibility to 2500 direct ZAROM and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb helicopter visibility to 2500 direct ZAROM and hold.
```

## KAND_R23

![KAND_R23 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAND_R23_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.89`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 2500 direct OYUNA and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2500 direct OYUNA and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to altimeter 2500 direct OYUNA and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to altimeter 2500 direct OYUNA and hold.
```

## KANE_R09

![KANE_R09 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KANE_R09_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.89`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 3100 direct JUDAL and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3100 direct JUDAL and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 3100 direct JUDAL and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3100 direct JUDAL and hold.
```

## KANE_R18

![KANE_R18 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KANE_R18_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `95.0`

OCR raw candidate:

```text
MISSED APPROACH: Climbing left turn to 2600 direct RUNRR and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climbing left turn to 2600 direct RUNRR and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climbing left turn to 2600 direct RUNRR and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climbing left turn to 2600 direct RUNRR and hold.
```

## KANE_R27

![KANE_R27 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KANE_R27_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `88.18`

OCR raw candidate:

```text
MISSED APPROACH: Climb MALSR to 2700 direct GEP VORTAC ss Ge and hold, continue climb-in-hold to 2700.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb MALSR to 2700 direct GEP VORTAC ss Ge and hold, continue climb-in-hold to 2700.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb increase MALSR to 2700 direct GEP VORTAC SM, and hold, continue D 14 A5 climb-in-hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb increase MALSR to 2700 direct GEP VORTAC SM, and hold, continue D 14 A5 climb-in-hold.
```

## KANY_R18

![KANY_R18 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KANY_R18_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `93.8`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 3000 then climbing left turn to 3300 direct UZZUF and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3000 then climbing left turn to 3300 direct UZZUF and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 3000 then climbing left turn to 3300 direct UZZUF and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3000 then climbing left turn to 3300 direct UZZUF and hold.
```

## KANY_R36

![KANY_R36 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KANY_R36_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `95.22`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 3300 direct UZZUF and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3300 direct UZZUF and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: NA. Climb to 3300 direct UZZUF and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: NA. Climb to 3300 direct UZZUF and hold.
```

## KAPA_R17LY

![KAPA_R17LY MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAPA_R17LY_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `92.37`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 6300 then climbing right turn to 10400 direct HOHUM and hold, continue climb-in-hold to 10400.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 6300 then climbing right turn to 10400 direct HOHUM and hold, continue climb-in-hold to 10400.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 6300 then climbing right turn to 10400 direct HOHUM and hold, continue climb-in-hold to 10400.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 6300 then climbing right turn to 10400 direct HOHUM and hold, continue climb-in-hold to 10400.
```

## KAPA_R28

![KAPA_R28 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAPA_R28_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `95.53`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 6400 then climbing right turn to 9000 direct EZBEL and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 6400 then climbing right turn to 9000 direct EZBEL and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 6400 above then climbing right turn to 9000 direct 35L EZBEL and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 6400 above then climbing right turn to 9000 direct 35L EZBEL and hold.
```

## KAPA_R35R

![KAPA_R35R MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAPA_R35R_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `90.05`

OCR raw candidate:

```text
MISSED APPROACH: (Do not exceed | 240K until BPUTN) Climb to 8200 then climbing left turn to 9600 direct BPUTN and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: (Do not exceed | 240K until BPUTN) Climb to 8200 then climbing left turn to 9600 direct BPUTN and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: (Do not exceed 240K until BPUTN) Climb to 8200 then climbing left turn to 9600 direct A5 BPUTN and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: (Do not exceed 240K until BPUTN) Climb to 8200 then climbing left turn to 9600 direct A5 BPUTN and hold.
```

## KAPN_R01

![KAPN_R01 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAPN_R01_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `85.57`

OCR raw candidate:

```text
5A°C, Baro- MALSR| MISSED APPROACH ill Cats visibility Climb to 3500 direct 36 SM. When © = | HIMVO and on track > 1029 feet and &) 307° to RABBO and hold. ) feet. For inop —)
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: ill Cats visibility Climb to 3500 direct 36 SM. When © = | HIMVO and on track > 1029 feet and &) 307° to RABBO and hold. ) feet. For inop —)
```

PDF text-layer candidate:

```text
MISSED APPROACH: LPV all Cats visibility Climb to 3500 direct DA to 1 to 3 8 1029 SM. feet When and A5 307° HIMVO to and RABBO on track 60 feet. For inop and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: LPV all Cats visibility Climb to 3500 direct DA to 1 to 3 8 1029 SM. feet When and A5 307° HIMVO to and RABBO on track 60 feet. For inop and hold.
```

## KAPN_R07

![KAPN_R07 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAPN_R07_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.36`

OCR raw candidate:

```text
MISSED APPROACH Climb to 3000 direct MUNCN and hold, continue climb-in- hold to 3000.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3000 direct MUNCN and hold, continue climb-in- hold to 3000.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 3000 direct MUNCN and hold, continue climb-in- hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3000 direct MUNCN and hold, continue climb-in- hold.
```

## KAPN_R19

![KAPN_R19 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAPN_R19_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.78`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 2800 direct JEGOB and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2800 direct JEGOB and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 2800 direct JEGOB and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2800 direct JEGOB and hold.
```

## KARR_R09

![KARR_R09 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KARR_R09_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.8`

OCR raw candidate:

```text
MALSR MISSED APPROACH: Climb to 2500 direct HOGIE and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2500 direct HOGIE and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: 54°C. Climb to 2500 direct A5 HOGIE and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: 54°C. Climb to 2500 direct A5 HOGIE and hold.
```

## KARR_R15

![KARR_R15 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KARR_R15_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.62`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 3000 direct UQITY and hold, continue climb-in-hold to 3000.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3000 direct UQITY and hold, continue climb-in-hold to 3000.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 54°C. 3000 direct UQITY and hold, continue climb-in-hold to 3000.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 54°C. 3000 direct UQITY and hold, continue climb-in-hold to 3000.
```

## KARR_R27

![KARR_R27 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KARR_R27_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.0`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 2700 direct TOBBY and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2700 direct TOBBY and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 2700 direct 54°C. TOBBY and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2700 direct 54°C. TOBBY and hold.
```

## KART_R07

![KART_R07 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KART_R07_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `89.39`

OCR raw candidate:

```text
MALSR MISSED APPROACH: Climb to 900 then climbing lett turn to &3) 7 3500 direct NOYAQ and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 900 then climbing lett turn to &3) 7 3500 direct NOYAQ and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to -20°C 900 then climbing left turn to Cats A5 3500 direct NOYAQ and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to -20°C 900 then climbing left turn to Cats A5 3500 direct NOYAQ and hold.
```

## KART_R10

![KART_R10 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KART_R10_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.67`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 3600 direct BAMPE and on track 146° to PATEE and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3600 direct BAMPE and on track 146° to PATEE and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 3600 direct BAMPE and or on track 146° to PATEE and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3600 direct BAMPE and or on track 146° to PATEE and hold.
```

## KART_R28

![KART_R28 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KART_R28_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `88.46`

OCR raw candidate:

```text
MALSR | MISSED APPROACH: Climb to 2400 direct & 7 TAREE and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2400 direct & 7 TAREE and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 2400 direct A5 TAREE and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2400 direct A5 TAREE and hold.
```

## KATW_R21

![KATW_R21 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KATW_R21_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `93.88`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 2900 direct APIXE and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2900 direct APIXE and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 2900 direct APIXE and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2900 direct APIXE and hold.
```

## KAVL_I17

![KAVL_I17 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAVL_I17_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `88.57`

OCR raw candidate:

```text
SED APPROACH: Climb to 5400 direct BRA NDB | hold. Continue climb-in-hold to 5400.
```

OCR MISSED APPROACH candidate:

```text
SED APPROACH: Climb to 5400 direct BRA NDB | hold. Continue climb-in-hold to 5400.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 5400 direct BRA NDB and hold. Continue climb-in-hold to 5400.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 5400 direct BRA NDB and hold. Continue climb-in-hold to 5400.
```

## KAVP_L04

![KAVP_L04 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAVP_L04_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `90.79`

OCR raw candidate:

```text
MISSED APPROACH: MALSR | Climb to 3000 then climbing — right turn to 4000 direct LVZ VORTAC and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: MALSR | Climb to 3000 then climbing — right turn to 4000 direct LVZ VORTAC and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: MALSR Climb to 3000 then climbing A5 right turn to 4000 direct LVZ VORTAC and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: MALSR Climb to 3000 then climbing A5 right turn to 4000 direct LVZ VORTAC and hold.
```

## KAVP_R22

![KAVP_R22 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAVP_R22_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `95.13`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 1900 then climbing right turn to 4000 direct LOPEZ and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 1900 then climbing right turn to 4000 direct LOPEZ and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 1900 then climbing right turn to 4000 direct LOPEZ and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 1900 then climbing right turn to 4000 direct LOPEZ and hold.
```

## KAXN_R22

![KAXN_R22 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KAXN_R22_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.61`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 3500 direct MOVSE and right turn on track 315° to EVDEQ and on track 024° to TILER and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3500 direct MOVSE and right turn on track 315° to EVDEQ and on track 024° to TILER and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 3500 direct MOVSE and right turn on track 315° to EVDEQ and on track 024° to TILER and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3500 direct MOVSE and right turn on track 315° to EVDEQ and on track 024° to TILER and hold.
```

## KBKW_R01

![KBKW_R01 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KBKW_R01_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.46`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 5900 direct YISUK and hold, continue climb-in-hold to 5900.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 5900 direct YISUK and hold, continue climb-in-hold to 5900.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 5900 direct YISUK and hold, continue climb-in-hold to 5900.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 5900 direct YISUK and hold, continue climb-in-hold to 5900.
```

## KBWC_R26

![KBWC_R26 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KBWC_R26_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `83.67`

OCR raw candidate:

```text
COACH: Climbing lett turn to 3600 direct and hold.
```

OCR MISSED APPROACH candidate:

```text
COACH: Climbing lett turn to 3600 direct and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climbing left turn to 3600 direct VORTAC and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climbing left turn to 3600 direct VORTAC and hold.
```

## KBYI_R20

![KBYI_R20 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KBYI_R20_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `91.6`

OCR raw candidate:

```text
MISSED APPROACH: Climbing left turn to 7000 direct IREME and hold, continue climb-in-hold to 7000.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climbing left turn to 7000 direct IREME and hold, continue climb-in-hold to 7000.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climbing left turn to 7000 direct IREME and hold, continue climb-in-hold to 7000.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climbing left turn to 7000 direct IREME and hold, continue climb-in-hold to 7000.
```

## KBYL_L20

![KBYL_L20 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KBYL_L20_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.25`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 1800 then climbing left turn to 4000 direct LOZ VOR/DME and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 1800 then climbing left turn to 4000 direct LOZ VOR/DME and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 1800 then climbing left turn to 4000 direct LOZ VOR/DME and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 1800 then climbing left turn to 4000 direct LOZ VOR/DME and hold.
```

## KCFO_I26

![KCFO_I26 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KCFO_I26_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.2`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 6100 then climbing left turn to 7200 on heading 080° and on FQF VORTAC R-O45 to SKIPI/I-FTG 7 DME and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 6100 then climbing left turn to 7200 on heading 080° and on FQF VORTAC R-O45 to SKIPI/I-FTG 7 DME and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 6100 then climbing left turn to 7200 on heading 080° and on FQF VORTAC R-045 to SKIPI/I-FTG 7 DME and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 6100 then climbing left turn to 7200 on heading 080° and on FQF VORTAC R-045 to SKIPI/I-FTG 7 DME and hold.
```

## KCFO_L17

![KCFO_L17 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KCFO_L17_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `82.69`

OCR raw candidate:

```text
COACH: Climb to 8500 on heading 172° and »R-127 to HUNTN INT/FQF 9.8 DME and hold.
```

OCR MISSED APPROACH candidate:

```text
COACH: Climb to 8500 on heading 172° and »R-127 to HUNTN INT/FQF 9.8 DME and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 8500 on heading 172° and VORTAC R-127 to HUNTN INT/FQF 9.8 DME and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 8500 on heading 172° and VORTAC R-127 to HUNTN INT/FQF 9.8 DME and hold.
```

## KCIC_R13L

![KCIC_R13L MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KCIC_R13L_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.54`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 3600 direct UNJED and hold, continue climb-in-hold to 3600.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3600 direct UNJED and hold, continue climb-in-hold to 3600.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 3600 direct UNJED and hold, continue climb-in-hold to 3600.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3600 direct UNJED and hold, continue climb-in-hold to 3600.
```

## KCLL_R11

![KCLL_R11 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KCLL_R11_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `95.22`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 3000 direct EDAYA and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 3000 direct EDAYA and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to or 3000 direct EDAYA and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to or 3000 direct EDAYA and hold.
```

## KCOE_L06

![KCOE_L06 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KCOE_L06_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.2`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 2900 then climbing lett turn to 6000 on COE R-350 outbound then climbing left turn to 6500 on COE R-350 inbound to COE VOR/DME and hold.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2900 then climbing lett turn to 6000 on COE R-350 outbound then climbing left turn to 6500 on COE R-350 inbound to COE VOR/DME and hold.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 2900 then MALSR climbing left turn to 6000 on COE R-350 outbound then climbing left turn to 6500 on COE R-350 inbound to COE VOR/DME and hold.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 2900 then MALSR climbing left turn to 6000 on COE R-350 outbound then climbing left turn to 6500 on COE R-350 inbound to COE VOR/DME and hold.
```

## KCOE_R02

![KCOE_R02 MA_TEXT crop](E:/experiment3/github_work/faa-chart-to-424-benchmark-experiment5/formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/admin_ma_text_crops_v2/KCOE_R02_admin_ma_text_crop_v2.png)

- OCR candidate confidence: `94.08`

OCR raw candidate:

```text
MISSED APPROACH: Climb to 7000 direct ZEXEL and hold, continue climb-in-hold to 7000.
```

OCR MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 7000 direct ZEXEL and hold, continue climb-in-hold to 7000.
```

PDF text-layer candidate:

```text
MISSED APPROACH: Climb to 7000 direct ZEXEL and hold, continue climb-in-hold to 7000.
```

PDF MISSED APPROACH candidate:

```text
MISSED APPROACH: Climb to 7000 direct ZEXEL and hold, continue climb-in-hold to 7000.
```

