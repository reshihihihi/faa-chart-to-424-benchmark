# 实验组2新窗口交接说明

生成时间：2026-05-03

本文用于在新窗口继续推进实验组2。新窗口开始后，建议先阅读本文，再读取文中列出的关键文件。本文只写实验组2相关内容，实验组3只在“依赖关系”处简要说明。

## 1. 实验组2要回答什么问题

实验组2的核心目的不是重新跑模型，也不是重新评分实验组1。

实验组2要做的是：

把实验组1已经跑出的字段级结果，和人工标注中的证据位置、证据类型对应起来，分析不同方法在哪些证据来源上容易成功或失败。

换句话说，实验组2研究的是：

1. 哪些字段类型更容易错。
2. 错误是否和证据来源有关。
3. 模型是否更擅长读复飞文字，还是更擅长读平面图、图中小字、高度框、定位点框。
4. 对于不该填写的字段，模型是否会乱填。
5. 对于由航段结构或编码语义推出的字段，模型是否能处理。

实验组2不直接评价“哪张图更难”。这个问题属于实验组3。

## 2. 实验组2使用哪些输入

实验组2目前依赖三类输入。

### 2.1 实验组1字段级评分结果

实验组1已经为每张航图、每种方法、每个字段生成了字段级对错结果。

实验组2会读取这些结果，得到类似下面的信息：

```text
某张航图
某个方法
某个航段
某个字段
模型预测值
标准答案
是否正确
错误类型
```

目前相关来源主要在：

```text
<FAA_BENCH_REPO>/formal_runs/group1
```

当前实验组2脚本使用的是实验组1正式评估结果目录：

```text
<GROUP1_RUN>
```

### 2.2 标准答案字段表

标准答案来自 424 编码转换后的固定格式。

实验组2使用的字段级标准答案表是：

```text
<FAA_BENCH_REPO>/benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/field_targets_chart_display_v2.jsonl
```

这个文件把每张航图拆成字段级目标。例如：

```text
第2段的航段类型
第2段的定位点
第2段的高度限制
第2段的航向/航迹/径向
```

其中字段名会保留代码形式，例如：

```text
Q_terminator = 航段类型
Q1_fix_ident = 定位点或导航台名称
Q2_altitude_constraint = 高度限制
Q3_turn = 转弯方向
Q4_course_or_radial = 航向、航迹、径向，或“直接飞向”
Q5_hold_params = 等待程序参数
```

### 2.3 人工标注结果

人工标注结果来自标注平台后台导出。

最近一次用于检查的后台状态保存在：

```text
<GROUP2_ANNOTATION_STATUS_ROOT>
```

其中：

```text
<GROUP2_ANNOTATION_STATUS_ROOT>/admin_overview_formal300_latest_20260503.json
<GROUP2_ANNOTATION_STATUS_ROOT>/shujuji_annotation_export_2026-05-03T07-24-24-338Z.json
```

当前后台标注状态是：

```text
正式集总数：300 张
已提交：300 张
已领取但未提交：0 张
未领取：0 张
当前草稿：0 张
正式标注文件：300 张
提交快照覆盖：300 张
后台显示进度：100%
```

最后补齐的 4 张是：

| 序号 | 航图 | 程序 | 类型 | 当前状态 | 标注人 |
|---|---|---|---|---|---|
| 1 | KABE_I06 | ILS OR LOC RWY 06 | ILS | 已提交 | A21 |
| 2 | KALS_I02 | ILS OR LOC RWY 02 | ILS | 已提交 | A21 |
| 10 | KBUY_I06-Z | ILS Z OR LOC Z RWY 06 | ILS | 已提交 | A21 |
| 88 | KCBF_R36 | RNAV (GPS) RWY 36 | RNAV | 已提交 | A21 |

注意：后台管理员口令不要写入仓库文件或公开文档。需要刷新时，在本地或浏览器里临时使用即可。

## 3. 实验组2当前已经做过什么

实验组2已经先用一批试跑样本验证过流程。

当前试跑目录是：

```text
<GROUP23_ROOT>
```

已做过的主要事情包括：

1. 读取人工标注导出。
2. 选择已经提交且实验组1结果齐全的航图。
3. 生成字段级人工证据表。
4. 读取实验组1各方法字段级评分。
5. 把字段级评分和人工证据按“航图、航段、字段”对齐。
6. 把实验组2主表、负类表、审查表分开。
7. 发现并修复“直接飞向字段证据漏生成”的程序问题。
8. 修复后重新生成实验组2和实验组3相关文件。

## 4. 当前试跑样本情况

一开始拿 30 张做流程验证。

其中真正满足“人工标注已提交、实验组1各方法结果齐全、可以做方法间对比”的是 19 张。

因此当前实验组2的完整可比试跑结果，是基于这 19 张。

