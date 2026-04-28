# 冻结与预冻结记录 - 2026-04-28

## 已正式冻结

本轮正式冻结的是实验评估合同中最基础、跨方法复用、且不应随方法表现调整的部分：

1. canonical schema

路径：

```text
schemas/missed_approach_leg.schema.json
```

SHA256：

```text
7ccb2cb9dcc73e67167d7ae5a8874e73dc201f56ad243615009db620494482d9
```

含义：B1、B1′、C3、C4 以及后续输出 canonical missed-approach JSON 的方法，都必须按这个 schema 输出后再评分。

2. strict JSON 输出与解析政策

正式要求：

- 模型输出必须是裸 JSON；
- 使用 assistant prefill `{`；
- 不允许 markdown code fence；
- 不允许 parser 去掉 code fence；
- 不允许抽取第一个 JSON object；
- 不允许语义修复；
- parser 不得读取 target；
- schema failure 不由 parser 修复。

含义：格式错误、额外解释文字、非 JSON、schema 不合格，都记录为失败，不能为了提高结果在后处理阶段补救。

3. pilot10_external 的样本角色

10 张 pilot 样本只用于 feasibility/pipeline 检查，不能进入 formal300 的正式训练、调参或最终评估。

正式冻结文件：

```text
configs/formal_freeze_core_v1_20260428.json
```

## 已预冻结

预冻结表示：当前可以作为下一轮 pilot/probe 的候选固定参数使用，但如果后续更大 dev/probe 发现问题，可以升级版本后再改；不能把它当成最终 formal freeze。

本轮预冻结记录在：

```text
configs/prefreeze_candidate_methods_after_r3_v1_20260428.json
```

包括：

- B1 当前方法边界、allowed/forbidden inputs、strict-prefill run 中使用的 prompt hash；
- C3 当前方法边界、questionnaire prompt hash、questionnaire-to-canonical converter hash；
- B1′ 当前方法边界、field_candidates schema、B1′ prompt hash、matcher v3 候选；
- C4 当前方法边界、C4 prompt v1 hash；
- OCR artifact manifest 格式；
- add-2 run artifact layout。

## B1′ matcher v3 状态

B1′ matcher v3 已完成本地干跑验证：

```text
schema_errors: 0
leakage_error_files: 0
forbidden_key_files: 0
known_noise_total: 0
```

但是，r3 的 B1′ 分数仍然属于 matcher v2：

```text
run_id: pilot10_exp1_b1prime_c4_semantic_matcher_v2_20260427_r3
B1′ score: 111/220
```

v3 目前只能说是“预冻结候选，等待新 run_id 重跑验证”，不能说它已经有模型成绩。

## 仍未正式冻结

这些不能现在正式冻结：

- model/provider/max_tokens；
- formal rerun policy；
- formal300 split/target；
- formal300 OCR artifact policy；
- B1/B1′/C3/C4 最终 prompt manifest；
- B1′ matcher v3 的正式性能；
- field_candidates schema 作为 repo 级 benchmark contract。

原因：这些要么还需要更大样本验证，要么会影响正式实验可复现性和公平性，不能只依据 10 张 pilot 直接锁死。
