# 实验组 1：SFT 相关方法最终推荐方案

> 目的：基于“从航图得到复飞信息有两个步骤”的理解，重新整理实验组 1 中 SFT 相关方法应该保留、补充和扩展哪些。本文只给最终推荐，不再使用临时编号或随意造缩写。

---

## 0. 核心结论

实验组 1 中，当前已有的 **D1** 可以作为主 SFT 方法保留。它代表的是：

```text
完整航图图像
→ SFT 后的 Qwen-2B 视觉语言模型
→ D-SFT 原始输出
→ D1 规范化为 canonical JSON
```

但是，只保留 D1 不够，因为 D1 是端到端方法，它把两个能力混在了一起：

```text
第一步：从航图中取得复飞相关图像、文字、符号和区域证据。
第二步：从这些证据中组织出复飞程序语义，例如航段、fix、高度、左转/右转、course/radial、holding、Q_terminator 等。
```

因此，最终建议按下面三层做：

```text
必须做：
1. 同底座未微调对照；
2. 保留当前 D1；
3. 人工确认图上证据 → 复飞程序语义 的 SFT 诊断实验。

强烈建议做：
4. 完整航图 → 图上证据记录 的 SFT 诊断实验；
5. 自动两阶段系统：完整航图 → 图上证据记录 → canonical JSON。

可选做：
6. 问卷式作答形式，作为第二步输出方式的一个变体；
7. 图像 + OCR 文本的 SFT，作为 OCR 辅助诊断；
8. OCR 文本到 canonical JSON 的 SFT，作为只测“作答/结构化”的文本诊断。
```

最小可行版本是：

```text
同底座未微调对照
+ 当前 D1
+ 人工确认图上证据 → 复飞程序语义 的 SFT
```

完整推荐版本是：

```text
同底座未微调对照
+ 当前 D1
+ 人工确认图上证据 → 复飞程序语义 的 SFT
+ 完整航图 → 图上证据记录 的 SFT
+ 自动两阶段系统
```

---

## 1. 为什么要这样设计

### 1.1 任务本质不是单一步骤

从航图得到复飞程序语义，至少包含两个步骤。

### 第一步：从航图中取得复飞相关证据

这一阶段回答：

```text
图上有什么？在哪里？属于哪类复飞证据？
```

它需要识别或提取：

```text
上方 missed approach 文本；
平面图中的 fix、course、radial、DME；
holding pattern 图形；
转弯箭头；
高度文字；
lower missed approach detail/icon 区域中的摘要信息；
复飞相关区域的位置。
```

这一阶段的输出不应该是 canonical JSON，而应该是“图上证据记录”。

---

### 第二步：从图上证据中组织复飞程序语义

这一阶段回答：

```text
这些证据对应哪些 missed approach 航段？
每个航段的 fix、高度、转弯、course/radial、holding 是什么？
哪些字段需要隐式规则？
哪些字段是 424-derived？
最终 canonical JSON 是什么？
```

它需要处理：

```text
字段归属到哪个 leg；
航段数量和顺序；
左转 / 右转；
高度约束；
course / radial；
holding 参数；
默认 holding time；
CA、DF、HM 等 path terminator；
canonical JSON 作答格式。
```

---

### 1.2 当前 D1 把两步混在了一起

当前 D1 的端到端流程是：

```text
完整航图图像
→ SFT 视觉模型
→ canonical JSON
```

它同时训练：

```text
看图 / 读文字 / 找证据；
抽字段 / 绑定 leg / 推理隐式字段 / 输出 JSON。
```

因此，如果 D1 做错了，我们不知道错在哪里：

```text
是看不出图上证据？
还是证据看出来了但不会组织成程序？
还是程序知道但 JSON 输出不稳定？
还是模型主要靠文本模板？
```

这就是为什么需要把 SFT 相关实验拆开。

---

## 2. 必须做的实验一：同底座未微调对照

