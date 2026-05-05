# 实验组 6 当前状态说明：424 反事实核验实验

生成时间：2026-05-02  
当前主结果目录：

```text
formal_runs/experiment6/experiment6_group1formal200_full200_v10_d1_20260502_r1
```

旧结果保留目录：

```text
formal_runs/experiment6/experiment6_group1formal200_full200_v9_chartdisplay_20260501_r1
```

---

## 1. 实验组 6 要回答什么问题

实验组 6 的主题是 **424 反事实核验**。

它不是普通的“从航图抽取 canonical JSON”实验，而是进一步模拟一个更接近发布核验的任务：

```text
给定一张航图 + 一个 candidate 424-like record，
判断这个 candidate 是否与航图一致；
如果不一致，指出错在哪些字段。
```

这里的 candidate record 来自 canonical target 的投影：

- 正例：candidate 与 canonical target 一致；
- 负例：在 canonical target 基础上构造一个反事实错误，例如改 fix、改 altitude、改 course/radial、删 CA leg、改 hold 参数等。

实验组 6 的目的不是单纯追求最高准确率，而是回答：

1. 系统能不能发现 candidate 424-like record 与航图之间的不一致；
2. 直接看图核验是否比 OCR 文本核验更强；
3. “先抽取 canonical JSON，再和 candidate 比较”的路线是否成立；
4. 比较规则过硬或过松会如何影响结论；
5. D-SFT 的输出经过 D1 格式规范化后，能否更公平地进入 424 反事实核验流程。

---

## 2. 当前使用的数据与 case 构造

当前实验组 6 使用的是实验组 1 formal200 对应的 E6-core verification split。

case 文件：

```text
formal_runs/experiment6/experiment6_group1formal200_full200_v9_chartdisplay_20260501_r1/E6_core/cases/e6_core_200pos_200neg_seed20260501_chartdisplay_v2.jsonl
```

规模：

| 项目 | 数量 |
|---|---:|
| unique charts | 200 |
| verification cases | 400 |
| positive cases | 200 |
| negative counterfactual cases | 200 |

每条 verification case 包含：

- `verification_case_id`
- `chart_id`
- `sample_id`
- `candidate_record`
- `label` / 一致性标签
- `counterfactual_type`
- 预期错误字段标签，用于评分

当前 v9/v10 使用的是 `chart-display v2` candidate，也就是已经吸收实验组 1 PR #25 的显示值等价规则，避免把 harmless display differences 当作反事实错误。

---

## 3. 已经完成的方法

实验组 6 当前已经完成以下路线。

### 3.1 V1：OCR text verification

方法名：

```text
V1_OCR_text_chartdisplay_v2
```

输入：

```text
OCR text + candidate record
```

做什么：

模型只看 OCR 文本和 candidate record，判断 candidate 是否与航图一致。

目的：

作为文本证据核验 baseline，判断只靠 OCR 文本能否做 AIP–424 一致性检查。

当前结果：

| 指标 | 数值 |
|---|---:|
| total | 400 |
| valid | 400 |
| binary accuracy | 49.00% |
| positive accept | 69.50% |
| negative reject | 28.50% |
| invalid rate | 0.00% |

解释：

V1 接近随机，说明只靠 OCR 文本核验 candidate 的能力有限。它容易接受正例，但很难拒绝负例。

---

### 3.2 V2：direct image verification

方法名：

```text
V2_direct_image_policyv3_chartdisplay_v2
```

输入：

```text
完整航图图像 + candidate record
```

做什么：

VLM 直接看图和 candidate record，判断 candidate 是否一致。

目的：

测试直接图像核验路线是否比 OCR 文本更强。

当前结果：

| 指标 | 数值 |
|---|---:|
| total | 400 |
| valid | 400 |
| binary accuracy | 56.75% |
| positive accept | 40.50% |
| negative reject | 73.00% |
| invalid rate | 0.00% |

解释：

V2 是当前直接核验路线里较有解释力的结果。它更擅长拒绝负例，但接受正例能力偏弱，说明模型容易对 candidate 保守或过度怀疑。

---

### 3.3 V3-C4：C4 extract-then-compare

方法名：

