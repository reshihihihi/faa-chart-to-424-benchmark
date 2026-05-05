# 实验组 1 D2 对照实验汇总：D1_DEV50_ONLY 继续训练证据框 grounding 方法

日期：2026-05-05

## 1. 本文档记录的实验

本文档记录当前对话中实际完成的第二个对照实验。为避免和仓库中的正式 method id 混淆，本文把它简称为 `D2`：

```text
D2 = D1_DEV50_ONLY checkpoint
     -> 继续训练 D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL
     -> 仍按旧 canonical JSON 路径评分
```

对应的正式 method id 仍然是：

```text
D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL
```

`D2` 不是新的 scorer 格式，不是两阶段推理，也不是 D1_DEV400。它只是把 `D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL` 的继续训练起点从旧 D1 checkpoint 换成了 `D1_DEV50_ONLY` checkpoint。

## 2. 实验目的

这个实验要回答的问题是：

```text
如果 D1 底座只用 first 50 中的训练样本训练过，
再继续用同一批 first 50 的人工证据框/字段 grounding 监督训练，
是否能形成和旧 D1 继续训练证据方法相近的 canonical JSON 输出能力？
```

它的直接对照是当前远端分支 `group1-sft-extension-plan-20260503` 最新提交 `59b8dce3 Document D1 evidence method dev50 validation` 记录的实验：

```text
旧 D1 checkpoint
-> D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL
-> dev50 canonical score = 700 / 1010
```

当前 `D2` 的不同点只有继续训练起点：

```text
D1_DEV50_ONLY checkpoint
-> D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL
```

其它原则保持对齐：

- 使用同一个 first 50 数据来源。
- 使用同一个 40/10 train/dev 划分。
- 训练时学习证据框、字段 grounding 和最终 canonical answer。
- 正式评分仍只使用旧 canonical JSON。
- `evidence_boxes` 和 `answer_grounding` 只作为训练/诊断对象，不作为 scorer 输入。

## 3. 代码基线和 PR scope

执行时仓库 HEAD：

```text
branch: exec/group1-e5-run
upstream: origin/group1-sft-extension-plan-20260503
HEAD: 59b8dce3 Document D1 evidence method dev50 validation
```

相关代码文件已经存在于当前分支，本次 D2 执行没有为了实验方向修改推理或训练入口脚本。相关代码包括：

- `scripts/group1_sft/build_d1_evidence_boxes_canonical_jsonl_from_annotations.py`
- `scripts/group1_sft/train_qwen2vl_group1_sft_lora.py`
- `scripts/group1_sft/run_qwen2vl_group1_sft_inference.py`
- `scripts/group1_sft/prepare_group1_sft_run_package.py`
- `scripts/run_d1_output_canonicalizer.py`
- `scripts/scorers/group1_canonical_field_scorer_v2.py`
- `training/group1_sft/prompts/d1_chart_to_evidence_boxes_and_canonical.zh.md`
- `training/group1_sft/manifests/d1_chart_to_evidence_boxes_and_canonical.schema.json`
- `docs/d1_output_canonicalization_policy_zh.md`
- `docs/d1_method_card_zh.md`

本 PR 新增的是这份实验执行汇总文档。大型本地实验产物不纳入 git：

- `training/group1_sft/configs/local_paths.local.json`
- checkpoint
- train/dev JSONL
- PNG 图片
- raw model outputs
- canonicalized outputs
- per-sample score JSON

## 4. 数据来源和训练集构建

训练数据来自标注后台已有的人工审核关系，包括：

- 图上框的位置、类型、可见文字。
- 框和 missed approach 航段的关系。
- 框和 canonical 字段的关系。
- 字段答案和证据框的 grounding 关系。
- 人工审核后的最终 canonical 字段答案。

使用固定 `50+200+50` 划分：

- first 50：允许用于训练和开发验证。
- middle 200：正式评估。
- last 50：本轮不使用。

当前 D2 使用 first 50 构建：

| split | rows | local artifact |
|---|---:|---|
| train | 40 | `group1_sft_local/train_jsonl/d1_evidence_boxes_and_canonical_multitask_train.jsonl` |
| dev | 10 | `group1_sft_local/train_jsonl/d1_evidence_boxes_and_canonical_multitask_dev.jsonl` |