### 2.1 它是什么

使用和 D1 相同的 Qwen-2B 视觉语言模型底座，但不加载 SFT / LoRA 微调权重。

流程：

```text
完整航图图像
→ 同一个 Qwen-2B 视觉语言模型底座
→ 不加载 SFT / LoRA 权重
→ 使用和 D1 尽量一致的 prompt、解码参数、parser、scorer
→ canonical JSON
```

---

### 2.2 为什么必须做

它回答最基础的问题：

```text
D1 的提升到底是不是来自 SFT？
```

C1、C4 不能替代这个对照，因为 C1/C4 通常使用不同模型或不同输入协议。它们只能说明“其他通用 VLM 方法表现如何”，不能隔离同一个底座模型训练前后的差异。

同底座未微调对照要求：

```text
模型底座相同；
图像输入相同；
prompt 尽量相同；
输出解析方式相同；
评分方式相同；
唯一差别是不加载微调权重。
```

---

### 2.3 怎么做

需要准备：

```text
1. 当前 D1 使用的 Qwen-2B 底座模型；
2. D1 推理时使用的完整航图图像输入；
3. D1 尽量相同的 prompt；
4. 同一个 canonical JSON parser；
5. 同一个 PR #25 scoring-equivalence v2 scorer；
6. 同一个 strict 424 exact diagnostic scorer。
```

执行：

```text
对 formal200 evaluation split 跑完整推理；
保存 raw output；
保存 parsed canonical JSON；
记录 schema valid / invalid；
统一评分；
和 D1 对比。
```

---

### 2.4 输出

建议输出：

```text
raw_outputs/qwen2b_unfinetuned/*.txt 或 *.json
parsed_predictions/qwen2b_unfinetuned/*.json
reports/qwen2b_unfinetuned_result.md
```

表格至少包含：

```text
field accuracy；
valid JSON rate；
schema invalid rate；
leg count accuracy；
Q_terminator accuracy；
procedure exact match；
strict vs v2 score；
与 D1 的差值。
```

---

### 2.5 论文中怎么解释

如果同底座未微调明显低于 D1：

```text
说明 SFT 对 chart-to-schema extraction 有真实贡献。
```

如果同底座未微调接近 D1：

```text
说明 Qwen-2B 底座本身已有较强能力，D1 的收益需要谨慎解释，可能主要来自输出格式或少量领域适配。
```

---

## 3. 必须做的实验二：当前 D1

### 3.1 它是什么

D1 是当前已有的 SFT 主方法。

流程：

```text
完整航图图像
→ SFT 后的 Qwen-2B 视觉语言模型
→ D-SFT 原始输出
→ D1 规范化为当前 canonical JSON 接口
→ canonical JSON
```

---

### 3.2 D1 的定位

D1 是：

```text
端到端图像到 canonical JSON 的 SFT 结果。
```

D1 不是：

```text
新的第二个 SFT 模型；
根据 target 修正答案的后处理；
oracle 方法；
实验组 6 的 verifier。
```

D1 的作用是作为实验组 1 的主 SFT baseline。

---

### 3.3 为什么保留 D1

D1 最接近实验组 1 的正式抽取任务：

```text
完整航图 → canonical JSON
```

它回答：

```text
端到端 SFT 能把完整航图直接映射到 canonical missed approach schema 吗？
```

这对主实验很重要，因为它可以和以下方法比较：

```text
未微调 VLM；
图像 + OCR VLM；
OCR + LLM；
OCR + rules。
```

---

### 3.4 需要注意的解释边界

D1 分数高，不等于：

```text
模型真正读懂了所有图形；
模型掌握了所有隐式规则；
模型具备 424 verification 能力；
SFT 已经解决任务。
```

D1 只是证明：

```text
端到端监督微调能提高字段级 schema recovery。
```

后续必须通过实验组 2、3、4、6 分析：

