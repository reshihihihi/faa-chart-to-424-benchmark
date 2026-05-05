# 给另一台电脑 Codex 的交接指令：实验组5 dev50 后台输入优先

把下面整段发给另一台电脑的 Codex。注意：这里已经不再是“OCR 优先”的交接，dev50 的主输入源是 shujuji admin 后台的人工审核关系。

```text
请继续实验组5 dev50 输入准备与运行。

repo: https://github.com/reshihihihi/faa-chart-to-424-benchmark.git
branch: experiment5-diagnostic-20260503

先执行：
git clone https://github.com/reshihihihi/faa-chart-to-424-benchmark.git
cd faa-chart-to-424-benchmark
git checkout experiment5-diagnostic-20260503
git pull origin experiment5-diagnostic-20260503

先阅读：
formal_runs/experiment5/experiment5_dev50_20260503_r1/reports/experiment5_dev50_execution_status_20260503_zh.md
formal_runs/experiment5/experiment5_dev50_20260503_r1/reports/experiment5_g_admin_execution_report_zh.md
formal_runs/experiment5/experiment5_dev50_20260503_r1/reports/admin_dev50_artifacts_export_report_zh.md
formal_runs/experiment5/experiment5_detailed_experiment_plan_zh.md

核心理解：
实验组5是诊断实验，不是排行榜。dev50 用来冻结输入转换、方法边界、no-leakage 检查和运行策略；evaluation200 只能在 dev50 策略固定后按同一规则执行，不能用来调参。

dev50 需要的输入以 shujuji admin 后台 formal300 submissions 为准。后台提供的是一套完整人工审核关系：
- regions/boxes
- legs/fields
- field_reviews
- evidence links / evidence_provenance
- annotation_pr28_json 最终字段答案
- 每个字段和证据框之间的关系

先从后台导出/下载最新 formal300 export。不要把 admin token 写进仓库；在本机环境变量里设置：

PowerShell:
$env:SHUJUJI_ADMIN_TOKEN='<用户提供的 admin_token>'
python scripts/experiment5/download_shujuji_admin_export.py --output-dir downloads/experiment5_admin

然后用下载脚本 JSON 输出里的 output_path 重新生成 dev50 后台工件：

python scripts/experiment5/export_admin_dev50_artifacts.py --admin-export <output_path> --run-dir formal_runs/experiment5/experiment5_dev50_20260503_r1
python scripts/experiment5/build_experiment5_dev50_admin_observables.py --run-dir formal_runs/experiment5/experiment5_dev50_20260503_r1

也可以打开 downloads/experiment5_admin/latest_download_summary.json，使用其中记录的 output_path。

已经存在/需要核对的 dev50 工件：
- formal_runs/experiment5/experiment5_dev50_20260503_r1/admin_artifacts/admin_gold_answer_dev50.jsonl
- formal_runs/experiment5/experiment5_dev50_20260503_r1/admin_artifacts/admin_field_review_dev50.jsonl
- formal_runs/experiment5/experiment5_dev50_20260503_r1/admin_artifacts/admin_regions_dev50.jsonl
- formal_runs/experiment5/experiment5_dev50_20260503_r1/admin_artifacts/admin_evidence_links_dev50.jsonl
- formal_runs/experiment5/experiment5_dev50_20260503_r1/inputs/admin_regions_sanitized_dev50.jsonl
- formal_runs/experiment5/experiment5_dev50_20260503_r1/inputs/gold_observable_dev50_accept.jsonl
- formal_runs/experiment5/experiment5_dev50_20260503_r1/inputs/gold_observable_dev50_accept_pending.jsonl

输入边界必须写清楚：
- admin_gold_answer_dev50.jsonl 是最终人工答案，只能评分/审计。
- admin_field_review_dev50.jsonl 和 admin_evidence_links_dev50.jsonl 是完整人工审核关系，只能用于 G0/G1 oracle replay、诊断和错误归因；其中 canonical_answer/canonical_leg_index/leg_type/support_mode 不能进入 A3/B2/B3/B4/G3 的 blind 方法输入。
- gold_observable_dev50_accept*.jsonl 是从后台 regions 派生的 answer-stripped method-safe observable，可用于 G3。
- 后台 regions 的 label、bbox、region_type、review_action 可以作为可见证据输入；accepted_mappings、canonical_answer、canonical_leg_index、final_value 等答案侧内容不能混入 blind 方法输入。

优先做的不是 OCR，而是后台关系解析：
1. 核对 latest admin export 覆盖 formal300 300/300，并确认 dev50 50/50 都有 final submission。
2. 重新导出 dev50 的 gold answer、field review、regions、evidence links。
3. 重新生成 answer-stripped gold_observable，并跑 forbidden-key/no-leakage 扫描。
4. 运行或复核 G0/G1/G3 dev50：
   - G0_Direct: 只作为 direct_visible oracle replay，允许使用 field_review 答案侧关系，诊断里必须标记 uses_canonical_answer=True。
   - G1_Rules: direct_visible + rule_default_completion oracle replay，同样只作为诊断上限。
   - G3_LLM_Rules: 只能用 gold_observable answer-stripped input。
5. A3/B2 的 gold_ma_prose 只有在后台存在 chart-side 复飞文字/人工确认文本源时才从后台导出；不能从 annotation_pr28_json、canonical_answer、accepted_mappings、final_value 反推 prose。
6. B3/B4 的 ROI 输入优先从后台 region_type/label/bbox/review_action 解析可见文本和候选；必须剥离答案侧字段，不能把最终字段答案当方法输入。

严禁把这些字段作为 A3/B2/B3/B4/G3 方法输入：
- target
- score
- canonical_answer
- canonical_leg_index
- Q_terminator
- leg_type
- field_review_v2
- accepted_mappings.canonical_answer
- accepted_mappings.final_value
- annotation_pr28_json

最后输出中文状态报告，写清：
- 使用的后台 export 文件名和时间
- dev50 覆盖率
- 每类工件的用途：方法输入 / 评分 / oracle 诊断
- no-leakage 检查结果
- G0/G1/G3 结果
- A3/B2/B3/B4 是否已有合法后台输入；如果没有合法 chart-side 文本源，明确标记 blocked，不要用最终答案反推。
```
