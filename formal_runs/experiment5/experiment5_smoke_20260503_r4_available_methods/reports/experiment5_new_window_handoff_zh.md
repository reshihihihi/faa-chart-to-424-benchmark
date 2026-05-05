# 实验组5新窗口接力说明

生成日期：2026-05-03  
当前仓库：`external_artifact://E/experiment3\github_work\faa-chart-to-424-benchmark-experiment5`  
当前主要运行目录：`formal_runs/experiment5/experiment5_smoke_20260503_r4_available_methods`  
用途：在新窗口继续实验组5时，作为完整接力说明，避免重复摸索、避免方法边界串组、避免把 target 或人工答案泄漏进方法输入。

---

## 1. 实验组5的定位

实验组5不是新的 leaderboard，也不是为了刷分增加更多 baseline。  
它的核心作用是做 oracle / diagnostic 诊断：

```text
端到端方法失败时，到底失败在哪一层？
```

完整任务可拆成：

```text
航图图像
  -> 区域发现
  -> OCR / 图形 / icon 识别
  -> 图上事实提取
  -> 字段候选发现
  -> 字段绑定到 missed approach 程序步骤
  -> 领域规则与 424 path terminator 推理
  -> canonical JSON
  -> field-level scorer
```

实验组1回答：

```text
完整端到端方法能做到多少。
```

实验组5回答：

```text
如果把某一层换成 oracle 或人工确认输入，后续环节还能不能做好。
```

所以实验组5要严格保持“诊断链条”的含义，不能为了提高分数把 target、score、CIFP/424、人工字段答案、canonical JSON 或其他方法预测塞进方法输入。

---

## 2. 实验组5总方法矩阵

实验组5分三层。

### 2.1 Layer 1：Gold MA prose text oracle

目的：消除 OCR 错误，检查“如果复飞文字完全正确，文本通道和规则/LLM 能做到多少”。

| 方法 | 输入 | 方法 | 输出 | 目的 |
|---|---|---|---|---|
| `A3_GoldText_Rules` | 人工校正的 missed approach prose | 冻结规则系统 | canonical JSON | 与 A1 对比，诊断 OCR 错误对规则系统的影响 |
| `B2a_GoldText_LLM` | 人工校正的 missed approach prose | LLM | canonical JSON | 与 B1 对比，诊断 OCR 错误/全图噪声对 LLM 的影响 |
| `B2b_GoldText_FieldCandidates_LLM` | 人工校正的 missed approach prose + 自动字段候选 | field candidates + LLM | canonical JSON | 与 B2a 对比，诊断字段候选是否帮助文本 LLM |

重要禁止项：

```text
不能输入 field_review_v2
不能输入 canonical_answer
不能输入 Q_terminator
不能输入 leg_type
不能输入 canonical_leg_index
不能输入 support_mode
不能输入 candidate_mappings
不能输入 score
不能输入 target JSON
```

A3/B2 只允许使用纯人工校正的 `gold_ma_prose`。

---

### 2.2 Layer 2：Human-confirmed ROI / region OCR diagnostic

目的：固定区域，减少全图噪声，诊断 ROI OCR、区域标注、field candidates 和规则/LLM 的作用。

T/P/D 含义：

```text
T = MISSED_APPROACH_TEXT
P = PLAN_VIEW
D = MISSED_APPROACH_DETAIL_AREA
```

| 方法 | 输入 | 方法 | 输出 | 目的 |
|---|---|---|---|---|
| `B3_T` | MA_TEXT ROI OCR + 自动 field candidates | LLM | canonical JSON | 与 B1 对比，诊断全图 OCR 噪声和只看复飞文字的上限 |
| `B3_TPD` | MA_TEXT + PLAN_VIEW + DETAIL ROI OCR + 自动 field candidates | LLM | canonical JSON | 与 B3_T 对比，诊断 P/D 区域 OCR 是否帮助 LLM |
| `B3_PD` | PLAN_VIEW + DETAIL ROI OCR + 自动 field candidates，不含 MA_TEXT | LLM | canonical JSON | 与实验组4 source-view 消融呼应，检查没有复飞文字时 P/D 能提供多少 |
| `B4_TPD` | MA_TEXT + PLAN_VIEW + DETAIL ROI OCR + 自动 field candidates | deterministic rules | canonical JSON | 与 B3_TPD 对比，诊断同样输入下规则是否比 LLM 更稳定 |

重要禁止项：

