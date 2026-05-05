# 实验组3 formal200 难例集冻结前审查说明

生成时间：2026-05-05

## 1. 当前结论

实验组3原本任务的主体已经完成：已经从实验组1实际 formal200 的 200 张航图中，按预先定义的结构/证据/语义困难规则选出 20 张 hard cases，占 10.00%。当前文件用于冻结前人工审查；bootstrap 由另一流程执行，不在本文中完成。

**建议状态：可以进入人工审查；在 20 张 hard cases 被确认前，不建议标记为 fully frozen。**

## 2. 实验组3要回答什么

- 实验组1给出各方法在 formal200 上的总体抽取表现。
- 实验组3进一步问：这些方法在普通样本 core 和预先定义的困难样本 hard cases 上是否表现不同。
- hard cases 不能根据模型错误率选择，否则会变成“模型错的就是难例，再证明模型在难例上差”的循环论证。
- 因此本版 hard cases 只使用 target 结构、comparison policy、人工证据来源标注和样本多样性生成；模型分数只在选定 hard cases 后用于分析。

## 3. 候选池与口径

- 候选池：实验组1实际 formal200 样本，共 200 张。
- hard case 数量：20 张，占 10.00%。
- formal300 split 分布：evaluation=51，development=131，probe=18。
- 旧的 19/30 张试跑和 144 overlap 诊断集合不作为正式实验组3冻结口径。

## 4. 选择规则

### 4.1 不允许使用的依据

- 不按某个模型是否做错来选难例。
- 不按 D_SFT、C4 或任何单一方法的低分来选难例。
- 不使用模型输出内容、预测 JSON、score value、源编码记录作为难例选择输入。

### 4.2 允许使用的依据

- canonical/field target 的结构信号：如 CA/HM、CA→DF、multi-leg、terminator-derived。
- comparison policy 的显示等价敏感信号：如 degree display rounding。
- 人工证据来源标注派生信号：如 text_missing_visual_present、rule_default_completion_case、visible_joint、cross_modal_required。
- 多样性约束：保证不同困难类型都有代表样本。

## 5. 配额审查

| primary_type | 中文含义 | 目标/实际数量 | 审查意见 |
| --- | --- | ---: | --- |
| visual_non_text_evidence | 图形/非文本证据 | 4/4 | 数量满足配额 |
| implicit_rule | 隐式规则 | 4/4 | 数量满足配额 |
| 424_derived_semantics | 424 派生语义 | 4/4 | 数量满足配额 |
| cross_modal_evidence | 跨模态/多证据融合 | 3/3 | 数量满足配额 |
| leg_structure_complexity | 航段结构复杂 | 3/3 | 数量满足配额 |
| ocr_display_quality | OCR/显示质量 | 2/2 | 数量满足配额 |

dominant tag 分布：text_missing_visual_present=4，rule_default_completion_case=4，ca_df_sequence=4，cross_modal_multi_leg=3，wrong_leg_risk=3，display_equivalence_sensitive=2。

hard cases 的 formal300 split 分布：probe=6，development=9，evaluation=5。该分布只用于记录，不作为选择优化目标。

## 6. 最终 20 张 hard cases 审查表

