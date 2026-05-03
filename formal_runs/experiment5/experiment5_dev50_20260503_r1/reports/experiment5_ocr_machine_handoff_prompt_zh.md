# 给另一台 OCR 电脑 Codex 的指令

把下面整段发给另一台有 OCR 环境的 Codex。

```text
请继续实验组5的 dev50 OCR 输入准备和后续运行。

仓库：
https://github.com/reshihihihi/faa-chart-to-424-benchmark.git

分支：
experiment5-diagnostic-20260503

请先执行：

git clone https://github.com/reshihihihi/faa-chart-to-424-benchmark.git
cd faa-chart-to-424-benchmark
git checkout experiment5-diagnostic-20260503
git pull origin experiment5-diagnostic-20260503

先阅读这些交接文件：

formal_runs/experiment5/experiment5_dev50_20260503_r1/reports/experiment5_dev50_execution_status_20260503_zh.md
formal_runs/experiment5/experiment5_dev50_20260503_r1/reports/experiment5_g_admin_execution_report_zh.md
formal_runs/experiment5/experiment5_dev50_20260503_r1/reports/admin_dev50_artifacts_export_report_zh.md

当前已经完成：

1. dev50 固定划分已确认，不能改样本。
2. 后台 dev50 人工审核工件已经导出：
   - formal_runs/experiment5/experiment5_dev50_20260503_r1/admin_artifacts/admin_gold_answer_dev50.jsonl
   - formal_runs/experiment5/experiment5_dev50_20260503_r1/admin_artifacts/admin_field_review_dev50.jsonl
   - formal_runs/experiment5/experiment5_dev50_20260503_r1/admin_artifacts/admin_regions_dev50.jsonl
   - formal_runs/experiment5/experiment5_dev50_20260503_r1/admin_artifacts/admin_evidence_links_dev50.jsonl
3. G0/G1/G3 dev50 已跑完。
4. 当前阻塞只剩 OCR/文字输入：
   - 后台有 MISSED_APPROACH_TEXT 框，但 ocr_text 为空。
   - 需要用你这台电脑的 OCR 能力生成正式 gold_ma_prose 和 ROI OCR。

严禁：

不要把这些答案侧字段作为方法输入：

- target
- score
- canonical_answer
- canonical_leg_index
- Q_terminator
- leg_type
- field_review_v2
- admin_gold_answer_dev50.jsonl
- admin_field_review_dev50.jsonl 中的 canonical_* 字段

这些答案侧工件只允许用于评分、oracle 诊断、错误归因，不能进入 A3/B2/B3/B4/G3 的预测输入。

第一步：生成正式 gold_ma_prose

输入图片优先使用：

formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/ma_text_crops/*_ma_text_crop.png

这些图片是后台 MISSED_APPROACH_TEXT 框裁剪出来的 dev50 复飞文字区域。

如果 OCR 效果不好，可以回到：

formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/pdf_pages/*.png
formal_runs/experiment5/experiment5_dev50_20260503_r1/admin_artifacts/admin_regions_dev50.jsonl

用 admin_regions 里的 MISSED_APPROACH_TEXT bbox 重新裁剪或放大 OCR。

输出文件建议写成：

formal_runs/experiment5/experiment5_dev50_20260503_r1/inputs/gold_ma_text_dev50_ocr_reviewed.jsonl

每行 JSONL 格式：

{
  "chart_id": "KAVL_I17",
  "checked_scopes": ["MISSED_APPROACH_TEXT"],
  "gold_ma_prose": "MISSED APPROACH: ...",
  "source": "admin_ma_text_crop_ocr_reviewed",
  "ocr_engine": "你的OCR引擎名称",
  "review_status": "ocr_reviewed",
  "notes": "不要从 canonical_answer 反推。"
}

要求：

- 50 个 dev50 chart_id 必须都有一行。
- gold_ma_prose 必须是图上复飞文字区域的文字，不是从最终答案反推的文字。
- 可以人工校正 OCR 错字。
- 不要混入 minima、MALSR、A5、灯光系统、页脚等非复飞说明文字，除非它确实是复飞说明句子的一部分。

第二步：用正式 gold_ma_prose 跑 A3/B2 dev50

A3：

python scripts/experiment5/run_experiment5_gold_text_a3.py --run-dir formal_runs/experiment5/experiment5_dev50_20260503_r2_ocr --gold-text formal_runs/experiment5/experiment5_dev50_20260503_r1/inputs/gold_ma_text_dev50_ocr_reviewed.jsonl --limit 50 --force

B2：

先确认本机 openai-compatible API 可用，模型用 gpt-5.4。

python scripts/experiment5/run_experiment5_gold_text_b2.py --run-dir formal_runs/experiment5/experiment5_dev50_20260503_r2_ocr --gold-text formal_runs/experiment5/experiment5_dev50_20260503_r1/inputs/gold_ma_text_dev50_ocr_reviewed.jsonl --methods B2a_GoldText_LLM,B2b_GoldText_FieldCandidates_LLM --model gpt-5.4 --base-url http://127.0.0.1:8080/v1 --limit 50 --max-workers 8 --request-timeout 240 --schema-retry-count 1 --resume-existing

第三步：生成 ROI OCR 输入

输入：

formal_runs/experiment5/experiment5_dev50_20260503_r1/admin_artifacts/admin_regions_dev50.jsonl
formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/pdf_pages/*.png

需要对这些 region_type 做 OCR 或读取框内文字：

- FIX_TEXT
- ALTITUDE_TEXT
- HEADING_TEXT
- RADIAL_TEXT
- TRACK_OR_RADIAL_TEXT
- NAVAID_TEXT
- OUTBOUND_INBOUND_MARK
- MISSED_APPROACH_TEXT

输出建议写成：

formal_runs/experiment5/experiment5_dev50_20260503_r1/inputs/roi_ocr_dev50_ocr_reviewed.jsonl

每行至少包含：

{
  "chart_id": "KAVL_I17",
  "region_id": "KAVL_I17_iconalign_001_fix_text",
  "region_type": "FIX_TEXT",
  "bbox": {...},
  "ocr_text": "BRA",
  "ocr_engine": "你的OCR引擎名称",
  "review_status": "ocr_reviewed"
}

第四步：再跑 B3/B4 dev50

先检查现有 B3/B4 脚本需要的输入格式。如果需要，把 roi_ocr_dev50_ocr_reviewed.jsonl 转成现有 runner 需要的 field_candidates / validation 输入。不要把 admin_field_review 里的 canonical_answer 当成候选输入。

第五步：输出报告

请更新或新建中文报告：

formal_runs/experiment5/experiment5_dev50_20260503_r2_ocr/reports/experiment5_dev50_ocr_run_status_zh.md

报告必须写清：

- OCR 引擎
- gold_ma_prose 覆盖率：50/50 是否齐全
- ROI OCR 覆盖率
- A3/B2/B3/B4 结果
- no-leakage 检查
- 哪些文件是方法输入，哪些文件只用于评分

如果发现现有脚本缺少转换器，可以新增脚本到 scripts/experiment5/，但要保持输入边界不泄漏答案。
```
