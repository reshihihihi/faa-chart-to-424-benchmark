# 实验组 1 D 系列 final-v2 两机并行执行手册

日期：2026-05-06

本文档是 `docs/group1_d_final_v2_experiment_plan_zh_20260506.md` 的执行补充，用于在两台 GPU 设备上并行运行 D 系列 final-v2 SFT。本文档只写通用流程，不写 Dataverse 预览 token、本机绝对路径、checkpoint 或 raw output。

## 1. 并行目标

时间不足时，D 系列 final-v2 的两个 SFT run 应拆到两台设备并行执行：

| 设备 | 推荐任务 | 说明 |
| --- | --- | --- |
| 设备 A | `D1-500_FINAL_V2` | 训练时间最长，适合放在数据、模型、GPU 环境最稳定的机器上 |
| 设备 B | `D1-50_FINAL_V2`，可顺带跑 `D_BASE_SAME_BACKBONE_FINAL_V2` | D1-50 训练短，可快速验证流程；D-base 不训练，也适合空闲设备跑 |

如果设备 B 的显存或模型路径不稳定，则设备 B 只跑 D1-50；D-base 可回到设备 A 或任一空闲设备执行。

## 2. 两台设备必须完全一致的内容

以下内容必须一致，否则 D1-50 和 D1-500 的对照不干净：

```text
Git commit
PR #39 final-v2 scoring code / policy 版本
Dataverse final-v2 artifact package 版本
formal300 split 文件
base VLM model
final-v2 D prompt
schema / no-unknown policy
训练脚本
推理脚本
评分脚本
训练超参数
parser/canonicalization policy
```

允许不同的只有：

```text
run_id
训练 JSONL：D1-50 用 subset50，D1-500 用 train500
checkpoint 输出目录
推理输出目录
评分输出目录
```

## 3. 先冻结一次，不要两台机器各自随机生成

在正式并行前，必须先在一台机器上冻结以下文件或 manifest：

```text
corrected D1-500 train JSONL
corrected dev100 JSONL
D1-50 subset JSONL
D1-50 subset manifest
final-v2 D prompt
final-v2 output policy
data audit report
```

D1-50 不能由两台机器各自随机抽样。它必须来自 corrected D1-500 train set 的固定 seed 子集。

推荐记录：

```text
subset seed: 260506
source train500 hash
subset50 JSONL hash
50 个 sample_id / chart_id
dev100 JSONL hash
prompt hash
policy hash
```

## 4. 设备共同准备步骤

两台设备都先执行：

```powershell
git fetch origin
git checkout <同一个 commit 或 branch>
git status --short --branch
```

确认以下文件存在：

```text
docs/group1_d_final_v2_experiment_plan_zh_20260506.md
docs/group1_d_final_v2_two_machine_runbook_zh_20260506.md
scripts/score_final_v2_sft_outputs.py
benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/comparison_policy_v2.jsonl
reports/final_v2_field_legality_unknown_cleanup_zh_20260506.md
```

如果 PR #39 尚未合入 main，则两台设备必须明确 checkout 到包含 PR #39 等价内容的 commit，或在本地 fetch PR #39 并使用相同 merge commit。

## 5. 本地路径配置

每台机器单独创建本地路径配置，例如：

```text
local_paths.local.json
```

至少填写：

```text
repo_root
dataset_root
formal_images_dir
formal_split_file
final_v2_policy_path
corrected_train500_jsonl
corrected_dev100_jsonl
subset50_jsonl
base_vlm_model_dir
output_root
reports_dir
```

本地路径配置不能提交 Git。

## 6. 设备 A：D1-500 执行步骤

设备 A 执行：

```text
1. 读取主实验方案和本手册。
2. 校验 corrected train500/dev100 的 hash。
3. 跑数据审计，确认 no-unknown、schema、图片路径、leakage check。
4. 使用 train500 训练 D1-500_FINAL_V2。
5. 训练完成后保存 checkpoint hash 和训练指标。
6. 先跑 smoke5 推理。
7. smoke5 无路径或脚本错误后，跑 formal200 推理。
8. 使用 final-v2 scorer 评分。
9. 输出运行报告。
```

run id 建议：

```text
d1_500_final_v2_qwen2vl_lora_20260506_r1
```

## 7. 设备 B：D1-50 执行步骤

设备 B 执行：

```text
1. 读取主实验方案和本手册。
2. 校验 subset50/dev100 的 hash。
3. 确认 subset50 manifest 中的 sample_id / chart_id 与冻结记录一致。
4. 跑数据审计，确认 no-unknown、schema、图片路径、leakage check。
5. 使用 subset50 训练 D1-50_FINAL_V2。
6. 训练完成后保存 checkpoint hash 和训练指标。
7. 先跑 smoke5 推理。
8. smoke5 无路径或脚本错误后，跑 formal200 推理。
9. 使用 final-v2 scorer 评分。
10. 输出运行报告。
```

