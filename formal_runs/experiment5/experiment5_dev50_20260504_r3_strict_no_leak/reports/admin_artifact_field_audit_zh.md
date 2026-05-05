# Experiment 5 strict source audit

Generated: 2026-05-04T02:08:27.026907+00:00

## 总结

- `admin_regions` 可以作为 strict 输入来源，但必须只使用 bbox、region_type、review_action、可见 label 左侧 literal、图元类型和 provenance。
- `admin_field_review` 含 `canonical_answer`、`canonical_leg_index`、`leg_type` 等答案级字段，不能直接作为方法输入。
- `admin_gold_answer` 只能用于评分或事后审计，不能用于构造输入。
- `admin_evidence_links` 可作为关系来源候选，但必须先剥离字段名和答案字段，只保留 evidence region 关系。

## admin_regions 可用性

- charts: 50
- MA_TEXT rows: 50
- MA_TEXT nonempty ocr_text rows: 0
- plan/detail visible observable rows: 243

region_type counts:
- `CLIMB_ARROW`: 71
- `ALTITUDE_TEXT`: 63
- `FIX_TEXT`: 55
- `MISSED_APPROACH_TEXT`: 50
- `PLAN_VIEW`: 50
- `MISSED_APPROACH_DETAIL_AREA`: 50
- `FIX_SYMBOL`: 42
- `RADIAL_TEXT`: 3
- `PATH_SEGMENT`: 3
- `NAVAID_TEXT`: 2
- `HEADING_TEXT`: 2
- `OUTBOUND_INBOUND_MARK`: 2

text class counts:
- `bbox_only_no_text`: 150
- `visible_label_literal_available`: 125
- `visible_icon_available`: 118

## 方法 gate

- `A3`: `blocked_missing_visible_ma_text` - MISSED_APPROACH_TEXT rows=50, nonempty ocr_text=0; strict A3 needs real visible MA text.
- `B2`: `blocked_missing_visible_ma_text` - B2 depends on the same legal MA_TEXT prose as A3.
- `B3_T`: `blocked_missing_roi_text` - ROI text requires nonempty OCR/corrected text; available MA_TEXT OCR rows=0/50.
- `B3_PD`: `ready_visible_region_labels` - Plan/detail visible label or icon rows available=243; values must use literal label left side only.
- `B3_TPD`: `partial_missing_text` - TPD can combine PD observables with text only after legal ROI text exists.
- `B4_TPD`: `partial_missing_text` - B4 uses the same strict TPD evidence base before extra relation handling.
- `G`: `requires_rebuild_from_visible_observables` - Existing gold_observable files include interpreted value objects; rebuild as visible facts only.

## artifact forbidden-key scan

### admin_regions

- rows: 393
- forbidden key hits: 0

### admin_evidence_links

- rows: 542
- forbidden key hits:
  - `candidate_leg_id`: 542
  - `canonical_answer`: 542
  - `canonical_leg_index`: 542
  - `leg_type`: 542

### admin_field_review

- rows: 542
- forbidden key hits:
  - `candidate_leg_id`: 542
  - `canonical_answer`: 542
  - `canonical_leg_index`: 542
  - `leg_type`: 542

### admin_gold_answer

- rows: 50
- forbidden key hits:
  - `annotation_pr28_json.missed_approach.legs[].answers.Q_terminator`: 160
  - `annotation_pr28_json`: 50

## 可见 label 抽样

- `KAVL_I17` `ALTITUDE_TEXT` `accept` had_suffix: ALTITUDE_TEXT: 5400
- `KAVL_I17` `FIX_TEXT` `accept` had_suffix: FIX_TEXT: BRA
- `KAVL_I17` `CLIMB_ARROW` `pending` literal_only: detected lower detail: climb arrow
- `KCFO_I26` `ALTITUDE_TEXT` `accept` had_suffix: ALTITUDE_TEXT: 6100
- `KCFO_I26` `ALTITUDE_TEXT` `accept` literal_only: 高度文字
- `KCFO_I26` `FIX_TEXT` `accept` had_suffix: FIX_TEXT: SKIPI
- `KCFO_I26` `NAVAID_TEXT` `pending` had_suffix: NAVAID_TEXT: FQF
- `KCFO_I26` `RADIAL_TEXT` `pending` had_suffix: RADIAL_TEXT: R-045
- `KCFO_I26` `HEADING_TEXT` `accept` had_suffix: HEADING_TEXT: 080°
- `KCFO_I26` `CLIMB_ARROW` `pending` literal_only: detected lower detail: climb arrow
- `KCFO_I26` `CLIMB_ARROW` `pending` literal_only: detected lower detail: climb arrow
- `KAVP_L04` `ALTITUDE_TEXT` `accept` had_suffix: ALTITUDE_TEXT: 3000
- `KAVP_L04` `ALTITUDE_TEXT` `accept` had_suffix: ALTITUDE_TEXT: 4000
- `KAVP_L04` `FIX_TEXT` `accept` had_suffix: FIX_TEXT: LVZ
- `KAVP_L04` `CLIMB_ARROW` `pending` literal_only: detected lower detail: climb arrow
- `KBYL_L20` `ALTITUDE_TEXT` `accept` had_suffix: ALTITUDE_TEXT: 4000
- `KBYL_L20` `ALTITUDE_TEXT` `accept` had_suffix: ALTITUDE_TEXT: 1800
- `KBYL_L20` `FIX_TEXT` `accept` had_suffix: FIX_TEXT: LOZ
- `KBYL_L20` `CLIMB_ARROW` `pending` literal_only: detected lower detail: climb arrow
- `KBYL_L20` `CLIMB_ARROW` `pending` literal_only: detected lower detail: climb arrow

## 审计结论

dev50 后台导出的框和关系可以支持 B3_PD 类 strict 输入的重建；但当前 admin_regions 中 MA_TEXT 的 `ocr_text` 为空，因此 A3/B2/B3_T/B3_TPD/B4_TPD 的文本侧仍需要合法的图面 OCR 或人工校正文本文本，不能再用 r2 的 answer-derived prose 补。
