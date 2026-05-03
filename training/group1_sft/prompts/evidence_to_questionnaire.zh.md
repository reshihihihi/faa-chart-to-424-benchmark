# 人工确认图上证据到复飞程序语义：问卷式输出提示词草案

你会收到一张航图的人工确认图上证据记录。你的任务是根据这些图上证据，回答复飞程序相关问题。

只允许使用输入中的图上证据记录。不要使用标准答案、评分结果、424 原始记录或其他方法预测。

输出必须是裸 JSON，不要输出解释，不要输出 Markdown 代码块。

每个 leg 必须包含 `Q_terminator`、`Q1_fix_ident`、`Q2_altitude_constraint`、`Q3_turn`、`Q4_course_or_radial`、`Q5_hold_params` 六个问题字段。每个问题字段的值必须是 `{"status": "...", "value": ...}` 对象，不能是 `null`，也不能省略。证据不足时使用 `{"status": "unknown", "value": null}`。

输出结构：

```json
{
  "leg_count": null,
  "legs": [
    {
      "leg_index": 1,
      "Q_terminator": {"status": "unknown", "value": null},
      "Q1_fix_ident": {"status": "unknown", "value": null},
      "Q2_altitude_constraint": {"status": "unknown", "value": null},
      "Q3_turn": {"status": "unknown", "value": null},
      "Q4_course_or_radial": {"status": "unknown", "value": null},
      "Q5_hold_params": {"status": "unknown", "value": null}
    }
  ]
}
```

如果图上证据不足，使用 `unknown`。不要猜测不存在的字段。
