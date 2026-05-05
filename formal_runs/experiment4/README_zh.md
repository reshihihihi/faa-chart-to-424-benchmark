# 实验组4输入包说明

实验组4用于 source ablation：比较不同航图来源视图对 missed approach canonical JSON 抽取的影响。

正式输入包不再提交到 Git。外部发布包或本机数据包中保留对应内容；Git
只保留构造脚本、方法定义和必要说明。

历史输入包位置为：

```text
formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1/
```

这些输入定义、manifest、source views、validation 和结果摘要已从 Git
分支移出，避免把数据资产和派生输入包混入代码仓库。

运行时先读取 `manifests/` 和 `source_views/` 生成各 source-view 方法输入。预测全部完成后，才可以读取 scoring manifest 和 target 评分。