| rank | chart_id | 程序 | split | primary_type | dominant_tag | leg_count | present_fields | 主要选择理由 |
| ---: | --- | --- | --- | --- | --- | ---: | ---: | --- |
| 1 | KAKH_R03 | RNAV (GPS) RWY 03 | probe | 图形/非文本证据 | text_missing_visual_present | 5 | 15 | 文本信息不足，但图形/非文本区域存在关键证据 |
| 2 | KANB_R05 | RNAV (GPS) RWY 05 | development | 图形/非文本证据 | text_missing_visual_present | 5 | 18 | 文本信息不足，但图形/非文本区域存在关键证据 |
| 3 | KAST_R26 | RNAV (GPS) RWY 26 | development | 图形/非文本证据 | text_missing_visual_present | 5 | 15 | 文本信息不足，但图形/非文本区域存在关键证据 |
| 4 | KAPC_I01L | ILS OR LOC Z RWY 01L | probe | 图形/非文本证据 | text_missing_visual_present | 4 | 14 | 文本信息不足，但图形/非文本区域存在关键证据 |
| 5 | KAUS_I18L | ILS OR LOC RWY 18L | development | 隐式规则 | rule_default_completion_case | 4 | 14 | 需要规则默认补全或领域规则参与 |
| 6 | KANJ_R14 | RNAV (GPS) RWY 14 | probe | 隐式规则 | rule_default_completion_case | 4 | 14 | 需要规则默认补全或领域规则参与 |
| 7 | KARV_R18 | RNAV (GPS) RWY 18 | development | 隐式规则 | rule_default_completion_case | 4 | 15 | 需要规则默认补全或领域规则参与 |
| 8 | KARV_R28 | RNAV (GPS) RWY 28 | probe | 隐式规则 | rule_default_completion_case | 4 | 14 | 需要规则默认补全或领域规则参与 |
| 9 | KAPT_R04 | RNAV (GPS) RWY 04 | evaluation | 424 派生语义 | ca_df_sequence | 4 | 13 | 存在 CA→DF 等 424 path terminator 序列语义 |
| 10 | KAVQ_R21 | RNAV (GPS) RWY 21 | evaluation | 424 派生语义 | ca_df_sequence | 4 | 13 | 存在 CA→DF 等 424 path terminator 序列语义 |
| 11 | KBDN_R34 | RNAV (GPS) RWY 34 | probe | 424 派生语义 | ca_df_sequence | 4 | 13 | 存在 CA→DF 等 424 path terminator 序列语义 |
| 12 | KBOS_R32 | RNAV (GPS) RWY 32 | probe | 424 派生语义 | ca_df_sequence | 4 | 13 | 存在 CA→DF 等 424 path terminator 序列语义 |
| 13 | KBUR_R08-Z | RNAV (GPS) Z RWY 08 | evaluation | 跨模态/多证据融合 | cross_modal_multi_leg | 4 | 14 | 需要跨区域、多证据或多航段整合 |
| 14 | KAOO_R03-Z | RNAV (GPS) Z RWY 03 | development | 跨模态/多证据融合 | cross_modal_multi_leg | 4 | 13 | 需要跨区域、多证据或多航段整合 |
| 15 | KAOO_R21 | RNAV (GPS) RWY 21 | development | 跨模态/多证据融合 | cross_modal_multi_leg | 4 | 13 | 需要跨区域、多证据或多航段整合 |
| 16 | KCOI_R11 | RNAV (GPS) RWY 11 | development | 航段结构复杂 | wrong_leg_risk | 4 | 13 | 字段容易绑定到错误航段，存在航段对齐风险 |
| 17 | KABE_R13 | RNAV (GPS) RWY 13 | development | 航段结构复杂 | wrong_leg_risk | 4 | 13 | 字段容易绑定到错误航段，存在航段对齐风险 |
| 18 | KABE_R24 | RNAV (GPS) RWY 24 | evaluation | 航段结构复杂 | wrong_leg_risk | 4 | 13 | 字段容易绑定到错误航段，存在航段对齐风险 |
| 19 | KBUR_L08-Z | ILS Z OR LOC Z RWY 08 | evaluation | OCR/显示质量 | display_equivalence_sensitive | 4 | 14 | 航向/径向等显示形式对评分等价规则敏感 |
| 20 | KCJR_L04 | LOC RWY 04 | development | OCR/显示质量 | display_equivalence_sensitive | 4 | 14 | 航向/径向等显示形式对评分等价规则敏感 |

## 7. 逐张审查说明

### 1. KAKH_R03：RNAV (GPS) RWY 03