```text
D1 的提升来自文本还是图形？
D1 在 hard cases 上是否仍强？
D1 遮掉 missed approach prose 后是否下降？
D1 的抽取能不能支持 424 candidate 核验？
```

---

## 4. 必须做的实验三：人工确认图上证据 → 复飞程序语义 的 SFT

### 4.1 它是什么

这是专门测试第二步的实验。

输入不是完整航图，而是人工确认过的图上证据记录。

流程：

```text
人工确认图上证据记录
→ SFT 模型
→ 复飞程序语义输出
→ canonical JSON
```

---

### 4.2 它为什么必须做

它回答一个关键问题：

```text
如果图上证据已经给对，模型能不能组织出正确的 missed approach 程序？
```

这可以隔离第二步。

如果这个实验表现高，而 D1 或自动两阶段表现低，说明：

```text
主要瓶颈在第一步，也就是模型没有稳定找到/读出图上证据。
```

如果这个实验表现也低，说明：

```text
即使证据给对，模型仍不会组织程序语义。
第二步本身就是瓶颈。
```

---

### 4.3 输入是什么

输入应该是结构化的“图上证据记录”，来自 PR #18 标注网页或人工确认数据。

示例：

```text
[上方复飞文本]
MISSED APPROACH: CLIMB TO 3000 DIRECT ABCDE AND HOLD.

[平面图证据]
FIX_TEXT: ABCDE
HOLDING_PATTERN: present
COURSE_TEXT: 233
TURN_ARROW: RIGHT

[下方复飞细节区]
No explicit holding time.
```

或者 JSONL 形式：

```json
{
  "chart_id": "KAAA_R03",
  "evidence_items": [
    {
      "source_region": "MISSED_APPROACH_TEXT",
      "item_type": "text_line",
      "text": "CLIMB TO 3000 DIRECT ABCDE AND HOLD"
    },
    {
      "source_region": "PLAN_VIEW",
      "item_type": "fix_text",
      "value": "ABCDE"
    },
    {
      "source_region": "PLAN_VIEW",
      "item_type": "holding_pattern",
      "value": "present"
    },
    {
      "source_region": "PLAN_VIEW",
      "item_type": "course_or_radial_text",
      "value": "233"
    }
  ]
}
```

---

### 4.4 输入来源

主要来自：

```text
PR #18 标注网页的 ROI；
小框；
field_review_v2；
evidence_region_ids；
evidence_source；
checked_scopes；
support_mode；
人工确认的图上事实。
```

注意：

```text
输入可以包含图上可见事实；
不能包含 canonical target；
不能包含 expected value；
不能包含 score；
不能包含 error label；
不能包含“这个字段应该是什么”的答案，除非它确实是图上证据本身。
```

例如：

可以输入：

```text
图上有 holding pattern；
图上 fix 文本为 ABCDE；
图上 course 文字为 233；
图上没有显式 holding time。
```

不应输入：

```text
Q_terminator = HM；
leg_3.Q5_hold_params.leg_time_min = 1；
该字段属于 424_derived；
expected canonical answer is ...
```

除非这是专门的 oracle 诊断，并且在论文中明确标注。

---

### 4.5 输出是什么

可以有两种输出方式。

### 方式一：直接输出 canonical JSON

```text
图上证据记录
→ SFT
→ canonical JSON
```

优点：

```text
和实验组 1 scorer 直接对接；
可以和 D1 直接比较；
更接近最终 extraction 任务。
```

缺点：

```text
输出结构复杂；
可能仍然混入 JSON 作答困难。
```

---

### 方式二：输出固定问卷，再转 canonical JSON

```text
图上证据记录
→ SFT
→ 固定问卷表单
→ 程序转 canonical JSON
```

优点：

```text
降低输出难度；
更适合小模型；
更容易分析每个问题；
可以判断完整 JSON 作答是不是瓶颈。
```

缺点：

```text
需要设计问卷到 canonical JSON 的转换器；
问卷设计不当会丢失航段结构。
```

