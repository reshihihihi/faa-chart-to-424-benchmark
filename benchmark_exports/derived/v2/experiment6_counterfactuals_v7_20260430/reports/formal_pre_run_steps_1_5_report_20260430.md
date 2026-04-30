# 实验组6正式运行前步骤 1-5 报告

日期：2026-04-30

状态：前五步已完成。实验组6 v7 包已作为 freeze candidate 合并，等待执行正式 V1/V2/V3 evaluation split 运行。

## 1. 已冻结的 policy

已写入：

- `configs/implicit_hold_time_policy.md`
- `configs/424_derived_policy.md`
- `configs/424_sequence_policy.md`
- `configs/artifact_control_policy.md`

这些文件分别固定隐含 hold time、424-derived counterfactual、sequence counterfactual 和 candidate-only artifact control 的解释规则。正式结果不得反向修改这些定义。

## 2. v7 freeze package

已生成并合并：

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

- `V1_text_only`：OCR-1 full-chart text + candidate record；
- `V2_direct_vlm`：full chart image + candidate record；
- `V3_extract_then_compare`：预先选择的冻结 Group 1 extraction + symbolic comparer；
- `V4_sft_verifier_optional`：仅在 no-leakage SFT verifier checkpoint 冻结后运行。

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
- V2 输出控制：强制 `audit_decision` tool call，解析 tool arguments，并要求严格两键 JSON；
- V3：symbolic comparer，formal extractor 必须在评分前记录；
- V4：未运行，等待合格 SFT verifier checkpoint。

输出控制：

- formal 输出必须是裸 JSON 或 runner 固定的 tool-call JSON；
- markdown code fence 视为 parse/schema failure；
- API failure 只能对同一失败 case 用相同输入、prompt、模型和参数重跑；
- 不允许按低分样本选择性重跑。

## 5. Smoke test

最新 smoke 设置：

- split：evaluation；
- case 数：5；
- 仅用于工程链路检查，不作为论文结果。

结果：

| 方法 | 结果 |
|---|---|
| V1 text-only | 5/5 API ok，5/5 parse ok，scorer ok |
| V2 direct VLM | prompt-only 严格 parser 下 0/5 parse ok；改为强制 `audit_decision` tool call 后 5/5 parse ok |
| V3 extract-then-compare | 5/5 parse ok，scorer ok |

Smoke score 只证明链路可运行，不代表正式准确率。

## 当前结论

实验组6已经具备正式 evaluation split 运行前的必要条件：

1. 题库 v7 已集中冻结；
2. policy 已写入；
3. 方法边界和禁止输入已明确；
4. V1/V2/V3 输入包 no-leakage 均通过；
5. V1/V2/V3 在最新严格输出规则下均已 smoke 跑通；
6. V3 formal extractor 需要在正式运行 manifest 中固定为预选 Group 1 extraction 来源。

建议正式运行顺序：

1. V1 text-only；
2. V2 direct VLM；
3. V3 extract-then-compare；
4. V4 仅在 SFT verifier checkpoint 合格后运行。
