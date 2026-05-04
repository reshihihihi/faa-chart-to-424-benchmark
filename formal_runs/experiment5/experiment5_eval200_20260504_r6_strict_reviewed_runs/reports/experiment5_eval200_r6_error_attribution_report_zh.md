# 实验组5 eval200 r6 错误归因报告

- run_id: `experiment5_eval200_20260504_r6_strict_reviewed_runs`
- 日期: 2026-05-04
- 样本: eval200，200 条
- 本报告只做错误归因，不重新 OCR、不重跑实验、不在 eval200 上调参。
- MA_TEXT 正式输入固定为: `formal_runs/experiment5/experiment5_eval200_20260504_r5_ma_text_ocr_review/inputs/gold_ma_text_eval200_ocr_reviewed.jsonl`

## 归因目标

实验组5要回答的问题不是单纯“哪个方法分数高”，而是判断失败主要来自哪里：

1. MA_TEXT 文本输入是否仍然是瓶颈。
2. plan/detail 区域候选是否足够替代 MA_TEXT。
3. 后台框、字段、证据关系派生出来的可见输入是否有用。
4. 规则解析和 LLM canonical 转换分别错在哪里。
5. 目前剩余错误更像 OCR/区域问题，还是字段结构化问题。

## 总体结果

| 方法 | eval200 v2 | dev50 v2 | eval-dev 变化 | schema retry | 归因定位 |
| --- | ---: | ---: | ---: | ---: | --- |
| `A3_GoldText_Rules` | 2752/4052 = 67.92% | 66.34% | +1.58 | 0 | reviewed MA_TEXT + 规则解析上限 |
| `B4_TPD` | 2718/4052 = 67.08% | 65.74% | +1.34 | 0 | MA_TEXT+PD 候选 + 规则解析 |
| `B3_T` | 1227/4052 = 30.28% | 28.32% | +1.96 | 3 | MA_TEXT 区域 + LLM 转换 |
| `B3_TPD` | 1170/4052 = 28.87% | 27.03% | +1.84 | 1 | MA_TEXT+PD 候选 + LLM 转换 |
| `B2b_GoldText_FieldCandidates_LLM` | 1100/4052 = 27.15% | 29.11% | -1.96 | 0 | MA_TEXT + 文本候选 + LLM |
| `B2a_GoldText_LLM` | 970/4052 = 23.94% | 23.47% | +0.47 | 17 | 纯 MA_TEXT + LLM |
| `G3_LLM_Rules` | 265/4052 = 6.54% | 5.54% | +1.00 | 176 | answer-stripped 后台可见事实摘要 + LLM |
| `B3_PD` | 84/4052 = 2.07% | 1.68% | +0.39 | 0 | 只给 plan/detail 可见候选，不给 MA_TEXT |

dev50 到 eval200 的趋势高度一致，所有主要方法变化都在约 2 个百分点以内。因此本轮结果不是 dev50 偶然现象，错误归因可以作为稳定结论使用。

## 一级结论

### 1. MA_TEXT 文本输入已经不是主要瓶颈

证据：

- reviewed MA_TEXT 文件 200 行，no-leakage `PASS`，全部以 `MISSED APPROACH:` 开头。
- A3 只读 reviewed MA_TEXT，达到 67.92%。
- B4_TPD 读 reviewed MA_TEXT + PD visible 候选，达到 67.08%，与 A3 几乎相同。
- 如果 MA_TEXT 文本本身严重错误，A3/B4 不可能稳定到 67% 左右，且 dev50/eval200 趋势不会这么一致。

结论：本轮失败不能主要归因于 OCR 或 MA_TEXT 文本准备。剩余问题主要在“从合法可见文本/候选到 canonical 424 字段”的转换。

### 2. plan/detail 区域不能替代 MA_TEXT

`B3_PD` 只给 `[PLAN_VIEW]` 和 `[MISSED_APPROACH_DETAIL_AREA]` 的后台可见框、label 左半边、图形标记，不给 MA_TEXT。结果只有 2.07%。

字段级也说明它基本恢复不了程序结构：

| 字段 | B3_PD 正确率 |
| --- | ---: |
| `Q1_fix_ident` | 0.00% |
| `Q2_altitude_constraint` | 0.00% |
| `Q3_turn` | 0.00% |
| `Q4_course_or_radial` | 0.16% |
| `Q5_hold_params` | 12.93% |
| `Q_terminator` | 0.00% |
| `leg_count` | 0.00% |

结论：plan/detail 里的框和图形关系可以作为辅助证据，但不能独立恢复 missed approach canonical。它回答了实验组5里的一个关键问题：区域识别/证据关系本身不够，MA_TEXT 仍是主证据源。

### 3. 当前 LLM 失败主要来自 canonical 结构化能力，而不是缺输入

同样都有 MA_TEXT：

- A3 规则法: 67.92%
- B4_TPD 规则法: 67.08%
- B3_T LLM: 30.28%
- B2a LLM: 23.94%
- B2b LLM: 27.15%