---

### 4.6 我推荐哪种输出

推荐优先做：

```text
固定问卷表单 → 程序转 canonical JSON
```

原因是这个实验的目的主要是测试第二步：

```text
证据已知时，模型能不能作答和组织程序语义。
```

如果直接输出长 JSON，可能又把“JSON 格式输出难度”混进去。

所以更干净的设计是：

```text
人工确认图上证据
→ 固定问卷式 SFT 作答
→ deterministic parser
→ canonical JSON
→ 统一评分
```

---

### 4.7 评价指标

使用实验组 1 的同一套指标：

```text
field accuracy；
leg count accuracy；
Q_terminator accuracy；
procedure exact match；
valid JSON rate；
over-assertion / under-assertion；
strict score；
scoring-equivalence v2 score。
```

同时要单独按字段类型看：

```text
fix；
altitude；
turn；
course/radial；
holding；
Q_terminator；
implicit/default-rule；
424-derived。
```

---

### 4.8 论文怎么解释

这个实验不能和 D1 完全公平排名，因为它使用了人工确认的图上证据。它应该标成：

```text
oracle / diagnostic second-stage SFT
```

论文中可以写：

> 该实验不是端到端系统，而是为了隔离第二步能力：在图上证据已知的情况下，模型能否组织出正确的复飞程序语义。

---

## 5. 强烈建议做的实验四：完整航图 → 图上证据记录 的 SFT

### 5.1 它是什么

这是专门测试第一步的实验。

流程：

```text
完整航图图像
→ SFT 视觉模型
→ 图上证据记录
```

输出不是 canonical JSON，而是图上证据记录。

---

### 5.2 为什么要做

它回答：

```text
模型能不能从完整航图中找到并读出复飞相关证据？
```

这一步直接测试：

```text
复飞文本识别；
fix 识别；
高度识别；
course/radial 识别；
holding pattern 识别；
转弯箭头识别；
下方 detail/icon 识别；
plan view 证据识别。
```

如果这个实验表现低，说明：

```text
瓶颈在第一步。
```

---

### 5.3 训练数据从哪里来

主要来自 PR #18 标注网页：

```text
MISSED_APPROACH_TEXT；
PLAN_VIEW；
MISSED_APPROACH_DETAIL_AREA；
小框；
evidence_region_ids；
evidence_source；
人工确认的 evidence items。
```

也可以结合 OCR 输出。

---

### 5.4 输出格式

建议输出固定 JSONL 格式的证据记录：

```json
{
  "chart_id": "KAAA_R03",
  "evidence_items": [
    {
      "source_region": "MISSED_APPROACH_TEXT",
      "item_type": "text_line",
      "text": "CLIMB TO 3000 DIRECT ABCDE AND HOLD"
    },
    {
      "source_region": "PLAN_VIEW",
      "item_type": "fix_text",
      "value": "ABCDE"
    },
    {
      "source_region": "PLAN_VIEW",
      "item_type": "holding_pattern",
      "value": "present"
    }
  ]
}
```

不要让它输出：

```text
canonical JSON；
Q_terminator；
CA/DF/HM；
final leg sequence；
expected answer。
```

否则第一步和第二步又混在一起。

---

### 5.5 评价指标

它不能用实验组 1 的 canonical JSON 字段分数直接评。

应该评：

```text
复飞文本召回率；
fix 证据召回率；
altitude 证据召回率；
course/radial 证据召回率；
holding pattern 识别率；
turn 证据识别率；
source_region 分类准确率；
证据 item precision / recall / F1。
```

---

### 5.6 论文怎么解释

这个实验回答：

> 当前端到端模型失败，是不是因为第一步就没有找到图上证据？

如果图上证据抽取 SFT 表现高，而 D1 表现仍低，说明：

```text
第一步不是主要瓶颈，第二步更难。
```

如果图上证据抽取 SFT 表现低，说明：