训练报告记录的 sha256：

```text
train sha256 = 09c908e3ea8c0b23bf84f8acf9d1758392fa8a4b1b41f0351f056ccd6e55fa12
dev   sha256 = cd77608422dbcce9f49d95b568109032c65905a64a096f9b738299f8458cd893
```

训练样本输入只包含：

- 完整航图图片。
- `D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL` 专用 prompt。

禁止进入模型输入的内容：

- evaluation 200 labels。
- probe 50 labels。
- scorer output。
- 其它方法预测。
- raw 424 record。
- raw CIFP record。

## 5. 训练目标 JSON 形状

训练时 assistant label 是一个诊断 wrapper：

```json
{
  "evidence_boxes": [],
  "answer_grounding": [],
  "canonical_prediction": {}
}
```

三个字段含义：

- `evidence_boxes`：图上证据框。
- `answer_grounding`：每个航段、每个字段由哪些 box 支持。
- `canonical_prediction`：旧 D1 missed approach canonical JSON。

关键边界：

```text
canonical_prediction 是唯一最终答案对象。
evidence_boxes 和 answer_grounding 不进入正式 scorer。
```

## 6. 证据框设计

当前 schema 限制：

```text
evidence_boxes maxItems = 8
box_id 最大到 box_008
```

这次不是“三个粗框”。实际 first 50 中每张图包含多个证据框：

| statistic | value |
|---|---:|
| rows | 50 |
| min evidence boxes per chart | 4 |
| max evidence boxes per chart | 8 |
| avg evidence boxes per chart | 6.62 |
| min answer grounding items per chart | 8 |
| max answer grounding items per chart | 16 |
| avg answer grounding items per chart | 10.84 |

region type 分布：

| region_type | count |
|---|---:|
| `CLIMB_ARROW` | 70 |
| `ALTITUDE_TEXT` | 63 |
| `FIX_TEXT` | 55 |
| `MISSED_APPROACH_TEXT` | 47 |
| `FIX_SYMBOL` | 42 |
| `PLAN_VIEW` | 42 |
| `RADIAL_TEXT` | 3 |
| `PATH_SEGMENT` | 3 |
| `NAVAID_TEXT` | 2 |
| `HEADING_TEXT` | 2 |
| `OUTBOUND_INBOUND_MARK` | 2 |

设计原则：

- 优先使用细框：fix text、altitude text、climb arrow、fix symbol、course/radial text 等。
- 保留必要大框：`PLAN_VIEW`、`MISSED_APPROACH_TEXT` 用作上下文。
- 一个字段允许对应多个证据框。
- 如果字段来自规则默认，不假装它是直接可见证据。

## 7. 训练设置

训练起点：

```text
group1_sft_local/checkpoints/D1_DEV50_ONLY/
  d1_dev50_only_20260504_r2/checkpoint-final
```

输出 checkpoint：

```text
group1_sft_local/checkpoints/D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL/
  d1_evidence_after_d1_dev50_dev50_multitask_20260504_r3/checkpoint-final
```

训练配置：

| item | value |
|---|---|
| base model | `models/qwen2_vl_2b_base` |
| initial adapter | `D1_DEV50_ONLY/d1_dev50_only_20260504_r2/checkpoint-final` |
| method id | `D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL` |
| epochs | 1 |
| train rows | 40 |
| dev rows | 10 |
| global steps | 40 |
| optimizer steps | 5 |
| learning rate | `2e-4` |
| gradient accumulation | 8 |
| max sequence length | 4096 |
| compute dtype | `float16` |
| load in 4bit | true |
| LoRA r | 8 |
| LoRA alpha | 16 |
| LoRA dropout | 0.05 |
| seed | 260503 |

训练结果：

| metric | value |
|---|---:|
| best dev loss | 0.24679685533046722 |
| truncated train samples | 13 |
| max train seq length seen | 4340 |
| dev eval samples | 10 |
| dev truncated count | 2 |
| max dev seq length seen | 4497 |

注意：`dev_loss` 是 teacher-forcing 下的 token loss，不等价于实际自由生成质量。

## 8. 推理和评分路径

正式评分必须和旧 D1 对齐。因此 dev50 和 formal200 推理时不让 scorer 读取外层 wrapper，而是走旧 canonical JSON 路径：

