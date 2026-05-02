# B1 Pilot Prompt v1 中文候选版：完整航图 OCR 到 Canonical JSON

## 实验定位

你执行的是 paper-v2 的 B1 baseline：


完整未遮盖 FAA approach chart 图像
  -> 预先生成的完整航图 OCR 全文
  -> LLM
  -> canonical JSON

B1 的研究目的，是测试文本大模型能否仅从完整航图 OCR 全文中组合 missed approach 程序语义。B1 不应获得自动字段候选、ROI、bbox、CIFP 或 target 信息；这些属于其他实验分支。

## 规范来源与继承关系

本 prompt 仍然定义同一个 paper-v2 B1 方法，不引入新方法、不改变实验计划中的 B1 边界。B1 对应：


full-chart OCR -> LLM -> canonical JSON

本 prompt 必须继承并严格执行以下既有规范：

- Issue #11：B1 是 `OCR + LLM`，输出统一 leg-level JSON；LLM 原始输出和解析后 JSON 都必须保存。
- PR #28：canonical leg-level schema；所有方法输出和 CIFP-derived proxy GT 共享同一个 canonical schema。
- Issue #6：字段状态规则为 `present`、`not_applicable`、`not_observable`、`unknown`。
- Issue #19：大模型提示词必须允许 `unknown` / `not_observable`，不得在证据不足时硬猜。
- PV2-03：方法、prompt hash、parser repair、rerun policy 必须记录，不能看到结果后改方法。
- PV2-08：实验组 1 中 B1 是 `OCR->LLM->canonical JSON` 主抽取方法，必须保存 raw / parsed / final，并记录 invalid、parser repair 和失败原因。

因此，本 prompt 的约束只用于落实既有协议，不允许引入字段匹配、ROI、CIFP、target、人工答案、历史输出或 parser 语义修复。

## 与其他实验的边界

- 不要执行 A1 的规则系统。
- 不要使用 B1′ 的自动字段匹配候选。
- 不要使用 B2/B3 的人工校正复飞文本、ROI 或区域 OCR。
- 不要使用 C 组方法的图像输入。
- 不要使用 domain-rule prompt 中的扩展领域规则；该变体后续单独评估。

## 允许输入

仅允许使用以下输入：

- `chart_id`
- `airport`
- `approach_ident`
- `chart_name`
- 完整航图 OCR 全文
- 本 prompt 中定义的 canonical 输出契约

## 禁止输入

不得使用以下任何信息：

- 航图图像像素
- OCR bbox、坐标、区域标签、ROI、prelabel 或人工标注框
- 自动字段候选、字段匹配结果、gold observable evidence
- CIFP、ARINC 424 或任何原始导航数据库记录
- canonical proxy target JSON、answer key、scorer 输出
- 人工标注、人工校正文本、人工字段对应
- 同一张航图的历史模型输出
- 除 manifest metadata 外，从图像文件名或 PDF 文件名推断出的信息
- 外部航空数据库或网页搜索

## 任务

仅根据 OCR 全文，抽取发布航图中的 missed approach procedure，并输出 canonical JSON。

输出必须描述复飞程序的有序 leg 序列。若 OCR 文本缺失、损坏、有歧义或相互冲突，使用 `unknown`，不要猜测。

## Status 枚举

每个 answer 的 `status` 必须是以下四个之一：

- `present`
- `not_applicable`
- `not_observable`
- `unknown`

不要输出 `invalid`。`invalid` 只由 validator 或 scorer 在输出不合法时标记。

## Status 判定规则

- 使用 `present`：OCR 文本明确支持该值，或该值来自本 prompt 明确允许的结构性约定。
- 使用 `not_applicable`：该字段对当前 leg 类型没有结构意义。
- 使用 `not_observable`：字段理论上可能适用，但允许输入中有足够上下文判断该字段没有可观测证据；不得把 OCR 损坏或 OCR 漏识别当作 `not_observable`。
- 使用 `unknown`：OCR 缺失、损坏、顺序混乱、字符歧义、字段冲突，或无法可靠确定 leg 切分、terminator、fix、course、altitude、hold 参数。

B1 特别规则：

