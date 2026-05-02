# C3 Pilot Prompt v1 中文候选版：完整航图图像到结构化问卷

## 实验定位

你执行的是 paper-v2 的 C3 baseline：


完整未遮盖 FAA approach chart 图像
  -> VLM 填固定结构化问卷
  -> deterministic parser
  -> canonical JSON

你的输出只能是结构化 questionnaire JSON。后续由单独 parser 转换为 canonical JSON。

C3 的研究目的，是测试固定问卷表单是否能减少直接 JSON 输出中的格式错误和幻觉。C3 不能接收 OCR 文本、ROI、bbox、CIFP 或 target 信息。

## 规范来源与继承关系

本 prompt 仍然定义同一个 paper-v2 C3 方法，不引入新方法、不改变实验计划中的 C3 边界。C3 对应旧实验命名中的 E / questionnaire extraction：完整航图图像 -> 结构化问卷 -> deterministic parser -> canonical JSON。

本 prompt 必须继承并严格执行以下既有规范：

- PR #28 的 canonical leg-level schema 与 structured questionnaire template。
- Issue #12 的图像输入问卷约束提取方法：保存 raw response、parsed questionnaire JSON、final canonical JSON，且 final JSON 必须可进入统一 validator / scorer。
- Issue #6 的字段状态规则：`present`、`not_applicable`、`not_observable`、`unknown`。
- Issue #19 的大模型提示词规范：图上看不出或无法可靠判断时必须允许 `unknown` / `not_observable`，不得硬猜。
- paper-v2 PV2-08 的实验组 1 要求：C3 是 `questionnaire->JSON` 主抽取方法，输出必须可追溯、可验证、可评分，invalid 必须被记录。

因此，本 prompt 的修订只是在原 C3 方法内强化既有格式约束，不允许引入 OCR、CIFP、target、人工答案、历史输出或 parser 语义修复。

## 与其他实验的边界

- 不要执行 C1 的单次完整 canonical JSON 输出。
- 不要执行 C2 的多轮 QA 聚合协议。
- 不要执行 C4 的图像 + OCR 混合输入。
- 不要使用 B 组方法的 OCR 文本。
- 不要使用 domain-rule prompt 中的扩展领域规则；该变体后续单独评估。

## 允许输入

仅允许使用以下输入：

- `chart_id`
- `airport`
- `approach_ident`
- `chart_name`
- 完整航图图像
- 本 prompt 中定义的 questionnaire 输出契约

## 禁止输入

不得使用以下任何信息：

- 外部 OCR 文本
- OCR bbox、坐标、区域标签、ROI、prelabel 或人工标注框
- 自动字段候选、字段匹配结果、gold observable evidence
- CIFP、ARINC 424 或任何原始导航数据库记录
- canonical proxy target JSON、answer key、scorer 输出
- 人工标注、人工校正文本、人工字段对应
- 同一张航图的历史模型输出
- 除 manifest metadata 外，从图像文件名或 PDF 文件名推断出的信息
- 外部航空数据库或网页搜索

## 任务

直接读取完整航图图像，并填写 missed-approach questionnaire。

可以使用图上可见的 missed-approach text box、plan view、profile view、holding depiction。问卷必须描述复飞程序的有序 leg 序列。

若图像太小、模糊、遮挡、文本不可读、有歧义或相互冲突，使用 `unknown`，不要猜测。

## Status 枚举

每个 answer 的 `status` 必须是以下四个之一：

- `present`
- `not_applicable`
- `not_observable`
- `unknown`

不要输出 `invalid`。`invalid` 只由 validator 或 scorer 在输出不合法时标记。

## Status 判定规则

- 使用 `present`：航图图像明确支持该值，或该值来自本 prompt 明确允许的结构性约定。
- 使用 `not_applicable`：该字段对当前 leg 类型没有结构意义。
- 使用 `not_observable`：字段理论上可能适用，但完整航图图像中没有可观测证据。
- 使用 `unknown`：图像不可读、字段歧义、证据冲突，或无法可靠确定 leg 切分、terminator、fix、course、altitude、hold 参数。

不要为了补全问卷而编造 ARINC terminator、fix、course、radial、altitude 或 hold 参数。

## Status 与 value 联动规则

每个 answer 必须满足以下联动规则：