这 19 张不是正式结论，只用于验证流程是否正确。

正式实验组2应该在 300 张人工标注完成后，使用更大的正式集合重新生成。

## 5. 实验组2数据表如何分

修复后的实验组2把字段分成几类，避免混在一起。

### 5.1 应该填写的字段主表

这是实验组2最重要的主表。

条件是：

```text
标准答案状态 = 应该填写
并且找到了同一张图、同一航段、同一字段的人工证据
```

这部分用来分析：

```text
不同方法在不同证据来源上的准确率
```

修复后，19 张完整可比样本中：

```text
应填写字段主表行数：2220
```

### 5.2 不适用字段表

不适用字段的意思不是“图上没有这个字”，也不是“424 编码缺失”。

它的意思是：

```text
在当前航段语义下，这个字段不应该填写。
```

例如某个航段不需要等待程序参数，那么等待程序字段就是不适用。

这部分用于分析：

```text
模型是否会在不该填的地方乱填。
```

它不能混进“证据来源主表”，否则会把实验组2问题搞偏。

### 5.3 航段数量字段

航段数量是任务规模控制变量，不是普通证据来源字段。

它应该单独保留，用于控制样本复杂度，例如：

```text
两段航图
三段航图
四段及以上航图
```

不能把航段数量当作“文本证据”或“图像证据”来分析。

### 5.4 审查表

如果字段不能严格按同一航段对齐，就进入审查表，不能进入主表。

之前最主要的问题是：

```text
第2段的“航向/航迹/径向 = 直接飞向”没有找到同航段证据，
程序退而找到了同图第1段的同名字段证据。
```

这在逻辑上是不允许的。

修复后：

```text
旧的跨航段回退行：70
修复后的跨航段回退行：0
```

## 6. 已修复的重要程序问题

### 6.1 问题是什么

以 `KAPC_I01L` 为例。

航图右上角复飞文字中有：

```text
direct SGD
```

意思是：

```text
第2段直接飞向 SGD。
```

标准答案中对应：

```text
第2段的航向/航迹/径向 = 直接飞向
```

人工标注中，右上角复飞文字框已经包含这个信息。

但旧程序生成实验组2字段证据表时，只读了正式字段复核表，没有充分利用区域框中的已接受映射，也没有把“同一航段直接飞向某点”补成“航向/航迹/径向=直接飞向”字段证据。

结果导致：

```text
第2段证据漏了；
程序退到第1段同名字段；
第1段和第2段被错误混在一起。
```

### 6.2 为什么这是程序问题

因为人工标注原始数据中已经存在相关信息。

在原始导出中，`KAPC_I01L_01_missed_approach_text` 这个复飞文字框下面，能看到：

```text
第2段
航段类型 = 直接飞向某点
字段 = 航向/航迹/径向
值 = 直接飞向
人工复核 = 接受
```

但实验组2使用的字段级证据表里没有生成对应行。

所以问题不在实验组1，不在模型，不在 424 标准答案，也不是人工完全没标。

问题是：

```text
原始标注结果 → 字段级证据表
```

这一步漏掉了应有的字段证据。

### 6.3 修复规则

当前修复只允许两种同航段情况。

第一种：

```text
区域框里已经接受了：
本航段的航向/航迹/径向 = 直接飞向
但字段级证据表漏了这一行。
```

第二种：

```text
字段级证据表里已经接受了：
本航段的航段类型 = 直接飞向某点
且标准答案要求：
本航段的航向/航迹/径向 = 直接飞向
则补出这一行。
```

两种情况都必须满足：

```text
同一张图
同一航段
同一语义
不能跨航段
```

### 6.4 修复结果

修复脚本：

```text
<GROUP23_ROOT>/scripts/run_group2_group3_direct_q4_fix.py
```

修复报告：

```text
<GROUP23_ROOT>/reports/direct_q4_fix_20260503_report_zh.md
```

审计文件：

```text
<GROUP23_ROOT>/reports/direct_q4_fix_20260503_audit.json
```

修复后的关键结果：

```text
原字段级证据行数：347
修复后字段级证据行数：357
新增“直接飞向”字段证据行：10
旧的跨航段回退行：70
修复后的跨航段回退行：0
修复后仍属于“直接飞向”的回退行：0
```

新增 10 行里：

```text
3 行来自“区域映射直接补证据”
7 行来自“同航段直接飞向航段类型推出航向/航迹/径向为直接飞向”
```

涉及航图：

```text
KAPC_I01L
KAXH_L09
KBFF_L12
KBMI_I29
KBPT_L12
KBRD_L34
KBTL_L23R
KBTP_L08
KBYL_L20
KCRW_L05
```

其中之前重点审查的 7 张全部补齐：

