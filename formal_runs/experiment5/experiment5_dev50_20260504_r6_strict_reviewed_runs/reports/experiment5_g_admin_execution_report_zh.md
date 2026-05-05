# 实验组5 dev50 G 系列运行报告

- run_id: `experiment5_dev50_20260504_r6_strict_reviewed_runs`
- admin gold answer: `formal_runs/experiment5/experiment5_dev50_20260503_r1/admin_artifacts/admin_gold_answer_dev50.jsonl`
- gold observable: `formal_runs/experiment5/experiment5_dev50_20260504_r3_strict_no_leak/inputs/g_visible_observables_dev50_strict.jsonl`
- model: `gpt-5.4`

## 结果

| 方法 | schema-valid | retry | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---:|---:|---:|---:|---:|
| `G3_LLM_Rules` | 50/50 | 5 | 56/1010 | 5.54% | 5.54% |

## 输入边界

- `G0_Direct` 使用后台 `field_reviews` 中 `support_mode=direct_visible` 的人工审核字段关系，属于 direct-visible oracle replay。
- `G1_Rules` 使用后台 `direct_visible + rule_default_completion` 的人工审核字段关系，属于 rules-completion oracle replay。
- `G3_LLM_Rules` 只使用去答案字段后的 `gold_observable` 和 prompt 里的规则说明。
- 评分统一使用 `admin_gold_answer_dev50.jsonl`。

## 审查

- G3 method input forbidden key hits: `0`
- G0/G1 answer-side oracle usage recorded: `False`
