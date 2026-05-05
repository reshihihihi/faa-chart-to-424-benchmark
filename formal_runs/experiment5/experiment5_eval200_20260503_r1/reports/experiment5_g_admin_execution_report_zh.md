# 实验组5 dev50 G 系列运行报告

- run_id: `experiment5_eval200_20260503_r1`
- admin gold answer: `formal_runs/experiment5/experiment5_eval200_20260503_r1/admin_artifacts/admin_gold_answer_eval200.jsonl`
- gold observable: `formal_runs/experiment5/experiment5_eval200_20260503_r1/inputs/gold_observable_eval200_admin.jsonl`
- model: `gpt-5.4`

## 结果

| 方法 | schema-valid | retry | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---:|---:|---:|---:|---:|
| `G0_Direct` | 200/200 | 0 | 1079/4052 | 26.63% | 26.63% |
| `G1_Rules` | 200/200 | 0 | 2380/4052 | 58.74% | 58.74% |
| `G3_LLM_Rules` | 200/200 | 0 | 284/4052 | 7.01% | 7.01% |

## 输入边界

- `G0_Direct` 使用后台 `field_reviews` 中 `support_mode=direct_visible` 的人工审核字段关系，属于 direct-visible oracle replay。
- `G1_Rules` 使用后台 `direct_visible + rule_default_completion` 的人工审核字段关系，属于 rules-completion oracle replay。
- `G3_LLM_Rules` 只使用去答案字段后的 `gold_observable` 和 prompt 里的规则说明。
- 评分统一使用 `admin_gold_answer_dev50.jsonl`。

## 审查

- G3 method input forbidden key hits: `0`
- G0/G1 answer-side oracle usage recorded: `True`
