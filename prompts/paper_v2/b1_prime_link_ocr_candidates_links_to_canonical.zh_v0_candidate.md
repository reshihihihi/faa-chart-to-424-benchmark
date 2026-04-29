# B1_prime_link prompt draft

Status: draft only, not frozen

你将收到同一张 FAA approach chart 的 OCR-1 全图文本，以及自动生成的 `field_to_leg_links` 候选表。你的任务是根据这些输入输出 missed approach 的 canonical JSON。

## 方法边界

- `field_to_leg_links` 是弱证据，不是答案。
- `candidate_leg_index` 是自动算法生成的候选序号，不是 gold leg index。
- 候选表可能有错、漏、重复或来自 OCR 错序文本。
- 如果 OCR 正文和候选表冲突，应优先根据 OCR 中可见的 missed approach instruction 判断。
- 不要使用外部知识、CIFP、ARINC 424、历史答案、人工标注或 scorer 结果。
- 不要根据 FAA procedure 常识补全 OCR 中不可见的值。

## 使用 candidate legs 的规则

- `direct_to_fix`、`track_to_fix`、`course_to_fix`、`radial_to_fix`、`hold_at_fix` 只能作为候选航段证据。
- `candidate_legs` 数量少不代表真实航段少；如果 OCR route table 或 plan-view 文本没有被 linker 绑定，仍应检查 OCR 正文和 unlinked context。
- `candidate_legs` 不是 canonical legs。不要把每个 candidate_leg 机械地一对一复制成输出 legs。
- 不要把 `candidate_leg_index` 当作输出 `leg_index`。
- 不要把 `link_type` 直接翻译成 `Q_terminator`。例如 `track_to_fix` 不一定等于 `TF`，`hold_at_fix` 不一定等于 `HM`，必须结合 OCR 正文判断。
- 不要把 `leg_count.value` 设置为 `candidate_legs` 的数量，除非 OCR 正文本身也支持这个航段数量。
- B1′-link linker 可能没有生成 initial climb / CA leg；如果 OCR 明确写有 climb to altitude，应考虑是否需要单独的初始 climb leg。
- 如果 `direct_to_fix` 和 `hold_at_fix` 共享同一个 fix，通常表示先 direct 到该 fix，再在该 fix hold；不要把 direct 和 hold 无依据地合并成一个 HM leg。
- 如果 `track_to_fix` 和 `hold_at_fix` 共享同一个 fix，可能是“track to fix and hold”的同一 hold 结构，也可能是 track leg 后接 hold leg；必须由 OCR 正文决定，不要机械拆分或机械合并。
- `linking_warnings` 是重要输入。遇到同一 fix 的 direct/track + hold 配对警告时，应重新检查 OCR_TEXT，而不是直接照抄 candidate legs。
- 如果一个可见 route chain 包含多个 `to FIX`，不要无故压缩成只到第一个 fix 和最终 hold。
- 如果候选 evidence 明显来自 notes、minima、communications、procedure NA、altimeter setting、frequency 或不相关区域，应降低可信度。
- 如果候选链条不完整，可以把缺失字段设为 `status: "unknown"`，但不要忽略 OCR 正文里清楚出现的 flown route。
- 对 KAVO_R05 这类 OCR 错序风险要特别谨慎：`direct ANA` 这类短语虽然可能出现在 OCR snippet 中，但如果上下文混有 minima/notes/altimeter language，应作为弱证据。
- 对 KLLJ_RNV-A 这类 route-table-heavy 样本要特别谨慎：只出现一个 final hold candidate 不代表中间 route legs 不存在。

## 输出格式

- 只输出 canonical JSON。
- 输出必须是裸 JSON。
- 不允许 markdown code fence。
- 不允许解释性文字。
- 所有字段必须使用 schema 规定的 `status` / `value` 结构。
- 不确定但可见字段不足时，用 `status: "unknown", "value": null`。
- 不适用字段用 `status: "not_applicable", "value": null`。
- 只要 `status` 是 `"unknown"`，`value` 必须是 JSON `null`，绝对不能写字符串 `"unknown"`。
- 只要 `status` 是 `"not_applicable"`，`value` 必须是 JSON `null`，绝对不能写字符串、对象、数字或 `"unknown"`。
- `Q_terminator` 也必须遵守这条规则：如果无法确定 terminator，输出 `{"status":"unknown","value":null}`，不要输出 `{"status":"unknown","value":"unknown"}`。

## 严格字段格式

`Q4_course_or_radial.value` 绝对不能是裸数字、字符串、`degrees`、`deg`、`track`、`heading`、`nav_ref` 或 `nav_fix` 自创格式。

如果是 course / track / heading 度数，必须写成：

`{"type":"course_deg","course_deg":191}`

如果是 navaid radial，必须写成：

`{"type":"navaid_radial","navaid":"BOS","radial_deg":30,"direction":"outbound"}`

如果只是 direct，没有可用 course/radial，必须写成：

`{"type":"direct"}`

错误示例，禁止输出：

- `"value": 191`
- `"value": "R-030"`
- `"value": {"type":"track","degrees":191}`
- `"value": {"heading_deg":60}`
- `"value": {"radial_deg":295,"nav_ref":"SBJ"}`

`Q_terminator.value` 只能使用 schema 允许的 ARINC terminator 字符串，例如 `CA`, `DF`, `TF`, `HM`, `VM`, `unknown`，不能自创解释。

`Q2_altitude_constraint.value` 如果 present，必须是：

`{"desc":"AT_OR_ABOVE","altitude_ft":3000,"altitude_2_ft":null}`

`Q5_hold_params.value` 如果 present，必须包含：

`{"inbound_course_deg":null,"leg_time_min":null,"leg_distance_nm":null,"turn":null}`

## 输入

chart_id: {{chart_id}}
airport: {{airport}}
chart_name: {{chart_name}}

OCR-1 full-chart text:

{{ocr_text}}

field_to_leg_links:

{{field_to_leg_links_json}}
