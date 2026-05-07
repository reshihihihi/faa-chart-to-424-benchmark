# 实验组1 D 系列 final-v2：4090 从零执行方案

日期：2026-05-06

关联 PR：`#40 Group 1 D final-v2 execution plan`

## 1. 正式口径

正式记录中，`D_BASE_SAME_BACKBONE_FINAL_V2`、`D1-50_FINAL_V2`、`D1-500_FINAL_V2` 都按“尚未正式运行”处理。后续在 4090 机器上从统一数据、统一 prompt、统一推理脚本和统一评分口径重新开始。

本文件不引用任何本机临时训练、临时 smoke 或非正式诊断结果。4090 上产生的新 run id、summary、score 才作为本轮 D 系列 final-v2 的正式运行记录。

## 2. 三个方法分别是什么

| 方法 | 是否训练 | 训练样本 | 输入 | 输出 | 目的 |
| --- | --- | ---: | --- | --- | --- |
| `D_BASE_SAME_BACKBONE_FINAL_V2` | 否 | 0 | 完整航图 PNG + final-v2 D prompt | final-v2 canonical JSON | 同底座未微调对照 |
| `D1-50_FINAL_V2` | 是 | 50 | 完整航图 PNG + final-v2 D prompt | final-v2 canonical JSON | 小数据 SFT 对照 |
| `D1-500_FINAL_V2` | 是 | 500 | 完整航图 PNG + final-v2 D prompt | final-v2 canonical JSON | D 系列主 SFT 结果 |

三者必须共用：

```text
base model
final-v2 D prompt
formal200 image-only manifest
formal200 smoke5 image-only manifest
parser policy
comparison_policy_v2
scoring script
```

允许不同：

```text
D-base: 不加载 LoRA checkpoint，不训练
D1-50: 使用固定 seed 的 train50 JSONL
D1-500: 使用 train500 JSONL
run id / checkpoint / output directory
```

## 3. 推荐执行顺序

如果只有一张空闲 4090，推荐顺序如下：

1. 拉取 PR #40 最新分支。
2. 准备并审计 final-v2 train500、train50、dev100、formal200 image-only manifest、formal200 smoke5 manifest。
3. 先跑 `D_BASE_SAME_BACKBONE_FINAL_V2` smoke5，确认图片路径、prompt、模型加载、推理 runner 都能工作。
4. 跑 `D1-50_FINAL_V2` 训练，然后 smoke5。
5. 跑 `D1-500_FINAL_V2` 训练，然后 smoke5。
6. 三个方法的工程 blocker 清零后，分别跑 formal200。
7. 所有预测完成后再统一评分。
8. 汇总 D-base、D1-50、D1-500 的 score、parse failure、schema failure、unknown 输出数量和 run manifest。

smoke5 的作用是工程闸门：检查路径、依赖、显存、prompt、parser、输出目录和 run id 是否正确。不能在推理阶段读取 target、score、raw 424/CIFP、其他方法预测或 comparison policy。

如果 smoke5 出现路径、依赖、脚本、配置错误，应修工程问题并完整重跑 smoke5。如果是模型自然输出导致 parse/schema failure，记录在 summary 中，不要用 target 或 scorer 修输出，也不要删除失败样本。

## 4. 拉取代码

4090 机器执行：

```powershell
git fetch origin
git checkout codex/group1-d-final-v2-d1-50-20260506
git pull
git rev-parse --short HEAD
```

确认 commit 至少包含：

```text
74e98b070 Add 4090 execution plan for group1 D final-v2
```

## 5. 本地文件边界

不要提交：

```text
local_paths.local.json
本机绝对路径配置
模型权重
LoRA checkpoint
PNG
raw outputs
prediction 大结果
score 大结果
```

可以提交：

```text
脚本
prompt
schema/policy 小文件
中文方案文档
不含本机路径和大结果的摘要报告
```

## 6. 统一数据准备

只构造一次 final-v2 SFT 数据，然后三种方法共用。

目标文件：

```text
d_sft_train500_dev100.final_v2.train500.jsonl
d_sft_train500_dev100.final_v2.train50_seed260506.jsonl
d_sft_train500_dev100.final_v2.dev100.jsonl
d1_final_v2_train500_dev100_and_subset_manifest.json
formal200_evaluation_image_only_manifest.jsonl
formal200_evaluation_image_only_smoke5_manifest.jsonl
```

