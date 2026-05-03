# 实验组4 source-view ablation 最终结果包

本目录是实验组4结果在仓库中的 freeze 摘要。完整可复现产物位于：

- `formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1`

## 主分析口径

- 主结果：`D1 + chart_display_aware_v2`
- 补充结果：`D_SFT raw` 用于说明 coverage/failure_rate 和输出格式稳定性
- ROI 来源：`prelabel_not_gold`，已人工确认，但不能写成 gold
- PR25 关系：沿用 Group 1 scoring-equivalence v2 和 D1 fixed-output-interface 口径

## 关键结论

1. D_SFT/D1 并不是只靠 missed approach 文本框；遮挡 MA prose 后的 `V2_full_minus_ma_prose` 仍保持较高 D1 v2 accuracy。
2. `plan view` 是最关键的信息来源；`detail/icon` 有补充价值，但单独不足。
3. C4 在 `V1_ma_text_only` 上更好，说明 OCR/规则方法更直接依赖 MA prose。
4. `V1_ma_text_only` 的 D1 低分不代表文字框无信息，而是 D_SFT 在只给局部文本框时输出结构失稳；D1 只修格式，不补答案。

## 文件

- `formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1/reports/experiment4_result_analysis_zh.md`
- `formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1/reports/experiment4_final_metrics_table.csv`
- `formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1/reports/experiment4_freeze_manifest.json`
- `formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1/reports/experiment4_submission_package_manifest_zh.md`