- 类型：图形/非文本证据（visual_non_text_evidence）
- dominant tag：text_missing_visual_present（文本信息不足，但图形/非文本区域存在关键证据）
- split / procedure：probe / RNAV
- 结构摘要：leg_count=5，present_field_count=15，key_not_applicable_count=15，direct_route_count=3
- 证据计数：rule_default_completion=8，insufficient_for_encoding=5，direct_visible=13，visible_joint=1
- 证据来源计数：ma_text=7，plan_view=2，chart_text=4
- 难度分：difficulty_score=42，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入图形/非文本证据类，核心依据是人工证据派生标签显示：仅靠 missed approach 文本不足，需要从图形、plan view 或其他非纯文本区域获得关键证据。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 看 missed approach 文本是否不足以独立恢复关键字段。
  - 检查 plan view / profile / 图形区域是否提供了文字段落没有直接给出的证据。
  - 确认该样本不是单纯 OCR 失败导致的困难。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 2. KANB_R05：RNAV (GPS) RWY 05

- 类型：图形/非文本证据（visual_non_text_evidence）
- dominant tag：text_missing_visual_present（文本信息不足，但图形/非文本区域存在关键证据）
- split / procedure：development / RNAV
- 结构摘要：leg_count=5，present_field_count=18，key_not_applicable_count=12，direct_route_count=3
- 证据计数：rule_default_completion=8，insufficient_for_encoding=6，direct_visible=17，visible_joint=1
- 证据来源计数：ma_text=9，plan_view=2，chart_text=6
- 难度分：difficulty_score=42，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入图形/非文本证据类，核心依据是人工证据派生标签显示：仅靠 missed approach 文本不足，需要从图形、plan view 或其他非纯文本区域获得关键证据。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 看 missed approach 文本是否不足以独立恢复关键字段。
  - 检查 plan view / profile / 图形区域是否提供了文字段落没有直接给出的证据。
  - 确认该样本不是单纯 OCR 失败导致的困难。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 3. KAST_R26：RNAV (GPS) RWY 26

- 类型：图形/非文本证据（visual_non_text_evidence）
- dominant tag：text_missing_visual_present（文本信息不足，但图形/非文本区域存在关键证据）
- split / procedure：development / RNAV
- 结构摘要：leg_count=5，present_field_count=15，key_not_applicable_count=15，direct_route_count=3
- 证据计数：rule_default_completion=8，insufficient_for_encoding=5，direct_visible=13，visible_joint=1
- 证据来源计数：ma_text=7，plan_view=2，chart_text=4
- 难度分：difficulty_score=42，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入图形/非文本证据类，核心依据是人工证据派生标签显示：仅靠 missed approach 文本不足，需要从图形、plan view 或其他非纯文本区域获得关键证据。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 看 missed approach 文本是否不足以独立恢复关键字段。
  - 检查 plan view / profile / 图形区域是否提供了文字段落没有直接给出的证据。
  - 确认该样本不是单纯 OCR 失败导致的困难。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 4. KAPC_I01L：ILS OR LOC Z RWY 01L

- 类型：图形/非文本证据（visual_non_text_evidence）
- dominant tag：text_missing_visual_present（文本信息不足，但图形/非文本区域存在关键证据）
- split / procedure：probe / ILS
- 结构摘要：leg_count=4，present_field_count=14，key_not_applicable_count=10，direct_route_count=2
- 证据计数：rule_default_completion=9，insufficient_for_encoding=6，direct_visible=14，visible_joint=1
- 证据来源计数：ma_text=8，plan_view=2，chart_text=4
- 难度分：difficulty_score=42，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入图形/非文本证据类，核心依据是人工证据派生标签显示：仅靠 missed approach 文本不足，需要从图形、plan view 或其他非纯文本区域获得关键证据。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 看 missed approach 文本是否不足以独立恢复关键字段。
  - 检查 plan view / profile / 图形区域是否提供了文字段落没有直接给出的证据。
  - 确认该样本不是单纯 OCR 失败导致的困难。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 5. KAUS_I18L：ILS OR LOC RWY 18L

