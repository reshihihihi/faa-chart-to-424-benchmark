# 实验组4 source-view ablation 最终执行报告

生成时间：2026-05-02T11:55:40.587414+00:00

## 实验目的

实验组4用于检查 missed approach 信息来自不同航图区域时，对 Group1 冻结方法输出质量的影响。V0 复用实验组1整图 baseline；V1-V5 使用人工确认后的 source-view 图像。

## 输入与边界

- 评估集：Group1 冻结 formal300 split 中的 evaluation 200 张。
- ROI 来源：`prelabel_not_gold`，已经人工检查确认可用于本实验；报告中不得把该 ROI 当成 gold。
- OCR：B1/C4 使用与实验组1一致的 OCR-1 路径；D_SFT 不使用 OCR。
- V0：复用实验组1冻结整图结果，不重跑。
- C4：已在 `formal_eval200` 下找到 V1-V5 的正式输出，并纳入 strict 与 PR25 v2 分析。
- D1：按 PR #25 的 D1 fixed-output-interface 策略，对 D_SFT raw output 做统一 canonicalization 后纳入评分；D1 不使用 target、score、424/CIFP raw、OCR 或其他方法输出来修字段答案。

## Variant 定义

- `V0_full_chart`：实验组1整图 baseline。
- `V1_ma_text_only`：只保留 missed approach 文本框。
- `V2_full_minus_ma_prose`：整图遮挡 missed approach 文字说明。
- `V3_plan_view_only`：只保留 plan view 大框。
- `V4_icon_detail_only`：只保留 missed approach detail/icon 大框。
- `V5_plan_detail_no_ma`：保留 plan view 与 detail/icon，但不保留 missed approach 文字说明。

## Strict Scoring 汇总

|variant|method|status|samples|schema_valid|scored|failures|accuracy|coverage|failure_rate|
|---|---|---|---|---|---|---|---|---|---|
|V0_full_chart|B1|complete|200|200|200|0|0.272458|1.000000|0.000000|
|V0_full_chart|C4|complete|200|200|200|0|0.400790|1.000000|0.000000|
|V0_full_chart|D_SFT|complete_with_method_failures|200|184|184|16|0.735499|0.920000|0.080000|
|V0_full_chart|D1|complete|200|200|200|0|0.733465|1.000000|0.000000|
|V1_ma_text_only|B1|complete|200|200|200|0|0.286278|1.000000|0.000000|
|V1_ma_text_only|C4|complete|200|200|200|0|0.478776|1.000000|0.000000|
|V1_ma_text_only|D_SFT|complete|200|4|4|196|0.697368|0.020000|0.980000|
|V1_ma_text_only|D1|complete|200|200|200|0|0.019497|1.000000|0.000000|
|V2_full_minus_ma_prose|B1|complete|200|200|200|0|0.181885|1.000000|0.000000|
|V2_full_minus_ma_prose|C4|complete|200|200|200|0|0.365252|1.000000|0.000000|
|V2_full_minus_ma_prose|D_SFT|complete|200|180|180|20|0.689182|0.900000|0.100000|
|V2_full_minus_ma_prose|D1|complete|200|200|200|0|0.673248|1.000000|0.000000|
|V3_plan_view_only|B1|complete|200|200|200|0|0.030109|1.000000|0.000000|
|V3_plan_view_only|C4|complete|200|200|200|0|0.317621|1.000000|0.000000|
|V3_plan_view_only|D_SFT|complete|200|144|144|56|0.581956|0.720000|0.280000|
|V3_plan_view_only|D1|complete|200|200|200|0|0.547631|1.000000|0.000000|
|V4_icon_detail_only|B1|complete|200|200|200|0|0.000000|1.000000|0.000000|
|V4_icon_detail_only|C4|complete|200|200|200|0|0.007897|1.000000|0.000000|
|V4_icon_detail_only|D_SFT|complete|200|13|13|187|0.723320|0.065000|0.935000|
|V4_icon_detail_only|D1|complete|200|200|200|0|0.082675|1.000000|0.000000|
|V5_plan_detail_no_ma|B1|complete|200|200|200|0|0.063919|1.000000|0.000000|
|V5_plan_detail_no_ma|C4|complete|200|200|200|0|0.282083|1.000000|0.000000|
|V5_plan_detail_no_ma|D_SFT|complete|200|151|151|49|0.647020|0.755000|0.245000|
|V5_plan_detail_no_ma|D1|complete|200|200|200|0|0.620188|1.000000|0.000000|

