# 完整航图到图上证据记录：输出提示词草案

你会收到一张完整 FAA 航图图像。你的任务不是直接输出最终程序 JSON，而是列出图上可见的复飞相关证据。

只输出图上证据记录。不要输出航段类型、最终 canonical JSON、424 字段答案或评分信息。

输出必须是裸 JSON，不要输出解释，不要输出 Markdown 代码块。

输出结构：

```json
{
  "chart_id": null,
  "evidence_items": [
    {
      "source_region": "MISSED_APPROACH_TEXT",
      "item_type": "text_line",
      "text": null,
      "value": null,
      "bbox": null
    }
  ]
}
```

允许的 `source_region`：

```text
MISSED_APPROACH_TEXT
PLAN_VIEW
PROFILE_VIEW
MISSED_APPROACH_DETAIL_AREA
CHART_TEXT
OTHER
```

允许的 `item_type` 示例：

```text
text_line
fix_text
altitude_text
course_or_radial_text
holding_pattern
turn_arrow
dme_text
navaid_text
```

如果不能确定，保留为可见事实，不要推导最终程序答案。
