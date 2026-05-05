# 实验组5详细实验方案

生成日期：2026-05-03

仓库：

```text
https://github.com/reshihihihi/faa-chart-to-424-benchmark.git
branch: experiment5-diagnostic-20260503
HEAD: c69c184
```

本地工作目录：

```text
external_artifact://C/Users\admin\Documents\New project\faa-chart-to-424-benchmark-c69c184
```

## 1. 实验组5定位

实验组5不是新的 leaderboard，也不是为了证明某个方法端到端最好。它是诊断实验：

```text
当 full-chart / OCR / LLM / rule pipeline 失败时，失败到底发生在哪一层？
```

它把完整任务拆成若干中间层：

```text
chart image
  -> region / source-view selection
  -> ROI OCR
  -> field candidate discovery
  -> missed-approach prose / observable facts
  -> leg structure and path terminator reasoning
  -> canonical JSON
  -> field-level scorer
```

实验组5通过逐层替换为 oracle 或半 oracle 输入，判断瓶颈来自：

- OCR 文本质量；
- source-view / ROI 选择；
- field candidate 是否有用；
- LLM 是否能把 prose 转成 leg/path terminator；
- deterministic rules 是否比 LLM 更稳定；
- 如果图上事实已经人工确认，后续规则/LLM 能否补全隐含 424 语义。

## 2. 总体原则

### 2.1 方法输入和评分必须隔离

方法预测阶段禁止使用：

```text
target
score
canonical_answer
canonical_leg_index
Q_terminator
leg_type
field_review_v2
CIFP / ARINC 424 records
gold_observable_evidence，除非方法本身是 G 系列
previous model/rule output for same chart
web search / external aviation database
```

target 和 score 只能在 prediction 已经写盘后用于评价。

### 2.2 每个方法必须记录 provenance

每个 run 需要保存：

- run manifest；
- method input manifest；
- prompt；
- raw model output / raw response；
- canonical JSON prediction；
- schema validation；
- v2 score；
- strict score；
- no-leakage report；
- execution report。

### 2.3 smoke20 不是 formal200 结论

当前所有结果都是 smoke20 诊断结果。它们可以用于判断下一步方向，但不能直接写成 formal200 级别结论。

## 3. 数据与目录

### 3.1 主要输入目录

```text
benchmark_exports/derived/v2/experiment5_diagnostic/
```

关键文件：

```text
smoke20_manifest.jsonl
roi_ocr_candidate_input_manifest_smoke20.jsonl
rule_registry.yaml
gold_ma_text_smoke20_template.jsonl
gold_observable_smoke20_template.jsonl
```

### 3.2 当前 r4 运行目录

```text
formal_runs/experiment5/experiment5_smoke_20260503_r4_available_methods/
```

已确认存在：

| 工件 | 状态 |
|---|---:|
| `inputs/` | 递归 60 files |
| `field_candidates/` | 递归 60 files |
| `field_candidates_validation/` | 递归 60 files |
| `B3_T/prompts/` | 20 files |
| `B3_TPD/prompts/` | 20 files |
| `B3_PD/prompts/` | 20 files |
| `B4_TPD/rule_diagnostics/` | 20 files |

### 3.3 当前 gold text / A3 / B2 运行目录

```text
formal_runs/experiment5/experiment5_gold_text_20260503_r1/
```

关键报告：

```text
reports/experiment5_a3_gold_text_execution_report_zh.md
reports/experiment5_b2_gold_text_execution_report_zh.md
reports/experiment5_post_b2_remaining_methods_audit_zh.md
reports/experiment5_r4_plus_a3_current_status_zh.md
reports/experiment5_safe_speedup_plan_zh.md
```

## 4. 方法矩阵

### 4.1 Layer 1: Gold MA prose oracle

目的：消除 missed approach prose OCR 错误，测试后续 text-to-canonical 能力。

| 方法 | 输入 | 方法 | 输出 | 诊断问题 |
|---|---|---|---|---|
| `A3_GoldText_Rules` | adjudicated `gold_ma_prose` | deterministic rules | canonical JSON | 如果文本完美，规则能恢复多少 |
| `B2a_GoldText_LLM` | adjudicated `gold_ma_prose` | `gpt-5.4` LLM | canonical JSON | 如果文本完美，LLM 能恢复多少 |
| `B2b_GoldText_FieldCandidates_LLM` | adjudicated `gold_ma_prose` + 从同一 prose 自动生成的 weak field candidates | `gpt-5.4` LLM | canonical JSON | weak candidates 是否帮助 LLM |

允许输入：

```text
chart_id
airport
approach_ident
chart_name
gold_ma_prose
automatic field candidates from the same gold prose, only for B2b
schema contract
```

禁止输入：

