# D1 输出格式规范化策略

## 版本

- policy_id: `d1_output_canonicalization_20260502_r4`
- 适用方法: `D1`
- 适用输入: D-SFT formal200 的全部 raw output。

## 目的

本策略只解决一个问题：D-SFT 原始输出与 424/CIFP 派生 target 所使用的固定 canonical 阶层 JSON 格式不一致。

本策略不以提高准确率为目标，不根据分数修改输出，不把 target 或 424 raw 信息注入 prediction。

## 固定目标格式

最终 prediction 必须采用与 424/CIFP 派生 target 相同的 canonical 阶层：

```text
chart_id
procedure
  airport
  approach_ident
  chart_name
missed_approach
  leg_count
    status
    value
  legs[]
    leg_index
    answers
      Q_terminator
      Q1_fix_ident
      Q2_altitude_constraint
      Q3_turn
      Q4_course_or_radial
      Q5_hold_params
```

## 允许的格式转换

允许使用 manifest 固定样本身份外壳，允许使用 raw output 自身已有的信息做 missed-approach 格式转换：

1. 去掉 raw output 前后空白。
2. 去掉单层 markdown code fence。
3. 从 raw output 中解析 JSON 对象。
4. 使用 formal200/input manifest 固定顶层 `chart_id` 与 `procedure`：
   - `chart_id`
   - `procedure.airport`
   - `procedure.approach_ident`
   - `procedure.chart_name`
   这些字段只用于标识当前 prediction 对应哪一张航图，不作为 missed-approach 答案字段评分。
5. 若 raw output 是短格式：
   - 顶层有 `chart_id`、`leg_count`、`legs`；
   - 则包装成 canonical 顶层；
   - missed-approach 内容仍来自 raw output。
6. 若 raw output 已经是 canonical 格式但带有额外顶层字段，只删除不属于 canonical 顶层的字段。
7. 若 raw output 拆成 metadata JSON 和 body JSON 两个对象，只允许合并 raw output 内部已有字段：
   - metadata 对象提供 `chart_id`、可选 `approach_ident`、`approach`、`chart_name`；
   - body 对象提供 `procedure` 与 `missed_approach`；
   - 合并后 missed-approach 内容仍不使用 target、424 raw 或 score 改值。
8. 若 `missed_approach.leg_count` 是裸整数，可包装为 `{"status":"present","value":N}`。
9. 对每个 leg 补齐六个固定 answer 字段。
10. 对不符合 schema 的 answer 值做统一 fallback：
    - 非法 status -> `{"status":"unknown","value":null}`。
    - 非法 fix、turn、course/radial、altitude、hold 参数 -> `{"status":"unknown","value":null}`，或在 hold object 内将非法子字段置为 `null`。
    - 缺失字段 -> `{"status":"unknown","value":null}`。
    该 fallback 只保证 JSON 合法，不推断正确答案。

## 禁止的处理

1. 不允许使用 target JSON。
2. 不允许使用 424/CIFP raw record。
3. 不允许使用 score 文件或 scorer 结果来选择修复方式。
4. 不允许人工修改字段答案。
5. 不允许只处理失败样本；必须对全部 200 个 raw output 统一执行。
6. 不允许用 manifest 修正模型输出的 fix、altitude、turn、course/radial 或 hold 参数。
7. 不允许为了提高分数改变字段语义值。

## 审计输出

每个样本必须保存：

- raw output 副本；
- canonicalized JSON；
- format actions；
- schema validation 结果；
- 是否与 expected chart_id 一致的审计标记。

schema validation 只用于判断格式是否满足固定 canonical schema，不用于选择性提高分数。