```text
不能输入 canonical target
不能输入 expected value
不能输入 field_review_v2
不能输入 support_mode
不能输入 score
不能输入 human decision
不能输入 CIFP/ARINC 424
不能输入 gold observable
```

允许项：

```text
ROI OCR text
region label
自动 field candidates
```

---

### 2.3 Layer 3：Gold observable evidence diagnostic

目的：人工确认图上事实后，检查规则或 LLM 是否能把这些事实转成 implicit / 424-derived canonical 字段。

Gold observable 是“图上可观察事实”，不是 target，不是 canonical JSON。

允许包含：

```text
visible fix
visible altitude
visible turn direction
visible course/radial
visible holding pattern
visible holding fix
visible holding inbound course
explicit hold time 是否存在
explicit hold distance 是否存在
source regions
evidence region ids
checked scopes
显式缺失，例如 hold_leg_time_explicit = false
```

禁止包含：

```text
Q_terminator = CA / DF / HM
canonical_leg_index target answer
expected_value
score
final canonical JSON
candidate_424 positive/negative label
error_fields label
```

方法矩阵：

| 方法 | 输入 | 方法 | 输出 | 目的 |
|---|---|---|---|---|
| `G0_Direct` | gold observable facts | 只直接填可见字段，不做隐式/424 推理 | canonical JSON 或字段预测 | 量化“图上事实直接可填字段”的上限 |
| `G1_Rules` | gold observable facts + 冻结规则 | deterministic rules | canonical JSON | 诊断规则能否从可见事实推出 implicit / 424-derived 字段 |
| `G2_LLM` | gold observable facts | LLM，不给显式规则 | canonical JSON | 可选，诊断 LLM 自己是否会推理 |
| `G3_LLM_Rules` | gold observable facts + 明确规则说明 | LLM | canonical JSON | 诊断事实和规则都已知时，LLM 能否应用规则 |

---

## 3. 已完成工作

### 3.1 已生成/使用的关键文件

实验组5诊断目录：

```text
benchmark_exports/derived/v2/experiment5_diagnostic/
```

已有重要文件：

```text
benchmark_exports/derived/v2/experiment5_diagnostic/smoke20_manifest.jsonl
benchmark_exports/derived/v2/experiment5_diagnostic/roi_ocr_candidate_input_manifest_smoke20.jsonl
benchmark_exports/derived/v2/experiment5_diagnostic/source_view_summary_for_experiment5_current.json
benchmark_exports/derived/v2/experiment5_diagnostic/rule_registry.yaml
benchmark_exports/derived/v2/experiment5_diagnostic/gold_ma_text_smoke20_template.jsonl
benchmark_exports/derived/v2/experiment5_diagnostic/gold_observable_smoke20_template.jsonl
```

Schema / prompt：

```text
schemas/experiment5_roi_field_candidates.schema.v1.json
prompts/paper_v2/experiment5_roi_ocr_candidates_to_canonical.zh_v1_region_priority.md
```

脚本：

```text
scripts/experiment5/prepare_experiment5_smoke_inputs.py
scripts/experiment5/run_experiment5_smoke_b3_b4.py
scripts/experiment5/audit_experiment5_remaining_methods.py
```

当前主要结果目录：

```text
formal_runs/experiment5/experiment5_smoke_20260503_r4_available_methods/
```

主要报告：

```text
formal_runs/experiment5/experiment5_smoke_20260503_r4_available_methods/reports/experiment5_smoke20_r4_execution_report_zh.md
formal_runs/experiment5/experiment5_smoke_20260503_r4_available_methods/reports/experiment5_remaining_methods_input_audit_zh.md
formal_runs/experiment5/experiment5_smoke_20260503_r4_available_methods/reports/experiment5_smoke20_r4_no_leakage_report.json
```

---

### 3.2 r2 已跑结果

r2 运行目录：

```text
formal_runs/experiment5/experiment5_smoke_20260503_r2/
```

r2 方法：

```text
B3_T
B3_TPD
B4_TPD
```

r2 结果：

| 方法 | v2 accuracy | 备注 |
|---|---:|---|
| `B3_T` | 30.85% | MA_TEXT ROI OCR + field candidates + LLM |
| `B3_TPD` | 28.51% | T/P/D ROI OCR + field candidates + LLM |
| `B4_TPD` | 65.96% | T/P/D ROI OCR + field candidates + rules |

r2 暴露的问题：

