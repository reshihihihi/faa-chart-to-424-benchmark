# 实验组 6 v11 最终整理报告：对齐 #25 scoring-equivalence v2 与 D1

## 1. 本次做了什么

本次没有重新调用模型，也没有改变实验组 6 的科学问题。v11 只做四件事：

1. 沿用 v10-D1 已审定的 D-SFT V3/V4 符号比较结果，并确认其 D1 来源与 #25 D1 canonical JSON 哈希一致。
2. 把所有 D1 来源写成仓库相对路径，去掉 Windows 本地盘符绝对路径。
3. 把 control、V1、V2、V3-C4、V3-D1-SFT、V4-C4、V4-D1-SFT 统一成最终结果表。
4. 写入 #25 dependency manifest 和完整 integrity/no-leakage audit。

## 2. 为什么必须吸收 #25

#25 对实验组 6 有两个直接影响：

- Group 1 scoring-equivalence v2 允许极窄范围的显示等价，例如 fix/navaid 显示规范化，以及 course/radial/hold inbound course 的整数/小数显示等价。
- D1 把 D-SFT 原始输出规范化为当前 canonical JSON。实验组 6 中使用 D-SFT 作为 extractor 的分支必须使用 D1 后结果，否则会把输出接口错误混入 424 反事实核验能力。

因此 v11 的主结果使用 D1 后的 D-SFT；pre-D1 只保留为附录诊断。

## 3. 方法边界

| 方法 | 输入 | 输出 | 目的 | 主结果 |
|---|---|---|---|---|
| control_all_accept | case label 结构控制 | 全部接受 | 检查正负样本平衡 | 是 |
| control_all_reject | case label 结构控制 | 全部拒绝 | 检查正负样本平衡 | 是 |
| control_oracle_label | oracle label | oracle decision | 上限 sanity check | 是 |
| control_v0_candidate_integrity | candidate record only | verification decision | 检查 counterfactual 是否有明显伪造痕迹 | 是 |
| V1 OCR text | OCR text + candidate | verification decision | 文本证据核验 baseline | 是 |
| V2 direct image | chart image + candidate | verification decision | 直接图像核验 | 是 |
| V3-C4 | candidate + C4 canonical extraction | symbolic compare | 普通 extract-then-compare | 是 |
| V3-D1-SFT | candidate + D1-SFT canonical extraction | symbolic compare | 强 extractor 的普通比较 | 是 |
| V4-C4 | candidate + C4 canonical extraction | tolerant symbolic compare | 诊断字段等价、航段对齐、partial compare 后是否改善 | 是 |
| V4-D1-SFT | candidate + D1-SFT canonical extraction | tolerant symbolic compare | 强 extractor 的诊断 tolerant compare | 是 |

注意：V4 是实验组 6 的诊断性 tolerant compare，不是 #25 scoring-equivalence v2 的正式评分规则。

## 4. #25 不允许被混入的放宽项

以下内容没有进入 #25 scoring-equivalence v2，不能把它们说成实验组 1 的正式评分等价：

- altitude tolerance
- turn semantic relaxation
- holding default time
- DME/distance tolerance
- reciprocal radial/course equivalence
- Q_terminator relaxation
- leg alignment changes

如果这些能力出现在 V4，只能解释为实验组 6 的诊断性核验器设计，用来分析反事实核验路线是否受字段表示、航段对齐和抽取缺证据影响。

## 5. D1 覆盖与合法性

- D1 run_id: `group1_formal200_D1_20260502_r4`
- D1 samples_total: 200
- D1 raw_outputs_found: 200
- D1 canonical_json_written: 200
- D1 schema_valid: 200/200
- D1 schema_invalid: 0
- D1 final_chart_id_mismatch_count: 0

D1 只规范输出接口，不把 target、score、CIFP raw、OCR text、field candidates 或其他方法预测输入给 D-SFT。

## 6. 主结果表