训练标签规则：

```text
输入 = 完整航图 PNG + final-v2 D prompt
输出 = final-v2 canonical JSON
unknown = 不允许作为正式 status
DF direct-to-fix = 用 Q_terminator=DF + Q1_fix_ident 表达
DF 的 Q4_course_or_radial direct = 改为 not_applicable/null
CF/DF 未限制左右转 = Q3_turn present BOTH
```

D1-50 必须从 D1-500 train500 中固定 seed 抽 50 条，不能单独随机抽样，也不能使用 formal300 的第一个 50。

## 7. D-base 命令模板

D-base 不训练，不传 `--checkpoint`。

smoke5：

```powershell
python scripts\d_sft\run_d_sft_final_v2_inference.py `
  --config <本机路径>\d_base_same_backbone_final_v2_20260506_r1.local.json `
  --method-id D_BASE_SAME_BACKBONE_FINAL_V2 `
  --manifest <本机路径>\formal200_evaluation_image_only_smoke5_manifest.jsonl `
  --output-root <本机输出根目录> `
  --run-id d_base_same_backbone_final_v2_smoke5_20260506_r1 `
  --sample-role formal200_evaluation_smoke5_image_only
```

formal200：

```powershell
python scripts\d_sft\run_d_sft_final_v2_inference.py `
  --config <本机路径>\d_base_same_backbone_final_v2_20260506_r1.local.json `
  --method-id D_BASE_SAME_BACKBONE_FINAL_V2 `
  --manifest <本机路径>\formal200_evaluation_image_only_manifest.jsonl `
  --output-root <本机输出根目录> `
  --run-id d_base_same_backbone_final_v2_formal200_20260506_r1 `
  --sample-role formal200_evaluation_image_only
```

## 8. D1-50 命令模板

D1-50 使用 train50，dev100 与 D1-500 相同。

训练：

```powershell
python scripts\d_sft_train_qwen2vl_lora.py `
  --config <本机路径>\d1_50_final_v2_qwen2vl_lora_20260506_r1.local.json `
  --output-root <本机输出根目录> `
  --run-id d1_50_final_v2_qwen2vl_lora_20260506_r1
```

smoke5：

```powershell
python scripts\d_sft\run_d_sft_final_v2_inference.py `
  --config <本机路径>\d1_50_final_v2_qwen2vl_lora_20260506_r1.local.json `
  --checkpoint <本机输出根目录>\checkpoints\d1_50_final_v2_qwen2vl_lora_20260506_r1\checkpoint-final `
  --method-id D1-50_FINAL_V2 `
  --manifest <本机路径>\formal200_evaluation_image_only_smoke5_manifest.jsonl `
  --output-root <本机输出根目录> `
  --run-id d1_50_final_v2_smoke5_20260506_r1 `
  --sample-role formal200_evaluation_smoke5_image_only
```

formal200：

```powershell
python scripts\d_sft\run_d_sft_final_v2_inference.py `
  --config <本机路径>\d1_50_final_v2_qwen2vl_lora_20260506_r1.local.json `
  --checkpoint <本机输出根目录>\checkpoints\d1_50_final_v2_qwen2vl_lora_20260506_r1\checkpoint-final `
  --method-id D1-50_FINAL_V2 `
  --manifest <本机路径>\formal200_evaluation_image_only_manifest.jsonl `
  --output-root <本机输出根目录> `
  --run-id d1_50_final_v2_formal200_20260506_r1 `
  --sample-role formal200_evaluation_image_only
```

## 9. D1-500 命令模板

D1-500 使用 train500，dev100 与 D1-50 相同。

训练：

```powershell
python scripts\d_sft_train_qwen2vl_lora.py `
  --config <本机路径>\d1_500_final_v2_qwen2vl_lora_20260506_r1.local.json `
  --output-root <本机输出根目录> `
  --run-id d1_500_final_v2_qwen2vl_lora_20260506_r1
```

smoke5：

