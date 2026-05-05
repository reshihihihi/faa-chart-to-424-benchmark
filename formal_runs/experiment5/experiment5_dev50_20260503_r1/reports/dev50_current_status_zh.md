# 实验组5 dev50 当前状态

生成时间：2026-05-03

## 样本边界

- 本轮 50 个样本严格来自 `formal300_50_200_50_seed20260437` 的 `dataset_split=development`。
- 没有使用 `previous_dataset_split`。dev50 内部 `previous_dataset_split` 分布为 development 34、evaluation 12、probe 4，说明这个历史字段不能用于本轮选择。
- dev50 与正式 evaluation 200 的 chart/sample 交集均为 0；与 probe 50 的 chart/sample 交集均为 0。
- 审计文件：`formal_runs/experiment5/experiment5_dev50_20260503_r1/reports/dev50_split_audit.json`。

## 已完成输入

- `dev50_chart_manifest.jsonl`：50/50，方法安全样本边界文件，不含 target/canonical/CIFP 答案字段。
- `admin_regions_sanitized_dev50.jsonl`：393 行，来自 admin export 的区域证据，已去掉 accepted/candidate mappings、field review 结构和答案侧字段。
- `gold_observable_dev50_admin.jsonl`：50/50，直接从 admin 框标注的 `region_type`、`label`、`bbox`、`review_action` 等可观察字段解析得到。
- `gold_observable_dev50_admin_facts.jsonl`：396 条扁平 observable fact。
- `gold_ma_text_dev50_candidate.jsonl`：50/50，从 FAA PDF text layer + 去泄漏 MA_TEXT bbox 自动抽取；这是临时 A3/B2 跑通工件，不应作为正式主输入。
- admin box overlay 图已生成：`formal_runs/experiment5/experiment5_dev50_20260503_r1/visuals/dev50_admin_box_overlays_contact_sheet.png`。

## 已跑方法

| 方法 | 输入 | schema-valid | v2 正确/总数 | v2 accuracy | failure |
|---|---|---:|---:|---:|---:|
| `A3_GoldText_Rules` | dev50 PDF-bbox MA prose candidate | 50/50 | 610/1010 | 60.40% | 0 |
| `B2a_GoldText_LLM` | dev50 PDF-bbox MA prose candidate | 50/50 | 261/1010 | 25.84% | 0 |
| `B2b_GoldText_FieldCandidates_LLM` | dev50 PDF-bbox MA prose candidate + regex candidates | 50/50 | 275/1010 | 27.23% | 0 |

模型：`gpt-5.4` via local `openai-oauth` API。B2 本轮使用 `--max-workers 4`，100 次模型调用约 216 秒完成。并发只改变调度速度，不改变模型、prompt、输入、schema 或 scorer。

No-leakage 审查：

- A3：`hard_leakage_detected=false`，forbidden key hits `{}`。
- B2a/B2b：`hard_leakage_detected=false`，forbidden key hits `{}`。
- target/score 仅在 prediction 写盘后用于评分，没有进入方法输入。

## 主要问题

1. 之前用 PDF text-layer + MA_TEXT bbox 自动抽 `gold_ma_prose` 是不合适的主路径，容易混入最低标准、灯光标识、温度限制等非复飞文本。这个工件只能保留为临时跑通输入。
2. 正确路径应以 admin 框标注为主：框本身已经给出了 `FIX_TEXT`、`ALTITUDE_TEXT`、`HEADING_TEXT`、`RADIAL_TEXT`、`CLIMB_ARROW`、`FIX_SYMBOL` 等可观察证据。
3. 目前已经从 admin 框标注生成 `gold_observable_dev50_admin.jsonl`，forbidden key 扫描为 0；但 G0/G1/G3 runner 还未实现/运行。
4. 本机没有原始 `source_views` 和 ROI OCR artifacts，所以不能重新 prepare dev50 的 B3/B4 ROI 输入；B3/B4 目前只能用已经补全的 r4 smoke20 工件，除非恢复原始 ROI/OCR 工件。
5. A3/B2 runner 的旧报告标题仍写着 smoke/gold text，这是复用脚本的命名问题；实际 run manifest 和 chart_ids 是 dev50 的 50 个样本。

## 下一步

1. 先基于 `gold_observable_dev50_admin.jsonl` 写 G0/G1/G3 runner，跑 dev50。
2. 对 admin 框中 `review_action=pending` 的细节框做 policy：是否允许进入 G 方法输入，还是只允许 `accept` 框。
3. 如仍需要 A3/B2 的 gold prose 条件，应从 admin MA_TEXT 框对应的人类文本/OCR字段补齐；不要再依赖 PDF text-layer 自动抽取作为正式 gold。
4. 若要 dev50 覆盖 B3/B4，先恢复 `external_artifact://E/experiment3\zu4\source_views` 和对应 ROI OCR artifacts；否则不要重建 ROI 输入。
5. dev50 全方法跑通并修正输入问题后，再冻结配置，最后只对 `dataset_split=evaluation` 的正式 200 样本跑 full experiment。
