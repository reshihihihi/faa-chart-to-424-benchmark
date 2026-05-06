# 实验组1 D 系列 final-v2：4090 执行方案

日期：2026-05-06

关联 PR：`#40 Group 1 D final-v2 D1-50 preparation and smoke diagnostic`

## 1. 现在要跑的三个方法

本轮只处理 D 系列 final-v2 三个方法：

| 方法 | 是否训练 | 训练样本 | 输入 | 输出 | 目的 |
| --- | --- | ---: | --- | --- | --- |
| `D_BASE_SAME_BACKBONE_FINAL_V2` | 否 | 0 | 完整航图 PNG + final-v2 D prompt | final-v2 canonical JSON | 同底座未微调对照 |
| `D1-50_FINAL_V2` | 是 | 50 | 完整航图 PNG + final-v2 D prompt | final-v2 canonical JSON | 小数据 SFT 对照 |
| `D1-500_FINAL_V2` | 是 | 500 | 完整航图 PNG + final-v2 D prompt | final-v2 canonical JSON | D 系列主 SFT 结果 |

三者必须共用同一个 final-v2 prompt、formal200 split、推理 parser policy、评分脚本和 comparison policy。允许不同的只有是否加载 LoRA checkpoint、训练 JSONL 和 run id。

## 2. 已经完成的状态

D1-50 final-v2 已在本机训练完成，但 smoke 没有通过：

```text
formal200 smoke5: parse_ok=1/5, final_v2_valid=1/5
train-seen5 diagnostic: parse_ok=2/5, final_v2_valid=2/5
```

结论是：`50 samples / 1 epoch / 7 optimizer steps` 没有让模型稳定学会输出 final-v2 JSON。这个结果应保留为 D1-50 r1 的 smoke 失败证据，不建议直接跑 formal200，也不建议通过补括号、去尾逗号、模板填充等方式把它改成可评分结果。

## 3. 4090 上的优先级

4090 空闲后，优先顺序应为：

1. 先跑 `D1-500_FINAL_V2` 训练。
2. D1-500 训练完成后，立刻跑 formal200 smoke5。
3. 如果 smoke5 是路径、依赖、脚本错误，先修工程问题后重跑完整 smoke5。
4. 如果 smoke5 能稳定产生可解析 final-v2 JSON，再跑 formal200。
5. 同一台 4090 在 D1-500 结束后跑 `D_BASE_SAME_BACKBONE_FINAL_V2` smoke5 和 formal200。
6. `D1-50_FINAL_V2` 不再直接 formal200；除非单独冻结一个新变体，例如 `D1-50_MORE_EPOCHS_FINAL_V2`，否则不改变已记录的 r1 结论。

这样安排的原因是：D1-500 是当前最重要、也最可能通过 smoke 的主结果；D-base 不训练，排在后面也不会影响训练窗口；D1-50 已有明确 smoke 失败证据，继续 formal200 只会消耗 GPU 并产生大量不可解析失败。

## 4. 4090 机器接手前必须拿到的内容

4090 机器需要从 PR #40 拉取代码：

```powershell
git fetch origin
git checkout codex/group1-d-final-v2-d1-50-20260506
git pull
git rev-parse --short HEAD
```

确认 commit 至少包含：

```text
a4a006496 Document D1-50 final-v2 smoke diagnostic
```

本地不要提交以下内容：

```text
local_paths.local.json
训练配置里的本机绝对路径
模型权重
LoRA checkpoint
PNG
raw outputs
prediction 大结果
score 大结果
```

## 5. D1-500 应该怎么跑

D1-500 使用和 D1-50 同一套构造脚本、prompt、训练脚本、推理脚本。区别只有训练 JSONL：

```text
D1-50:  d_sft_train500_dev100.final_v2.train50_seed260506.jsonl
D1-500: d_sft_train500_dev100.final_v2.train500.jsonl
dev:    d_sft_train500_dev100.final_v2.dev100.jsonl
```

4090 机器应新建自己的本地 config，例如：

```text
d1_500_final_v2_qwen2vl_lora_20260506_r1.local.json
```

关键字段：