```text
完整航图图片
-> 模型输出旧 canonical JSON
-> D1 canonicalizer
-> missed_approach_leg.schema.json
-> group1_canonical_field_scorer_v2.py
-> scoring_equivalence_v2 target
```

formal200 run package：

```text
group1_sft_local/runs/
  group1_sft_d1_evidence_after_d1_dev50_formal200_canonical
```

formal200 preflight：

| item | value |
|---|---:|
| split_subset | evaluation |
| input rows | 200 |
| scoring rows | 200 |
| missing images | 0 |
| image sha256 mismatches | 66 |
| prompt exists | true |
| schema exists | true |
| scoring target exists | true |
| ready_for_remote_execution | false |

`image_sha256_mismatch=66` 是本地图片哈希风险；没有缺图，也不是 prompt/schema/target 缺失。

## 9. dev50 结果

dev50 package：

```text
group1_sft_local/runs/
  group1_sft_d1_evidence_after_d1_dev50_dev50_canonical
```

dev50 raw inference：

```text
raw_text = 50 / 50
parsed_json = 35 / 50
validation = 35 / 50
```

dev50 canonicalized summary：

```text
canonical_json_written = 50 / 50
schema_valid = 50 / 50
samples_scored = 50 / 50
final_chart_id_mismatch_count = 0
failures = []
```

正式分数：

```text
358 / 1010 = 0.35445544554455444
```

对照方法在 `59b8dce3` 的 dev50 结果：

```text
旧 D1 -> D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL
700 / 1010
```

因此 D2 dev50 明显低于旧 D1 继续训练证据方法。

## 10. formal200 结果

formal200 raw inference：

```text
raw_text = 200 / 200
parsed_json = 136 / 200
validation = 136 / 200
```

raw inference summary 里的直接 score 只覆盖少数 strict-valid 样本，不作为最终结果：

```text
samples_scored = 22
failure_count = 178
raw direct score = 222 / 454
```

正式结果以后处理 canonicalized summary 为准：

```text
canonical_json_written = 200 / 200
schema_valid = 200 / 200
schema_invalid = 0
samples_scored = 200 / 200
raw_chart_id_mismatch_count = 135
final_chart_id_mismatch_count = 0
failures = []
```

formal200 正式分数：

```text
1328 / 4052 = 0.32773938795656465
```

canonicalizer action counts：

| action | count |
|---|---:|
| `parse_entire_raw_as_json_object` | 133 |
| `fallback_no_parseable_json_to_empty_canonical` | 64 |
| `raw_object_not_convertible_to_canonical_shape` | 66 |
| `fallback_missing_missed_approach` | 66 |
| `fallback_missing_legs` | 66 |
| `set_manifest_chart_id_envelope` | 200 |
| `strip_outer_whitespace` | 200 |

这说明正式流程能把 200 个样本全部 canonicalize 并评分，但 raw 生成本身并不稳定。

## 11. formal200 字段级得分

总分：

```text
1328 / 4052 = 0.327739
```

按字段聚合：

| field | correct | total | accuracy |
|---|---:|---:|---:|
| `Q3_turn` | 393 | 642 | 0.6121 |
| `Q_terminator` | 314 | 642 | 0.4891 |
| `Q5_hold_params` | 297 | 642 | 0.4626 |
| `Q4_course_or_radial` | 154 | 642 | 0.2399 |
| `Q1_fix_ident` | 135 | 642 | 0.2103 |
| `Q2_altitude_constraint` | 31 | 642 | 0.0483 |
| `leg_count` | 4 | 200 | 0.0200 |

按 target status 拆开后，问题更明显：

| field/status | correct | total | accuracy |
|---|---:|---:|---:|
| `Q3_turn`, target `not_applicable` | 393 | 590 | 0.6661 |
| `Q5_hold_params`, target `not_applicable` | 297 | 444 | 0.6689 |
| `Q4_course_or_radial`, target `not_applicable` | 153 | 233 | 0.6567 |
| `Q1_fix_ident`, target `not_applicable` | 135 | 203 | 0.6650 |
| `Q2_altitude_constraint`, target `not_applicable` | 29 | 48 | 0.6042 |
| `Q_terminator`, target `present` | 314 | 642 | 0.4891 |
| `Q1_fix_ident`, target `present` | 0 | 439 | 0.0000 |
| `Q2_altitude_constraint`, target `present` | 2 | 594 | 0.0034 |
| `Q3_turn`, target `present` | 0 | 52 | 0.0000 |
| `Q4_course_or_radial`, target `present` | 1 | 409 | 0.0024 |
| `Q5_hold_params`, target `present` | 0 | 198 | 0.0000 |
| `leg_count`, target `present` | 4 | 200 | 0.0200 |

