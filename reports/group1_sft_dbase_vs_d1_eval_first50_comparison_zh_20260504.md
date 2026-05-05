# 实验组1 D-base 与 D1 的 50 张对比结论

日期：2026-05-04

## 目的

本次提交记录 D-base 和 D1 已经共同跑过的同一批 50 张航图，用来说明未经过 SFT 的同底座模型效果不行。

## 这 50 张是什么

这 50 张不是训练集，也不是 probe。它们来自 formal300 的 `evaluation` split，是使用 run-package 准备命令的 `--limit 50` 选出的 evaluation 前 50 条。

样本清单已提交：

```text
formal_runs/group1_sft/dbase_vs_d1_eval_first50_20260504_r1/sample_set_50.jsonl
```

每一行包含：

- `sample_id`
- `chart_id`
- `airport`
- `proc_ident`
- `chart_name`

不包含图片文件、target JSON、score 文件、raw output 或本机绝对路径。

## 两个方法怎么比

相同点：

- 都输入完整航图图片。
- 都使用同一个 Qwen2-VL-2B-Instruct 底座。
- 都使用同一个 canonical prompt。
- 都输出 missed approach canonical JSON。
- 都使用同一套 `scoring_equivalence_v2` target 和 `comparison_policy_v2` 在预测完成后评分。

不同点：

- `D_BASE_SAME_BACKBONE` 不加载 SFT adapter。
- `D1` 加载 D1 SFT adapter/checkpoint。

所以这个对比是在控制底座、样本、prompt、schema、评分器之后，只看 SFT 是否带来效果。

## 结果

| 方法 | raw strict JSON parse ok | raw samples scored | canonicalized samples scored | field-level score |
|---|---:|---:|---:|---:|
| D_BASE_SAME_BACKBONE | 8/50 | 0/50 | 50/50 | 0/1022 = 0.0000 |
| D1 | 49/50 | 46/50 | 50/50 | 727/1022 = 0.7114 |

D-base 不是简单的“少一个格式修复”问题。保守 canonicalization 已经把 50 条都变成合法 schema 并送入评分，但字段得分仍然是 0/1022。

D1 在同样 50 张上 raw parse 明显更好，canonicalization 后 50/50 可评分，最终得到 727/1022。

## 结论

这组 50 张对比说明：

1. 未经过 SFT 的同底座 Qwen2-VL 不能稳定完成实验组1的 missed approach canonical JSON 任务。
2. D-base 的失败主要是任务能力不足，而不是图片路径、评分器或 canonicalization 流程坏了。
3. D1 SFT 对输出结构和字段语义都有明显提升。
