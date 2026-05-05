# 实验组4最终提交/归档清单

生成时间：2026-05-03T01:40:16.447896+00:00

## 1. 使用口径

- 主结果：`D1 + chart_display_aware_v2`。
- 补充结果：`D_SFT raw` 用于说明 coverage/failure_rate 和输出格式稳定性。
- ROI 来源：`prelabel_not_gold`，已人工确认，但不能写成 gold。

## 2. 必带文件

|文件|状态|大小 bytes|
|---|---:|---:|
|`reports/experiment4_final_execution_report_zh.md`|存在|6375|
|`reports/experiment4_result_analysis_zh.md`|存在|6703|
|`reports/experiment4_final_metrics_table.csv`|存在|5631|
|`reports/experiment4_final_metrics_summary.json`|存在|20324|
|`reports/experiment4_v2_scoring_summary.csv`|存在|1874|
|`reports/experiment4_v2_scoring_summary.json`|存在|383573|
|`reports/experiment4_freeze_manifest.json`|存在|80784|
|`reports/experiment4_analysis_artifacts_manifest.json`|存在|674|
|`reports/experiment4_d1_v2_accuracy_by_variant.png`|存在|42241|
|`reports/experiment4_method_v2_accuracy_by_variant.png`|存在|56256|
|`reports/experiment4_dsft_raw_vs_d1_coverage_failure.png`|存在|47395|
|`manifests/experiment4_evaluation200_chart_ids.json`|存在|107449|
|`source_views/manifests/source_view_manifest.jsonl`|存在|2711849|
|`validation/input_manifest_no_leakage_final_report.json`|存在|5003|
|`validation/source_view_validation_after_residual_guard_report.json`|存在|600|
|`scripts/build_source_views.py`|存在|15037|
|`scripts/prepare_experiment4_manifests.py`|存在|9988|
|`scripts/run_d1_output_canonicalizer.py`|存在|28363|
|`scripts/score_d1_strict.py`|存在|6813|
|`scripts/rescore_experiment4_v2.py`|存在|13175|
|`scripts/summarize_experiment4_results.py`|存在|17234|
|`scripts/create_experiment4_freeze_manifest.py`|存在|5697|
|`scripts/generate_experiment4_analysis_artifacts.py`|存在|23128|

## 3. D1 输出目录

|variant|D1 root|
|---|---|
|`V1_ma_text_only`|`formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1\runs\formal_eval200\V1_ma_text_only\D1`|
|`V2_full_minus_ma_prose`|`formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1\runs\formal_eval200\V2_full_minus_ma_prose\D1`|
|`V3_plan_view_only`|`formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1\runs\formal_eval200\V3_plan_view_only\D1`|
|`V4_icon_detail_only`|`formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1\runs\formal_eval200\V4_icon_detail_only\D1`|
|`V5_plan_detail_no_ma`|`formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1\runs\formal_eval200\V5_plan_detail_no_ma\D1`|

## 4. 提交说明

提交或归档时，优先带上 `reports`、`scripts`、`manifests`、`validation`、`source_views/manifests`，以及 `runs/formal_eval200/*/D1/reports` 和 D1 canonical JSON 输出。大体积 source-view PNG 可按需要单独归档，但冻结清单中已经记录了 source-view 图片目录摘要。