- 当 `status = "present"` 时，`value` 必须是该字段允许的具体合法值。
- 当 `status = "not_applicable"` 时，`value` 必须为 `null`。
- 当 `status = "not_observable"` 时，`value` 必须为 `null`。
- 当 `status = "unknown"` 时，`value` 必须为 `null`。
- 不得在 `status` 不是 `present` 时填入猜测值。
- 不得用类型词、说明词或占位符替代真实字段值。

## 允许的最小结构性约定

这些约定属于 questionnaire 输出结构，不属于扩展 domain-rule prompt：

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

## Questionnaire 输出契约

顶层 JSON 必须包含且只包含：

- `chart_id`
- `procedure`
- `questionnaire`

`procedure` 必须包含且只包含：

- `airport`
- `approach_ident`
- `chart_name`

`questionnaire` 必须包含且只包含：

- `Q0_leg_count`
- `legs`

`Q0_leg_count.status` 只能是：

- `present`
- `not_observable`
- `unknown`

`Q0_leg_count.value` 必须是 integer 或 null。

每个 questionnaire leg 必须包含：

- `leg_index`
- `Q_terminator`
- `Q1_fix_ident`
- `Q2_altitude_constraint`
- `Q3_turn`
- `Q4_course_or_radial`
- `Q5_hold_params`

`leg_index` 必须严格遵守：

- 第一条 leg 的 `leg_index` 必须是 `1`，不得是 `0`。
- 第二条 leg 的 `leg_index` 必须是 `2`，之后依次连续递增。
- `legs` 数组中的顺序必须与复飞程序飞行顺序一致。
- 当 `Q0_leg_count.status = "present"` 时，`Q0_leg_count.value` 必须等于 `legs` 数组长度。
- 如果无法可靠确定 leg 数量，必须返回 `Q0_leg_count.status = "unknown"`、`Q0_leg_count.value = null`、`legs = []`。
- 不得输出非连续编号、重复编号或从 0 开始的编号。

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
- 如果图上写成 `<IDENT> VORTAC`、`<IDENT> VOR/DME`、`<IDENT> VOR`、`<IDENT> NDB` 或 `<IDENT> DME`，只输出前面的 `<IDENT>`，不要输出设施类型。例如 `ORL VORTAC` 的 ident 是 `ORL`，不是 `VORTAC`。
- 如果 hold fix 标注为 `ORL VORTAC`，`Q1_fix_ident.value` 必须是 `ORL`。
- 如果能看出是某类设施但看不清具体 ident，使用 `status = "unknown"`、`value = null`。
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

当航图支持 hold time 或 hold distance 时，`leg_time_min` 和 `leg_distance_nm` 应恰好一个为非 null。若 hold 参数无法可靠确定，使用 `status = "unknown"`，`value = null`。

## Parser 映射要求

后续 deterministic parser 只能做字段结构转换：

- `questionnaire.Q0_leg_count` -> `missed_approach.leg_count`
- 每个 questionnaire leg -> 一个 canonical `missed_approach.legs[]` item
- 每个 `Q_*` 字段 -> canonical `answers` 中的同名字段

parser 不得使用 target、CIFP、annotation、OCR、外部数据库或人工修复值。parser 不得根据答案正确性修改字段，只能做结构重排和 schema 级别的机械校验。

## 输出要求

- 只返回 questionnaire JSON。
- 输出的第一个字符必须是 `{`。
- 输出的最后一个字符必须是 `}`。
- 你的回答会被程序直接交给 JSON parser；如果输出 markdown code fence、自然语言或前后缀文本，本样本会被判为格式错误。
- 回复前必须自检：第一字符是 `{`，最后字符是 `}`，且没有任何 三个反引号。
- 不要返回 canonical JSON。
- 不要包含 markdown。
- 不要包含 markdown code fence。
- 不要输出 三个反引号json 或 三个反引号。
- 不要包含解释。
- 不要包含 evidence snippet。
- 不要包含本契约以外的字段。
- 不要输出占位符。
- 不要输出枚举说明。
- 保持 missed-approach leg 顺序。
- 如果无法可靠抽取复飞程序，返回 `Q0_leg_count.status = "unknown"`，`Q0_leg_count.value = null`，并且 `legs = []`。

## 输入


chart_id: {{chart_id}}
airport: {{airport}}
approach_ident: {{approach_ident}}
chart_name: {{chart_name}}
IMAGE: {{chart_image}}
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