```text
模型连图上证据都不能稳定获得。
```

---

## 6. 强烈建议做的实验五：自动两阶段系统

### 6.1 它是什么

这是把第一步和第二步串起来。

流程：

```text
完整航图图像
→ 图上证据抽取 SFT
→ 自动图上证据记录
→ 程序语义 SFT
→ canonical JSON
```

---

### 6.2 为什么要做

它回答：

```text
显式分两步是否比端到端 D1 更好？
```

如果自动两阶段系统优于 D1，说明：

```text
把任务拆成“证据取得”和“程序组织”更适合这个领域。
```

如果 D1 优于自动两阶段系统，说明：

```text
两阶段接口可能丢失信息；
证据记录格式还不够好；
端到端模型能利用一些未显式记录的视觉上下文。
```

两种结果都有论文价值。

---

### 6.3 评价指标

使用实验组 1 的同一套 canonical JSON 指标：

```text
field accuracy；
leg count；
Q_terminator；
procedure exact match；
valid JSON；
strict score；
v2 score。
```

并且必须进入实验组 2、3、4、6 的后续分析。

---

### 6.4 注意事项

自动两阶段系统不能用人工证据记录。它必须使用第一步模型自动生成的证据记录。

否则它就不是端到端自动方法，而是 oracle / diagnostic。

---

## 7. 可选实验：图像 + OCR 文本的 SFT

### 7.1 它是什么

流程：

```text
完整航图图像 + 完整航图 OCR 文本
→ SFT 模型
→ canonical JSON 或固定问卷
```

---

### 7.2 为什么做

它回答：

```text
OCR 文本能不能减轻 SFT 模型的图中文字识别负担？
```

它对应实验组 1 中的 C4：

```text
C4：未微调模型 + 图像 + OCR 文本；
图像 + OCR 文本 SFT：微调模型 + 图像 + OCR 文本。
```

---

### 7.3 风险

它可能强化文本捷径。

如果做了这个实验，必须用实验组 2 和实验组 4 检查：

```text
它是不是只在 text_explicit 字段上提升？
遮掉上方 missed approach 文本后是否大幅下降？
plan_profile_only、implicit、424_derived 是否仍低？
```

---

## 8. 可选实验：OCR 文本到 canonical JSON 的 SFT

### 8.1 它是什么

流程：

```text
完整航图 OCR 文本
→ SFT 模型
→ canonical JSON
```

---

### 8.2 为什么做

它隔离的是“作答/结构化能力”。

它回答：

```text
如果图中文字已经由 OCR 提供，模型能不能把文本组织成 canonical JSON？
```

它更像 B 组的监督版本，不是视觉 SFT 主线。

---

### 8.3 什么时候做

如果想进一步区分：

```text
视觉识别瓶颈
vs
文本到 schema 的结构化瓶颈
```

可以做。

但它不是当前最优先。

---

## 9. 不推荐现在做的内容

### 9.1 直接核验 SFT

流程：

```text
航图图像 + candidate 424 record
→ consistent / inconsistent + error_fields
```

这个属于实验组 6，不属于实验组 1。

不要混进实验组 1。

---

### 9.2 只改 parser / prompt 的变体

如果只是：

```text
换一个 parser；
换一个输出清洗器；
换一个 prompt；
```

这不应该被称为新的 SFT 方法。

---

### 9.3 过多 SFT 变体

不要在主文中放太多 SFT 方法，否则论文会偏离 E&D benchmark 主线，变成 SFT 工程论文。

---

## 10. 最终推荐执行顺序

### 阶段一：必须完成

```text
1. 跑同底座未微调对照；
2. 保留当前 D1；
3. 做人工确认图上证据 → 复飞程序语义 的 SFT。
```

这三项可以回答：

```text
SFT 是否有贡献？
端到端 SFT 能做到多少？
如果证据已知，模型是否能组织程序语义？
```

---