| 方法 | role | total | valid | invalid | binary acc | balanced acc | positive accept | false alarm | negative reject | miss rate | error-field overlap norm |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| control_all_accept | control | 400 | 400 | 0 | 50.00% | 50.00% | 100.00% | 0.00% | 0.00% | 100.00% | 0.00% |
| control_all_reject | control | 400 | 400 | 0 | 50.00% | 50.00% | 0.00% | 100.00% | 100.00% | 0.00% | 18.00% |
| control_oracle_label | oracle_control | 400 | 400 | 0 | 100.00% | 100.00% | 100.00% | 0.00% | 100.00% | 0.00% | 100.00% |
| control_v0_candidate_integrity | candidate_artifact_control | 400 | 400 | 0 | 50.00% | 50.00% | 100.00% | 0.00% | 0.00% | 100.00% | 0.00% |
| V1_OCR_text_chartdisplay_v2 | main_method | 400 | 400 | 0 | 49.00% | 49.00% | 69.50% | 30.50% | 28.50% | 71.50% | 16.50% |
| V2_direct_image_policyv3_chartdisplay_v2 | main_method | 400 | 400 | 0 | 56.75% | 56.75% | 40.50% | 59.50% | 73.00% | 27.00% | 25.00% |
| V3_C4_group1v2_neutralized | main_method | 400 | 400 | 0 | 50.00% | 50.00% | 0.00% | 100.00% | 100.00% | 0.00% | 41.50% |
| V3_D1_SFT_group1v2_neutralized | main_method | 400 | 400 | 0 | 52.00% | 52.00% | 4.00% | 96.00% | 100.00% | 0.00% | 81.50% |
| V4_C4_tolerant_chartdisplay_v2 | diagnostic_tolerant_method | 400 | 400 | 0 | 50.50% | 50.50% | 61.50% | 38.50% | 39.50% | 60.50% | 20.00% |
| V4_D1_SFT_tolerant_chartdisplay_v2 | diagnostic_tolerant_method | 400 | 400 | 0 | 55.75% | 55.75% | 57.50% | 42.50% | 54.00% | 46.00% | 47.50% |

## 7. pre-D1 附录诊断

pre-D1 D-SFT 结果不再作为主结果，因为它混入了 D-SFT 输出接口/schema 问题。它只用于说明 D1 修正了什么。

| 方法 | total | valid | invalid | binary acc | positive accept | negative reject | invalid rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| V3_D_SFT_pre_D1_group1v2_neutralized | 400 | 370 | 30 | 48.25% | 3.80% | 100.00% | 7.50% |
| V4_D_SFT_pre_D1_tolerant | 400 | 370 | 30 | 52.00% | 57.61% | 54.84% | 7.50% |

## 8. 当前可以说的结论

1. 实验组 6 的 424 反事实核验路线可以独立评估模型是否能判断候选 424 记录与航图证据是否一致。
2. #25 的显示等价修正已经被吸收，避免把整数/小数等显示差异误当作反事实错误。
3. D1 消除了 D-SFT 输出接口错误，使 D-SFT 分支可以参与同一 canonical JSON 比较。
4. V3 的严格 extract-then-compare 对抽取缺陷非常敏感；V4 的 tolerant compare 用来诊断字段等价、航段对齐和 partial evidence 能否缓解这种敏感性。

## 9. 当前不能说的结论

- 不能把 V4 tolerant compare 说成实验组 1 的 scoring-equivalence v2。
- 不能说 V3/V4 直接代表 extractor 的字段抽取准确率；它们测的是候选记录核验中的 extract-then-compare 路线。
- 不能把 pre-D1 D-SFT 作为主结果，因为它含有输出接口/schema failure。
- 在 #25 合并前，v11 是依赖 #25 head 的整理包，不是完全独立于 #25 的最终冻结包。

## 10. 保存文件

- dependency manifest: `formal_runs/experiment6/experiment6_group1formal200_full200_v11_pr25_d1_20260502_r1/configs/experiment6_pr25_dependency_manifest.json`
- run manifest: `formal_runs/experiment6/experiment6_group1formal200_full200_v11_pr25_d1_20260502_r1/configs/v11_run_manifest.json`
- final metrics CSV: `formal_runs/experiment6/experiment6_group1formal200_full200_v11_pr25_d1_20260502_r1/reports/experiment6_v11_final_metrics_table_20260502.csv`
- final metrics JSON: `formal_runs/experiment6/experiment6_group1formal200_full200_v11_pr25_d1_20260502_r1/reports/experiment6_v11_final_metrics_table_20260502.json`
- integrity audit: `formal_runs/experiment6/experiment6_group1formal200_full200_v11_pr25_d1_20260502_r1/reports/experiment6_v11_integrity_no_leakage_audit_20260502.json`