```text
V3_C4_group1v2_neutralized
```

输入：

```text
C4 extraction canonical JSON + candidate record
```

做什么：

先用实验组 1 的 C4 方法抽取 canonical JSON，再把 C4 输出与 candidate record 做字段比较。

目的：

测试“先抽取，再比较”的路线是否可行。

当前结果：

| 指标 | 数值 |
|---|---:|
| total | 400 |
| valid | 400 |
| binary accuracy | 50.00% |
| positive accept | 0.00% |
| negative reject | 100.00% |
| invalid rate | 0.00% |

解释：

V3-C4 strict compare 出现极端行为：几乎全部判为不一致。这说明严格字段比较对抽取误差非常敏感，不能简单把 extraction output 和 candidate 做符号级硬比较。

---

### 3.4 V3-D1-SFT：D-SFT after D1, strict compare

方法名：

```text
V3_D1_SFT_group1v2_neutralized
```

输入：

```text
D1 canonicalized D-SFT output + candidate record
```

做什么：

先用 D1 把 D-SFT raw output 规范化成固定 canonical JSON，再与 candidate record 做严格比较。

目的：

消除 D-SFT 输出格式/schema 不一致造成的上游失败，让实验组 6 更公平地评估 D-SFT 抽取内容对反事实核验的作用。

当前结果：

| 指标 | pre-D1 | D1 后 |
|---|---:|---:|
| valid | 370/400 | 400/400 |
| parse/schema fail | 30 | 0 |
| binary accuracy | 48.25% | 52.00% |
| positive accept | 3.80% | 4.00% |
| negative reject | 100.00% | 100.00% |
| field overlap norm | 81.18% | 81.50% |

解释：

D1 主要修正了格式有效性问题，使 D-SFT 分支从 30 个失败降到 0 个失败。  
但 strict compare 仍然严重偏向“判不一致”，正例接受率只有 4.00%，说明严格比较仍不适合作为最终强 verifier 结论。

---

### 3.5 V4-C4：C4 tolerant compare

方法名：

```text
V4_C4_tolerant_chartdisplay_v2
```

输入：

```text
C4 extraction canonical JSON + candidate record
```

做什么：

仍然是 extract-then-compare，但加入更宽松的比较规则，例如字段等价、显示值容差、partial compare 等。

目的：

诊断 V3-C4 的极端结果是否由比较规则太硬导致。

当前结果：

| 指标 | 数值 |
|---|---:|
| total | 400 |
| valid | 400 |
| binary accuracy | 50.50% |
| positive accept | 61.50% |
| negative reject | 39.50% |
| invalid rate | 0.00% |

解释：

V4-C4 相比 V3-C4 不再全部拒绝，说明比较规则确实影响很大。但整体准确率仍接近 50%，说明 C4 抽取误差和字段对齐问题仍会限制 verification。

---

### 3.6 V4-D1-SFT：D-SFT after D1, tolerant compare

方法名：

```text
V4_D1_SFT_tolerant
```

输入：

```text
D1 canonicalized D-SFT output + candidate record
```

做什么：

用 D1 后的 D-SFT canonical JSON 作为 extraction source，再用 tolerant compare 判断 candidate 是否一致。

目的：

测试“更稳定的 D-SFT 输出 + 宽松比较规则”是否能形成更合理的 extract-then-compare verification 路线。

当前结果：

| 指标 | pre-D1 | D1 后 |
|---|---:|---:|
| valid | 370/400 | 400/400 |
| parse/schema fail | 30 | 0 |
| binary accuracy | 52.00% | 55.75% |
| positive accept | 57.61% | 57.50% |
| negative reject | 54.84% | 54.00% |
| field overlap norm | 48.39% | 47.50% |

解释：

V4-D1-SFT 是当前 D-SFT extract-then-compare 路线中更适合作为正式候选口径的一版。它不再有 schema/parse failure，且正负例行为比较均衡，但整体准确率仍只是在中等水平。

---

## 4. 已完成的 control / oracle

当前实验组 6 还完成了四个 control/oracle 检查项。