- 类型：隐式规则（implicit_rule）
- dominant tag：rule_default_completion_case（需要规则默认补全或领域规则参与）
- split / procedure：development / ILS
- 结构摘要：leg_count=4，present_field_count=14，key_not_applicable_count=10，direct_route_count=0
- 证据计数：rule_default_completion=10，insufficient_for_encoding=4，direct_visible=14，visible_joint=1
- 证据来源计数：ma_text=8，plan_view=2，chart_text=4
- 难度分：difficulty_score=49，evidence=5，reasoning=14，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入隐式规则类，核心依据是存在 rule_default_completion / rule_default_case 等标签，说明部分字段不是图上直接逐字给出，而需要按 FAA/424 规则补全。
- 相关 tags：applicability_boundary_high、cross_modal_multi_leg、cross_modal_required、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial、has_hm_leg、has_holding、implicit_hold_time 等 21 个
- 人工审查要点：
  - 确认是否存在图上未显式写出、但 424/canonical 需要通过规则补齐的字段。
  - 确认 rule_default_completion_case 不是标注噪声。
  - 确认规则补全不会泄漏 target，只是定义样本困难类型。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 6. KANJ_R14：RNAV (GPS) RWY 14

- 类型：隐式规则（implicit_rule）
- dominant tag：rule_default_completion_case（需要规则默认补全或领域规则参与）
- split / procedure：probe / RNAV
- 结构摘要：leg_count=4，present_field_count=14，key_not_applicable_count=10，direct_route_count=2
- 证据计数：rule_default_completion=7，insufficient_for_encoding=5，direct_visible=12，visible_joint=1
- 证据来源计数：ma_text=6，plan_view=2，chart_text=4
- 难度分：difficulty_score=49，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入隐式规则类，核心依据是存在 rule_default_completion / rule_default_case 等标签，说明部分字段不是图上直接逐字给出，而需要按 FAA/424 规则补全。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 确认是否存在图上未显式写出、但 424/canonical 需要通过规则补齐的字段。
  - 确认 rule_default_completion_case 不是标注噪声。
  - 确认规则补全不会泄漏 target，只是定义样本困难类型。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 7. KARV_R18：RNAV (GPS) RWY 18

- 类型：隐式规则（implicit_rule）
- dominant tag：rule_default_completion_case（需要规则默认补全或领域规则参与）
- split / procedure：development / RNAV
- 结构摘要：leg_count=4，present_field_count=15，key_not_applicable_count=9，direct_route_count=2
- 证据计数：rule_default_completion=7，insufficient_for_encoding=5，direct_visible=13，visible_joint=1
- 证据来源计数：ma_text=7，plan_view=2，chart_text=4
- 难度分：difficulty_score=49，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入隐式规则类，核心依据是存在 rule_default_completion / rule_default_case 等标签，说明部分字段不是图上直接逐字给出，而需要按 FAA/424 规则补全。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 确认是否存在图上未显式写出、但 424/canonical 需要通过规则补齐的字段。
  - 确认 rule_default_completion_case 不是标注噪声。
  - 确认规则补全不会泄漏 target，只是定义样本困难类型。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 8. KARV_R28：RNAV (GPS) RWY 28

- 类型：隐式规则（implicit_rule）
- dominant tag：rule_default_completion_case（需要规则默认补全或领域规则参与）
- split / procedure：probe / RNAV
- 结构摘要：leg_count=4，present_field_count=14，key_not_applicable_count=10，direct_route_count=2
- 证据计数：rule_default_completion=7，insufficient_for_encoding=5，direct_visible=12，visible_joint=1
- 证据来源计数：ma_text=6，plan_view=2，chart_text=4
- 难度分：difficulty_score=49，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入隐式规则类，核心依据是存在 rule_default_completion / rule_default_case 等标签，说明部分字段不是图上直接逐字给出，而需要按 FAA/424 规则补全。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 确认是否存在图上未显式写出、但 424/canonical 需要通过规则补齐的字段。
  - 确认 rule_default_completion_case 不是标注噪声。
  - 确认规则补全不会泄漏 target，只是定义样本困难类型。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 9. KAPT_R04：RNAV (GPS) RWY 04