```text
KAPC_I01L
KAXH_L09
KBFF_L12
KBRD_L34
KBTL_L23R
KBTP_L08
KCRW_L05
```

## 7. 当前生成的关键文件

### 7.1 修复后的字段级证据表

```text
<GROUP23_ROOT>/group2/evidence_provenance_pilot30_direct_q4_fix_20260503.jsonl
```

### 7.2 新增的 10 条直接飞向证据

```text
<GROUP23_ROOT>/group2/direct_q4_added_evidence_direct_q4_fix_20260503.jsonl
```

### 7.3 修复后的实验组2连接表

```text
<GROUP23_ROOT>/group2/group2_joined_field_scores_pilot30_direct_q4_fix_20260503.jsonl
```

### 7.4 修复后的实验组2完整可比 19 张审计

```text
<GROUP23_ROOT>/group2/group2_complete19_direct_q4_fix_20260503_audit.json
```

### 7.5 修复后的实验组2主表

```text
<GROUP23_ROOT>/group2/group2_positive_joined_field_scores_complete19_direct_q4_fix_20260503.jsonl
```

### 7.6 修复后的跨航段回退表

```text
<GROUP23_ROOT>/group2/group2_positive_question_fallback_complete19_direct_q4_fix_20260503.jsonl
```

这个文件现在应该是空的，因为跨航段回退已经清零。

## 8. 当前成果

实验组2现在已经完成了流程验证。

可以确认：

1. 实验组1字段级结果可以和人工证据表对齐。
2. 应填写字段、不适用字段、航段数量字段、审查字段已经分开。
3. 之前最主要的跨航段证据问题已经修掉。
4. 当前 19 张完整可比样本中，应填写字段已经可以进入主表。
5. 当前 19 张完整可比样本中，跨航段回退已经为 0。

关键数字：

```text
完整可比航图：19 张
应填写字段主表行数：2220
跨航段回退行数：0
应填写但没有证据的字段：0
```

这说明实验组2的主流程已经跑通。

## 9. 当前还存在的问题

### 9.1 正式 300 张已完成

目前正式集 300 张已经全部提交。

正式全量 runner 已经执行，审计通过。

paired 主表口径：

```text
<GROUP2_FORMAL_ROOT>/group2_formal300_paired200_methodfailure_v1_20260503_155704
```

available-score 补充口径：

```text
<GROUP2_FORMAL_ROOT>/group2_formal300_available_scores_v1_20260503_152409
```

paired 主表用于严格方法间比较：300 张标注中选取 Group1 已评分的 200 张；若某个方法在这 200 张内因 schema invalid 没有 score JSON，则按 method failure 计入，而不是丢弃整张图。available-score 表覆盖全部 300 张，但不同方法分母不完全一致，只作为补充。

### 9.2 已生成新的正式导出

正式导出已保存到：

```text
<GROUP2_ANNOTATION_STATUS_ROOT>
```

其中 export 文件：

```text
shujuji_annotation_export_2026-05-03T07-24-24-338Z.json
```

### 9.3 修复规则需要写进正式实验方案

“同一航段直接飞向某点，可以补出该航段航向/航迹/径向=直接飞向”这条规则必须写入实验组2正式方法说明。

否则正式实验中会出现：

```text
脚本里做了，但论文方法里没说
```

这是不允许的。

### 9.4 中文标签需要清理

部分旧输出文件里有中文乱码。

这主要是旧脚本里的中文字符串编码显示问题，不一定影响结果逻辑，但正式报告和提交前应统一清理。

建议后续新脚本使用清晰中文标签，例如：

```text
文本直接证据
平面图直接证据
图中文字证据
规则或默认补全
编码语义字段
同一航段补充证据
```

### 9.5 不适用字段还需要单独分析

不适用字段用于分析模型是否乱填。

后续需要单独生成：

```text
方法 × 不适用字段类型 × 乱填率
方法 × 字段族 × 乱填率
```

不能把不适用字段混进普通证据来源分析。

## 10. 新窗口推荐执行顺序

### 第一步：读取本交接文件

先读：

```text
<GROUP23_ROOT>/reports/group2_new_window_handoff_zh.md
```

### 第二步：确认后台标注是否已完成

读取或刷新后台进度。

最近一次本地保存结果：

```text
<GROUP2_ANNOTATION_STATUS_ROOT>/annotation_completion_check_20260503_summary.json
```

如果仍然是 296/300，就先不要正式跑全量。

如果已经是 300/300，则进入下一步。

### 第三步：生成新的后台导出

在后台管理页面生成正式导出。

注意：

```text
不要把管理员口令写入仓库文件。
导出 JSON 要保存到本地实验目录。
```

建议保存到：

```text
<GROUP2_ANNOTATION_STATUS_ROOT>
```

### 第四步：基于新导出重跑实验组2