因此 `0.328` 主要来自：

- `not_applicable/null` 状态碰对。
- 一部分 `Q_terminator` 模式碰对。

它不是来自稳定读图后的 fix、altitude、course、hold 参数正确。

## 12. 主要错误模式

### 12.1 raw chart id 经常不是当前图

raw output 的 chart id 错了 135 次。最常见错误：

| raw output chart_id | count |
|---|---:|
| `KORL` | 91 |
| `KORL_R08` | 10 |
| `KOSH_R08` | 9 |
| `KATL` | 9 |
| `KATI` | 4 |
| `KALB` | 4 |

canonicalizer 后会把外层 `chart_id` 设为 manifest chart id，所以 final chart id mismatch 是 0；但这不代表模型真正理解当前图。

### 12.2 leg_count 预测过长

target leg_count 分布：

| target leg_count | count |
|---|---:|
| 3 | 157 |
| 4 | 38 |
| 5 | 3 |
| 2 | 2 |

prediction leg_count 分布：

| predicted leg_count | count |
|---|---:|
| 6 | 87 |
| null/unknown | 66 |
| 5 | 43 |
| 3 | 4 |

`leg_count` 只对 `4/200`。

### 12.3 present fix 基本没有读对

`Q1_fix_ident`：

```text
target present = 439
correct present = 0
```

主要错误是把 target present 预测成 `not_applicable` 或空字段。

### 12.4 present altitude 基本没有读对

`Q2_altitude_constraint`：

```text
target present = 594
correct present = 2
```

模型常输出固定化 altitude：

```text
AT_OR_ABOVE 1000 ft: 130 次
```

而真实 target altitude 很分散，例如 3000、2000、4000、5000、2100、3500、3400 等。

### 12.5 course/radial 固定化

`Q4_course_or_radial`：

```text
target present = 409
correct present = 1
```

模型大量输出：

```text
course_deg = 270
```

这说明它更像是在输出模板，而不是从当前图读取 course/radial。

### 12.6 hold 参数基本没有输出

`Q5_hold_params`：

```text
target present = 198
correct present = 0
```

多数 present hold target 被预测成 `not_applicable` 或空字段。

## 13. 结论

D2 当前结果不支持“D1_DEV50_ONLY 底座加 evidence grounding 后已经具备较好 canonical 输出能力”这个判断。

更准确的结论是：

```text
D1_DEV50_ONLY 底座本身还没有稳定学会旧 D1 canonical JSON 的图表条件化生成。
继续训练 evidence wrapper/grounding 后，训练 loss 可以下降，
但正式 dev50/formal200 canonical scoring 仍然较低。
```

formal200 的 `0.328` 主要来自默认状态和结构模式：

- `not_applicable` 字段碰对。
- 一部分 path terminator 碰对。

真正需要读图的字段几乎没有学会：

- fix ident。
- altitude。
- course/radial。
- hold parameters。
- leg_count。

因此，这个 D2 对照实验的价值是负向结论：

```text
如果 D1 底座只用 first 50 训练，
再加同一 first 50 的 evidence grounding 监督，
不足以恢复或接近旧 D1 继续训练证据方法的效果。
```

## 14. 后续建议

后续不建议把当前 D2 checkpoint 作为正式主方法继续扩展。更合理的方向是：

1. 保留它作为对照结果。
2. 把它和 `旧 D1 -> D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL` 的 dev50/formal200 结果放在同一表中。
3. 后续若要继续改，应优先解决 canonical 输出稳定性，而不是单纯增加 evidence box 数量。
4. 如果要验证 grounding 是否帮助，应该以较强的旧 D1 checkpoint 作为起点，而不是弱的 `D1_DEV50_ONLY` 起点。