```text
field_review_v2
canonical_answer
canonical_leg_index
Q_terminator
leg_type
target JSON
score
CIFP / ARINC 424
gold observable facts
```

### 4.2 Layer 2: ROI OCR / field candidate diagnostic

目的：固定 source-view / ROI，减少 full-chart 噪声，诊断 ROI OCR 和自动候选的作用。

T/P/D 定义：

```text
T = MISSED_APPROACH_TEXT
P = PLAN_VIEW
D = MISSED_APPROACH_DETAIL_AREA
```

| 方法 | 输入 | 方法 | 输出 | 诊断问题 |
|---|---|---|---|---|
| `B3_T` | MA_TEXT ROI OCR + automatic field candidates | `gpt-5.4` LLM | canonical JSON | 只看复飞文字，LLM 能恢复多少 |
| `B3_TPD` | MA_TEXT + PLAN_VIEW + DETAIL ROI OCR + automatic field candidates | `gpt-5.4` LLM | canonical JSON | P/D OCR 是否帮助 LLM |
| `B3_PD` | PLAN_VIEW + DETAIL ROI OCR + automatic field candidates，不含 MA_TEXT | `gpt-5.4` LLM | canonical JSON | 没有复飞文字时 P/D 单独有多大价值 |
| `B4_TPD` | MA_TEXT + PLAN_VIEW + DETAIL ROI OCR + automatic field candidates | deterministic rules | canonical JSON | 同样 ROI/candidates 下规则是否比 LLM 稳定 |

允许输入：

```text
ROI OCR text
region labels
automatic field candidates
schema contract
```

禁止输入：

```text
target
score
field_review_v2
support_mode
human decision
CIFP / ARINC 424
gold_ma_prose
gold_observable
```

### 4.3 Layer 3: Gold observable evidence diagnostic

目的：人工确认“图上可观察事实”后，测试规则或 LLM 是否能从事实推出 canonical fields 和隐含 424 语义。

Gold observable 不是 target，不是 canonical JSON，也不是 field_review_v2。它只能写图上事实。

允许内容示例：

```text
visible_fix
visible_altitude
visible_turn_direction
visible_course_or_radial
holding_pattern_depicted
holding_fix
holding_inbound_course_deg
hold_leg_time_explicit
hold_leg_distance_explicit
source_regions
evidence_region_ids
checked_scopes
```

禁止内容：

```text
Q_terminator
canonical_leg_index
expected_value
score
target field
final canonical JSON
candidate_424 positive/negative label
```

| 方法 | 输入 | 方法 | 输出 | 诊断问题 |
|---|---|---|---|---|
| `G0_Direct` | gold observable facts | direct fill only，不做 424 推理 | canonical JSON 或字段预测 | 只填可见字段的上限 |
| `G1_Rules` | gold observable facts + frozen rules | deterministic rules | canonical JSON | 规则能否从可见事实推出隐含字段 |
| `G2_LLM` | gold observable facts | LLM | canonical JSON | 可选，LLM 自己能否推理 |
| `G3_LLM_Rules` | gold observable facts + explicit rule descriptions | LLM | canonical JSON | facts 和 rules 都给定时，LLM 能否应用 |

## 5. 当前已完成实验结果

### 5.1 r4 ROI 层结果

运行目录：

```text
formal_runs/experiment5/experiment5_smoke_20260503_r4_available_methods/
```

参数：

```text
model = gpt-5.4
temperature = 0
max_tokens = 4096
schema_retry_count = 1
base_url = http://127.0.0.1:8080/v1
```

| 方法 | schema-valid | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---:|---:|---:|---:|
| `B3_T` | 20/20 | 138/470 | 29.36% | 29.36% |
| `B3_TPD` | 20/20 | 126/470 | 26.81% | 26.81% |
| `B3_PD` | 20/20 | 8/470 | 1.70% | 1.70% |
| `B4_TPD` | 20/20 | 310/470 | 65.96% | 65.96% |

解释：

- `B4_TPD` 高，说明 ROI OCR + candidates 给定后，规则系统很强。
- `B3_TPD` 低于 `B3_T`，说明直接把 P/D OCR 加给 LLM 可能引入噪声或绑定错误。
- `B3_PD` 接近 0，说明没有 MA_TEXT 时，仅靠当前 P/D OCR 文本通道不能恢复完整 missed approach structure。

### 5.2 Gold MA prose 填写

文件：

```text
benchmark_exports/derived/v2/experiment5_diagnostic/gold_ma_text_smoke20_template.jsonl
```

状态：

```text
20/20 filled
review_status = adjudicated
source = FAA chart PDF text layer + Experiment 5 MA_TEXT ROI OCR cross-check
```

未使用：