- 类型：424 派生语义（424_derived_semantics）
- dominant tag：ca_df_sequence（存在 CA→DF 等 424 path terminator 序列语义）
- split / procedure：evaluation / RNAV
- 结构摘要：leg_count=4，present_field_count=13，key_not_applicable_count=11，direct_route_count=2
- 证据计数：rule_default_completion=7，insufficient_for_encoding=4，direct_visible=11，visible_joint=1
- 证据来源计数：ma_text=6，plan_view=1，chart_text=4
- 难度分：difficulty_score=42，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入 424 派生语义类，核心依据是存在 CA→DF 或 terminator-derived 等结构，模型需要理解航图表达如何投影到 424 path terminator / leg 语义。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 确认图上程序结构确实对应 CA→DF 或 terminator-derived 语义。
  - 检查难点是否来自航图到 424 编码的投影，而非模型单次输出格式错误。
  - 确认 primary_type 不是被其他类型更好解释。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 10. KAVQ_R21：RNAV (GPS) RWY 21

- 类型：424 派生语义（424_derived_semantics）
- dominant tag：ca_df_sequence（存在 CA→DF 等 424 path terminator 序列语义）
- split / procedure：evaluation / RNAV
- 结构摘要：leg_count=4，present_field_count=13，key_not_applicable_count=11，direct_route_count=2
- 证据计数：rule_default_completion=7，insufficient_for_encoding=3，direct_visible=12，visible_joint=1
- 证据来源计数：ma_text=7，plan_view=2，chart_text=3
- 难度分：difficulty_score=42，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入 424 派生语义类，核心依据是存在 CA→DF 或 terminator-derived 等结构，模型需要理解航图表达如何投影到 424 path terminator / leg 语义。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 确认图上程序结构确实对应 CA→DF 或 terminator-derived 语义。
  - 检查难点是否来自航图到 424 编码的投影，而非模型单次输出格式错误。
  - 确认 primary_type 不是被其他类型更好解释。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 11. KBDN_R34：RNAV (GPS) RWY 34

- 类型：424 派生语义（424_derived_semantics）
- dominant tag：ca_df_sequence（存在 CA→DF 等 424 path terminator 序列语义）
- split / procedure：probe / RNAV
- 结构摘要：leg_count=4，present_field_count=13，key_not_applicable_count=11，direct_route_count=2
- 证据计数：rule_default_completion=7，insufficient_for_encoding=4，direct_visible=11，visible_joint=1
- 证据来源计数：ma_text=6，plan_view=2，chart_text=3
- 难度分：difficulty_score=42，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入 424 派生语义类，核心依据是存在 CA→DF 或 terminator-derived 等结构，模型需要理解航图表达如何投影到 424 path terminator / leg 语义。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 确认图上程序结构确实对应 CA→DF 或 terminator-derived 语义。
  - 检查难点是否来自航图到 424 编码的投影，而非模型单次输出格式错误。
  - 确认 primary_type 不是被其他类型更好解释。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 12. KBOS_R32：RNAV (GPS) RWY 32

- 类型：424 派生语义（424_derived_semantics）
- dominant tag：ca_df_sequence（存在 CA→DF 等 424 path terminator 序列语义）
- split / procedure：probe / RNAV
- 结构摘要：leg_count=4，present_field_count=13，key_not_applicable_count=11，direct_route_count=2
- 证据计数：rule_default_completion=7，insufficient_for_encoding=4，direct_visible=11，visible_joint=1
- 证据来源计数：ma_text=6，plan_view=1，chart_text=4
- 难度分：difficulty_score=42，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入 424 派生语义类，核心依据是存在 CA→DF 或 terminator-derived 等结构，模型需要理解航图表达如何投影到 424 path terminator / leg 语义。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 确认图上程序结构确实对应 CA→DF 或 terminator-derived 语义。
  - 检查难点是否来自航图到 424 编码的投影，而非模型单次输出格式错误。
  - 确认 primary_type 不是被其他类型更好解释。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 13. KBUR_R08-Z：RNAV (GPS) Z RWY 08

- 类型：跨模态/多证据融合（cross_modal_evidence）
- dominant tag：cross_modal_multi_leg（需要跨区域、多证据或多航段整合）
- split / procedure：evaluation / RNAV
- 结构摘要：leg_count=4，present_field_count=14，key_not_applicable_count=10，direct_route_count=2
- 证据计数：rule_default_completion=7，insufficient_for_encoding=4，direct_visible=12，visible_joint=1
- 证据来源计数：ma_text=7，plan_view=2，chart_text=3
- 难度分：difficulty_score=43，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入跨模态/多证据融合类，核心依据是存在 cross_modal_required / visible_joint / multi-leg 等标签，字段证据需要跨区域合并，而不是单一文本片段即可决定。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 检查关键字段是否需要多个区域/证据共同支持。
  - 确认不是只看 missed approach paragraph 就能完成。
  - 确认跨区域证据与多航段结构确实会增加理解负担。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 14. KAOO_R03-Z：RNAV (GPS) Z RWY 03