- OCR 没有识别到某信息时，通常应为 `unknown`，不是 `not_observable`。
- 不要为了补全 schema 而编造 ARINC terminator、fix、course、radial、altitude 或 hold 参数。
- 如果不确定 leg_count，输出 `leg_count.status = "unknown"`，`leg_count.value = null`，`legs = []`。

## Status 与 value 联动规则

每个 answer 必须满足以下联动规则：

- 当 `status = "present"` 时，`value` 必须是该字段允许的具体合法值。
- 当 `status = "not_applicable"` 时，`value` 必须为 `null`。
- 当 `status = "not_observable"` 时，`value` 必须为 `null`。
- 当 `status = "unknown"` 时，`value` 必须为 `null`。
- 不得在 `status` 不是 `present` 时填入猜测值。
- 不得用类型词、说明词或占位符替代真实字段值。

## 允许的最小结构性约定

这些约定属于 schema 输出结构，不属于扩展 domain-rule prompt：

- 非 hold leg 的 `Q5_hold_params` 为 `not_applicable`。
- hold leg 的 `Q3_turn` 为 `not_applicable`，因为 hold turn 属于 `Q5_hold_params`。
- Q1 的 fix 适用性由 terminator 决定：
  - `CF / DF / TF / AF`：fix 是 terminator fix。
  - `FA / FC / FD / FM`：fix 是 origin fix。
  - `HA / HF / HM`：fix 是 hold fix。
  - `IF`：fix 是 initial fix。
  - `CA / VA / VD / VI / VM / VR / CD / CI / CR / VC / RF / PI`：Q1 为 `not_applicable`。
- Q2 没有 altitude constraint 时为 `not_applicable`。
- Q4 对 hold leg 为 `not_applicable`；hold 的 inbound course 属于 Q5。
- Q5 对非 hold leg 为 `not_applicable`。

不得加入未在本 prompt 中明确写出的额外航空规则。若需要测试额外规则，应使用后续独立的 domain-rule prompt。

## 字段契约

顶层 JSON 必须包含且只包含：

- `chart_id`
- `procedure`
- `missed_approach`

`procedure` 必须包含且只包含：

- `airport`
- `approach_ident`
- `chart_name`

`missed_approach` 必须包含且只包含：

- `leg_count`
- `legs`

`leg_count.status` 只能是：

- `present`
- `not_observable`
- `unknown`

`leg_count.value` 必须是 integer 或 null。

每个 leg 必须包含：

- `leg_index`
- `answers`

`leg_index` 必须严格遵守：

- 第一条 leg 的 `leg_index` 必须是 `1`，不得是 `0`。
- 第二条 leg 的 `leg_index` 必须是 `2`，之后依次连续递增。
- `legs` 数组中的顺序必须与复飞程序飞行顺序一致。
- 当 `leg_count.status = "present"` 时，`leg_count.value` 必须等于 `legs` 数组长度。
- 如果无法可靠确定 leg 数量，必须返回 `leg_count.status = "unknown"`、`leg_count.value = null`、`legs = []`。
- 不得输出非连续编号、重复编号或从 0 开始的编号。

每个 `answers` 必须包含且只包含以下六个字段：

- `Q_terminator`
- `Q1_fix_ident`
- `Q2_altitude_constraint`
- `Q3_turn`
- `Q4_course_or_radial`
- `Q5_hold_params`

## Q 字段取值规则

### Q_terminator

`status` 只能是 `present`、`not_observable` 或 `unknown`。

当 `status = "present"` 时，`value` 必须是以下 ARINC-style code 之一：


CA, CF, CI, CR, DF, FA, FM, HA, HF, HM, IF, RF, TF,
VA, VD, VI, VM, VR, AF, CD, FC, FD, VC, PI

如果不能确定 code，使用 `status = "unknown"`，`value = null`。

### Q1_fix_ident

`status` 可以是 `present`、`not_applicable`、`not_observable` 或 `unknown`。

当 `status = "present"` 时，`value` 是 fix、waypoint 或 navaid ident 字符串，最长 5 个字符。否则 `value = null`。

`Q1_fix_ident.value` 必须是真实 ident，不得是设施类型或泛称：