### 阶段二：强烈建议完成

```text
4. 做完整航图 → 图上证据记录 的 SFT；
5. 做自动两阶段系统。
```

这两项可以回答：

```text
模型能否获得图上证据？
两阶段分解是否优于端到端 D1？
```

---

### 阶段三：有余力再做

```text
6. 图像 + OCR 文本的 SFT；
7. OCR 文本到 canonical JSON 的 SFT；
8. 字段问答式 SFT。
```

这些用于更细的诊断，不是最低闭环必需。

---

## 11. 如何根据结果判断瓶颈

### 情况一：同底座未微调低，D1 高

说明：

```text
SFT 本身有效。
```

---

### 情况二：D1 低，但人工确认图上证据 → 程序语义 SFT 高

说明：

```text
第二步能做，第一步证据取得是瓶颈。
```

---

### 情况三：人工确认图上证据 → 程序语义 SFT 也低

说明：

```text
即使证据已知，模型仍不会组织复飞程序语义；
第二步是瓶颈。
```

---

### 情况四：图上证据抽取 SFT 高，但自动两阶段低

说明：

```text
证据记录和程序语义 SFT 之间的接口有问题，或者自动证据记录质量不够稳定。
```

---

### 情况五：自动两阶段高于 D1

说明：

```text
显式分解“证据取得 → 程序组织”优于端到端 SFT。
```

---

### 情况六：D1 高于自动两阶段

说明：

```text
端到端模型可能利用了两阶段接口丢掉的上下文；
当前图上证据记录格式可能太粗。
```

---

## 12. 与实验组 2、3、4、6 的关系

所有新增 SFT 结果都不能只看实验组 1 overall。

### 12.1 接入实验组 2

看：

```text
text_explicit；
plan_profile_only；
implicit_by_convention；
424_derived；
错误类型；
证据复杂度。
```

目的：

```text
判断 SFT 提升来自文本，还是来自图形/隐式/424-derived。
```

---

### 12.2 接入实验组 3

看：

```text
implicit_hold_time；
has_ca_leg；
has_hm_leg；
ca_df_sequence；
terminator_derived；
plan_profile_only_holding。
```

目的：

```text
判断 SFT 是否真的改善 hard cases。
```

---

### 12.3 接入实验组 4

看：

```text
完整航图；
只给上方文本；
遮掉上方文本；
只给 plan view；
只给 detail/icon；
只给非上方文本复飞区域。
```

目的：

```text
判断 SFT 是否依赖文本捷径。
```

---

### 12.4 接入实验组 6

如果某个 SFT 输出 canonical JSON，就可以作为 extract-then-compare 的 extraction source。

目的：

```text
判断抽取提升是否能转化成 424 candidate 核验能力。
```

---

## 13. 主文怎么写

建议主文只放最关键的 SFT 相关方法：

```text
同底座未微调对照；
当前 D1；
人工确认图上证据 → 复飞程序语义 SFT；
自动两阶段系统，如果完成。
```

如果版面不够，人工确认图上证据实验可以放诊断表，自动两阶段放主文或附录，视结果重要性决定。

不要把所有可选 SFT 变体都塞进主表。

---

## 14. 最终一句话

实验组 1 的 SFT 扩展不应围绕“多加几个微调模型”，而应围绕两步任务结构：

```text
第一步：从完整航图取得复飞相关图上证据；
第二步：从这些证据组织复飞程序语义并输出 canonical JSON。
```

因此，最终最有价值的设计是：

```text
同底座未微调对照
+ 当前 D1
+ 人工确认图上证据到程序语义的 SFT
+ 完整航图到图上证据记录的 SFT
+ 自动两阶段系统
```

这套设计能明确回答：

```text
SFT 是否有效；
端到端 D1 的能力在哪里；
失败是在图上证据取得阶段，还是在程序语义组织阶段；
显式两阶段分解是否比端到端更适合 chart-to-424 任务。
```
