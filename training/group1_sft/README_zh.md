# 实验组1 SFT 扩展运行说明

本目录保存实验组1 SFT 扩展的配置模板、提示词、清单格式和运行入口。大文件不提交到 Git。

## 方法集合

本目录对应五个核心方法：

| 方法 | 输入 | 输出 | 目的 |
|---|---|---|---|
| 同底座未微调对照 | 完整航图图像 | 固定格式 JSON | 判断 D1 提升是否来自微调 |
| D1 | 完整航图图像 | 固定格式 JSON | 保留当前端到端 SFT 主方法 |
| 人工证据到语义 SFT | 人工确认图上证据记录 | 问卷或固定格式 JSON | 诊断第二步是否能做 |
| 航图到证据 SFT | 完整航图图像 | 图上证据记录 | 诊断第一步是否能做 |
| 自动两阶段系统 | 完整航图图像 | 固定格式 JSON | 判断显式拆分是否优于端到端 |

## 本地准备

复制路径模板：

```powershell
Copy-Item training\group1_sft\configs\local_paths.template.json training\group1_sft\configs\local_paths.local.json
```

编辑 `local_paths.local.json`，填入另一台电脑上的真实路径。

检查：

```powershell
python scripts\group1_sft\validate_group1_sft_workspace.py --paths training\group1_sft\configs\local_paths.local.json
```

生成运行清单：

```powershell
python scripts\group1_sft\write_group1_sft_run_manifest.py --paths training\group1_sft\configs\local_paths.local.json --out E:\experiment3\group1_sft\reports\run_manifest.json
```

## 不要提交到 Git 的内容

```text
PDF
PNG 航图图片
训练 JSONL 大文件
模型底座
LoRA 权重
checkpoint
raw outputs
正式评测预测全集
API token
本地绝对路径配置 local_paths.local.json
```

`local_paths.local.json` 应该只留在本机，不提交。

## 正式运行前检查

正式运行前至少确认：

1. 使用的 split 与实验组1正式 split 一致。
2. D1 和同底座未微调对照使用同一底座、同一图像输入、同一解析器、同一评分器。
3. 人工证据到语义 SFT 不输入标准答案、评分结果或 424 原始记录。
4. 航图到证据 SFT 只输出图上证据记录，不直接输出程序语义。
5. 自动两阶段系统第二步只能使用第一步自动生成的证据记录。
6. 所有输出必须可追溯到清单和配置哈希。

