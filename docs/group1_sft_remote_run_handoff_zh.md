# 实验组1 SFT 扩展：远端机器运行交接说明

本文用于把实验组1新增 SFT 相关方案迁移到另一台电脑执行。当前分支只提交代码、配置模板、方法说明和脚本入口；训练图片、模型权重、检查点和大批量输出不放入 Git。

## 目标

在另一台电脑继续准备并运行实验组1的 SFT 扩展方法，重点包括：

1. 同底座未微调对照：完整航图图像到固定格式 JSON。
2. 当前 D1：已微调视觉模型到固定格式 JSON。
3. 人工确认图上证据到复飞程序语义的 SFT 诊断实验。
4. 完整航图到图上证据记录的 SFT 诊断实验。
5. 自动两阶段系统：完整航图到图上证据记录，再到固定格式 JSON。

## 仓库内已经包含什么

新增或整理的仓库内文件：

```text
docs/group1_sft_final_recommendations_zh.md
docs/group1_sft_remote_run_handoff_zh.md
training/group1_sft/README_zh.md
training/group1_sft/configs/local_paths.template.json
training/group1_sft/configs/group1_sft_method_set.json
training/group1_sft/manifests/group1_sft_manifest_schema.json
training/group1_sft/prompts/evidence_to_questionnaire.zh.md
training/group1_sft/prompts/chart_to_evidence.zh.md
scripts/group1_sft/validate_group1_sft_workspace.py
scripts/group1_sft/write_group1_sft_run_manifest.py
scripts/group1_sft/prepare_group1_sft_run_package.py
scripts/group1_sft/run_qwen2vl_group1_sft_inference.py
training/group1_sft/manifests/evidence_record.schema.json
training/group1_sft/manifests/evidence_questionnaire.schema.json
```

## 另一台电脑需要单独准备什么

这些内容不通过 Git 同步，需要在另一台电脑本地准备：

```text
正式评测图像
训练图像
训练 JSONL
开发集 JSONL
Qwen-2B 视觉语言模型底座
D1 已训练权重或 LoRA checkpoint
CUDA / PyTorch / transformers / peft 等运行环境
实验输出目录
```

建议本地大文件目录：

```text
<GROUP1_SFT_ROOT>\
  data\
  images\
  train_jsonl\
  dev_jsonl\
  checkpoints\
  raw_outputs\
  parsed_predictions\
  reports\
```

## 另一台电脑开始步骤

```powershell
git clone https://github.com/reshihihihi/faa-chart-to-424-benchmark.git
cd faa-chart-to-424-benchmark
git switch group1-sft-extension-plan-20260503
```

复制本地路径模板：

```powershell
Copy-Item training\group1_sft\configs\local_paths.template.json training\group1_sft\configs\local_paths.local.json
```

编辑：

```text
training/group1_sft/configs/local_paths.local.json
```

填入另一台电脑上的真实模型、数据、输出路径。

先做环境检查：

```powershell
python scripts\group1_sft\validate_group1_sft_workspace.py --paths training\group1_sft\configs\local_paths.local.json
```

生成一次运行清单：

```powershell
python scripts\group1_sft\write_group1_sft_run_manifest.py --paths training\group1_sft\configs\local_paths.local.json --out $env:GROUP1_SFT_ROOT\reports\run_manifest.json
```

生成 formal200 SFT 扩展 run package：

```powershell
python scripts\group1_sft\prepare_group1_sft_run_package.py --paths training\group1_sft\configs\local_paths.local.json
```

该 package 会优先使用 `benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/` 下的 chart-display v2 target 和 `comparison_policy_v2.jsonl`，只在 v2 target 不存在时回退到原始 scoring manifest。

如需先跑小样本冒烟：

```powershell
python scripts\group1_sft\prepare_group1_sft_run_package.py --paths training\group1_sft\configs\local_paths.local.json --limit 5 --run-id group1_sft_smoke5
```

run package 会写出：

```text
scoring_manifest.jsonl
D_BASE_SAME_BACKBONE/input_manifest.jsonl
D1/input_manifest.jsonl
EVIDENCE_TO_SEMANTICS_SFT/input_manifest.jsonl
CHART_TO_EVIDENCE_SFT/input_manifest.jsonl
TWO_STAGE_AUTO_SFT/input_manifest.jsonl
reports/preflight_report.json
reports/preflight_report_zh.md
RUN_COMMANDS.md
```

同底座未微调对照和 D1 复跑使用统一入口：

```powershell
python scripts\group1_sft\run_qwen2vl_group1_sft_inference.py --method D_BASE_SAME_BACKBONE --input-manifest $env:GROUP1_SFT_ROOT\runs\group1_sft_smoke5\D_BASE_SAME_BACKBONE\input_manifest.jsonl --model-dir $env:QWEN2_VL_2B_BASE --prompt training\d_sft\prompts\d_sft_image_to_canonical.v2.md --json-schema schemas\missed_approach_leg.schema.json --scoring-manifest $env:GROUP1_SFT_ROOT\runs\group1_sft_smoke5\scoring_manifest.jsonl --output-root $env:GROUP1_SFT_ROOT\runs\group1_sft_smoke5\D_BASE_SAME_BACKBONE
```

```powershell
python scripts\group1_sft\run_qwen2vl_group1_sft_inference.py --method D1 --input-manifest $env:GROUP1_SFT_ROOT\runs\group1_sft_smoke5\D1\input_manifest.jsonl --model-dir $env:QWEN2_VL_2B_BASE --adapter-checkpoint $env:D1_CHECKPOINT --prompt training\d_sft\prompts\d_sft_image_to_canonical.v2.md --json-schema schemas\missed_approach_leg.schema.json --scoring-manifest $env:GROUP1_SFT_ROOT\runs\group1_sft_smoke5\scoring_manifest.jsonl --output-root $env:GROUP1_SFT_ROOT\runs\group1_sft_smoke5\D1
```

## 当前还没有提交到 Git 的内容

本分支没有提交训练权重、训练集图片、正式评测输出、检查点和大文件。这是故意的，避免仓库膨胀，也避免把机器相关路径和临时结果混进论文仓库。

如果需要在两台机器之间同步大文件，建议使用外部硬盘、对象存储、压缩包或专门的模型/数据目录，不建议用 Git。

## 执行顺序建议

1. 先跑同底座未微调对照的小样本冒烟测试。
2. 确认 D1 权重能加载，并跑同一小样本。
3. 生成并检查 formal200 run package 的 preflight blocker。
4. 生成“人工确认图上证据到复飞程序语义”的训练/开发/评估清单。
5. 跑该诊断 SFT 的小样本训练。
6. 生成“完整航图到图上证据记录”的训练/开发清单。
7. 跑该诊断 SFT 的小样本训练。
8. 串起自动两阶段系统。
9. 最后再进入正式 split 推理和评分。

## 方法边界

实验组1 SFT 扩展仍然是抽取任务，不是实验组6的 424 反事实核验。

推理阶段禁止输入：

```text
标准答案 JSON
424 原始记录
评分结果
其他方法预测结果
人工答案
```

诊断实验如果使用人工确认图上证据，必须在报告中标明它是诊断/上界类实验，不能和端到端方法直接公平排名。