- 合法示例：`FKL`、`ALS`、`ORL`、`SMYRA`、`RW06`。
- 禁止示例：`VORTAC`、`VOR`、`NDB`、`FIX`、`WAYPOINT`、`NAVAID`、`HOLDING`、`AIRPORT`、`RUNWAY`。
- 如果 OCR 文本写成 `<IDENT> VORTAC`、`<IDENT> VOR/DME`、`<IDENT> VOR`、`<IDENT> NDB` 或 `<IDENT> DME`，只输出前面的 `<IDENT>`，不要输出设施类型。例如 `ORL VORTAC` 的 ident 是 `ORL`，不是 `VORTAC`。
- 如果能看出是某类设施但 OCR 无法可靠读出具体 ident，使用 `status = "unknown"`、`value = null`。
- 如果该 leg 类型没有 fix reference，使用 `status = "not_applicable"`、`value = null`。

### Q2_altitude_constraint

`status` 可以是 `present`、`not_applicable`、`not_observable` 或 `unknown`。

当 `status = "present"` 时，`value` 必须为：


{
  "desc": "AT_OR_ABOVE",
  "altitude_ft": 3000,
  "altitude_2_ft": null
}

`desc` 必须是以下之一：


AT, AT_OR_ABOVE, AT_OR_BELOW, BETWEEN

`altitude_ft` 和 `altitude_2_ft` 必须是 integer 或 null。只有 `desc = "BETWEEN"` 时，`altitude_2_ft` 才应为非 null。

### Q3_turn

`status` 可以是 `present`、`not_applicable`、`not_observable` 或 `unknown`。

当 `status = "present"` 时，`value` 必须是 `LEFT` 或 `RIGHT`。否则 `value = null`。

### Q4_course_or_radial

`status` 可以是 `present`、`not_applicable`、`not_observable` 或 `unknown`。

当 `status = "present"` 时，`value` 必须且只能是以下两种结构之一：


{"type": "course_deg", "course_deg": 70.0}


{"type": "navaid_radial", "navaid": "ABC", "radial_deg": 123.0, "direction": "outbound"}


`direction` 只能是 `outbound` 或 `inbound`。

DF / direct-to-fix 航段没有单独的 Q4 值；直飞含义由 `Q_terminator = DF` 和 `Q1_fix_ident` 表达，Q4 应标为 `not_applicable`。

### Q5_hold_params

`status` 可以是 `present`、`not_applicable`、`not_observable` 或 `unknown`。

当 `status = "present"` 时，`value` 必须为：


{
  "inbound_course_deg": 70.0,
  "leg_time_min": 1.0,
  "leg_distance_nm": null,
  "turn": "RIGHT"
}

`inbound_course_deg`、`leg_time_min`、`leg_distance_nm` 可以是 number 或 null。`turn` 可以是 `LEFT`、`RIGHT` 或 null。

当 OCR 支持 hold time 或 hold distance 时，`leg_time_min` 和 `leg_distance_nm` 应恰好一个为非 null。若 hold 参数无法可靠确定，使用 `status = "unknown"`，`value = null`。

## 输出要求

- 只返回 JSON。
- 输出的第一个字符必须是 `{`。
- 输出的最后一个字符必须是 `}`。
- 你的回答会被程序直接交给 JSON parser；如果输出 markdown code fence、自然语言或前后缀文本，本样本会被判为格式错误或记录 parser repair。
- 回复前必须自检：第一字符是 `{`，最后字符是 `}`，且没有任何 三个反引号。
- 不要包含 markdown。
- 不要包含 markdown code fence。
- 不要输出 三个反引号json 或 三个反引号。
- 不要包含解释。
- 不要包含 evidence snippet。
- 不要包含本契约以外的字段。
- 不要输出占位符。
- 不要输出枚举说明。
- 保持 missed-approach leg 顺序。

## 输入


chart_id: {{chart_id}}
airport: {{airport}}
approach_ident: {{approach_ident}}
chart_name: {{chart_name}}

OCR_TEXT:
{{ocr_text}}
## STRICT RAW OUTPUT CONTRACT / 严格原始输出协议

This section overrides any formatting habit from examples above. The final answer MUST be exactly one bare JSON object.

- The first non-whitespace character MUST be {.
- The last non-whitespace character MUST be }.
- Do NOT output Markdown.
- Do NOT output code fences.
- Do NOT output the string ` anywhere.
- Do NOT output json as a wrapper or label.
- Do NOT add explanation before or after the JSON.
- The evaluator will run strict JSON parsing on the raw response. Any Markdown fence or extra text is a format violation.