- 类型：跨模态/多证据融合（cross_modal_evidence）
- dominant tag：cross_modal_multi_leg（需要跨区域、多证据或多航段整合）
- split / procedure：development / RNAV
- 结构摘要：leg_count=4，present_field_count=13，key_not_applicable_count=11，direct_route_count=2
- 证据计数：rule_default_completion=7，insufficient_for_encoding=4，direct_visible=11，visible_joint=1
- 证据来源计数：ma_text=6，plan_view=2，chart_text=3
- 难度分：difficulty_score=43，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入跨模态/多证据融合类，核心依据是存在 cross_modal_required / visible_joint / multi-leg 等标签，字段证据需要跨区域合并，而不是单一文本片段即可决定。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 检查关键字段是否需要多个区域/证据共同支持。
  - 确认不是只看 missed approach paragraph 就能完成。
  - 确认跨区域证据与多航段结构确实会增加理解负担。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 15. KAOO_R21：RNAV (GPS) RWY 21

- 类型：跨模态/多证据融合（cross_modal_evidence）
- dominant tag：cross_modal_multi_leg（需要跨区域、多证据或多航段整合）
- split / procedure：development / RNAV
- 结构摘要：leg_count=4，present_field_count=13，key_not_applicable_count=11，direct_route_count=2
- 证据计数：rule_default_completion=7，insufficient_for_encoding=4，direct_visible=11，visible_joint=1
- 证据来源计数：ma_text=6，plan_view=2，chart_text=3
- 难度分：difficulty_score=43，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入跨模态/多证据融合类，核心依据是存在 cross_modal_required / visible_joint / multi-leg 等标签，字段证据需要跨区域合并，而不是单一文本片段即可决定。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 检查关键字段是否需要多个区域/证据共同支持。
  - 确认不是只看 missed approach paragraph 就能完成。
  - 确认跨区域证据与多航段结构确实会增加理解负担。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 16. KCOI_R11：RNAV (GPS) RWY 11

- 类型：航段结构复杂（leg_structure_complexity）
- dominant tag：wrong_leg_risk（字段容易绑定到错误航段，存在航段对齐风险）
- split / procedure：development / RNAV
- 结构摘要：leg_count=4，present_field_count=13，key_not_applicable_count=11，direct_route_count=2
- 证据计数：rule_default_completion=7，insufficient_for_encoding=4，direct_visible=11，visible_joint=1
- 证据来源计数：ma_text=6，plan_view=2，chart_text=3
- 难度分：difficulty_score=46，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入航段结构复杂类，核心依据是多航段、CA/HM/DF 等结构和 wrong_leg_risk 标签，风险在于字段值可能被抽对但绑定到错误航段。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 检查 leg_count、CA/HM/DF 等结构是否使航段绑定有歧义。
  - 看字段是否可能被抽到正确值但放到错误 leg。
  - 确认它代表结构难度，而不是单个字段显示差异。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 17. KABE_R13：RNAV (GPS) RWY 13

- 类型：航段结构复杂（leg_structure_complexity）
- dominant tag：wrong_leg_risk（字段容易绑定到错误航段，存在航段对齐风险）
- split / procedure：development / RNAV
- 结构摘要：leg_count=4，present_field_count=13，key_not_applicable_count=11，direct_route_count=2
- 证据计数：rule_default_completion=7，insufficient_for_encoding=4，direct_visible=11，visible_joint=1
- 证据来源计数：ma_text=6，plan_view=2，chart_text=3
- 难度分：difficulty_score=46，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入航段结构复杂类，核心依据是多航段、CA/HM/DF 等结构和 wrong_leg_risk 标签，风险在于字段值可能被抽对但绑定到错误航段。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 检查 leg_count、CA/HM/DF 等结构是否使航段绑定有歧义。
  - 看字段是否可能被抽到正确值但放到错误 leg。
  - 确认它代表结构难度，而不是单个字段显示差异。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 18. KABE_R24：RNAV (GPS) RWY 24

