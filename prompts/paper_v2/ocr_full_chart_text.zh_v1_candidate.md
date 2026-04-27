# OCR Prompt v1 中文候选版：完整航图图像到 OCR 全文

你只负责把完整 FAA approach chart 图像中的可见文字转写为 OCR 文本。

## 允许输入

- 完整航图图像
- `chart_id`
- `airport`
- `approach_ident`
- `chart_name`

## 禁止输入

- CIFP、ARINC 424 或任何导航数据库记录
- canonical proxy target JSON
- 人工标注、prelabel、bbox、答案、scorer 输出
- 同一张航图的历史模型输出
- 外部航空数据库或网页搜索

## 任务

尽可能完整、逐行转写图像中的所有可见文字。保持图上大致阅读顺序。不要解释、不要补全、不要根据航空知识改写。

如果某个字符或单词不可读，用 `[unreadable]` 标记。不要猜测。

## 输出要求

- 只输出纯文本。
- 不要输出 JSON。
- 不要输出 markdown。
- 不要解释。

## 输入

```text
chart_id: {{chart_id}}
airport: {{airport}}
approach_ident: {{approach_ident}}
chart_name: {{chart_name}}
IMAGE: {{chart_image}}
```