```text
target
score
canonical_answer
canonical_leg_index
Q_terminator
leg_type
field_review_v2
```

### 5.3 A3 结果

运行目录：

```text
formal_runs/experiment5/experiment5_gold_text_20260503_r1/
```

| 方法 | schema-valid | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---:|---:|---:|---:|
| `A3_GoldText_Rules` | 20/20 | 342/470 | 72.77% | 72.77% |

字段族：

| 字段 | 正确/总数 | accuracy |
|---|---:|---:|
| `Q1_fix_ident` | 73/75 | 97.33% |
| `Q2_altitude_constraint` | 19/75 | 25.33% |
| `Q3_turn` | 68/75 | 90.67% |
| `Q4_course_or_radial` | 38/75 | 50.67% |
| `Q5_hold_params` | 54/75 | 72.00% |
| `Q_terminator` | 71/75 | 94.67% |
| `leg_count` | 19/20 | 95.00% |

解释：

```text
A3 > B4_TPD，说明 OCR/prose quality 是瓶颈之一。
A3 仍未满分，主要问题在 altitude/course/hold detail 等字段。
```

### 5.4 B2 结果

模型服务：

```text
provider = openai_compatible_via_openai_oauth
base_url = http://127.0.0.1:8080/v1
model = gpt-5.4
temperature = 0
max_tokens = 4096
schema_retry_count = 1
```

| 方法 | schema-valid | retry | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---:|---:|---:|---:|---:|
| `B2a_GoldText_LLM` | 20/20 | 5 | 125/470 | 26.60% | 26.60% |
| `B2b_GoldText_FieldCandidates_LLM` | 20/20 | 0 | 137/470 | 29.15% | 29.15% |

字段族：

| 方法 | 字段 | 正确/总数 | accuracy |
|---|---|---:|---:|
| `B2a` | `Q1_fix_ident` | 38/75 | 50.67% |
| `B2a` | `Q2_altitude_constraint` | 0/75 | 0.00% |
| `B2a` | `Q3_turn` | 31/75 | 41.33% |
| `B2a` | `Q4_course_or_radial` | 11/75 | 14.67% |
| `B2a` | `Q5_hold_params` | 34/75 | 45.33% |
| `B2a` | `Q_terminator` | 9/75 | 12.00% |
| `B2a` | `leg_count` | 2/20 | 10.00% |
| `B2b` | `Q1_fix_ident` | 38/75 | 50.67% |
| `B2b` | `Q2_altitude_constraint` | 0/75 | 0.00% |
| `B2b` | `Q3_turn` | 38/75 | 50.67% |
| `B2b` | `Q4_course_or_radial` | 11/75 | 14.67% |
| `B2b` | `Q5_hold_params` | 37/75 | 49.33% |
| `B2b` | `Q_terminator` | 10/75 | 13.33% |
| `B2b` | `leg_count` | 3/20 | 15.00% |

解释：

- B2b 比 B2a 略高，说明 weak candidates 对 LLM 有小幅帮助。
- B2 仍明显低于 A3，说明 LLM 从 gold prose 到 canonical leg structure/path terminator 的转换仍不稳定。
- B2 和 B3_T 量级接近，说明单靠 gold prose 并没有让当前 LLM 自动解决结构推理问题。

## 6. No-leakage 审查

已完成方法的 no-leakage 均通过。

### 6.1 r4

```text
target_used_for_prediction = false
score_used_for_prediction = false
cifp_or_arinc_424_used_for_prediction = false
gold_observable_used_for_prediction = false
gold_ma_text_used_for_prediction = false
hard_leakage_detected = false
```

### 6.2 A3

```text
target_used_for_prediction = false
score_used_for_prediction = false
cifp_or_arinc_424_used_for_prediction = false
field_review_v2_used_for_prediction = false
hard_leakage_detected = false
forbidden_key_hits = {}
```

### 6.3 B2

```text
target_used_for_prediction = false
score_used_for_prediction = false
cifp_or_arinc_424_used_for_prediction = false
field_review_v2_used_for_prediction = false
hard_leakage_detected = false
forbidden_key_hits = {}
```

## 7. 当前问题

### 7.1 G 系列仍阻塞

文件：

```text
benchmark_exports/derived/v2/experiment5_diagnostic/gold_observable_smoke20_template.jsonl
```

状态：

```text
0/20 adjudicated
```

不能从 `field_review_v2`、canonical target 或 score 直接派生，否则会泄漏答案结构。

### 7.2 rule_registry 仍需正式审查

文件：

```text
benchmark_exports/derived/v2/experiment5_diagnostic/rule_registry.yaml
```

当前状态仍是 candidate。正式 claim 前必须审查：