- 类型：航段结构复杂（leg_structure_complexity）
- dominant tag：wrong_leg_risk（字段容易绑定到错误航段，存在航段对齐风险）
- split / procedure：evaluation / RNAV
- 结构摘要：leg_count=4，present_field_count=13，key_not_applicable_count=11，direct_route_count=2
- 证据计数：rule_default_completion=7，insufficient_for_encoding=4，direct_visible=11，visible_joint=1
- 证据来源计数：ma_text=6，plan_view=2，chart_text=3
- 难度分：difficulty_score=46，evidence=5，reasoning=16，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入航段结构复杂类，核心依据是多航段、CA/HM/DF 等结构和 wrong_leg_risk 标签，风险在于字段值可能被抽对但绑定到错误航段。
- 相关 tags：applicability_boundary_high、ca_df_sequence、ca_df_with_high_applicability_boundary、cross_modal_multi_leg、cross_modal_required、direct_route_semantic、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial 等 24 个
- 人工审查要点：
  - 检查 leg_count、CA/HM/DF 等结构是否使航段绑定有歧义。
  - 看字段是否可能被抽到正确值但放到错误 leg。
  - 确认它代表结构难度，而不是单个字段显示差异。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 19. KBUR_L08-Z：ILS Z OR LOC Z RWY 08

- 类型：OCR/显示质量（ocr_display_quality）
- dominant tag：display_equivalence_sensitive（航向/径向等显示形式对评分等价规则敏感）
- split / procedure：evaluation / LOC
- 结构摘要：leg_count=4，present_field_count=14，key_not_applicable_count=10，direct_route_count=0
- 证据计数：rule_default_completion=9，insufficient_for_encoding=4，direct_visible=14，visible_joint=1
- 证据来源计数：ma_text=8，plan_view=2，chart_text=4
- 难度分：difficulty_score=46，evidence=5，reasoning=14，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入 OCR/显示质量类，核心依据是 display_equivalence_sensitive，尤其是航向、航迹、径向的小数/整数显示形式容易造成严格字符串评分差异。
- 相关 tags：applicability_boundary_high、cross_modal_multi_leg、cross_modal_required、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial、has_hm_leg、has_holding、implicit_hold_time 等 21 个
- 人工审查要点：
  - 检查航向/径向/holding inbound course 等字段是否存在整数/小数显示等价问题。
  - 确认困难主要是显示/识别形式，而不是 424 语义或多证据融合。
  - 确认 OCR/显示质量类数量保持少量，不主导实验组3。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

### 20. KCJR_L04：LOC RWY 04

- 类型：OCR/显示质量（ocr_display_quality）
- dominant tag：display_equivalence_sensitive（航向/径向等显示形式对评分等价规则敏感）
- split / procedure：development / LOC
- 结构摘要：leg_count=4，present_field_count=14，key_not_applicable_count=10，direct_route_count=0
- 证据计数：rule_default_completion=8，insufficient_for_encoding=5，direct_visible=15，visible_joint=1
- 证据来源计数：ma_text=7，plan_view=1，chart_text=7
- 难度分：difficulty_score=46，evidence=5，reasoning=14，structure=8
- 图像审查：已在本地审查缓存完成；仓库冻结包不包含图像文件或图像路径。
- 为什么选它：该样本被归入 OCR/显示质量类，核心依据是 display_equivalence_sensitive，尤其是航向、航迹、径向的小数/整数显示形式容易造成严格字符串评分差异。
- 相关 tags：applicability_boundary_high、cross_modal_multi_leg、cross_modal_required、display_equivalence_sensitive、has_altitude_constraint、has_ca_leg、has_course_radial、has_hm_leg、has_holding、implicit_hold_time 等 21 个
- 人工审查要点：
  - 检查航向/径向/holding inbound course 等字段是否存在整数/小数显示等价问题。
  - 确认困难主要是显示/识别形式，而不是 424 语义或多证据融合。
  - 确认 OCR/显示质量类数量保持少量，不主导实验组3。
