# 实验组6最终完成报告：接入实验组1 scoring-equivalence v2 后

日期：2026-05-01

## 结论

实验组6已经完成到可冻结/可写论文分析的状态。

本轮主要解决的是实验组1造成的同源问题：canonical / 424-derived target 中存在一位小数航向或 radial，而航图和模型输出常使用整数显示。如果不处理，会导致实验组1评分和实验组6核验都把“显示等价”误判为错误。

已经完成：

- 实验组1实现 `narrowed_v2` scoring-equivalence；
- 实验组1 formal200 已按 v2 重评分；
- 实验组6 V2 direct-image verifier 已重跑 `policyv3 r2`；
- 实验组6 error_fields 越界问题已统一规范化；
- E6-core 400 case 已完成最终口径重评分；
- 所有最终纳入比较的方法均完成缺失、重复、parse、API、error_fields 合法性审计。

## 修复了哪些问题

### 1. 实验组1 strict scorer 问题

原来实验组1用完全严格相等评分，会把 `243.1` vs `243` 这类 424 内部值与航图显示值误判为不同。

现在新增：

- `scripts/scorers/group1_canonical_field_scorer.py --comparison-policy narrowed_v2`
- `scripts/rescore_group1_formal200_equivalence_v2.py`
- `benchmark_exports/derived/v2/formal300/targets/comparison_policy_v2.jsonl`

v2 只允许：

- `Q4_course_or_radial` 的 course/radial 整数显示等价；
- `Q5_hold_params.inbound_course_deg` 的整数显示等价；
- fix/navaid 名称的 harmless display normalization。

v2 不允许：

- 高度容差；
- 转弯方向放宽；
- holding 默认时间自动等价；
- 距离容差；
- reciprocal course equivalence；
- 航段重新对齐；
- status 放宽。

审计结果：439 个字段由 strict 错误改为 v2 正确，全部来自 `Q4_course_or_radial` 或 `Q5_hold_params`，violation_count = 0。

### 2. 实验组6 V2 prompt 边界问题

原 V2 r1 容易把 424-derived 字段当成必须逐字出现在航图上的字段，导致正例大量被误杀。

本轮测试了三个 prompt：

- `policy_v2`：只加入显示等价，smoke10 正例仍 0/5；
- `policy_v3`：加入 chart-visible vs 424-derived boundary，smoke10 正例 4/5、负例 3/5；
- `policy_v4`：继续放宽后负例识别明显变差，smoke10 正例 3/5、负例 1/5。

因此最终选择 `policy_v3`，并完整跑完 E6-core 400：

- run dir: `V2_direct_image_e6_core_policyv3_20260501_r2`
- raw predictions: 400/400
- parse_ok: 400
- api_error: 0
- missing/duplicate: 0

### 3. error_fields 输出格式问题

审计发现部分方法输出了过细路径，例如：

- `missed_approach.legs[3].hold_params.value.inbound_course_deg`
- `missed_approach.legs[3].hold_params.value.turn`

但实验组6允许词表中该粒度应统一归到：

- `missed_approach.legs[3].hold_params`

只有 `hold_params.value.leg_time_min` 是允许的单独子字段。

已经新增：

- `scripts/normalize_experiment6_error_fields.py`

该脚本只做机械路径规范化：

- 不改变 `consistent`；
- 不看 label / target / score；
- 不改变模型或 symbolic comparer 的接受/拒绝判断；
- 只把过细字段映射回 allowed vocabulary。

规范化后最终审计：

- V1：字段合法，0 越界；
- V2 r2 final：字段合法，0 越界；
- V3_C4：字段合法，0 越界；
- V4_C4_tolerant final：字段合法，0 越界；
- V4_PR25_C4_narrowed：字段合法，0 越界。

D-SFT 相关方法仍有 30 个 invalid case，这是上游 D-SFT extraction 没有 schema-valid canonical JSON，不是实验组6字段规范化能合法修复的问题。

## E6-core 400 最终结果

统一口径：

- 全部方法均按 E6-core 400 case 评分；
- V2/V4 使用 normalized error_fields 后的分数；
- D-SFT invalid extraction 计入 invalid/missing，不用 target 或人工答案修复。

| 方法 | total | valid | binary acc | positive accept | negative reject | false positive | false negative | normalized error-field overlap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V1 OCR text verifier | 400 | 400 | 0.5125 | 0.7050 | 0.3200 | 0.2950 | 0.6800 | 0.1800 |
| V2 direct-image r1 original | 400 | 400 | 0.5250 | 0.1750 | 0.8750 | 0.8250 | 0.1250 | 0.1800 |
| V2 direct-image r2 policyv3 final | 400 | 400 | 0.5225 | 0.3750 | 0.6700 | 0.6250 | 0.3300 | 0.2050 |
| V3-C4 strict extract-then-compare | 400 | 400 | 0.5000 | 0.0000 | 1.0000 | 1.0000 | 0.0000 | 0.4150 |
| V3-D-SFT strict extract-then-compare | 400 | 370 | 0.5000 | 0.0761 | 1.0000 | 0.9239 | 0.0000 | 0.8118 |
| V4-C4 tolerant final | 400 | 400 | 0.5050 | 0.6150 | 0.3950 | 0.3850 | 0.6050 | 0.2000 |
| V4-D-SFT tolerant final | 400 | 370 | 0.5200 | 0.5761 | 0.5484 | 0.4239 | 0.4516 | 0.4839 |
| control oracle | 400 | 400 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 1.0000 |
| control all-accept | 400 | 400 | 0.5000 | 1.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| control all-reject | 400 | 400 | 0.5000 | 0.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |

## 如何解释这些结果

### V2 r1 vs V2 r2

V2 r1 binary accuracy 略高一点，但问题是强烈偏向 reject：

- positive accept 只有 17.5%；
- false positive 82.5%；
- 很多正例被 424-derived / chart-display mismatch 误杀。

V2 r2 policyv3 修复后：

- positive accept 提高到 37.5%；
- false positive 降到 62.5%；
- negative reject 从 87.5% 降到 67.0%；
- binary accuracy 基本持平。

这说明修复不是单纯提分，而是把方法从“过度拒绝”校准到更合理的 chart-visible verification。剩余错误属于 V2 方法能力边界：直接看图核验 candidate record 时，模型仍难以稳定地区分 424-derived 抽象字段、holding 默认项、radial/course 关系。

### V3-C4 / V3-D-SFT 为什么极端

V3 是普通 extract-then-compare。它先用实验组1的 extraction 输出，再和 candidate 比较。只要 extraction 与 candidate 有大量结构差异，V3 就会把几乎所有 candidate 判为 false。

结果表现为：

- V3-C4 positive accept = 0；
- V3-D-SFT positive accept = 7.6%；
- negative reject 接近或等于 1。

这说明“先抽取再严格比较”会产生严重 all-reject bias，不能直接作为 424 反事实核验的主方法。

### V4 的意义

V4 是对 V3 的诊断性修正：加入字段路径规范化、部分容忍、对齐/比较策略后，观察 all-reject bias 是否缓解。

V4-C4：

- positive accept 从 0 提高到 61.5%；
- negative reject 降到 39.5%；
- 说明容忍策略能缓解 all-reject，但也带来漏检。

V4-D-SFT：

- positive accept 57.6%；
- negative reject 54.8%；
- balanced behavior 更接近中间，但仍受 D-SFT extraction invalid 影响。

### D-SFT invalid 怎么处理

D-SFT 相关 V3/V4 有 30 个 E6-core case invalid，来自 16 张 chart 的 D-SFT extraction 问题。

原因包括：

- 缺少 extraction validation 文件；
- extraction schema invalid；
- chart_id / airport 识别错误；
- 多出 schema 不允许字段。

这些是 D-SFT 方法输出失败，应计入方法失败。不能在实验组6里用 target 或人工答案修复，否则会改变 D-SFT 方法边界。

## 最终可写论文的故事线

实验组6不是为了证明某个 verifier 已经很强，而是为了回答：

> 从航图到 424/canonical 的方法，能不能进一步用于“候选 424 record 是否与航图一致”的反事实核验？

当前结果支持以下结论：

1. 反事实构造与评分管线成立：oracle control 达到 100%，说明 labels、case construction、scorer 可以闭环。
2. 直接图像核验可运行，但对 424-derived 抽象字段非常敏感：V2 r2 修复后仍只有约 52% binary accuracy。
3. 普通 extract-then-compare 会强烈 all-reject：V3-C4/V3-D-SFT 说明抽取误差会被比较器放大。
4. 容忍/对齐策略能缓解 all-reject，但引入漏检：V4 是必要诊断，不应伪装成最终强方法。
5. 这支持论文主线：missed approach chart → 424/canonical 不是单纯 OCR/LLM 抽取任务，还需要显式处理图面显示、424 派生字段、航段绑定、字段等价和核验策略。

## 最终文件

- E6-core cases: `benchmark_exports/derived/v2/experiment6_counterfactuals_v8_group1formal200_full200_20260501/selection/e6_core_200pos_200neg_seed20260501.jsonl`
- V2 r2 run config: `benchmark_exports/derived/v2/experiment6_counterfactuals_v8_group1formal200_full200_20260501/configs/formal_v2_e6_core_run_config_20260501_r2_policyv3.json`
- V2 r2 outputs: `formal_runs/experiment6/experiment6_group1formal200_full200_v8_20260501_r1/V2_direct_image_e6_core_policyv3_20260501_r2/`
- Final comparison CSV: `formal_runs/experiment6/experiment6_group1formal200_full200_v8_20260501_r1/reports/experiment6_e6_core_final_comparison_after_group1_v2_20260501.csv`
- Final integrity audit: `formal_runs/experiment6/experiment6_group1formal200_full200_v8_20260501_r1/reports/experiment6_core_final_integrity_audit_after_normalization_20260501.json`
- Group1 scoring-equivalence report: `reports/freeze/group1_scoring_equivalence_v2_formal200_zh_20260501.md`

## 冻结建议

可以冻结：

- E6-core 400 selection；
- V1 / V2 r2 policyv3 / V3-C4 / V4-C4 / V4-D-SFT 的 final scoring artifacts；
- error_fields normalization policy；
- V2 r2 prompt 与 run config；
- Group1 scoring-equivalence v2 policy。

不建议作为“已解决”冻结：

- D-SFT extraction invalid 本身。它应作为 D-SFT 方法失败计入结果，或者在实验组1/D-SFT 专门做新的 parser repair policy 后，用新 run_id 另行重跑。