当前 strict_group1_freeze 最高准确率为 V0_full_chart / D1：0.733465。

## PR25 v2 Scoring 汇总

|variant|method|status|samples|schema_valid|scored|failures|accuracy|coverage|failure_rate|
|---|---|---|---|---|---|---|---|---|---|
|V0_full_chart|B1|complete|200|200|200|0|0.273939|1.000000|0.000000|
|V0_full_chart|C4|complete|200|200|200|0|0.404245|1.000000|0.000000|
|V0_full_chart|D_SFT|complete|200|184|184|16|0.781418|0.920000|0.080000|
|V0_full_chart|D1|complete|200|200|200|0|0.779368|1.000000|0.000000|
|V1_ma_text_only|B1|complete|200|200|200|0|0.287759|1.000000|0.000000|
|V1_ma_text_only|C4|complete|200|200|200|0|0.480750|1.000000|0.000000|
|V1_ma_text_only|D_SFT|complete|200|4|4|196|0.697368|0.020000|0.980000|
|V1_ma_text_only|D1|complete|200|200|200|0|0.019497|1.000000|0.000000|
|V2_full_minus_ma_prose|B1|complete|200|200|200|0|0.194965|1.000000|0.000000|
|V2_full_minus_ma_prose|C4|complete|200|200|200|0|0.388450|1.000000|0.000000|
|V2_full_minus_ma_prose|D_SFT|complete|200|180|180|20|0.734761|0.900000|0.100000|
|V2_full_minus_ma_prose|D1|complete|200|200|200|0|0.717670|1.000000|0.000000|
|V3_plan_view_only|B1|complete|200|200|200|0|0.033070|1.000000|0.000000|
|V3_plan_view_only|C4|complete|200|200|200|0|0.330948|1.000000|0.000000|
|V3_plan_view_only|D_SFT|complete|200|144|144|56|0.599862|0.720000|0.280000|
|V3_plan_view_only|D1|complete|200|200|200|0|0.564906|1.000000|0.000000|
|V4_icon_detail_only|B1|complete|200|200|200|0|0.000000|1.000000|0.000000|
|V4_icon_detail_only|C4|complete|200|200|200|0|0.008638|1.000000|0.000000|
|V4_icon_detail_only|D_SFT|complete|200|13|13|187|0.723320|0.065000|0.935000|
|V4_icon_detail_only|D1|complete|200|200|200|0|0.082675|1.000000|0.000000|
|V5_plan_detail_no_ma|B1|complete|200|200|200|0|0.070829|1.000000|0.000000|
|V5_plan_detail_no_ma|C4|complete|200|200|200|0|0.290967|1.000000|0.000000|
|V5_plan_detail_no_ma|D_SFT|complete|200|151|151|49|0.664472|0.755000|0.245000|
|V5_plan_detail_no_ma|D1|complete|200|200|200|0|0.637463|1.000000|0.000000|

当前 chart_display_aware_v2 最高准确率为 V0_full_chart / D_SFT：0.781418。

## 文件位置

- source-view 图像：`formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1\source_views\images`
- source-view manifest：`formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1\source_views\manifests\source_view_manifest.jsonl`
- OCR 输出：`formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1\ocr_artifacts`
- 正式运行输出：`formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1\runs\formal_eval200`
- v2 分样本评分：`formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1\scores\v2`
- 最终结果表 CSV：`formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1\reports\experiment4_final_metrics_table.csv`

## 参数解释

`samples` 是该方法/variant 应评估样本数；`schema_valid` 是输出 JSON 通过 schema 的样本数；`scored` 是实际进入评分的样本数；`failures = samples - scored`；`accuracy = correct / total`；`coverage = scored / samples`；`failure_rate = failures / samples`。
