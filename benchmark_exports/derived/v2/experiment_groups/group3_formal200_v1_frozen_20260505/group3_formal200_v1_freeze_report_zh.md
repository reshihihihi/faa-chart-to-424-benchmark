# 实验组3 formal200 hard-case 子集冻结报告

冻结日期：2026-05-05

## 冻结结论

已接受当前 20 张 hard cases 和 6 类 primary type 配额。实验组3 hard-case 选择口径正式冻结为 `group3_formal200_v1_frozen_20260505`。

本冻结不包含 bootstrap。bootstrap 由独立流程执行，后续只回填统计区间和显著性结果，不改变 hard-case 选择集合。

## 冻结内容

- 候选池：实验组1实际 formal200 的 200 张航图。
- hard-case 数量：20 张。
- hard-case 比例：10.00%。
- 选择原则：不按模型错误率选难例；先按结构/证据/语义规则选定，再 join 实验组1结果做 core-vs-hard 分析。

## 6 类配额

| primary_type | 中文含义 | frozen count |
| --- | --- | ---: |
| visual_non_text_evidence | 图形/非文本证据 | 4 |
| implicit_rule | 隐式规则 | 4 |
| 424_derived_semantics | 424 派生语义 | 4 |
| cross_modal_evidence | 跨模态/多证据融合 | 3 |
| leg_structure_complexity | 航段结构复杂 | 3 |
| ocr_display_quality | OCR/显示质量 | 2 |

## 20 张冻结 hard cases

| rank | chart_id | chart_name | split | primary_type | dominant_tag |
| ---: | --- | --- | --- | --- | --- |
| 1 | KAKH_R03 | RNAV (GPS) RWY 03 | probe | visual_non_text_evidence | text_missing_visual_present |
| 2 | KANB_R05 | RNAV (GPS) RWY 05 | development | visual_non_text_evidence | text_missing_visual_present |
| 3 | KAST_R26 | RNAV (GPS) RWY 26 | development | visual_non_text_evidence | text_missing_visual_present |
| 4 | KAPC_I01L | ILS OR LOC Z RWY 01L | probe | visual_non_text_evidence | text_missing_visual_present |
| 5 | KAUS_I18L | ILS OR LOC RWY 18L | development | implicit_rule | rule_default_completion_case |
| 6 | KANJ_R14 | RNAV (GPS) RWY 14 | probe | implicit_rule | rule_default_completion_case |
| 7 | KARV_R18 | RNAV (GPS) RWY 18 | development | implicit_rule | rule_default_completion_case |
| 8 | KARV_R28 | RNAV (GPS) RWY 28 | probe | implicit_rule | rule_default_completion_case |
| 9 | KAPT_R04 | RNAV (GPS) RWY 04 | evaluation | 424_derived_semantics | ca_df_sequence |
| 10 | KAVQ_R21 | RNAV (GPS) RWY 21 | evaluation | 424_derived_semantics | ca_df_sequence |
| 11 | KBDN_R34 | RNAV (GPS) RWY 34 | probe | 424_derived_semantics | ca_df_sequence |
| 12 | KBOS_R32 | RNAV (GPS) RWY 32 | probe | 424_derived_semantics | ca_df_sequence |
| 13 | KBUR_R08-Z | RNAV (GPS) Z RWY 08 | evaluation | cross_modal_evidence | cross_modal_multi_leg |
| 14 | KAOO_R03-Z | RNAV (GPS) Z RWY 03 | development | cross_modal_evidence | cross_modal_multi_leg |
| 15 | KAOO_R21 | RNAV (GPS) RWY 21 | development | cross_modal_evidence | cross_modal_multi_leg |
| 16 | KCOI_R11 | RNAV (GPS) RWY 11 | development | leg_structure_complexity | wrong_leg_risk |
| 17 | KABE_R13 | RNAV (GPS) RWY 13 | development | leg_structure_complexity | wrong_leg_risk |
| 18 | KABE_R24 | RNAV (GPS) RWY 24 | evaluation | leg_structure_complexity | wrong_leg_risk |
| 19 | KBUR_L08-Z | ILS Z OR LOC Z RWY 08 | evaluation | ocr_display_quality | display_equivalence_sensitive |
| 20 | KCJR_L04 | LOC RWY 04 | development | ocr_display_quality | display_equivalence_sensitive |

## 文件

- `final_hard_case_selection_frozen_v1.jsonl`：冻结后的 20 张 hard-case 行级清单，去除了本地绝对路径，仅保留审查相对图片名。
- `group3_formal200_v1_freeze_manifest.json`：冻结 manifest，包含配额、chart_id、hash 和选择边界。
- `group3_formal200_freeze_pre_audit_zh.md`：冻结前审查说明，包含逐张审查理由。
- `group3_joined_chart_scores_final_hard_formal200_v1.jsonl`：hard cases 选定后 join 的实验组1 chart-level 分数，用于 core-vs-hard 分析。

## 后续使用规则

- 后续论文表格和 bootstrap 只能使用本冻结清单中的 20 张作为 formal200 hard cases。
- 不得因为 bootstrap、模型分数或某方法表现改变 hard-case 集合。
- 如果后续发现数据错误，只能走显式 revision，例如 `group3_formal200_v2`，不能静默替换 v1。
