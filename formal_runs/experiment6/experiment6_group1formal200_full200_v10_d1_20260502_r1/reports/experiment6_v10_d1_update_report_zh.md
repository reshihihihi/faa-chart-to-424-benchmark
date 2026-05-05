# 实验组6 v10-D1 更新报告

## 1. 本次更新做了什么

本次没有重跑实验组6全部方法，只重评了依赖 D-SFT canonical output 的两条分支：

- `V3_D1_SFT_group1v2_neutralized`
- `V4_D1_SFT_tolerant`

V1、V2、V3-C4、V4-C4、control/oracle、E6-core case 构造均未改变。

## 2. 为什么需要这样做

旧实验组6的 D-SFT 分支直接读取 D-SFT 原始 canonical 输出，其中有 30/400 个 verification case 因上游输出格式或 schema 问题不能进入比较。D1 的作用是把同一批 D-SFT raw output 统一规范化到已冻结 canonical JSON 结构。

D1 不使用 target、score、424 raw、OCR、field candidates 或其他方法预测结果；非法字段值只降级为合法 `unknown/null`，不猜正确答案。

## 3. D1 覆盖与合法性

- D1 样本数: 200
- D1 raw output 找到: 200
- D1 canonical JSON 写出: 200
- D1 schema-valid: 200/200
- D1 schema-invalid: 0
- E6-core unique charts: 200
- E6-core 缺失 D1 canonical JSON: 0
- D1 final chart_id mismatch: 0

## 4. pre-D1 与 D1 后结果对比

| 方法 | total | valid | invalid | binary acc | positive accept | false alarm | negative reject | miss rate | field overlap norm | parse fail |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| V3_D_SFT_pre_D1_group1v2_neutralized | 400 | 370 | 30 | 48.25% | 3.80% | 96.20% | 100.00% | 0.00% | 81.18% | 30 |
| V3_D1_SFT_group1v2_neutralized | 400 | 400 | 0 | 52.00% | 4.00% | 96.00% | 100.00% | 0.00% | 81.50% | 0 |
| V4_D_SFT_pre_D1_tolerant | 400 | 370 | 30 | 52.00% | 57.61% | 42.39% | 54.84% | 45.16% | 48.39% | 30 |
| V4_D1_SFT_tolerant | 400 | 400 | 0 | 55.75% | 57.50% | 42.50% | 54.00% | 46.00% | 47.50% | 0 |

## 5. 主要结论

- V3-D-SFT strict 分支的 parse/schema failure 从 30 降到 0。
- V4-D-SFT tolerant 分支的 parse/schema failure 从 30 降到 0。
- V3-D1-SFT 的 binary accuracy 为 52.00%，valid 为 400/400。
- V4-D1-SFT 的 binary accuracy 为 55.75%，valid 为 400/400。

D1 后结果应作为实验组6 D-SFT 分支的正式候选口径；pre-D1 结果保留为输出格式未规范化前的诊断记录。

## 6. 保存位置

- 对比表: `formal_runs\experiment6\experiment6_group1formal200_full200_v10_d1_20260502_r1\reports\experiment6_v10_d1_comparison_table.csv`
- 完整性审计: `formal_runs\experiment6\experiment6_group1formal200_full200_v10_d1_20260502_r1\reports\experiment6_v10_d1_integrity_audit.json`
- run manifest: `formal_runs\experiment6\experiment6_group1formal200_full200_v10_d1_20260502_r1\configs\v10_d1_run_manifest.json`