这说明 LLM 不是因为完全没有证据而失败，而是在把文本转成 leg 序列、terminator、altitude、course/radial、hold 参数时不稳定。

LLM 的字段级错误尤其明显：

| 字段 | B2a | B2b | B3_T | B3_TPD |
| --- | ---: | ---: | ---: | ---: |
| `Q1_fix_ident` | 43.77% | 46.88% | 46.11% | 42.68% |
| `Q2_altitude_constraint` | 0.47% | 0.78% | 2.80% | 4.67% |
| `Q3_turn` | 43.46% | 51.40% | 64.17% | 63.24% |
| `Q4_course_or_radial` | 11.37% | 13.24% | 11.21% | 9.50% |
| `Q5_hold_params` | 39.25% | 42.06% | 41.90% | 40.81% |
| `Q_terminator` | 9.35% | 11.37% | 20.25% | 17.60% |
| `leg_count` | 11.00% | 18.00% | 15.00% | 12.00% |

结论：LLM 的主要错误不是单个 fix 看不见，而是整体 leg decomposition 和字段归属不稳。尤其 `leg_count`、`Q_terminator` 很差，会导致后续字段成片错位。

### 4. PD 候选目前没有帮到 LLM，反而略微干扰

理论上 `B3_TPD` 比 `B3_T` 多了 plan/detail 可见候选，应该更好。但实际：

- `B3_T`: 30.28%
- `B3_TPD`: 28.87%

逐样本比较：

- TPD 比 T 更好的 chart: 48 个
- TPD 与 T 相同的 chart: 94 个
- TPD 比 T 更差的 chart: 58 个

也就是说，加入 PD 候选后，受益样本少于受损样本。

字段级对比也支持这一点：

| 字段 | B3_T | B3_TPD | 变化 |
| --- | ---: | ---: | ---: |
| `Q1_fix_ident` | 46.11% | 42.68% | -3.43 |
| `Q2_altitude_constraint` | 2.80% | 4.67% | +1.87 |
| `Q3_turn` | 64.17% | 63.24% | -0.93 |
| `Q4_course_or_radial` | 11.21% | 9.50% | -1.71 |
| `Q5_hold_params` | 41.90% | 40.81% | -1.09 |
| `Q_terminator` | 20.25% | 17.60% | -2.65 |
| `leg_count` | 15.00% | 12.00% | -3.00 |

结论：PD 候选的形式现在不适合直接塞给 LLM。它可能增加了候选噪声、改变了注意力、或让模型误把图形候选当作完整程序语义。后续如果要用 PD，需要设计显式融合规则，而不是简单拼接。

### 5. 规则法的剩余错误集中在高度、course/radial、hold

A3 和 B4 是当前最强方法，字段级如下：

| 字段 | A3 | B4_TPD | 主要含义 |
| --- | ---: | ---: | --- |
| `Q1_fix_ident` | 89.10% | 86.92% | fix 识别总体可靠 |
| `Q2_altitude_constraint` | 14.02% | 14.02% | 最大短板 |
| `Q3_turn` | 86.76% | 86.45% | turn 基本可靠 |
| `Q4_course_or_radial` | 55.92% | 55.76% | track/course/radial 仍有明显损失 |
| `Q5_hold_params` | 65.11% | 64.33% | hold 参数仍有损失 |
| `Q_terminator` | 90.34% | 89.10% | terminator 总体可靠 |
| `leg_count` | 88.00% | 86.00% | 航段数总体可靠，但错时影响很大 |

归因：

- `Q2_altitude_constraint` 错误最多，A3/B4 都是 552/642 个字段错误。高度字段不是单纯数字识别问题，而是 desc、归属 leg、是否是 climb-to/hold altitude、是否 AT_OR_ABOVE 等语义表示问题。
- `Q4_course_or_radial` 是第二大短板，A3/B4 约 56%。问题集中在 direct、track、course、radial、navaid radial 的类型判断和归属。
- `Q5_hold_params` 约 64% 到 65%。hold fix 通常能识别，但 inbound course、turn direction、leg distance/time 的完整参数不稳。
- `leg_count` 错的样本不多，A3 错 24/200，B4 错 28/200，但一旦 leg_count 错，多个 leg 字段会连锁错位。

### 6. G3 低分是输入表达太稀疏，不是程序运行失败

G3 使用 answer-stripped 后台可见事实摘要，`admin_gold_answer` 只用于评分。no-leakage 记录显示：

- `g3_uses_admin_gold_answer_for_prediction=false`
- `g3_uses_field_review_for_prediction=false`
- `g3_method_input_forbidden_key_hits=0`

G3 分数 6.54%，schema retry 176 次。字段级：

| 字段 | G3 正确率 |
| --- | ---: |
| `Q1_fix_ident` | 2.02% |
| `Q2_altitude_constraint` | 0.00% |
| `Q3_turn` | 4.98% |
| `Q4_course_or_radial` | 0.78% |
| `Q5_hold_params` | 33.18% |
| `Q_terminator` | 0.00% |
| `leg_count` | 1.00% |