```text
B3_TPD 没有高于 B3_T，说明 P/D OCR 直接加入 LLM 不一定有帮助。
B4_TPD 明显高，说明规则在候选已知条件下很强。
```

---

### 3.3 r3 / r3b 新增 B3_PD

新增 `B3_PD` 后单独跑过两次：

```text
formal_runs/experiment5/experiment5_smoke_20260503_r3/
formal_runs/experiment5/experiment5_smoke_20260503_r3b/
```

第一次 r3：

```text
B3_PD = 5 / 470 = 1.06%
```

第二次 r3b 修正记录字段后：

```text
B3_PD = 12 / 470 = 2.55%
```

注意：LLM 有非确定性，虽然 temperature=0，但代理/模型服务仍可能有轻微波动。因此最终统一采用 r4 的同 run_id 结果。

---

### 3.4 r4 统一重跑可合法执行方法

r4 运行目录：

```text
formal_runs/experiment5/experiment5_smoke_20260503_r4_available_methods/
```

r4 方法：

```text
B3_T
B3_TPD
B3_PD
B4_TPD
```

运行参数：

```text
text_model = gpt-5.4
temperature = 0
max_tokens = 4096
schema_retry_count = 1
provider = openai_compatible
base_url = http://127.0.0.1:8080/v1
```

r4 总结果：

| 方法 | schema-valid | retry | v2 正确/总数 | v2 accuracy | strict accuracy |
|---|---:|---:|---:|---:|---:|
| `B3_T` | 20/20 | 0 | 138/470 | 29.36% | 29.36% |
| `B3_TPD` | 20/20 | 0 | 126/470 | 26.81% | 26.81% |
| `B3_PD` | 20/20 | 0 | 8/470 | 1.70% | 1.70% |
| `B4_TPD` | 20/20 | 0 | 310/470 | 65.96% | 65.96% |

字段族表现：

| 方法 | 字段 | 正确/总数 | accuracy |
|---|---|---:|---:|
| `B3_T` | `Q1_fix_ident` | 28/75 | 37.33% |
| `B3_T` | `Q2_altitude_constraint` | 4/75 | 5.33% |
| `B3_T` | `Q3_turn` | 51/75 | 68.00% |
| `B3_T` | `Q4_course_or_radial` | 6/75 | 8.00% |
| `B3_T` | `Q5_hold_params` | 36/75 | 48.00% |
| `B3_T` | `Q_terminator` | 12/75 | 16.00% |
| `B3_T` | `leg_count` | 1/20 | 5.00% |
| `B3_TPD` | `Q1_fix_ident` | 25/75 | 33.33% |
| `B3_TPD` | `Q2_altitude_constraint` | 6/75 | 8.00% |
| `B3_TPD` | `Q3_turn` | 49/75 | 65.33% |
| `B3_TPD` | `Q4_course_or_radial` | 4/75 | 5.33% |
| `B3_TPD` | `Q5_hold_params` | 34/75 | 45.33% |
| `B3_TPD` | `Q_terminator` | 8/75 | 10.67% |
| `B3_TPD` | `leg_count` | 0/20 | 0.00% |
| `B3_PD` | `Q1_fix_ident` | 0/75 | 0.00% |
| `B3_PD` | `Q2_altitude_constraint` | 0/75 | 0.00% |
| `B3_PD` | `Q3_turn` | 1/75 | 1.33% |
| `B3_PD` | `Q4_course_or_radial` | 0/75 | 0.00% |
| `B3_PD` | `Q5_hold_params` | 7/75 | 9.33% |
| `B3_PD` | `Q_terminator` | 0/75 | 0.00% |
| `B3_PD` | `leg_count` | 0/20 | 0.00% |
| `B4_TPD` | `Q1_fix_ident` | 64/75 | 85.33% |
| `B4_TPD` | `Q2_altitude_constraint` | 19/75 | 25.33% |
| `B4_TPD` | `Q3_turn` | 63/75 | 84.00% |
| `B4_TPD` | `Q4_course_or_radial` | 38/75 | 50.67% |
| `B4_TPD` | `Q5_hold_params` | 49/75 | 65.33% |
| `B4_TPD` | `Q_terminator` | 62/75 | 82.67% |
| `B4_TPD` | `leg_count` | 15/20 | 75.00% |

---

## 4. r4 结果解释

### 4.1 B4_TPD 为什么最高

`B4_TPD` 使用：

```text
T/P/D ROI OCR
+ 自动 field candidates
+ deterministic rules
```

