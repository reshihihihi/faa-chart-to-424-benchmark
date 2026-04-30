# 实验组6正式运行前 1-5 步执行报告

日期：2026-04-30

状态：前五步已完成，等待用户决定是否启动正式全量运行。

## 1. 已冻结的 policy

已写入：

- `configs/implicit_hold_time_policy.md`
- `configs/424_derived_policy.md`
- `configs/424_sequence_policy.md`
- `configs/artifact_control_policy.md`

这些文件分别固定隐含 hold time、424-derived 反事实、sequence 反事实和 candidate-only artifact control 的解释规则。后续正式结果不得反向修改这些定义。

## 2. v7 freeze package

已生成：

`benchmark_exports/derived/v2/experiment6_counterfactuals_v7_20260430`

核心内容：

- v7 counterfactual cases：3091 条；
- builder：`experiment6_counterfactual_builder_prefreeze_v7`；
- validation：pass；
- V0/V1/V2/V3 packed inputs；
- V0/V1/V2/V3 no-leakage reports；
- Phase 4 strict QC report；
- V0 artifact baseline report；
- `freeze_manifest.json`；
- `checksums.sha256`。

## 3. 方法边界

已固定：

- `V1_text_only`：OCR-1 full-chart text + candidate；
- `V2_direct_vlm`：full chart image + candidate；
- `V3_extract_then_compare`：冻结的 Group 1 extraction + symbolic comparer；
- `V4_sft_verifier_optional`：仅在无泄漏 SFT checkpoint 冻结后运行。

方法边界文件：

- `configs/method_boundary_v1_v4_policy.md`
- `configs/formal_v1_v4_run_config_20260430.json`

## 4. Prompt / model / parser / retry

已写入 formal prompt/spec：

- `prompts/formal_v1_text_only_verifier.md`
- `prompts/formal_v2_direct_vlm_verifier.md`
- `prompts/formal_v3_extract_then_compare_spec.md`
- `prompts/formal_v4_sft_verifier_spec.md`

当前冻结候选运行参数：

- V1：`gpt-5.4`，OpenAI-compatible local proxy，temperature 0，max_tokens 300；
- V2：`claude-sonnet-4-5-20250929`，OpenAI-compatible Claude proxy `https://api.claudecode.uk/v1`，temperature 0，max_tokens 300；
- V3：symbolic comparer，默认 smoke extractor 为 C4；
- V4：未运行，等待合格 SFT checkpoint。

输出控制：

- formal 输出必须是裸 JSON 或 runner 固定的 tool JSON；
- markdown code fence 视为 parse/schema failure；
- API failure 只能对同一失败 case 用相同参数重跑；
- 不允许按低分样本选择性重跑。

## 5. Smoke test

smoke run 目录：

`external smoke run: formal_smoke_v1_v2_v3_20260430`

样本数：5 条，仅用于工程链路检查，不作为论文结果。

| 方法 | 结果 |
|---|---|
| V1 text-only | 5/5 API ok，5/5 parse ok，scorer ok |
| V2 direct VLM | Anthropic native `/v1/messages` 403；改用 OpenAI-compatible `/v1/chat/completions` 后 5/5 API ok，5/5 parse ok，scorer ok |
| V3 extract-then-compare | 5/5 parse ok，scorer ok |

Smoke score 仅证明链路可运行，不代表正式准确率。

## 当前结论

实验组6已经具备正式跑前的必要条件：

1. 题库 v7 已集中冻结；
2. policy 已写入；
3. 方法边界和禁止输入已明确；
4. V1/V2/V3 输入包 no-leakage 均通过；
5. V1/V2/V3 smoke test 均跑通并能评分。

下一步若用户确认，可以启动正式全量运行。建议正式运行顺序为：

1. V1 text-only；
2. V2 direct VLM；
3. V3 extract-then-compare；
4. V4 仅在 SFT verifier checkpoint 合格后运行。
