# 实验组2/3 直接飞向证据映射修复报告

生成时间：2026-05-03T13:25:14

## 这次修了什么

这次只修一个程序问题：原始人工标注区域里已经接受的“同一航段直接飞向”映射，没有进入实验组2使用的字段级证据表。

修复范围严格限制为两种同航段情况：

1. 区域框里已经接受了“本航段的航向/航迹/径向 = 直接飞向”，但字段级证据表漏了这一行。
2. 字段级证据表里已经接受了“本航段的航段类型 = 直接飞向某点”，且标准答案要求“本航段的航向/航迹/径向 = 直接飞向”，则补出这一行。

两种情况都必须同一张图、同一航段；不能跨航段补证据。

没有重新跑模型，没有改实验组1结果，没有把第1段证据补给第2段。

## 数量变化

- 原字段级证据行数：347
- 修复后字段级证据行数：357
- 新增“直接飞向”字段证据行：10
- 其中，区域映射直接补证据：3
- 其中，由同航段“直接飞向某点”航段类型补证据：7
- 旧的同字段名但航段不对齐回退行：70
- 修复后的同字段名但航段不对齐回退行：0
- 修复后仍属于“直接飞向”的回退行：0

## 新增证据涉及的航图

| chart_id | score_field | evidence_region_ids | canonical_answer | derived_rule |
| --- | --- | --- | --- | --- |
| KAPC_I01L | leg_2.Q4_course_or_radial | ['KAPC_I01L_01_missed_approach_text'] | {'status': 'present', 'value': {'type': 'direct'}} | 同一航段的直接飞向区域映射补成字段证据 |
| KAXH_L09 | leg_2.Q4_course_or_radial | ['KAXH_L09_01_missed_approach_text'] | {'status': 'present', 'value': {'type': 'direct'}} | 同一航段的直接飞向区域映射补成字段证据 |
| KBMI_I29 | leg_2.Q4_course_or_radial | ['KBMI_I29_01_missed_approach_text'] | {'status': 'present', 'value': {'type': 'direct'}} | 同一航段的直接飞向区域映射补成字段证据 |
| KBFF_L12 | leg_2.Q4_course_or_radial | ['KBFF_L12_01_missed_approach_text'] | {'status': 'present', 'value': {'type': 'direct'}} | 同一航段的直接飞向航段类型推出航向/航迹/径向为直接飞向 |
| KBYL_L20 | leg_2.Q4_course_or_radial | ['KBYL_L20_01_missed_approach_text', 'KBYL_L20_iconalign_002_fix_text'] | {'status': 'present', 'value': {'type': 'direct'}} | 同一航段的直接飞向航段类型推出航向/航迹/径向为直接飞向 |
| KCRW_L05 | leg_2.Q4_course_or_radial | ['KCRW_L05_01_missed_approach_text', 'KCRW_L05_iconalign_002_fix_text'] | {'status': 'present', 'value': {'type': 'direct'}} | 同一航段的直接飞向航段类型推出航向/航迹/径向为直接飞向 |
| KBPT_L12 | leg_2.Q4_course_or_radial | ['KBPT_L12_01_missed_approach_text'] | {'status': 'present', 'value': {'type': 'direct'}} | 同一航段的直接飞向航段类型推出航向/航迹/径向为直接飞向 |
| KBRD_L34 | leg_2.Q4_course_or_radial | ['KBRD_L34_01_missed_approach_text'] | {'status': 'present', 'value': {'type': 'direct'}} | 同一航段的直接飞向航段类型推出航向/航迹/径向为直接飞向 |
| KBTL_L23R | leg_2.Q4_course_or_radial | ['KBTL_L23R_01_missed_approach_text', 'KBTL_L23R_iconalign_002_fix_text'] | {'status': 'present', 'value': {'type': 'direct'}} | 同一航段的直接飞向航段类型推出航向/航迹/径向为直接飞向 |
| KBTP_L08 | leg_2.Q4_course_or_radial | ['KBTP_L08_01_missed_approach_text', 'KBTP_L08_iconalign_002_fix_text'] | {'status': 'present', 'value': {'type': 'direct'}} | 同一航段的直接飞向航段类型推出航向/航迹/径向为直接飞向 |

