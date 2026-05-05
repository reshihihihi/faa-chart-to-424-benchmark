# 实验组5安全加速方案

目标：缩短后续 B2/G3/formal200 运行时间，同时不改变方法定义和可比性。

## 不能做的加速

- 不换模型：继续用 `gpt-5.4`，不要改成 `gpt-5.4-mini`。
- 不改 prompt：同一方法保持同一 prompt 和 tool schema。
- 不降输入：不能删 gold prose、field candidates 或规则说明。
- 不降验证：schema validation、retry policy、score/no-leakage 仍保留。
- 不把 target、score、field_review_v2 或 canonical answer 加进任何方法输入。

## 可以做的加速

1. 保持 `openai-oauth` 常驻

当前服务已在：

```text
http://127.0.0.1:8080/v1
```

后续不要每个实验重启一次代理，只需复用该 endpoint。

2. 样本级并行

每个 chart 的 LLM 请求互相独立。后续可以把不同 chart 分给多个 worker，同一 worker 内仍执行：

```text
model = gpt-5.4
temperature = 0
max_tokens = 4096
schema_retry_count = 1
tool_schema = missed_approach_leg.schema.json
```

建议并行度：

```text
smoke20: 2 workers
formal200: 3 workers 起步，观察 rate limit 后再调到 4
```

3. 方法级并行但写入隔离目录

`B2a` 和 `B2b` 可以并行跑，但必须写入不同临时 run dir，最后用 merge 脚本合并 summary。不要让两个进程同时写同一个 `reports/b2_gold_text_summary.json`。

4. 断点续跑

后续 runner 应优先补 `--resume`：

- 如果 `canonical_json/<chart_id>.json`
- `validation/<chart_id>.json`
- `scores_v2/<chart_id>.json`

都存在且 schema-valid，则跳过该 chart。

这不改变结果，只避免网络中断后重跑已完成样本。

## 本次为什么没有中途并行

B2 已经顺序跑到一半时才讨论加速。如果中途启动并行进程，会与当前进程抢写同一输出目录，污染 raw responses、validation 和 summary。因此本次选择不打断，保证 run 目录干净。

## 下一步建议

在写 G3 或 formal200 runner 时直接加入：

```text
--max-workers 2
--resume
```

默认仍设为 `--max-workers 1`，只有在明确需要加速时开启并行。
