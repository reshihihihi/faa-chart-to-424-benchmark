# D1 方法卡

## 方法定位

D1 用于把 D-SFT 的原始模型输出统一落到实验组 1 已冻结的 canonical 阶层 JSON 格式。

D1 不改变实验目标：两边都使用同一个固定结构：

```text
424/CIFP -> canonical JSON target
D1 prediction -> canonical JSON prediction
```

然后后续再用同一个 schema 和 scorer 做验证与评分。

## 输入

D1 的输入是：

- D-SFT raw output。
- formal200/input manifest 中的样本编号、`chart_id`、`airport`、`approach_ident`、`chart_name`，仅用于固定 prediction 外壳和文件路由。
- 已冻结 canonical schema，仅用于验证输出格式。

## 禁止输入

D1 不得使用以下信息来改 prediction 内容：

- target JSON。
- 424/CIFP raw record。
- score 文件。
- 人工答案。
- OCR text 或 OCR boxes。
- field candidates。
- 其他方法预测结果。

## 输出

D1 输出必须是与 424/CIFP 派生 target 相同的固定 canonical 阶层 JSON：

- `chart_id`
- `procedure`
- `missed_approach`
- `missed_approach.leg_count`
- `missed_approach.legs[*].answers`
- 六个固定答案字段：`Q_terminator`、`Q1_fix_ident`、`Q2_altitude_constraint`、`Q3_turn`、`Q4_course_or_radial`、`Q5_hold_params`

## 边界

D1 只处理输出格式不一致的问题。D1 不以提高准确率为目标，不根据分数修输出，不用 424 答案补字段。

若 raw output 中的 missed-approach 字段值本身不满足 schema，例如 fix 名称长度超过 schema 上限，D1 不猜正确答案，而是将该字段降级为合法的 `unknown/null`，使输出保持 schema-valid，并让后续 scorer 把该字段记为错误。
