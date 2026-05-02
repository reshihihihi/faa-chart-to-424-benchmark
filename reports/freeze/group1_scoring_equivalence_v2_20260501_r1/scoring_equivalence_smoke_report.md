# 实验组1 scoring-equivalence v2 最小 smoke report

本 smoke test 只检查两类 scoring-equivalence v2 规则是否按预期工作：

1. Fix / navaid 名称显示形式差异。
2. 航向 / 航迹 / 径向 / holding inbound course 的 424 小数角度与航图整数显示差异。

## Case

Chart: `KABE_I06`

测试构造一个 display-equivalent prediction：它把 target 中部分小数角度按航图显示方式写成整数，同时保持其他字段不变。

| scorer/case | correct | total | accuracy | wrong fields |
|---|---:|---:|---:|---|
| strict v1 target vs display-equivalent prediction | 16 | 19 | 0.8421 | leg_1.Q4_course_or_radial, leg_2.Q4_course_or_radial, leg_3.Q5_hold_params |
| narrowed v2 target vs display-equivalent prediction | 19 | 19 | 1.0000 | none |
| narrowed v2 target vs bad radial prediction | 18 | 19 | 0.9474 | leg_2.Q4_course_or_radial |

结论：v2 可以接受 `63.3 -> 63`、`243.1 -> 243` 这类航图整数显示等价，但不会把明显错误的 `245` 径向放宽为正确。