```text
method_id = D1-500_FINAL_V2
train_jsonl = corrected final-v2 train500 JSONL
dev_jsonl = corrected final-v2 dev100 JSONL
prompt_path = training/d_sft/prompts/d_sft_image_to_canonical.final_v2.md
base_model_id = 本机 Qwen2-VL-2B-Instruct 路径或缓存名
epochs = 1
gradient_accumulation_steps = 8
learning_rate = 0.0002
assistant_prefill = "{"
parser_repair = false
```

训练命令模板：

```powershell
python scripts\d_sft_train_qwen2vl_lora.py `
  --config <本机路径>\d1_500_final_v2_qwen2vl_lora_20260506_r1.local.json `
  --output-root <本机输出根目录> `
  --run-id d1_500_final_v2_qwen2vl_lora_20260506_r1
```

## 6. D1-500 推理怎么跑

训练后先跑 smoke5，不能直接跑 formal200：

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

smoke5 通过后，再把 manifest 换成 formal200 image-only manifest：

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

## 7. D-base 怎么跑

D-base 不加载 LoRA checkpoint。PR #40 中的 final-v2 推理 runner 已支持 `--checkpoint` 为空，因此 D-base 可以和 D1-500 使用同一个 prompt、同一个 parser policy 和同一个 image-only manifest。

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

## 8. 评分

推理阶段禁止读取 target JSON、score、raw 424/CIFP、人类答案、其他方法预测或 comparison policy。只有预测全部完成后，才使用 scoring manifest 和 `comparison_policy_v2.jsonl` 评分。

评分命令模板：

```powershell
python scripts\score_final_v2_sft_outputs.py `
  --predictions-dir <本机输出根目录>\predictions\<run_id>\canonical_json `
  --scoring-manifest <formal200 scoring manifest> `
  --comparison-policy benchmark_exports\derived\v2\formal300\targets\scoring_equivalence_v2\comparison_policy_v2.jsonl `
  --output-dir <本机输出根目录>\scores\<run_id>
```

最终每个方法至少汇报：

```text
git commit hash
run id
prompt hash
train/dev JSONL hash，D-base 无训练则写 no training
checkpoint path/hash，D-base 写 no checkpoint
smoke5 summary_report.json
formal200 summary_report.json
score summary path
score
parse failure 数量
final-v2 validation failure 数量
是否输出 unknown
是否有代码改动
```

## 9. 给 4090 机器 Codex 的指令

```text
请在 4090 机器上继续实验组1 D 系列 final-v2 SFT。只使用 PR #40 分支 codex/group1-d-final-v2-d1-50-20260506。

优先跑 D1-500_FINAL_V2，不要重新抽样，不要改实验定义。D1-500 使用 corrected final-v2 train500/dev100，prompt 使用 training/d_sft/prompts/d_sft_image_to_canonical.final_v2.md，训练脚本使用 scripts/d_sft_train_qwen2vl_lora.py，推理脚本使用 scripts/d_sft/run_d_sft_final_v2_inference.py。

训练 D1-500 后先跑 formal200 smoke5。smoke5 如果只是路径/依赖/脚本问题，可以修工程问题并完整重跑 smoke5；如果是模型自然 parse/schema failure，记录失败，不要用 target 或 scorer 修输出。smoke5 通过后跑 formal200，再用 scripts/score_final_v2_sft_outputs.py 和 comparison_policy_v2.jsonl 评分。

D-base 使用同一个 final-v2 推理脚本，但不传 --checkpoint，只传 --method-id D_BASE_SAME_BACKBONE_FINAL_V2。D-base 也先 smoke5，再 formal200，再评分。

D1-50 r1 已在另一台机器训练完成但 smoke 未通过，formal200 不要继续跑。除非明确新增并冻结 D1-50_MORE_EPOCHS_FINAL_V2，否则不要改变 D1-50 r1 的训练 epoch 或 parser policy。

推理阶段禁止读取 target JSON、score、raw 424/CIFP、人类答案、其他方法预测或 comparison_policy。scoring_manifest 和 comparison_policy 只能在预测完成后用于评分。不要提交 local_paths.local.json、模型、checkpoint、PNG、raw outputs 或大结果。

最后汇报 commit hash、三个方法的运行状态、每个 run 的 summary_report.json 路径、score、parse/schema failure 数量、unknown 输出数量、checkpoint hash 和是否有代码改动。
```