它明显高于 `B3_TPD`，说明在这些 smoke20 样本上：

```text
当候选字段已经抽出来后，冻结规则比 LLM 更稳定。
```

但这不代表端到端视觉已经解决，因为 `B4_TPD` 的输入已经使用了人工确认 ROI 和自动候选。

应写成：

```text
在 ROI 和候选字段给定条件下，规则系统能显著恢复程序结构，说明后续规则推理不是唯一瓶颈；端到端失败很可能来自区域、OCR、字段发现和绑定。
```

不能写成：

```text
规则方法已经解决完整航图到 424。
```

---

### 4.2 B3_T 为什么高于 B3_TPD

`B3_T` 只给 MA_TEXT ROI OCR。  
`B3_TPD` 给 MA_TEXT + PLAN_VIEW + DETAIL OCR。

直觉上 `B3_TPD` 应该更强，但实际更低：

```text
B3_T = 29.36%
B3_TPD = 26.81%
```

说明：

```text
P/D 区域 OCR 直接加给 LLM 不一定有帮助。
额外 OCR 文本可能带来噪声。
LLM 可能无法正确判断哪些 P/D 内容与 missed approach 相关。
LLM 可能出现字段错误绑定。
```

这正是实验组5要诊断的问题之一。

---

### 4.3 B3_PD 为什么接近 0

`B3_PD` 明确不包含 MA_TEXT，只给：

```text
PLAN_VIEW ROI OCR
DETAIL_AREA ROI OCR
自动 field candidates
```

结果：

```text
B3_PD = 1.70%
```

说明：

```text
没有上方 missed approach prose 时，当前 P/D OCR + LLM 几乎无法恢复完整 missed approach 程序结构。
```

这个结果很重要，因为它和实验组4的 source-view 消融对应：

```text
MA_TEXT 是恢复程序结构的关键来源。
P/D 区域对部分 fix、altitude、hold 参数可能有帮助，但单独不足以恢复完整 canonical JSON。
```

---

### 4.4 v2 与 strict 为什么相同

r4 中四个方法：

```text
v2 score = strict score
```

说明本次差异不是由 PR #25 narrowed scoring-equivalence v2 的两类显示等价造成。  
也就是说，结果主要来自方法本身的预测差异，而不是评分放宽。

---

## 5. No-leakage 审查结论

r4 no-leakage 报告路径：

```text
formal_runs/experiment5/experiment5_smoke_20260503_r4_available_methods/reports/experiment5_smoke20_r4_no_leakage_report.json
```

关键结果：

```text
target_used_for_prediction = false
score_used_for_prediction = false
cifp_or_arinc_424_used_for_prediction = false
gold_observable_used_for_prediction = false
gold_ma_text_used_for_prediction = false
b3_pd_withholds_missed_approach_text = true
b4_uses_field_candidates = true
candidate_validation_error_rows = 0
candidate_cross_region_snippet_count = 0
candidate_unknown_source_section_count = 0
hard_leakage_detected = false
```

解释：

```text
r4 中 B3/B4 层没有把 target、score、CIFP/424、gold text、gold observable 输入方法。
```

---

## 6. 现有标注导出审计

标注导出路径：

```text
external_artifact://E/experiment3\group2_annotation_status_20260503\shujuji_annotation_export_2026-05-03T02-07-42-455Z.json
```

审计结果：

```text
smoke20 中有最新 submission 的样本: 20 / 20
字段审查记录总数: 237
非空 region OCR 数量: 0
```

但是这些标注记录不能直接喂给 A3/B2/G。

原因：

```text
它们是字段级 evidence review。
其中混有 canonical_answer、canonical_leg_index、field_key、leg_type、support_mode、candidate_leg_id 等禁用项。
```

如果直接使用，会造成：

```text
方法提前看到目标字段结构或答案；
实验组5从 oracle 诊断变成 target leakage；
结果不能写进论文。
```

因此：

```text
标注导出可用于实验组2/3分析；
不能原样作为实验组5 A3/B2/G 的方法输入。
```

---

## 7. 当前阻塞项

### 7.1 A3/B2 阻塞

当前模板：

```text
benchmark_exports/derived/v2/experiment5_diagnostic/gold_ma_text_smoke20_template.jsonl
```

状态：

```text
模板行数: 20
已填写: 0
未填写: 20
```

需要人工填写：

