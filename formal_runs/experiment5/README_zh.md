# 实验组5输入包说明

实验组5是诊断/上限实验，研究人工标注、可见证据、ROI 文本、field candidates、候选绑定等中间信息对最终 missed approach JSON 抽取的帮助。

实验组5输入资产不再提交到 Git。外部发布包或本机数据包中保留对应内容；
Git 只保留构造脚本、方法定义和必要说明。

历史输入资产位置为：

```text
benchmark_exports/derived/v2/experiment5_diagnostic/
formal_runs/experiment5/experiment5_dev50_20260504_r3_strict_no_leak/
formal_runs/experiment5/experiment5_eval200_20260504_r6_strict_visible_inputs/
scripts/experiment5/
```

`dev50` 用于开发和输入检查，`eval200` 用于正式 evaluation 200。严格输入
JSONL 可以作为方法输入；target、score、人工答案和其他方法预测不能在方法
运行时读取。

没有提交逐样本预测输出、HTML/PNG review、PDF 下载件、日志或大结果目录。
