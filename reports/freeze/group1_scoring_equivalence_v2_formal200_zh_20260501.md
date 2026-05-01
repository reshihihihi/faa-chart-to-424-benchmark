# 实验组1 scoring-equivalence v2 修复报告（formal200）

日期：2026-05-01

## 这次修复的问题

实验组1原评分器使用完全严格相等：

```text
pred == target
```

这会把一类本应视为等价的图面显示差异计为错误。例如：

- canonical target 来自 424/CIFP projection，可能保存为 `243.1`；
- 航图上通常显示为 `R-243` 或 `243`；
- 模型/规则方法从航图读取时常输出整数 `243`。

因此，旧评分会把“424 内部一位小数”和“航图整数显示”之间的等价情况误判为错误。这个问题会影响实验组1本身，也会传导到实验组6，因为实验组6的 candidate record 也是从 canonical target 投影得来。

## 修复原则

本次只实现 PR #25 中 narrow scope 的等价规则，不做高风险放宽。

允许：

- `Q4_course_or_radial` 中 `course_deg` / `radial_deg` 的整数图面显示等价；
- `Q4_course_or_radial` 中 `navaid` 的大小写、空格、连字符、点号等 harmless display normalization；
- `Q5_hold_params` 中 `inbound_course_deg` 的整数图面显示等价；
- `Q1_fix_ident` 的 harmless display normalization，虽然本次 formal200 没有实际触发该类改正。

禁止：

- 高度容差；
- 转弯方向放宽；
- holding 默认时间自动等价；
- 距离容差；
- reciprocal course equivalence；
- 航段重新对齐；
- `present` / `not_applicable` / `not_observed` 等 status 放宽。

## 已修改/新增文件

- `scripts/scorers/group1_canonical_field_scorer.py`
  - 保持默认 `--comparison-policy strict` 不变；
  - 新增 `--comparison-policy narrowed_v2`；
  - 在每个字段行输出 `strict_correct` 和 `match_policy`，便于审计。

- `scripts/rescore_group1_formal200_equivalence_v2.py`
  - 专门用于重算 formal200 的已有预测；
  - 自动收集 root run、C2 chunks、C3/C4/D-SFT 独立目录；
  - 不重新推理，不读取 target 到 prompt，仅在 scoring phase 读取 target。

- `benchmark_exports/derived/v2/formal300/targets/comparison_policy_v2.jsonl`
  - 每个 field target 对应一个 comparison policy；
  - 作为后续实验组引用的可追踪 policy manifest。

- `formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/`
  - 保存 v2 重评分结果、逐样本 score、policy scope audit、strict-vs-v2 delta。

## formal200 重评分结果

口径说明：

- `accuracy`：和原 formal summary 一致，只按 schema-valid / scored 样本统计；
- `invalid_as_zero_accuracy`：额外报告，把 missing/schema failure 样本按 0 分计入，便于看到方法失败的惩罚影响。

| 方法 | old accuracy | v2 accuracy | 增加正确字段 | v2 修正字段数 | invalid-as-zero accuracy |
|---|---:|---:|---:|---:|---:|
| A1 | 0.2922 | 0.2922 | 0 | 0 | 0.2922 |
| A2 | 0.2261 | 0.2261 | 0 | 0 | 0.2261 |
| B1 | 0.2725 | 0.2739 | +6 | 6 | 0.2739 |
| B1_prime | 0.3216 | 0.3228 | +5 | 5 | 0.3228 |
| B1_prime_link | 0.1949 | 0.1949 | 0 | 0 | 0.1772 |
| C1 | 0.3709 | 0.3939 | +93 | 93 | 0.3939 |
| C2 | 0.2394 | 0.2651 | +104 | 104 | 0.2651 |
| C3 | 0.3828 | 0.4007 | +71 | 71 | 0.3931 |
| C4 | 0.4008 | 0.4042 | +14 | 14 | 0.4042 |
| D-SFT | 0.7355 | 0.7747 | +146 | 146 | 0.7120 |

## policy scope audit

v2 共把 439 个字段从 strict 错误改为 v2 正确。

按字段：

- `Q4_course_or_radial`：370；
- `Q5_hold_params`：69；
- `Q1_fix_ident`：0；
- 其他字段：0。

按规则：

- `degree_display_rounding`：370；
- `hold_inbound_course_display_rounding`：69；
- `normalized_string`：0。

审计结论：

- violation_count = 0；
- 没有任何高度、转弯、航段对齐、status 放宽；
- 没有把 old strict correct 改成 v2 incorrect；
- C2 的 14 个 root 目录预测已补齐，v2 重评分 C2 为 200/200。

## 对实验组1的结论

实验组1的“424 内部数值 vs 航图显示值”评分问题已经被解决为一个可执行、可复现、可审计的 narrowed scoring-equivalence v2。

这不是提高分数的随意优化，而是修复评分定义和数据来源之间的不一致：target 是 424/CIFP projection，方法看到的是航图显示，评分必须允许这类狭窄的显示等价。

## 对实验组6的影响

实验组6的 candidate record 也来自 canonical target projection，因此同源问题会影响 direct-image verifier 和 extract-then-compare 方法。

当前已经新增 V2 direct-image policy prompts：

- `formal_v2_direct_vlm_verifier_policy_v2.md`：只加入显示等价，smoke10 正例仍 0/5；
- `formal_v2_direct_vlm_verifier_policy_v3.md`：加入 chart-visible vs 424-derived boundary，smoke10 正例 4/5、负例 3/5；
- `formal_v2_direct_vlm_verifier_policy_v4.md`：进一步放宽后反而变差，smoke10 正例 3/5、负例 1/5。

因此当前最合理的实验组6 V2 修复候选是 policy v3，而不是继续放宽。

## 当前保留的风险

- B1_prime_link 仍有 15 个 schema/method failure，本次 scoring-equivalence v2 不解决 runner 稳定性问题；
- C3 仍有 4 个失败样本；
- D-SFT 仍有 16 个失败样本；
- 实验组6 V2 policy v3 已启动 full E6-core r2，需要等待完整 400 case 结果后再决定是否替代 r1。
