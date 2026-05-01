# 实验组1 v2 修复与实验组6最终包说明

日期：2026-05-01

## 当前状态

本包用于把两个问题一起收口：

1. 实验组1原 strict scorer 把 424/CIFP 一位小数值与航图整数显示值误判为错误。
2. 实验组6继承了同源问题，V2 direct-image verifier 和 extract-then-compare 方法也会受到 424-derived 字段与 chart-visible 字段边界影响。

当前已经完成：

- 实验组1新增 `narrowed_v2` scoring-equivalence policy；
- 实验组1 formal200 既有预测已按 v2 重评分；
- 实验组6 V2 已用 policy v3 完整重跑 E6-core 400；
- 实验组6各方法已按 E6-core 400 统一口径重评分；
- `error_fields` 越界路径已机械规范化到 allowed vocabulary；
- 最终完整性审计已通过。

## 最重要的文件

### 实验组1修复

- `scripts/scorers/group1_canonical_field_scorer.py`
- `scripts/rescore_group1_formal200_equivalence_v2.py`
- `benchmark_exports/derived/v2/formal300/targets/comparison_policy_v2.jsonl`
- `benchmark_exports/derived/v2/formal300/targets/comparison_policy_v2_summary.json`
- `reports/freeze/group1_scoring_equivalence_v2_formal200_zh_20260501.md`
- `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/combined_summary_table.csv`
- `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/policy_scope_audit.json`

### 实验组6最终结果

- `benchmark_exports/derived/v2/experiment6_counterfactuals_v8_group1formal200_full200_20260501/prompts/formal_v2_direct_vlm_verifier_policy_v3.md`
- `benchmark_exports/derived/v2/experiment6_counterfactuals_v8_group1formal200_full200_20260501/configs/formal_v2_e6_core_run_config_20260501_r2_policyv3.json`
- `benchmark_exports/derived/v2/experiment6_counterfactuals_v8_group1formal200_full200_20260501/scripts/normalize_experiment6_error_fields.py`
- `formal_runs/experiment6/experiment6_group1formal200_full200_v8_20260501_r1/V2_direct_image_e6_core_policyv3_20260501_r2/`
- `formal_runs/experiment6/experiment6_group1formal200_full200_v8_20260501_r1/reports/experiment6_final_completion_after_group1_v2_zh_20260501.md`
- `formal_runs/experiment6/experiment6_group1formal200_full200_v8_20260501_r1/reports/experiment6_e6_core_final_comparison_after_group1_v2_20260501.csv`
- `formal_runs/experiment6/experiment6_group1formal200_full200_v8_20260501_r1/reports/experiment6_core_final_integrity_audit_after_normalization_20260501.json`

### 本包 manifest

- `reports/freeze/experiment6_group1_v2_final_freeze_manifest_20260501.json`

## 最终 E6-core 400 结果摘要

| 方法 | binary acc | positive accept | negative reject | invalid |
|---|---:|---:|---:|---:|
| V1 OCR text verifier | 0.5125 | 0.7050 | 0.3200 | 0.0000 |
| V2 r1 original | 0.5250 | 0.1750 | 0.8750 | 0.0000 |
| V2 r2 policyv3 final | 0.5225 | 0.3750 | 0.6700 | 0.0000 |
| V3-C4 strict extract-then-compare | 0.5000 | 0.0000 | 1.0000 | 0.0000 |
| V3-D-SFT strict extract-then-compare | 0.5000 | 0.0761 | 1.0000 | 0.0750 |
| V4-C4 tolerant final | 0.5050 | 0.6150 | 0.3950 | 0.0000 |
| V4-D-SFT tolerant final | 0.5200 | 0.5761 | 0.5484 | 0.0750 |
| oracle control | 1.0000 | 1.0000 | 1.0000 | 0.0000 |

## 可以冻结的内容

- 实验组1 `narrowed_v2` scoring-equivalence policy；
- 实验组1 formal200 v2 重评分结果；
- 实验组6 E6-core 400 split；
- 实验组6 V2 policy v3 prompt / run config / final score；
- 实验组6 `error_fields` normalization policy；
- 实验组6 E6-core final comparison table；
- 实验组6 final integrity audit。

## 不应伪装成已修复的内容

D-SFT 相关 V3/V4 仍有 30 个 E6-core case invalid，原因是上游 D-SFT extraction 没有 schema-valid canonical JSON。它应作为 D-SFT 方法失败计入，不能在实验组6里用 target、人工答案或选择性修复来补。

## PR 建议

建议 PR 只提交脚本、policy、配置、报告和小型 summary/audit 文件。完整 PNG/PDF、OCR artifacts、全量 raw predictions、旧 pilot 结果和大型 formal run 中间产物不建议进入 PR，除非需要做数据归档。
