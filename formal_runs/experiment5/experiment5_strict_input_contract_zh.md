# Experiment 5 strict 输入契约

日期：2026-05-04

## 实验目标

Experiment 5 的目标是回答：FAA chart 到 ARINC 424 失败主要来自哪里。

正式实验必须把不同信息源拆开，分别观察 OCR/文本、区域识别、候选生成、证据绑定、规则/模型推理对结果的影响。方法输入不能提前包含最终字段答案，否则实验会变成 oracle 上界，不再能做失败归因。

## 全局禁止输入

任何正式方法输入中都禁止出现或由以下内容派生：

- `annotation_pr28_json`
- `target`
- `score`
- `canonical_answer`
- `canonical_leg_index`
- `Q_terminator`
- `leg_type`
- `field_review_v2`
- 最终 canonical JSON
- 最终字段答案表
- 用最终答案重写的 missed approach prose
- 用最终答案生成的 field candidates

仅删除这些键名不够；如果值本身来自这些字段，也视为泄漏。

## 全局允许输入

允许使用来自图面或人工审核证据层的内容：

- chart id、procedure id、airport 等非答案元数据
- region id
- region type
- region bbox
- region source / annotation scope
- 原始 OCR 文本
- 人工校正的图面可见文本
- 图上可见 label 的 literal 部分
- 图上可见图元类型，例如 climb arrow、fix symbol、holding pattern 等
- evidence region id
- region 与 evidence 的关系，只要关系不直接包含最终字段答案

## label 使用规则

后台中的 label 有两种情况：

1. 纯可见文本或图元标签，例如 `FIX_TEXT: BRA`、`ALTITUDE_TEXT: 5400`。
2. 可见文本后面带了解释结果，例如 `ALTITUDE_TEXT: 5400 -> AT_OR_ABOVE 5400 ft`。

strict 输入只能使用 `->` 左侧的可见部分：

- `ALTITUDE_TEXT: 5400 -> AT_OR_ABOVE 5400 ft` 只能使用 `ALTITUDE_TEXT: 5400`
- `FIX_TEXT: BRA -> BRA` 只能使用 `FIX_TEXT: BRA`
- `HEADING_TEXT: 080° -> type=course_deg, course_deg=80.0` 只能使用 `HEADING_TEXT: 080°`
- `RADIAL_TEXT: R-045 -> type=navaid_radial, ...` 只能使用 `RADIAL_TEXT: R-045`

`->` 右侧是解释后的候选/答案信息，不能作为 strict 方法输入。

## 方法输入契约

### A3：gold MA text

目的：测试当 missed approach 文本已经正确时，模型能不能从文本生成 424。

允许输入：

- 图面 MA_TEXT 区域中的 OCR 文本
- 对该 OCR 文本做的人工校正
- 人工从图上直接抄录的 missed approach prose

禁止输入：

- 从 `annotation_pr28_json` 或最终字段答案反写出来的 prose
- 来自 profile/detail 区域的最终结构化字段

如果后台只有 MA_TEXT bbox、没有文本，则 A3 strict 输入状态为 `blocked_missing_visible_ma_text`，不能正式运行。

### B2：MA text + parsing aids

目的：在真实 MA_TEXT 文本基础上加入非答案辅助信息，测试文本解析改善。

允许输入：

- A3 的合法 MA_TEXT 文本
- 非答案元数据
- 与文本区域相关的 bbox/provenance

禁止输入：

- 最终字段答案
- 由最终答案生成的候选字段

如果 A3 文本不存在，B2 也不能正式运行。

### B3_T：ROI text only

目的：测试只给区域文本时的表现。

允许输入：

- MA_TEXT、PLAN、PROFILE、DETAIL 等 ROI 的真实 OCR/人工校正文本文字
- region bbox/type/provenance

禁止输入：

- 由最终答案反写的文本
- `canonical_answer` 生成的字段候选

如果 ROI 只有 bbox 没有文本，则该样本状态为 `blocked_missing_roi_text` 或 `partial_missing_roi_text`。

### B3_PD：plan/detail observable candidates

目的：测试图面 plan/detail 框、图元和可见文字候选对失败归因的贡献。

允许输入：

- region bbox/type
- 可见 label 左侧文本
- 图元类型，例如 climb arrow、fix symbol
- evidence region id
- review_action 作为证据状态标记

禁止输入：

- label `->` 右侧的解释结果
- `canonical_answer`
- leg index、terminator、leg type、最终字段名

### B3_TPD / B4_TPD

目的：组合文本 ROI 与 plan/detail observable candidates，观察融合输入效果。

允许输入：

- B3_T 的合法 ROI 文本
- B3_PD 的合法可见候选
- bbox/evidence provenance

禁止输入：

- answer-derived prose
- answer-derived candidates

如果文本侧缺失但 PD 侧存在，状态必须标记为 `partial_missing_text`，不能伪装成完整 TPD。

### G：gold observable facts

目的：测试在“可观察事实已经人工审核”的条件下，模型/规则能否组织成 424。

允许输入：

- 从人工框和证据关系中得到的可观察事实
- 可见文本 literal
- 图元类型
- bbox/evidence provenance

条件限制：

- 不允许携带最终字段名、leg index、terminator、leg_type。
- 不允许携带由 `canonical_answer` 直接生成的值。
- 如果事实值来自后台 label 的 `->` 右侧或 field_review 的 `canonical_answer`，必须剔除或标记为不合格。

## provenance 必填项

每一条 strict 输入事实至少要能追踪：

- `source_file`
- `source_field`
- `source_region_id`
- `source_type`
- `review_action`
- `transform`
- `derived_from_final_answer`

其中 `derived_from_final_answer` 必须是 `false` 才能进入正式方法输入。

## 跑模型前的 gate

dev50 模型运行前必须满足：

1. 生成 no-leakage provenance 报告。
2. 抽样展示输入给人工确认。
3. 报告中 forbidden key scan 为 0。
4. 报告中 answer-derived value scan 为 0。
5. 每个方法都明确标记 ready / partial / blocked。
6. blocked 的方法不能拿去报告正式分数。