| 方法 | 作用 | 结果意义 |
|---|---|---|
| `control_all_accept` | 全部判一致 | 50/50 数据下应约 50%，用于确认基础线 |
| `control_all_reject` | 全部判不一致 | 50/50 数据下应约 50%，用于确认负例偏置 |
| `control_oracle_label` | 使用真实 label | 应为 100%，用于确认 scorer 没坏 |
| `control_v0_candidate_integrity` | candidate-only / 构造完整性检查 | 用于检查 candidate 构造方向和标签方向 |

这些 control 的作用是防止把数据构造、scorer、label 方向或 candidate artifact 的问题误认为模型能力。

---

## 5. 已完成的审计

当前已经完成以下审计：

1. **no-leakage 审计**
   - V1、V2、V3 输入检查均通过；
   - 没有把 target、score、counterfactual label、expected error fields 泄漏到模型输入。

2. **missing / duplicate / unexpected case 审计**
   - v9/v10 主分支均检查过；
   - 新增 D1 分支 400 条 case 全部覆盖；
   - 无 missing case；
   - 无 duplicate case；
   - 无 unexpected case。

3. **D1 覆盖审计**
   - D1 formal200 样本数：200；
   - raw output 找到：200；
   - canonical JSON 写出：200；
   - schema-valid：200/200；
   - schema-invalid：0；
   - E6-core 缺失 D1 canonical JSON：0；
   - final chart_id mismatch：0。

4. **retry / attempt 汇总**
   - V1/V2 是模型调用；
   - V3/V4 是基于已有 extraction output 的 symbolic compare；
   - D1 后 D-SFT 分支没有 API retry，也没有选择性重跑低分样本。

5. **分层统计**
   - 已按 counterfactual type；
   - procedure/sample 类型；
   - leg_count；
   - field category；
   - 做过分层统计。

---

## 6. 当前主要结果总结

当前最重要的主表如下：

| 方法 | total | valid | invalid | binary acc | positive accept | false alarm | negative reject | miss rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V1 OCR text | 400 | 400 | 0 | 49.00% | 69.50% | 30.50% | 28.50% | 71.50% |
| V2 direct image | 400 | 400 | 0 | 56.75% | 40.50% | 59.50% | 73.00% | 27.00% |
| V3-C4 strict | 400 | 400 | 0 | 50.00% | 0.00% | 100.00% | 100.00% | 0.00% |
| V3-D1-SFT strict | 400 | 400 | 0 | 52.00% | 4.00% | 96.00% | 100.00% | 0.00% |
| V4-C4 tolerant | 400 | 400 | 0 | 50.50% | 61.50% | 38.50% | 39.50% | 60.50% |
| V4-D1-SFT tolerant | 400 | 400 | 0 | 55.75% | 57.50% | 42.50% | 54.00% | 46.00% |

当前比较合理的正式候选结果是：

- `V2_direct_image_policyv3_chartdisplay_v2`
- `V4_D1_SFT_tolerant`

`V3-C4` 和 `V3-D1-SFT strict` 更适合作为诊断结果，说明严格抽取后比较容易退化为“几乎全部拒绝”。

---

## 7. 已完成但不建议作为正式主口径的内容

以下内容已经做了，但不建议作为论文主口径：

1. **pre-D1 D-SFT 分支**
   - 原因：有 30/400 个上游 parse/schema failure；
   - 保留价值：说明 D-SFT raw output 需要格式规范化。

2. **V3 strict extract-then-compare**
   - 原因：正例接受率极低；
   - 保留价值：说明简单符号级比较过硬，不足以代表完整 verification 能力。

3. **旧 v8/v9 诊断记录**
   - 原因：部分口径是在 PR #25 scoring-equivalence v2 完全消除前生成；
   - 保留价值：记录问题发现和修正过程。

---

## 8. 还没有做完的事情

当前实验组 6 的核心实验和 D1 修正已经完成，但还有以下事情没有完全做完。

### 8.1 正式 freeze package 尚未最终整理

还需要把当前 v10-D1 口径整理成正式冻结包，包括：

- 方法定义；
- 输入边界；
- candidate 构造政策；
- D1 policy；
- scorer；
- case manifest；
- prediction manifest；
- hash；
- no-leakage 审计；
- 最终结果表。

### 8.2 PR 整理尚未完成