需要把脚本里的人工标注导出路径切换到最新导出。

当前相关脚本：

```text
<GROUP23_ROOT>/scripts/run_group2_group3_direct_q4_fix.py
```

但这个脚本目前是针对 pilot30/complete19 的修复验证脚本。
本分支已经新增正式/已提交标注 runner：

```text
scripts\group2\run_group2_formal_submitted_v1.py
```

推荐输出目录仍使用：

```text
<GROUP2_FORMAL_ROOT>/<run_id>\
```

如果 300 张全部完成，用 `formal300` 命名。当前正式 paired 主输出已经采用 200 张 Group1 交集口径：

```text
group2_formal300_paired200_methodfailure_v1_20260503_155704
```

该 run 显式使用：

```text
--expected-analysis-count 200
--count-missing-scores-as-method-failure
```

其中 D1 修正后是 200 张；`B1_prime_link` 有 15 张 schema-invalid/无 score，`C3` 有 4 张 schema-invalid/无 score，已按 method failure 计入。

如果只用 296 张已提交子集，用 `formal_submitted296` 命名，避免误写成完整 300。
此时命令应显式使用：

```text
--expected-submitted-count 296
```

这样报告会把结论限定在 submitted296 口径内，而不是 formal300。

正式 runner 每次会写 chart / field / region 三层标注快照。当前 formal300 run 已经用 submitted296 run 作为基线完成变更定位：

```text
changed_chart_count = 4
changed_field_count = 42
changed_region_count = 34
changed_chart_ids = KABE_I06, KALS_I02, KBUY_I06-Z, KCBF_R36
```

后续如果修改已有标注，下一次运行时传入：

```text
--previous-run-root <旧的 group2_formal run 目录>
```

即可生成：

```text
inputs/annotation_change_audit.json
inputs/annotation_changed_charts.jsonl
inputs/annotation_changed_fields.jsonl
inputs/annotation_changed_regions.jsonl
```

这些文件用于定位后续改动发生在哪张图、哪个字段、哪个区域；确认改动无误后，以最新 run 的表格和报告作为当前结论版本。

示例命令见：

```text
docs/group2/run_on_second_machine_zh.md
```

### 第五步：保留四类输出

正式跑实验组2时，至少输出：

```text
字段级证据表
实验组1字段评分与证据连接表
应填写字段主表
不适用字段分析表
审查/异常表
总审计文件
中文报告
```

建议目录结构：

```text
<GROUP2_FORMAL_ROOT>/
  inputs\
  evidence\
  joined\
  tables\
  audits\
  reports\
```

### 第六步：跑完后必须检查

正式跑完后，至少检查：

```text
1. 总样本数是否等于预期。
2. 每张图是否有实验组1结果。
3. 应填写字段是否都能找到同航段证据。
4. 跨航段回退是否为 0。
5. 不适用字段是否没有混进主表。
6. 航段数量是否只作为规模控制变量。
7. 直接飞向补证据规则是否只作用在同一航段。
8. 中文报告是否可读，没有乱码。
```

如果这些检查不过，不能进入正式结论。

## 11. 实验组2正式报告应该包含什么

正式报告建议包含：

1. 使用了多少张航图。
2. 人工标注完成情况。
3. 每个方法覆盖了多少字段。
4. 应填写字段主表数量。
5. 不适用字段数量。
6. 异常/审查字段数量。
7. 证据来源分类结果。
8. 方法在不同证据来源上的准确率。
9. 方法在不同字段类型上的准确率。
10. 模型乱填不适用字段的比例。
11. 直接飞向补证据规则的数量和审计结果。
12. 明确哪些结果可以作为正式结论，哪些只是审计或补充说明。

## 12. 当前最推荐的下一步

现在最推荐的动作是：

1. 使用 `group2_formal300_paired200_methodfailure_v1_20260503_155704` 作为实验组2 paired 主表结论来源。
2. 使用 `group2_formal300_available_scores_v1_20260503_152409` 作为覆盖全部 300 张的补充分析，注意不用于严格 paired 方法比较。
3. 先写实验组2正式结果摘要，明确输入是 300/300 人工标注、Group1 scoring-equivalence v2 字段分数。
4. 报告审计数字：`positive_question_fallback_rows = 0`，`unmatched_present_rows = 0`，`evidence_on_not_applicable_rows = 0`。
5. 后续如有任何标注修改，必须用 `--previous-run-root` 对比当前 formal300 run，并审查 `annotation_changed_*` 文件。

当前可以说：

```text
实验组2已经在 formal300 全量人工标注上完成；
paired 主表覆盖 Group1 已评分的 200 张航图；
证据对齐审计通过，没有跨航段 fallback 和应填写字段缺证据问题；
available-score 版本覆盖全部 300 张，但只作为补充。
```

