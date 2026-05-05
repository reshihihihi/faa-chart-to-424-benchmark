# 实验组5 dev50 样本边界与输入可用性审计

- 生成时间 UTC: `2026-05-03T08:55:51.180602+00:00`
- split manifest: `benchmark_exports/derived/v2/formal300/split_candidates/split_50_200_50_seed20260437/sample_manifest_50_200_50_seed20260437.jsonl`
- 选择规则: `row.dataset_split == 'development'`
- 是否使用 previous_dataset_split: `False`
- split 计数: `{'development': 50, 'evaluation': 200, 'probe': 50}`
- dev50 样本数: 50
- dev50 与 evaluation chart/sample 交集: 0/0
- dev50 与 probe chart/sample 交集: 0/0
- 审计结论 pass: `True`

## 关键说明

- 这 50 个样本来自 `dataset_split=development`，不是文件前 50 行，也不是 `previous_dataset_split=development`。
- dev50 内部的 `previous_dataset_split` 分布不一致，这是历史字段，不能用于本轮选择。
- 输出的 `dev50_chart_manifest.jsonl` 删除了 target/canonical/CIFP 路径和答案字段，只保留样本边界与非答案元数据。
- 从 admin export 抽出的 `admin_regions_sanitized_dev50.jsonl` 只保留区域框、区域类型、label/notes/OCR 文本等可观察来源；已丢弃 accepted/candidate mappings 与 field review 结构。

## 输入可用性

- 本地完整 formal300 PDF 文件数: 0/50
- 本地完整 formal300 image 文件数: 0/50
- source_view manifest 存在: `False`
- admin export dev50 submission: 50/50
- 去泄漏 admin region 行数: 393

## 方法状态

| 方法 | 当前状态 | 原因 |
|---|---|---|
| `A3_GoldText_Rules` | `blocked_until_dev50_gold_ma_prose` | dev50 gold_ma_prose is not yet adjudicated. |
| `B2a_GoldText_LLM` | `blocked_until_dev50_gold_ma_prose` | dev50 gold_ma_prose is not yet adjudicated. |
| `B2b_GoldText_FieldCandidates_LLM` | `blocked_until_dev50_gold_ma_prose` | gold text field candidates must be derived only from dev50 gold_ma_prose. |
| `B3_T_B3_TPD_B3_PD_B4_TPD` | `blocked_missing_local_roi_source_views_and_ocr` | The original source_view manifest and ROI OCR artifact manifests are not present on this machine. |
| `G0_G1_G3` | `source_available_needs_gold_observable_conversion` | Admin export has region annotations, but a method-safe gold_observable file still needs to be constructed and audited. |

## 下一步

1. 先制作 dev50 的 `gold_ma_prose`，再用同一个 A3/B2 runner 跑 50 样本。
2. 用 `admin_regions_sanitized_dev50.jsonl` 构建无泄漏 `gold_observable_dev50.jsonl`，通过 forbidden-key 审计后再跑 G0/G1/G3。
3. B3/B4 需要恢复原始 source_views 与 ROI OCR artifacts；当前机器没有这些工件，不能重新 prepare ROI 输入。