```powershell
python scripts\d_sft\run_d_sft_final_v2_inference.py `
  --config <本机路径>\d1_500_final_v2_qwen2vl_lora_20260506_r1.local.json `
  --checkpoint <本机输出根目录>\checkpoints\d1_500_final_v2_qwen2vl_lora_20260506_r1\checkpoint-final `
  --method-id D1-500_FINAL_V2 `
  --manifest <本机路径>\formal200_evaluation_image_only_smoke5_manifest.jsonl `
  --output-root <本机输出根目录> `
  --run-id d1_500_final_v2_smoke5_20260506_r1 `
  --sample-role formal200_evaluation_smoke5_image_only
```

formal200：

```powershell
python scripts\d_sft\run_d_sft_final_v2_inference.py `
  --config <本机路径>\d1_500_final_v2_qwen2vl_lora_20260506_r1.local.json `
  --checkpoint <本机输出根目录>\checkpoints\d1_500_final_v2_qwen2vl_lora_20260506_r1\checkpoint-final `
  --method-id D1-500_FINAL_V2 `
  --manifest <本机路径>\formal200_evaluation_image_only_manifest.jsonl `
  --output-root <本机输出根目录> `
  --run-id d1_500_final_v2_formal200_20260506_r1 `
  --sample-role formal200_evaluation_image_only
```

## 10. 评分

推理阶段禁止读取 scoring manifest 和 comparison policy。只有预测全部完成后，才使用它们评分。

评分命令模板：

```powershell
python scripts\score_final_v2_sft_outputs.py `
  --predictions-dir <本机输出根目录>\predictions\<run_id>\canonical_json `
  --scoring-manifest <formal200 scoring manifest> `
  --comparison-policy benchmark_exports\derived\v2\formal300\targets\scoring_equivalence_v2\comparison_policy_v2.jsonl `
  --output-dir <本机输出根目录>\scores\<run_id>
```

每个方法最终汇报：

```text
git commit hash
run id
prompt hash
train/dev JSONL hash，D-base 写 no training
checkpoint path/hash，D-base 写 no checkpoint
smoke5 summary_report.json
formal200 summary_report.json
score summary path
score
parse failure 数量
final-v2 validation failure 数量
unknown 输出数量
是否有代码改动
```

## 11. 给 4090 机器 Codex 的指令

```text
请在 4090 机器上从零执行实验组1 D 系列 final-v2 三个方法：D_BASE_SAME_BACKBONE_FINAL_V2、D1-50_FINAL_V2、D1-500_FINAL_V2。

仓库：
https://github.com/reshihihihi/faa-chart-to-424-benchmark

分支：
codex/group1-d-final-v2-d1-50-20260506

先执行：
git fetch origin
git checkout codex/group1-d-final-v2-d1-50-20260506
git pull
git rev-parse --short HEAD

正式口径中三个方法都按尚未运行处理。请不要引用任何其他机器上的临时 smoke、临时 checkpoint 或非正式诊断结果。

先准备 final-v2 train500、train50、dev100、formal200 image-only manifest、formal200 smoke5 manifest。D1-50 必须是 train500 的固定 seed 子集，不能重新随机抽样，不能用 formal300 的第一个 50。

三个方法必须使用同一个 final-v2 D prompt、同一个 formal200 split、同一个 parser policy、同一个 scoring script 和同一个 comparison_policy_v2。

D-base 不训练，不传 --checkpoint。
D1-50 用 train50 训练。
D1-500 用 train500 训练。

每个方法都先跑 smoke5，再跑 formal200。smoke5 如果发现路径、依赖、脚本或配置错误，可以修工程问题并完整重跑 smoke5；如果是模型自然 parse/schema failure，记录失败，不要读取 target 或 scorer 修输出，不要删除失败样本。

推理阶段禁止读取 target JSON、score、raw 424/CIFP、人类答案、其他方法预测、scoring_manifest 或 comparison_policy。scoring_manifest 和 comparison_policy 只能在预测完成后用于评分。

不要提交 local_paths.local.json、模型、checkpoint、PNG、raw outputs、prediction 大结果或 score 大结果。

最后汇报 commit hash、三个方法的 run id、summary_report.json 路径、score、parse/schema failure 数量、unknown 输出数量、checkpoint hash 和是否有代码改动。
```
