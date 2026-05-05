# 实验组5 dev50 当前执行状态

更新时间：2026-05-03

## 加速策略

本轮加速只做工程层优化，不改变实验效果：

- 模型不变：`gpt-5.4`
- 输入不变：仍使用后台导出的 dev50 工件
- 提示词语义不变：不加入 target、score、canonical_answer、canonical_leg_index、Q_terminator、leg_type、field_review_v2 等答案侧字段
- 评分不变：统一对 `admin_gold_answer_dev50.jsonl` 评分
- 加速方式：提高并发、断点复用、schema retry、避免重复模型调用

已落地：

- `run_experiment5_admin_g_methods.py`
  - 增加 `--resume-existing`
  - G3 增加 `--schema-retry-count`
  - 报告中记录 schema retry 数
  - 复用样本仍重新做 forbidden key 扫描
- `run_experiment5_gold_text_b2.py`
  - 增加 `--resume-existing`
  - 复用前检查 input payload 和 prompt 一致，避免错误复用旧输出

## 已完成

1. dev50 划分确认

- 使用 formal300 的固定 development 50。
- dev50 与 evaluation200、probe50 无重叠。
- 注意：不能使用 `previous_dataset_split` 字段做当前实验划分。

2. 后台人工审核工件导出

输出目录：

- `formal_runs/experiment5/experiment5_dev50_20260503_r1/admin_artifacts/`
- `formal_runs/experiment5/experiment5_dev50_20260503_r1/inputs/`

已导出：

- `admin_gold_answer_dev50.jsonl`：50 个最终人工答案，只用于评分或审计
- `admin_field_review_dev50.jsonl`：542 条字段审核关系
- `admin_regions_dev50.jsonl`：393 个后台框
- `admin_evidence_links_dev50.jsonl`：542 条字段-证据关系
- `gold_observable_dev50_accept.jsonl`：去答案字段后的 accept observable
- `gold_observable_dev50_accept_pending.jsonl`：去答案字段后的 accept+pending observable

3. G 系列 dev50 已跑通

运行参数：

```text
model: gpt-5.4
base_url: http://127.0.0.1:8080/v1
max_workers: 8
schema_retry_count: 1
gold_observable: gold_observable_dev50_accept_pending.jsonl
```

结果：

| 方法 | 输入边界 | schema-valid | v2 正确/总数 | v2 accuracy |
|---|---|---:|---:|---:|
| G0_Direct | 后台 direct_visible 字段关系，oracle 诊断 | 50/50 | 274/1010 | 27.13% |
| G1_Rules | 后台 direct_visible + rule_default_completion 字段关系，oracle 诊断 | 50/50 | 600/1010 | 59.41% |
| G3_LLM_Rules | 去答案字段后的 gold_observable + prompt 规则 | 50/50 | 76/1010 | 7.52% |

G3 no-leakage 检查：

- `g3_method_input_forbidden_key_hits`: 0
- `g3_uses_admin_gold_answer_for_prediction`: false
- `g3_uses_field_review_for_prediction`: false

## 当前问题

1. G3 准确率低

G3 已经不是 schema 问题。schema retry 后 50/50 都合格，但准确率只有 7.52%。

主要原因是当前 `gold_observable` 是方法安全的可见事实输入，它包含框、region type、visible label、bbox、accept/pending 状态，但不包含答案侧的航段绑定、leg_count、Q_terminator 或 canonical_leg_index。
所以 G3 很难恢复完整航段序列和终止符：

- `leg_count`: 0/50
- `Q_terminator`: 0/160
- `Q1_fix_ident`: 5/160
- `Q2_altitude_constraint`: 15/160
- `Q4_course_or_radial`: 3/160

这说明：如果只给 answer-stripped observable，当前信息量不足以作为完整 blind predictor，但可以用于验证“只靠可见事实能恢复多少”。

2. 正式 `gold_ma_prose` 还没有准备好

后台有 `MISSED_APPROACH_TEXT` 框，但当前导出的 `ocr_text` 为空：

- formal300 中 300 个 `MISSED_APPROACH_TEXT` 框存在
- `ocr_text` 非空数量：0
- dev50 的 `MISSED_APPROACH_TEXT` 框存在
- dev50 的 `ocr_text` 非空数量：0

之前用 PDF text layer 自动抽过一个候选文件，但它会混入 minima、MALSR、A5 等非复飞文字，不能作为正式 gold prose。

3. ROI OCR 还不能正式跑

后台框已经足够生成 ROI crop，但当前缺少 OCR 文本来源：

- 后台导出没有 OCR 文本
- 本机未安装 `tesseract`
- 本机未安装 `pytesseract`
- 本机未安装 `easyocr`
- 本机未安装 `paddleocr`

因此，B3/B4 如果要正式用 ROI OCR 输入，还需要先补 OCR 引擎或让后台导出 OCR 结果。

## 下一步

推荐继续顺序：

1. 先补正式 `gold_ma_prose`
   - 优先方案：从后台导出 `MISSED_APPROACH_TEXT` 框对应的人工文本或 OCR 文本。
   - 备选方案：用后台框裁剪 dev50 MA_TEXT 图片，接 OCR，再人工校正。
   - 禁止方案：从 `canonical_answer` 反推 prose。

2. 用正式 `gold_ma_prose` 跑 A3/B2 dev50
   - A3：规则方法，速度快。
   - B2：LLM 方法，使用 `--max-workers 8 --resume-existing`。

3. 补 ROI OCR 输入后跑 B3/B4 dev50
   - ROI 框直接来自后台 `admin_regions`。
   - OCR 文本必须来自 OCR/人工转写，不能来自最终字段答案。

4. dev50 全部方法确认无泄漏、无 schema 问题后，再扩展到 formal200。
