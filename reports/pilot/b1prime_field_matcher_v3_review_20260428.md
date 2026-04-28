# B1′ field matcher v3 审查 - 2026-04-28

## 本次优化

`B1′ matcher v3` 仍然是 OCR-only regex pilot matcher，方法边界没有改变：

- 只读取同一张航图的 full-chart OCR text；
- 不读取 target、scorer、CIFP/ARINC 424、人类证据、字段目标或 leg mapping；
- 不输出 `leg_index`、`candidate_leg_id`、`schema_field`、`expected_value`、`target_value`、`Q_terminator`。

相对 v2，本次优化只做候选降噪和候选上限控制：

- `candidate_source` 改为 `ocr_text_only_regex_field_matcher_pilot_v3`；
- 规则 ID 改为 `*_regex_v3`；
- 对 `fix_candidates`、`altitude_candidates`、`course_candidates` 加入按 `source_section` 的候选上限；
- 保留 missed approach text 优先，同时减少 `full_chart_unknown` 回退候选数量；
- 不加入 target-aware 规则，不加入 field-to-leg linking，不加入 schema-slot assignment。

## 干跑验证

验证范围：10 个 pilot OCR 文本 artifact；没有调用模型，没有读取 target/scorer/CIFP。

结果：

```text
schema_errors: 0
leakage_error_files: 0
forbidden_key_files: 0
known_noise_total: 2
runner_sha256: 38f485934fcef9cf720bf32e16d807aca1639943aeec7490fe0e027603976a68
```

候选数量从 v2 到 v3：

```text
fix_candidates: 516 -> 341
altitude_candidates: 355 -> 194
turn_candidates: 6 -> 6
course_candidates: 54 -> 51
hold_candidates: 15 -> 15
direct_phrase_snippets: 6 -> 6
climb_phrase_snippets: 10 -> 10
total: 962 -> 623
```

`source_section` 从 v2 到 v3：

```text
missed_approach_text: 502 -> 425
full_chart_unknown: 442 -> 186
profile_view: 18 -> 12
```

## 判断

v3 可以作为下一轮 B1′ pilot/probe 的预冻结候选，因为它降低了 OCR 全图噪声，同时保持实验方法含义不变。

但它还不能声明为正式冻结，也不能把 r3 的 B1′ 分数归因于 v3。r3 模型结果使用的是 matcher v2；v3 目前只完成了本地干跑验证。下一步如果要检验性能，需要用新 `run_id` 重跑 B1′，并把 v3 的 `field_candidates`、raw response、canonical JSON、validation 和 score 单独保存。

详细统计保存于：

```text
reports/pilot/b1prime_field_matcher_v3_stats_20260428.json
```
