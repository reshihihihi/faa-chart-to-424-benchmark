# D1 / D-SFT LoRA 复现命令记录 20260506

本文只记录命令形态和执行边界，不记录本机绝对路径。实际运行前，先把 `training/d_sft/configs/d1_lora_artifact_paths.template.json` 复制成本机不提交的 local 配置，并把 `<external-artifact-root>`、`<huggingface-cache>` 等占位符替换成真实路径。

## 1. 复现前必须准备的外部 artifact

```text
1. 底座模型 Qwen/Qwen2-VL-2B-Instruct
2. Hugging Face cache revision 895c3a49bc3fa70a340399125c650a463535e71c
3. D-SFT LoRA checkpoint-final 整个目录
4. d_sft_train500_dev100 训练 JSONL、dev JSONL、combined manifest
5. 对应 FAA 航图 PNG
6. pilot100 或 formal manifest
7. 预测完成后才使用的 scoring manifest / target
```

需要用 `training/d_sft/manifests/d1_lora_artifact_manifest_20260506.json` 核对文件大小和 SHA256。

## 2. 训练命令形态

```powershell
python scripts\d_sft_train_qwen2vl_lora.py `
  --config training\d_sft\configs\d_sft_training_config.candidate.json `
  --output-root <external-artifact-root>\d_sft `
  --run-id d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1
```

关键训练设置：

```text
base_model = Qwen/Qwen2-VL-2B-Instruct
train_samples = 500
dev_samples = 100
epochs = 1
per_device_train_batch_size = 1
gradient_accumulation_steps = 8
learning_rate = 0.0002
weight_decay = 0.0
max_grad_norm = 1.0
max_seq_len = 4096
gradient_checkpointing = true
assistant_prefill = {
checkpoint_selection = lowest dev loss
```

训练输入边界：

```text
允许：完整航图 PNG、D-SFT prompt v2、训练 split label、dev split label
禁止：formal300、pilot10、pilot100 external、OCR、field candidates、scorer output、其他方法预测
```

## 3. pilot100 推理命令形态

```powershell
python scripts\d_sft_infer_qwen2vl_lora.py `
  --config training\d_sft\configs\d_sft_training_config.frozen_20260428_r1.json `
  --checkpoint <external-artifact-root>\d_sft\checkpoints\d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1\checkpoint-final `
  --manifest <external-artifact-root>\pilot100_external\pilot100_external_manifest.jsonl `
  --schema schemas\missed_approach_leg.schema.json `
  --output-root <external-artifact-root>\d_sft `
  --run-id d_sft_pilot100_promptv2_prefill_20260428_r1
```

关键推理设置：

```text
full_chart_image_only = true
min_pixels = 3136
max_pixels = 501760
max_new_tokens = 1536
do_sample = false
parser_policy = strict JSON only
semantic_repair = false
selective_retry = false
```

推理阶段禁止读取：

```text
target JSON
score
raw 424/CIFP
OCR
field candidates
evidence boxes
other method predictions
```

## 4. formal200 D1 推理和评分边界

formal200 D1 的已记录 run：

```text
run_id = group1_formal200_D1_20260502_r4
canonical_json_written = 200 / 200
schema_valid = 200
scored = 200
failures = 0
```

评分只允许在预测完成之后进行。scoring manifest、target JSON、comparison policy 都不能进入预测 runner。

正式结果：

```text
strict field-level score = 2972 / 4052 = 73.35%
v2 field-level score = 3158 / 4052 = 77.93682132280355%
```

## 5. 另一台机器复现顺序

```text
1. checkout 仓库和对应 commit
2. 下载或复制 Qwen/Qwen2-VL-2B-Instruct 到 Hugging Face cache
3. 复制 checkpoint-final 整个目录到外部 artifact root
4. 复制训练 JSONL、dev JSONL、combined manifest、图像 manifest、PNG 到外部 artifact root
5. 用 d1_lora_artifact_manifest_20260506.json 核对 SHA256
6. 填写本机 local paths 文件，但不要提交
7. 运行推理
8. 推理完成后再运行评分
9. 保存 raw outputs、parser logs、summary report 到外部 artifact root，不提交大结果
```

## 6. 当前无法精确复原的命令

以下内容没有在现有冻结记录中完整保留，不能凭空补：

```text
训练当时完整 shell history
formal200 raw inference 的原始本机命令全文
训练 wall-clock 起止时间
训练当时完整 conda env export
训练当时完整 pip freeze
```

如果后续找到这些原始记录，应追加到本报告或新增 provenance 文件。