```json
{
  "chart_id": "KAAA_R03",
  "gold_ma_prose": "MISSED APPROACH: Climb to 2700 direct PIMKE and hold.",
  "source": "human_corrected_from_chart",
  "review_status": "adjudicated"
}
```

必须注意：

```text
只写航图上方 missed approach 文本。
不要写 leg index。
不要写 CA/DF/HM。
不要写 target JSON。
不要写字段拆解结果。
不要写 score。
```

完成后才能跑：

```text
A3_GoldText_Rules
B2a_GoldText_LLM
B2b_GoldText_FieldCandidates_LLM
```

---

### 7.2 G 系列阻塞

当前模板：

```text
benchmark_exports/derived/v2/experiment5_diagnostic/gold_observable_smoke20_template.jsonl
```

状态：

```text
模板行数: 20
已填写: 0
未填写: 20
```

需要单独制作：

```text
gold_observable_smoke20.jsonl
```

每行或每个 observable group 应只包含可观察事实。例如：

```json
{
  "chart_id": "KAAA_R03",
  "observable_id": "KAAA_R03__obs_001",
  "observable_group_id": "ma_step_001",
  "source_regions": ["MISSED_APPROACH_TEXT", "PLAN_VIEW"],
  "evidence_region_ids": ["KAAA_R03_01_missed_approach_text", "KAAA_R03_02_plan_view"],
  "checked_scopes": ["MISSED_APPROACH_TEXT", "PLAN_VIEW", "MISSED_APPROACH_DETAIL_AREA"],
  "facts": {
    "visible_fix": "PIMKE",
    "visible_altitude": 2700,
    "holding_pattern_depicted": true,
    "holding_fix": "PIMKE",
    "holding_turn_direction": "RIGHT",
    "holding_inbound_course_deg": 215,
    "hold_leg_time_explicit": false,
    "hold_leg_distance_explicit": true,
    "hold_leg_distance_nm": 4
  },
  "review_status": "adjudicated"
}
```

禁止写：

```text
Q_terminator = HM
canonical_leg_index = 3
expected value
target field
score
final canonical JSON
```

完成后才能跑：

```text
G0_Direct
G1_Rules
G3_LLM_Rules
G2_LLM optional
```

---

### 7.3 rule_registry 需要审查

当前规则注册表：

```text
benchmark_exports/derived/v2/experiment5_diagnostic/rule_registry.yaml
```

它已经被 `B4_TPD` 使用，但正式结论前还要审查：

```text
哪些是 direct fill 规则；
哪些是 convention/default 规则；
哪些是 424-derived 程序语义规则；
哪些规则会不会偷偷依赖 target；
规则是否只使用允许输入；
B4/G1/G3 是否共用同一冻结规则定义。
```

---

## 8. 新窗口建议执行顺序

### 阶段 1：确认当前状态

进入仓库：

```powershell
Set-Location external_artifact://E/experiment3\github_work\faa-chart-to-424-benchmark-experiment5
```

查看 r4 报告：

```powershell
Get-Content formal_runs\experiment5\experiment5_smoke_20260503_r4_available_methods\reports\experiment5_smoke20_r4_execution_report_zh.md -Encoding UTF8
Get-Content formal_runs\experiment5\experiment5_smoke_20260503_r4_available_methods\reports\experiment5_remaining_methods_input_audit_zh.md -Encoding UTF8
```

确认脚本可编译：

```powershell
python -m py_compile scripts\experiment5\prepare_experiment5_smoke_inputs.py scripts\experiment5\run_experiment5_smoke_b3_b4.py scripts\experiment5\audit_experiment5_remaining_methods.py
```

---

### 阶段 2：如果只继续 ROI 层

已完成 smoke20：

```text
B3_T
B3_TPD
B3_PD
B4_TPD
```

下一步可以扩展到：

```text
formal200
或冻结的 diagnostic subset
```

但扩展前建议先做：

```text
1. 审查 B4_TPD 的 rule_registry；
2. 确认 ROI OCR source-view manifest 在 formal200 中完整；
3. 冻结 run_id、prompt hash、schema hash、candidate schema hash；
4. 明确 schema retry policy；
5. 明确如果 LLM 输出失败是否允许重跑。
```

---

### 阶段 3：补 A3/B2

先人工填写：

```text
benchmark_exports/derived/v2/experiment5_diagnostic/gold_ma_text_smoke20_template.jsonl
```

填写完成后先重跑审计：

```powershell
python scripts\experiment5\audit_experiment5_remaining_methods.py --run-dir formal_runs\experiment5\experiment5_smoke_20260503_r4_available_methods
```