- 哪些是 direct fill rule；
- 哪些是 convention/default rule；
- 哪些是 424-derived semantic rule；
- 每条规则允许使用哪些输入；
- 是否任何规则隐含使用 target 或 score；
- B4/A3/G1/G3 是否共用同一冻结规则定义。

### 7.3 r4 manifest hash 有换行归一化差异

`roi_ocr_candidate_input_manifest_smoke20.jsonl` 中 120 个 input/candidate 工件都存在。

当前 checkout 原始 byte hash 与 manifest 不一致，但 CRLF-normalized hash 一致：

```text
exists: 120/120
raw hash matches: 0/120
CRLF-normalized hash matches: 120/120
```

解释：这是 Git checkout 换行归一化问题，不是工件缺失。正式归档前应补 newline-normalized hash audit 或固定 `.gitattributes`。

### 7.4 LLM 速度问题

当前 `openai-oauth` 已能提供：

```text
http://127.0.0.1:8080/v1
Available Models: gpt-5.5, gpt-5.4, gpt-5.4-mini, ...
```

本次 B2 选择顺序执行，原因是当时 run 已经写入同一输出目录；中途并行会抢写 `raw_responses`、`validation` 和 `summary`。

后续安全加速方案：

- 样本级并行；
- 默认 `--max-workers 1`，需要时设为 2 或 3；
- 不换模型；
- 不改 prompt；
- 不减少输入；
- 不跳过 validation/no-leakage；
- 不让多个进程写同一 run dir；
- 加 `--resume` 跳过已完成样本。

## 8. 下一步计划

### Step 1: 制作 gold_observable

产物：

```text
benchmark_exports/derived/v2/experiment5_diagnostic/gold_observable_smoke20.jsonl
```

每条记录只写：

```text
chart_id
observable_id
observable_group_id
source_regions
evidence_region_ids
checked_scopes
facts
review_status
notes
```

facts 只允许可观察事实和显式缺失，例如：

```json
{
  "visible_fix": "PIMKE",
  "visible_altitude": 2700,
  "visible_turn_direction": null,
  "visible_course_or_radial": null,
  "holding_pattern_depicted": true,
  "holding_fix": "PIMKE",
  "holding_inbound_course_deg": null,
  "hold_leg_time_explicit": false,
  "hold_leg_distance_explicit": true,
  "hold_leg_distance_nm": 4
}
```

禁止：

```text
Q_terminator
canonical_leg_index
expected_value
target field
score
final canonical JSON
```

### Step 2: 写 gold_observable checker

checker 必须验证：

- 不包含 forbidden keys；
- `review_status = adjudicated`；
- `checked_scopes` 非空；
- `source_regions` 非空；
- explicit absence 用布尔值写出；
- 不包含 canonical answer / leg index / target；
- 每个 fact 的类型合法。

### Step 3: 跑 G0/G1

先跑不依赖 LLM 的：

```text
G0_Direct
G1_Rules
```

G0 只直接填可见字段，不做 path terminator 推理。
G1 使用冻结规则，从 observable facts 推出 canonical JSON。

### Step 4: 跑 G3

使用当前可用模型服务：

```text
base_url = http://127.0.0.1:8080/v1
model = gpt-5.4
temperature = 0
max_tokens = 4096
schema_retry_count = 1
```

G3 输入：

```text
gold observable facts
explicit rule descriptions
schema contract
```

禁止：

```text
target
score
canonical answer
canonical leg index
field_review_v2
```

### Step 5: 生成 smoke20 all-methods 总报告

等 G0/G1/G3 完成后，生成：

```text
formal_runs/experiment5/<run_id>/reports/experiment5_smoke20_all_methods_report_zh.md
```

报告至少包含：

- 方法矩阵；
- 输入边界；
- no-leakage；
- schema-valid；
- parse failure；
- retry；
- v2 score；
- strict score；
- 字段族分数；
- 与实验组1端到端对比；
- 与 B3/B4/A3/B2 诊断链解释；
- 当前不能推出的结论；
- 是否扩展 formal200 的建议。

## 9. 当前一句话结论

实验组5当前已经跑通 ROI 层、gold prose rules 和 gold prose LLM：

```text
B3_T / B3_TPD / B3_PD / B4_TPD / A3 / B2a / B2b
```

主要发现：

```text
MA_TEXT 很关键；
P/D OCR 直接加给 LLM 未必有益；
没有 MA_TEXT 时 P/D 文本通道几乎不能恢复完整程序；
gold prose 下规则 A3 明显强于 LLM B2；
当前 LLM 的主要问题是 leg structure / path terminator / canonical mapping 不稳定；
下一步必须制作无泄漏 gold_observable，才能诊断“图上事实已知”时规则和 LLM 是否能补全隐含 424 语义。
```