结论：G3 这种可见事实摘要不能直接作为完整程序重建输入。它对 hold 相关事实略有信号，但几乎不能恢复 leg 序列和 terminator。

## 二级归因：按错误来源分类

| 错误来源 | 是否主要问题 | 证据 |
| --- | --- | --- |
| MA_TEXT OCR/文本准备 | 不是主要问题 | reviewed MA_TEXT 200 行 PASS；A3/B4 稳定 67% |
| MA_TEXT 区域是否找到 | 不是本轮主要问题 | 后台 MA_TEXT 框已用于 reviewed 文本；不再依赖自动找框 |
| plan/detail 区域能否单独恢复程序 | 是明确问题 | B3_PD 仅 2.07%，leg_count 0% |
| PD 候选融合方式 | 是问题 | B3_TPD 低于 B3_T，58 个样本变差 |
| 规则解析 | 是剩余主要问题之一 | A3/B4 高但卡在 altitude、course/radial、hold |
| LLM canonical 转换 | 是主要问题 | 同样 MA_TEXT，LLM 只有 24% 到 30% |
| 评分器或 schema 运行错误 | 不是主要问题 | failure_count 全 0；除 G3 外 v2/strict 一致 |

## 样本层面现象

### A3/B4 的低分样本通常伴随 leg_count 错

A3:

- `leg_count` 错 24/200。
- 低于 30% 的 chart 有 11 个。
- 最差样本包括 `KBLF_R05`、`KAPC_R01LY`、`KAPC_R01LZ`、`KACJ_R23`、`KADM_R31`、`KALO_R12`、`KARG_R04`、`KATL_I09R`、`KAVQ_R12`、`KAWM_L17`。

B4_TPD:

- `leg_count` 错 28/200。
- 低于 30% 的 chart 也有 11 个。
- 最差样本高度重合，说明规则法的失败模式稳定，不是随机 API 输出。

### B3_T/B3_TPD 的问题更大：大多数样本 leg_count 不稳

B3_T:

- `leg_count` 错 170/200。
- 低于 30% 的 chart 有 115/200。
- 没有 chart 达到 80%。

B3_TPD:

- `leg_count` 错 176/200。
- 低于 30% 的 chart 有 136/200。
- 有 1 个 chart 0 分。

结论：LLM 方法失败时不是个别字段错，而是程序结构本身没搭起来。

## 对实验组5原问题的回答

实验组5原本关心失败来自哪里：OCR、区域识别、证据关系、字段解析，还是模型转换。

本轮归因回答如下：

1. OCR/MA_TEXT 文本不是这轮主要瓶颈。用户审核后的 MA_TEXT 足够让规则法达到约 67%。
2. MA_TEXT 区域是关键证据源。没有 MA_TEXT 的 B3_PD 几乎失败。
3. 后台 plan/detail 框和关系不是没用，但不能简单替代文本，也不能直接拼给 LLM。
4. 当前最大可改进点在字段结构化：高度约束、course/radial、hold 参数和 leg split。
5. LLM 当前不适合直接从这些输入一步生成 canonical JSON。它需要更强约束的分阶段 prompt 或中间表示。

## 后续动作建议

不要在 eval200 上继续调参。后续应回到 dev50 做针对性修复：

1. 优先修 A3/B4 规则法的 `Q2_altitude_constraint`。
   - 区分 `AT`、`AT_OR_ABOVE`、`AT_OR_BELOW`。
   - 明确 climb-to altitude 与 hold altitude 的归属。
   - 处理 continue climb-in-hold、climb to X then direct Y 等结构。

2. 修 `Q4_course_or_radial`。
   - 区分 direct、track、course、radial、navaid radial。
   - 处理 `via 105° track to`、`on track 307° to`、`R-xxx` 等表达。

3. 修 `Q5_hold_params`。
   - 把 hold fix 与 hold inbound course、turn、distance/time 分开解析。
   - 对 “and hold” 缺参数场景给出稳定默认/unknown 策略。

4. 重新设计 LLM 方法。
   - 不要让 LLM 一步生成完整 canonical。
   - 先让它抽 leg sequence，再逐 leg 填字段，再 schema 校验。
   - PD 候选要作为 disambiguation evidence，不应和 MA_TEXT 平铺混在同一个大输入里。

5. G3 只作为后台可见事实摘要诊断，不应作为正式 blind 主方法。

## 最终结论

实验组5 eval200 r6 的错误归因结论是：

- 主要错误不来自 MA_TEXT OCR。
- 主要错误也不来自是否有后台框。
- 真正瓶颈是把可见文本和候选证据转成 canonical missed approach legs。
- 对规则法来说，瓶颈集中在 altitude、course/radial、hold。
- 对 LLM 来说，瓶颈更前置，主要是 leg_count、terminator、字段归属整体不稳。
- plan/detail 区域目前只能作为辅助证据，不能替代 MA_TEXT，也不能未经结构化融合直接提升 LLM。