如果审计显示 A3/B2 ready，再写/跑：

```text
A3_GoldText_Rules
B2a_GoldText_LLM
B2b_GoldText_FieldCandidates_LLM
```

---

### 阶段 4：补 G 系列

先制作：

```text
gold_observable_smoke20.jsonl
```

然后写 schema 和 checker，检查：

```text
不含 canonical_answer
不含 canonical_leg_index
不含 Q_terminator answer
不含 target JSON
不含 score
包含 checked_scopes
包含 source_regions / evidence_region_ids
包含 explicit absence，例如 hold_leg_time_explicit = false
```

审计通过后再跑：

```text
G0_Direct
G1_Rules
G3_LLM_Rules
```

G2 可选。

---

### 阶段 5：整合 smoke20 全方法报告

等 A3/B2/G 跑通后，生成一个总报告：

```text
formal_runs/experiment5/<new_run_id>/reports/experiment5_smoke20_all_methods_report_zh.md
```

至少包含：

```text
方法矩阵
输入边界
no-leakage
schema-valid
parse failure
retry
v2 score
strict score
字段族分数
与实验组1对照
与实验组2证据来源对照
与实验组3难例标签对照
当前不能推出的结论
```

---

## 9. 论文故事线中如何解释实验组5

可用表述：

```text
实验组5通过逐层 oracle 诊断显示，单纯把输入限制到 ROI 并不一定提升 LLM 表现；
MA_TEXT 仍是恢复程序结构的关键来源；
P/D 区域包含有用证据，但直接 OCR 文本化后给 LLM，可能引入噪声或绑定错误；
当 ROI OCR 和字段候选已经给定时，冻结规则显著优于 LLM，说明字段候选到程序结构的规则推理仍然是关键环节；
Gold observable 系列尚未完成，后续将进一步验证：如果图上事实由人工确认，规则或 LLM 是否能补全 implicit / 424-derived 字段。
```

不能写：

```text
B4_TPD 证明规则端到端最好。
B3_PD 证明 P/D 区域没用。
现有 field_review 可以直接作为 gold observable。
G 系列已经完成。
```

更准确的写法是：

```text
B4_TPD 证明在 ROI OCR 与自动候选给定条件下，规则系统很强。
B3_PD 证明当前 P/D OCR 文本通道单独不足以恢复完整程序结构，不等于图形区域没有信息。
现有 field_review 可用于实验组2/3分析，但不能作为实验组5方法输入。
G 系列需要重新制作无泄漏的 gold observable 后才能执行。
```

---

## 10. 当前需要特别避免的错误

1. 不要从 canonical target 生成 `gold_ma_prose`。
2. 不要把 `field_reviews` 原样作为 G 的输入。
3. 不要把 `canonical_answer`、`canonical_leg_index`、`Q_terminator`、`leg_type` 放进方法输入。
4. 不要用 score 或 target 决定是否重跑某个样本。
5. 不要把实验组5当成正式 leaderboard；它是诊断实验。
6. 不要把 smoke20 结果直接当 formal200 结论。
7. 不要因为 `B3_PD` 低就说 P/D 区域没有价值；它只能说明“当前 P/D OCR 文本化 + LLM 通道单独不足”。
8. 不要因为 `B4_TPD` 高就说规则系统端到端解决任务；它仍然依赖 ROI OCR 和自动候选。

---

## 11. 当前状态一句话总结

实验组5目前已经把合法的 ROI 诊断层跑通：

```text
B3_T / B3_TPD / B3_PD / B4_TPD
```

结果显示：

```text
MA_TEXT 对程序结构恢复很关键；
P/D OCR 直接加入 LLM 未必有益；
没有 MA_TEXT 的 P/D 通道几乎不能恢复完整程序；
在 ROI OCR + 自动候选给定时，规则系统明显强于 LLM。
```

但：

```text
A3/B2 仍缺无泄漏 gold_ma_prose；
G0/G1/G3 仍缺无泄漏 gold_observable；
rule_registry 仍需正式审查后才能支撑 formal claim。
```

新窗口应优先做：

```text
1. 补 gold_ma_prose，跑 A3/B2；
2. 制作无泄漏 gold_observable，跑 G0/G1/G3；
3. 审查 rule_registry；
4. 汇总 smoke20 全方法；
5. 再决定是否扩展到 formal200 或 diagnostic subset。
```