## 实验组2修复后主表概况

| method | evidence_evidence_bucket | correct | total | accuracy |
| --- | --- | --- | --- | --- |
| A1 | 下方细节区或图中文字证据 | 23 | 54 | 42.59% |
| A1 | 多证据共同支持 | 0 | 1 | 0.00% |
| A1 | 文本直接证据 | 3 | 21 | 14.29% |
| A1 | 规则或默认补全 | 25 | 146 | 17.12% |
| A2 | 下方细节区或图中文字证据 | 12 | 54 | 22.22% |
| A2 | 多证据共同支持 | 0 | 1 | 0.00% |
| A2 | 文本直接证据 | 2 | 21 | 9.52% |
| A2 | 规则或默认补全 | 18 | 146 | 12.33% |
| B1 | 下方细节区或图中文字证据 | 19 | 54 | 35.19% |
| B1 | 多证据共同支持 | 0 | 1 | 0.00% |
| B1 | 文本直接证据 | 17 | 21 | 80.95% |
| B1 | 规则或默认补全 | 42 | 146 | 28.77% |
| B1_prime | 下方细节区或图中文字证据 | 14 | 54 | 25.93% |
| B1_prime | 多证据共同支持 | 0 | 1 | 0.00% |
| B1_prime | 文本直接证据 | 15 | 21 | 71.43% |
| B1_prime | 规则或默认补全 | 39 | 146 | 26.71% |
| B1_prime_link | 下方细节区或图中文字证据 | 14 | 54 | 25.93% |
| B1_prime_link | 多证据共同支持 | 0 | 1 | 0.00% |
| B1_prime_link | 文本直接证据 | 14 | 21 | 66.67% |
| B1_prime_link | 规则或默认补全 | 6 | 146 | 4.11% |
| C1 | 下方细节区或图中文字证据 | 29 | 54 | 53.70% |
| C1 | 多证据共同支持 | 0 | 1 | 0.00% |
| C1 | 文本直接证据 | 10 | 21 | 47.62% |
| C1 | 规则或默认补全 | 41 | 146 | 28.08% |
| C2 | 下方细节区或图中文字证据 | 41 | 54 | 75.93% |
| C2 | 多证据共同支持 | 0 | 1 | 0.00% |
| C2 | 文本直接证据 | 13 | 21 | 61.90% |
| C2 | 规则或默认补全 | 67 | 146 | 45.89% |
| C3 | 下方细节区或图中文字证据 | 28 | 54 | 51.85% |
| C3 | 多证据共同支持 | 0 | 1 | 0.00% |
| C3 | 文本直接证据 | 9 | 21 | 42.86% |
| C3 | 规则或默认补全 | 45 | 146 | 30.82% |
| C4 | 下方细节区或图中文字证据 | 44 | 54 | 81.48% |
| C4 | 多证据共同支持 | 0 | 1 | 0.00% |
| C4 | 文本直接证据 | 19 | 21 | 90.48% |
| C4 | 规则或默认补全 | 42 | 146 | 28.77% |
| D1 | 下方细节区或图中文字证据 | 41 | 54 | 75.93% |
| D1 | 多证据共同支持 | 0 | 1 | 0.00% |
| D1 | 文本直接证据 | 11 | 21 | 52.38% |
| D1 | 规则或默认补全 | 84 | 146 | 57.53% |

## 实验组3修复后难度分布

| difficulty_level | count |
| --- | --- |
| hard | 10 |
| moderate | 9 |

## 当前判断

如果修复后“直接飞向”回退行为 0，说明这类问题已经从程序层面补上；后续可以用这套规则继续扩展到更多已标注样本。

如果仍有其他回退行，它们不能进入主表，需要继续逐类审查，不能直接当作实验组2正式结论。