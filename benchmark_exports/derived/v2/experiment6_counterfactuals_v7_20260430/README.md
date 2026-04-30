# 实验组6反事实验证包 v7

状态：正式冻结候选包，等待用户确认后再执行完整 V1/V2/V3 正式运行。

日期：2026-04-30

## 范围

本包包含 paper-v2 实验组6的反事实验证集合及正式运行前资产。任务形式为：

```text
航图证据 + 候选 424-like missed-approach 记录
-> 审核判定 JSON
```

这是一个验证任务，不是完整的 canonical JSON 抽取任务。实验组6关注的是：给定一份候选 missed-approach 记录后，方法能否根据允许的证据判断该候选记录是否与航图一致。

## 包含内容

- `cases/verification_counterfactuals_v7_formal300.jsonl`
  v7 版本的带标签验证样本。标签只用于评分，不能进入任何方法输入。
- `packed_inputs/`
  不含标签的 V0/V1/V2/V3 输入包。
- `configs/`
  schema、method card、no-leakage policy、反事实构造规则，以及正式运行前冻结策略。
- `prompts/`
  正式 V0/V1/V2 prompt，以及 V3/V4 方法规格说明。
- `scripts/`
  本包使用的 builder、packer、no-leakage checker、validator、runner 和 scorer。
- `qc/`
  builder summary、validation report 和 no-leakage reports。
- `runs/v0_candidate_only/`
  V0 candidate-only artifact baseline 的 summary 和 report。
- `reports/`
  严格 QC 审查报告，以及正式运行前步骤 1-5 报告。
- `freeze_manifest.json` 和 `checksums.sha256`
  本包 manifest 和文件 hash 清单。

## 样本数量

总样本数：3091，来源于 formal300。

| 类型 | 数量 |
|---|---:|
| positive | 300 |
| fix_substitution | 300 |
| altitude_perturbation | 292 |
| turn_direction_flip | 86 |
| course_radial_error | 299 |
| holding_parameter_error | 298 |
| implicit_hold_time_omission | 35 |
| path_terminator_substitution | 300 |
| ca_omission | 294 |
| ca_to_df_sequence_error | 287 |
| text_only_trap | 300 |
| 424_derived_trap | 300 |

## 冻结方法含义

- V0 candidate-only baseline
  只输入候选记录，不输入航图证据。用于 artifact control，检查候选记录自身是否可能泄漏答案或带来偏置。
- V1 text-only verifier
  输入冻结的 OCR-1 全航图文本和候选记录。
- V2 direct VLM verifier
  输入完整航图图像和候选记录。
- V3 extract-then-compare
  输入冻结的实验组1抽取结果，再通过符号比较器进行审核。
- V4 SFT verifier
  可选方法；只有在 no-leakage 的 SFT verifier checkpoint 被冻结后才运行。

## 关键正式运行前结果

- case validation：通过。
- V0/V1/V2/V3 no-leakage：通过。
- V0 candidate-only artifact score：0.20315299175922608。
- V1/V2/V3 smoke test：每个方法均为 5/5 成功解析。
- V2 必须使用 OpenAI-compatible Claude proxy route，而不是 Anthropic native Messages API，因为 native route 在 smoke test 中返回 403。

## 正式运行规则

本包一旦被接受为冻结候选包，不得根据模型表现修改 cases、labels、`error_fields`、prompts、method inputs 或 retry rules。

任何重新设计都必须使用新的 builder version，并生成新的实验包。