- 审查结论栏：同意 / 不同意 / 需要替换。若不同意，需说明是 primary_type 错、dominant_tag 错，还是该图不应进入 hard 10%。

## 8. core vs hard 初步结果说明

下表是 hard cases 选定之后才 join 的实验组1结果，只用于解释，不参与难例选择。bootstrap 结果由后续流程另行补充。

| method | split | correct | total | row_count | missing | accuracy |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| A1 | core | 1015 | 3534 | 180 | 0 | 28.72% |
| A1 | hard | 169 | 518 | 20 | 0 | 32.63% |
| A2 | core | 802 | 3534 | 180 | 0 | 22.69% |
| A2 | hard | 114 | 518 | 20 | 0 | 22.01% |
| B1 | core | 978 | 3534 | 180 | 0 | 27.67% |
| B1 | hard | 132 | 518 | 20 | 0 | 25.48% |
| B1_prime | core | 1138 | 3534 | 180 | 0 | 32.20% |
| B1_prime | hard | 170 | 518 | 20 | 0 | 32.82% |
| B1_prime_link | core | 634 | 3321 | 171 | 9 | 19.09% |
| B1_prime_link | hard | 84 | 362 | 14 | 6 | 23.20% |
| C1 | core | 1410 | 3534 | 180 | 0 | 39.90% |
| C1 | hard | 186 | 518 | 20 | 0 | 35.91% |
| C2 | core | 956 | 3534 | 180 | 0 | 27.05% |
| C2 | hard | 118 | 518 | 20 | 0 | 22.78% |
| C3 | core | 1396 | 3458 | 176 | 4 | 40.37% |
| C3 | hard | 197 | 518 | 20 | 0 | 38.03% |
| C4 | core | 1389 | 3534 | 180 | 0 | 39.30% |
| C4 | hard | 249 | 518 | 20 | 0 | 48.07% |
| D_SFT | core | 2697 | 3256 | 166 | 14 | 82.83% |
| D_SFT | hard | 213 | 468 | 18 | 2 | 45.51% |

解释时需要注意：

- C4 在当前 hard set 上高于 core，不代表 hard set 设计错误；它可能说明 C4 对某些结构化/多证据难点更稳，也可能需要 bootstrap 检查不确定性。
- D_SFT 在 hard set 上明显下降，说明 SFT 方法虽然总体强，但对 curated hard cases 的鲁棒性仍需单独报告。
- B1_prime_link、C3、D_SFT 存在 missing score，分析表中保留 missing，不参与难例选择。

## 9. 冻结前必须确认的问题

1. 20 张 hard cases 是否都能在图上找到与 primary_type 对应的真实困难。
2. dominant_tag 是否代表该图的主要困难，而不是次要困难。
3. OCR/显示质量类只占 2 张，是否符合“不让实验组3变成 OCR 专项分析”的要求。
4. 424 派生语义类的 CA→DF / terminator-derived 是否确实来自程序结构，而非转换脚本误判。
5. 跨模态/多证据类是否确实需要跨区域证据，不是单一 missed approach paragraph 可直接确定。
6. 航段结构复杂类是否确实存在 field-to-leg binding 风险。
7. 是否有明显应该进入 hard 10% 但被排除的样本。

## 10. 冻结建议

如果人工审查接受上述 20 张 hard cases 和 6 类配额，则实验组3可以冻结以下内容：

- formal200 candidate pool：实验组1实际 200 张。
- final_hard_case_count：20 张，即 10%。
- hard-case primary type 配额：4/4/4/3/3/2。
- challenge tag 生成来源：target-derived、comparison-policy-derived、annotation-field-review-derived。
- core vs hard join 口径：选定 hard cases 后再 join 实验组1分数。
- bootstrap 输入：使用已提交 PR #37 的 Group3 derived row-level scores，由 bootstrap 流程单独执行。

若任一 hard case 被人工否决，应优先在同一 primary_type 候选中替换，保持 20/200 和类型配额不变。