run id 建议：

```text
d1_50_final_v2_qwen2vl_lora_20260506_r1
```

## 8. D-base 放在哪台机器跑

D-base 不训练，只需要底座模型推理。它可以放在任一空闲设备上跑。

推荐：

```text
如果设备 B 跑完 D1-50 后空闲，则设备 B 跑 D-base。
如果设备 B 环境不稳定，则设备 A 在 D1-500 训练空档或训练完成后跑 D-base。
```

D-base run id 建议：

```text
d_base_same_backbone_final_v2_20260506_r1
```

D-base 必须使用和 D1-50/D1-500 完全相同的 prompt、parser/canonicalization policy、formal split 和 final-v2 scorer。

## 9. 推理边界

推理阶段只能读取：

```text
完整航图 PNG
final-v2 D prompt
base model
对应 LoRA checkpoint，D-base 无 LoRA
```

推理阶段禁止读取：

```text
target JSON
score
raw 424/CIFP
其他方法预测
comparison policy
scoring manifest
```

comparison policy 和 scoring manifest 只能在预测全部完成后用于评分。

## 10. 评分命令模板

每个 run 完成后执行：

```powershell
python scripts\score_final_v2_sft_outputs.py `
  --predictions-dir <run_output>\canonical_json `
  --dataset-root <NIPS-AIP-Dataset-v1.0-draft> `
  --split evaluation `
  --policy benchmark_exports\derived\v2\formal300\targets\scoring_equivalence_v2\comparison_policy_v2.jsonl `
  --output-dir <run_output>\final_v2_scores
```

评分输出：

```text
aggregate_summary.json
per_sample_scores.jsonl
field_scores.jsonl
sample_errors.jsonl
run_manifest.json
```

## 11. 每台机器最终必须回传的内容

可以回传或提交小型摘要文件：

```text
run_manifest.json
train_metrics.json
dev_metrics.json
aggregate_summary.json
per_sample_scores.jsonl
field_scores.jsonl
sample_errors.jsonl
中文运行报告
```

不要提交：

```text
模型权重
LoRA checkpoint
PNG/PDF
raw outputs
local_paths.local.json
Dataverse token
大结果目录
```

checkpoint 只记录：

```text
本机路径
adapter hash
文件大小
训练 run id
```

## 12. 给另一台 Codex 的建议指令

可以把下面这段发给另一台设备的 Codex：

```text
请在本机继续实验组 1 D 系列 final-v2 SFT 的并行任务，只跑 D1-50_FINAL_V2，不要跑 D1-500。

仓库：
https://github.com/reshihihihi/faa-chart-to-424-benchmark.git

请 checkout 我指定的 commit/branch：<填入最终 commit 或 branch>

先执行：
1. git status --short --branch
2. git pull
3. 确认以下文件存在：
   - docs/group1_d_final_v2_experiment_plan_zh_20260506.md
   - docs/group1_d_final_v2_two_machine_runbook_zh_20260506.md
   - scripts/score_final_v2_sft_outputs.py
   - benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/comparison_policy_v2.jsonl
   - reports/final_v2_field_legality_unknown_cleanup_zh_20260506.md

任务：
1. 读取 docs/group1_d_final_v2_experiment_plan_zh_20260506.md 和 docs/group1_d_final_v2_two_machine_runbook_zh_20260506.md。
2. 配置本机 local_paths.local.json，但不要提交。
3. 使用 Dataverse final-v2 artifact package 中 corrected SFT train500/dev100。
4. 使用已经冻结的 D1-50 subset JSONL，不能重新随机抽样。
5. 跑 D1-50_FINAL_V2 训练。
6. 训练后先跑 smoke5，再跑 formal200。
7. 使用 scripts/score_final_v2_sft_outputs.py 和 final-v2 comparison_policy_v2.jsonl 评分。
8. 推理阶段禁止读取 target JSON、score、raw 424/CIFP、其他方法预测。
9. 不要提交模型、checkpoint、PNG、raw outputs、local_paths.local.json、大结果。
10. 最后汇报 run_id、commit hash、prompt hash、train/dev JSONL hash、checkpoint path/hash、parse/schema failure、unknown 输出数量、aggregate_summary.json 路径和 score。
```

## 13. 合并结果时的检查清单

汇总 D-base、D1-50、D1-500 结果前，确认：

```text
三者 Git commit 一致
三者 dataset artifact hash 一致
三者 prompt hash 一致
三者 final-v2 policy hash 一致
三者 formal split 一致
三者 parser/canonicalization policy 一致
D1-50 subset manifest 与冻结记录一致
评分输出均来自 PR #39 final-v2 scorer
parse/schema/missing failure 没有从 denominator 中删除
```

只有这些条件满足，D-base、D1-50、D1-500 才能放在同一张 final-v2 D 系列表格中比较。