当前结果还没有作为一个干净 PR 提交到 GitHub。

需要注意：

- 不能把过大的中间文件全部塞进 PR；
- 应该提交脚本、配置、method card、核心报告和小型 summary；
- 大文件可通过 artifact 路径或 release 说明保存。

### 8.3 paired bootstrap / 置信区间还没补齐

当前已有点估计和分层统计，但正式论文中最好补：

- chart-level paired bootstrap；
- V2 vs V4-D1-SFT；
- V1 vs V2；
- V3 strict vs V4 tolerant；
- confidence interval；
- difference stability。

这一步用于支持统计不确定性控制。

### 8.4 论文图表还没整理

当前已有 CSV/Markdown，但还需要做论文用表格：

- 主结果表；
- pre-D1 vs D1 修正表；
- negative reject / positive accept trade-off 表；
- counterfactual type 分层表；
- 关键失败案例表。

### 8.5 实验组 6 与实验组 1 PR #25 的最终依赖还需写清楚

当前 v9/v10 已经使用 chart-display v2 消除了 PR #25 对实验组 6 的影响，但正式说明中仍要写清楚：

- PR #25 是实验组 1 scoring-equivalence 修正；
- 实验组 6 不是把它当成新方法；
- 实验组 6 把它作为 candidate/display comparison 的前置规范；
- 这样避免 harmless display mismatch 被错误计为 counterfactual error。

---

## 9. 当前建议的正式口径

当前建议实验组 6 的正式口径如下：

| 角色 | 方法 |
|---|---|
| OCR baseline | `V1_OCR_text_chartdisplay_v2` |
| direct image verifier | `V2_direct_image_policyv3_chartdisplay_v2` |
| strict extract-then-compare diagnostic | `V3_C4_group1v2_neutralized`、`V3_D1_SFT_group1v2_neutralized` |
| tolerant extract-then-compare diagnostic / candidate | `V4_C4_tolerant_chartdisplay_v2`、`V4_D1_SFT_tolerant` |
| controls | `all_accept`、`all_reject`、`oracle_label`、`candidate_integrity` |

其中 D-SFT 分支建议使用 D1 后结果：

```text
V3_D1_SFT_group1v2_neutralized
V4_D1_SFT_tolerant
```

pre-D1 结果只作为诊断记录：

```text
V3_D_SFT_pre_D1_group1v2_neutralized
V4_D_SFT_pre_D1_tolerant
```

---

## 10. 当前结论

实验组 6 目前已经完成了一版完整、可解释、可复现的 424 反事实核验实验。

核心结论可以这样写：

1. 只靠 OCR 文本做 424 candidate verification 能力有限；
2. 直接图像核验 V2 相对更能发现负例，但也更容易误拒正例；
3. 直接把抽取 JSON 和 candidate 做严格符号比较会产生极端行为；
4. tolerant compare 能缓解严格比较的问题，但仍受抽取质量限制；
5. D1 消除了 D-SFT 输出格式/schema failure，使 D-SFT 分支可以公平进入实验组 6；
6. 实验组 6 支持论文故事线：从航图抽取到 424 发布核验之间，关键难点不仅是字段抽取，还包括证据绑定、字段等价、容差比较和反事实核验策略。

---

## 11. 关键文件位置

### 当前 v10-D1 结果

```text
formal_runs/experiment6/experiment6_group1formal200_full200_v10_d1_20260502_r1
```

### 中文更新报告

```text
formal_runs/experiment6/experiment6_group1formal200_full200_v10_d1_20260502_r1/reports/experiment6_v10_d1_update_report_zh.md
```

### D1 对比表

```text
formal_runs/experiment6/experiment6_group1formal200_full200_v10_d1_20260502_r1/reports/experiment6_v10_d1_comparison_table.csv
```

### D1 完整性审计

```text
formal_runs/experiment6/experiment6_group1formal200_full200_v10_d1_20260502_r1/reports/experiment6_v10_d1_integrity_audit.json
```

### 本状态说明

```text
formal_runs/experiment6/experiment6_group1formal200_full200_v10_d1_20260502_r1/reports/experiment6_current_status_and_work_done_zh.md
```
