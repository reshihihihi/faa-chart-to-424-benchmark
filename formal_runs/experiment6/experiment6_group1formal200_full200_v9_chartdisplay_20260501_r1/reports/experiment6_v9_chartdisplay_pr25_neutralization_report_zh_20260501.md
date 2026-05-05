# 实验组6：消除 PR #25 显示值等价影响后的 v9 结果

## 1. 这次真正要解决的问题

PR #25 给实验组1增加的是 `chart-display scoring-equivalence v2` 功能。它的本质不是新增一个模型方法，而是修正“424 内部值”和“航图显示值”之间的无害差异，例如：

- `63.3` 与航图显示 `063` / `63` 应视为同一航迹角显示；
- `243.1` 与航图显示 `R-243` 应视为同一径向线显示；
- fix / navaid 名称中的大小写、连字符、局部显示格式不应被当成实质错误。

实验组6原来的 v8 case 直接从 raw canonical target 投影 candidate record，所以大量正例 candidate 里带有 `63.3`、`243.1` 这类航图不会原样显示的值。这样会把“显示格式差异”误当成“424 反事实错误”，导致实验组6被 PR #25 的功能污染。

因此正确处理不是把 `V4_PR25` 当成一个新实验方法，而是把 PR #25 的功能作为实验组6的前置规范消除掉。

## 2. v9 的修正方式

v9 采用下面的处理：

- candidate record 改由 `canonical_proxy_gt_chart_display_v2.json` 生成；
- E6-core 仍使用原来的 400 条 case id，case id hash 不变；
- extract-then-compare 比较器使用 Group 1 v2 等价规则；
- 旧的 `V4_PR25` 不再作为论文方法解释，只作为 corrected / neutralized comparator 的实现来源；
- D-SFT 的 schema-invalid 继续按 D-SFT 上游方法失败计入，不在实验组6里修补。

这样，实验组6测的就是“候选 424-like record 是否真的和航图不一致”，而不是测模型能否忍受 424 小数和航图整数之间的显示差异。

## 3. 影响审计

- E6-core total cases: `400`
- candidate changed cases: `378`
- positive changed cases: `192`
- negative changed cases: `186`

这说明旧 v8 结果确实大范围受到 PR #25 显示值等价功能影响。v8 应标记为 pre-fix / affected-by-display-equivalence，不应继续作为实验组6主结果。

## 4. v9 E6-core 结果

| method | valid | binary acc | positive accept | false alarm | negative reject | miss rate | normalized error-field overlap | invalid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V1_OCR_text_chartdisplay_v2 | 400 | 49.0% | 69.5% | 30.5% | 28.5% | 71.5% | 16.5% | 0.0% |
| V2_direct_image_policyv3_chartdisplay_v2 | 400 | 56.8% | 40.5% | 59.5% | 73.0% | 27.0% | 25.0% | 0.0% |
| V3_C4_group1v2_neutralized | 400 | 50.0% | 0.0% | 100.0% | 100.0% | 0.0% | 41.5% | 0.0% |
| V3_D_SFT_group1v2_neutralized | 370 | 48.2% | 3.8% | 96.2% | 100.0% | 0.0% | 81.2% | 7.5% |
| V4_C4_tolerant_chartdisplay_v2 | 400 | 50.5% | 61.5% | 38.5% | 39.5% | 60.5% | 20.0% | 0.0% |
| V4_D_SFT_tolerant_chartdisplay_v2 | 370 | 52.0% | 57.6% | 42.4% | 54.8% | 45.2% | 48.4% | 7.5% |

## 5. 结果解释

1. PR #25 的显示值影响已经通过 v9 输入构造和 v2 等价比较被消除，不再作为实验组6的独立变量。
2. V2 direct image 是当前更可信的直接图像核验结果：binary acc 为 56.75%，negative reject 为 73.0%，但 positive accept 仍只有 40.5%，说明模型仍偏保守，容易拒绝真实候选。
3. V3_C4 在 neutralized 后仍然全拒绝，说明问题不只是 PR #25，而是 extraction-then-compare 的严格 leg/field 对齐仍会让正例失败。
4. V4 tolerant 可以缓解全拒绝，但它不是 PR #25 功能本身；它对应的是更宽的航段对齐、partial compare 和 mismatch threshold，应该作为 diagnostic / ablation 解释。
5. D-SFT 相关结果仍有 7.5% invalid，来源是上游 D-SFT canonical extraction schema-invalid；这不是实验组6构造问题。

## 6. 后续处理建议

- 实验组6主结果应使用 v9_chartdisplay，而不是旧 v8。
- 报告和 PR 中应删除“新增 V4_PR25 方法”的表述，改成“Group 1 v2 neutralization applied before Experiment 6 evaluation”。
- 如果后续写论文，v8 可以作为问题诊断过程，不作为正式实验结果。
