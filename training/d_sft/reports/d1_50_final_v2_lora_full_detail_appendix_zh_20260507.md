# D1-50_FINAL_V2 LoRA 全细节补充附录

日期：2026-05-07

对象只包括这次下午 50 样本 LoRA：

```text
method_id = D1-50_FINAL_V2
training_run_id = d1_50_final_v2_qwen2vl_lora_20260506_r1
formal_smoke5_run_id = d1_50_final_v2_smoke5_20260506_r1
train_seen5_diagnostic_run_id = d1_50_final_v2_train_seen5_diag_20260506_r1
```

本文补充 PR #44 中还可以展开得更细的内容。这里的“全部细节”指可提交到 Git 的完整复现实验记录、参数、hash、配置内容、环境快照和命令；不包括模型权重和 LoRA checkpoint 二进制本体。

## 1. 为什么没有提交 LoRA checkpoint binary

没有提交 `adapter_model.safetensors` 不是省略细节，而是 artifact 边界：

```text
adapter_model.safetensors 是训练得到的 LoRA 权重二进制文件。
它属于模型/checkpoint artifact，不属于代码、方案、manifest 或报告。
此前实验边界已经要求不要把模型、checkpoint、PNG、raw outputs、大结果提交到 Git。
```

这次提交到 Git 的是：

```text
checkpoint 的目录结构
checkpoint 每个文件名
checkpoint 每个文件大小
checkpoint 每个文件 SHA256
完整 adapter_config.json 内容
训练配置去本机路径版
训练参数
推理参数
环境版本
底座模型来源 URL 和 revision
训练/推理结果摘要
失败原因
复现命令
```

真正的二进制 artifact 应放在外部 artifact root、GitHub Release、Dataverse、对象存储或受控模型仓库，再用本 PR 中的 hash 校验。不能把 `adapter_model.safetensors` 直接混进代码 PR。

本次已经把 `checkpoint-final/` 打成 zip 并上传为 GitHub Release asset：

```text
release_page = https://github.com/reshihihihi/faa-chart-to-424-benchmark/releases/tag/d1-50-final-v2-lora-20260506-r1
download_url = https://github.com/reshihihihi/faa-chart-to-424-benchmark/releases/download/d1-50-final-v2-lora-20260506-r1/d1_50_final_v2_qwen2vl_lora_20260506_r1_checkpoint-final.zip
zip_file = d1_50_final_v2_qwen2vl_lora_20260506_r1_checkpoint-final.zip
zip_size_bytes = 36035954
zip_sha256 = 04502e74276a4d4a0df51a82842e2071fa4a1501f131da223077f6c0672d074a
```

因此，PR 中没有把 binary 写入 Git 历史，但已经提供了可直接下载、可用 SHA256 校验的 LoRA checkpoint artifact。

## 2. 底座模型完整来源

```text
model_id = Qwen/Qwen2-VL-2B-Instruct
huggingface_url = https://huggingface.co/Qwen/Qwen2-VL-2B-Instruct
official_code_url = https://github.com/QwenLM/Qwen2-VL
observed_huggingface_cache_revision = 895c3a49bc3fa70a340399125c650a463535e71c
local_files_only = true
download_source = local_huggingface_cache
```

运行时不是从 GitHub 代码仓库下载权重，而是由 Hugging Face 模型仓库提供权重；QwenLM GitHub 仓库是官方代码/说明来源。

底座模型关键文件：

```text
model-00001-of-00002.safetensors
  size_bytes = 3988609112
  sha256 = 994ac2b03f97de8bc647d0fe5eba2e4b632b3e28dc03574c29bdfc36cf47e1b9

model-00002-of-00002.safetensors
  size_bytes = 429441656
  sha256 = 92540d8353c8d226a589a3b179bdb33851c970ee2cc2ac7ba035f79425e7b833

model.safetensors.index.json
  size_bytes = 56411
  sha256 = 260ab9fa1418d6d6ab79daa1d9da2c47264f3b72edb4630fc799077ac67d27c6

config.json
  size_bytes = 1196
  sha256 = 422adefa19e62dd175961cec85bc0400344fe5bf9b22bd1182e05aaae78556e0

tokenizer.json
  size_bytes = 7029741
  sha256 = cb63a0a23eef3d5b01063a9880a1925a65aaf4d1591d519910ee3527852950a0
```

## 3. 完整去路径训练配置

下面是 `d1_50_final_v2_qwen2vl_lora_20260506_r1.local.json` 的去本机绝对路径版。字段值保留，只有本机路径替换成 `<external-artifact-root>`。

```json
{
  "status": "local_d1_50_final_v2_training_20260506_r1",
  "method_id": "D1-50_FINAL_V2",
  "created_at": "2026-04-28T00:00:00Z",
  "data": {
    "dataset_name": "d_sft_train500_dev100_final_v2_subset50_seed260506",
    "train_jsonl": "<external-artifact-root>/d_sft/final_v2_training_jsonl/d1_final_v2_20260506/d_sft_train500_dev100.final_v2.train50_seed260506.jsonl",
    "dev_jsonl": "<external-artifact-root>/d_sft/final_v2_training_jsonl/d1_final_v2_20260506/d_sft_train500_dev100.final_v2.dev100.jsonl",
    "combined_manifest": "<external-artifact-root>/d_sft/data/d_sft_train500_dev100/combined_manifest.jsonl",
    "prompt_path": "training/d_sft/prompts/d_sft_image_to_canonical.final_v2.md",
    "schema_path": "schemas/missed_approach_leg.schema.json",
    "label_source": "CIFP_projection_canonical_proxy_final_v2_field_legality_corrected_subset50_seed260506",
    "forbidden_sets": [
      "formal300_default_forbidden",
      "pilot10_external",
      "pilot100_external_heldout_feasibility"
    ]
  },
  "model": {
    "base_model_id": "Qwen/Qwen2-VL-2B-Instruct",
    "base_model_role": "local_trainable_vlm",
    "local_files_only": true,
    "download_source": "local_huggingface_cache",
    "load_in_4bit": true,
    "bnb_4bit_quant_type": "nf4",
    "bnb_4bit_use_double_quant": true,
    "device_map": "auto"
  },
  "lora": {
    "mode": "qlora_adapter",
    "r": 8,
    "lora_alpha": 16,
    "lora_dropout": 0.05,
    "target_modules": [
      "q_proj",
      "k_proj",
      "v_proj",
      "o_proj",
      "gate_proj",
      "up_proj",
      "down_proj"
    ]
  },
  "image": {
    "input_policy": "full_chart_image_only",
    "min_pixels": 3136,
    "max_pixels": 501760,
    "resize_policy": "Qwen2VLProcessor dynamic resize capped at max_pixels=501760; no OCR or crop input"
  },
  "output_control": {
    "assistant_prefill": "{",
    "policy": "training masks the prefilled opening brace and inference prepends the same brace before generation; final raw output must still be strict bare JSON",
    "parser_repair": false
  },
  "training": {
    "seed": 260428,
    "epochs": 1,
    "per_device_batch_size": 1,
    "gradient_accumulation_steps": 8,
    "learning_rate": 0.0002,
    "weight_decay": 0.0,
    "max_grad_norm": 1.0,
    "compute_dtype": "float16",
    "gradient_checkpointing": true,
    "max_seq_length": 4096,
    "checkpoint_save_policy": "save adapter and processor after each epoch plus final",
    "checkpoint_selection_policy": "lowest dev loss among epoch checkpoints; dev split only",
    "checkpoint_selection_dev_samples": 100
  },
  "inference": {
    "prompt_policy": "same prompt file as SFT training user message",
    "max_new_tokens": 1536,
    "decoding": "greedy_do_sample_false",
    "parser_policy": "strict_json_only_no_code_fence_no_semantic_repair",
    "rerun_policy": "no selective rerun; engineering failure may rerun complete failed run with new run_id"
  },
  "dry_run": {
    "train_samples": 16,
    "dev_samples": 4,
    "epochs": 3,
    "purpose": "engineering check only: image loading, JSON labels, checkpoint save, inference, parser, schema validation, scorer"
  },
  "freeze_manifest": {
    "status": "local_d1_50_final_v2_not_committed",
    "source": "generated by scripts/d_sft/build_d1_final_v2_training_jsonl.py from old D-SFT prompt_v2 JSONL using PR39 final-v2 field-legality rules",
    "subset_seed": 260506
  }
}
```

## 4. 完整 adapter_config.json

这是 `checkpoint-final/adapter_config.json` 的完整内容。它是文本配置，已经可提交；权重本体 `adapter_model.safetensors` 不提交。

```json
{
  "alora_invocation_tokens": null,
  "alpha_pattern": {},
  "arrow_config": null,
  "auto_mapping": null,
  "base_model_name_or_path": "Qwen/Qwen2-VL-2B-Instruct",
  "bias": "none",
  "corda_config": null,
  "ensure_weight_tying": false,
  "eva_config": null,
  "exclude_modules": null,
  "fan_in_fan_out": false,
  "inference_mode": true,
  "init_lora_weights": true,
  "layer_replication": null,
  "layers_pattern": null,
  "layers_to_transform": null,
  "loftq_config": {},
  "lora_alpha": 16,
  "lora_bias": false,
  "lora_dropout": 0.05,
  "lora_ga_config": null,
  "megatron_config": null,
  "megatron_core": "megatron.core",
  "modules_to_save": null,
  "peft_type": "LORA",
  "peft_version": "0.19.1",
  "qalora_group_size": 16,
  "r": 8,
  "rank_pattern": {},
  "revision": null,
  "target_modules": [
    "q_proj",
    "up_proj",
    "o_proj",
    "gate_proj",
    "v_proj",
    "k_proj",
    "down_proj"
  ],
  "target_parameters": null,
  "task_type": "CAUSAL_LM",
  "trainable_token_indices": null,
  "use_bdlora": null,
  "use_dora": false,
  "use_qalora": false,
  "use_rslora": false
}
```

## 5. checkpoint-final 文件清单

checkpoint-final zip 下载：

```text
https://github.com/reshihihihi/faa-chart-to-424-benchmark/releases/download/d1-50-final-v2-lora-20260506-r1/d1_50_final_v2_qwen2vl_lora_20260506_r1_checkpoint-final.zip
```

```text
adapter_config.json
  size_bytes = 1150
  sha256 = cfac22dc2e571284b9347d1f1402bc5c3eacbbbb4272913843911df4c4be7f05

adapter_model.safetensors
  size_bytes = 36986952
  sha256 = 439d0962ea650071bef1a6bd74d2a6852e60156155ec36eb3c395549fcaf3a96
  git_status = not_committed_binary_checkpoint

chat_template.jinja
  size_bytes = 1023
  sha256 = 6edff8eae4ef69923f937be5b1fcf91462227e7c827a0a936a98197f19642388

processor_config.json
  size_bytes = 1534
  sha256 = c2debefbf9071c2389a08126e86b1bb18f666a24c09a0967c8a8779911d8b9a6

README.md
  size_bytes = 5204
  sha256 = f84870e9c330a9a17f01ec27d85bd995fcc22addb5e7f1dd55259f3d1cda6adc

tokenizer.json
  size_bytes = 11420534
  sha256 = 312c03cb421e18f41c20c3e35f3302479a3a8f8b1f06779fd900326a0d32c22f

tokenizer_config.json
  size_bytes = 810
  sha256 = b7e922bac4f0585865ed00ad398b25ad14cddf1bef8bb0c7ab2aeaf421e75736
```

## 6. 训练报告完整关键字段

```text
created_at = 2026-05-06T06:34:59.322182+00:00
created_at_asia_shanghai = 2026-05-06 14:34:59
run_kind = formal_train
method_id_in_training_report = D_SFT
method_id_in_config = D1-50_FINAL_V2
config_sha256 = 890bdf1b5e32d26a6e94c90ab4a25039691b8556180fe98d74321de77cf85a92
train_jsonl_sha256 = fd9106f5850dd91aaeedd142e4b7e8ddd90df17cc771fb5597186838e55cfd62
dev_jsonl_sha256 = 2c457bb90d53fa783b619eb76ca035f9c8bdd8f1b6a4720ac4df2dffd78a8ef0
train_samples = 50
dev_samples = 100
epochs = 1
global_steps = 50
optimizer_steps = 7
truncated_train_samples = 0
max_train_seq_length_seen = 2041
best_dev_loss = 0.19552553363144398
best_checkpoint = checkpoint-epoch01
final_checkpoint = checkpoint-final
```

训练 forward input：

```text
full_chart_image
frozen_d_sft_prompt
```

assistant label source：

```text
CIFP_to_canonical_proxy_label_train_dev_only
```

forbidden training sources：

```text
formal300
pilot10
pilot100_external
OCR_text
field_candidates
scorer_output
other_method_predictions
```

## 7. 推理报告完整关键字段

formal200 smoke5：

```text
created_at = 2026-05-06T06:45:45.867897+00:00
run_id = d1_50_final_v2_smoke5_20260506_r1
method_id = D1-50_FINAL_V2
sample_role = formal200_evaluation_smoke5_image_only
checkpoint_adapter_sha256 = 439d0962ea650071bef1a6bd74d2a6852e60156155ec36eb3c395549fcaf3a96
samples_total = 5
parse_ok = 1
final_v2_valid = 1
parse_or_final_v2_failures = 4
target_used = false
```

formal200 smoke5 failures：

```text
KABE_I06: JSONDecodeError('No complete JSON object found: line 1 column 1 (char 0)')
KAMA_I04: JSONDecodeError('No complete JSON object found: line 1 column 1 (char 0)')
KAPC_I01L: JSONDecodeError('Illegal trailing comma before end of object: line 1 column 616 (char 615)')
KATL_I09R: JSONDecodeError('No complete JSON object found: line 1 column 1 (char 0)')
```

train-seen5 diagnostic：

```text
created_at = 2026-05-06T06:53:44.485410+00:00
run_id = d1_50_final_v2_train_seen5_diag_20260506_r1
method_id = D1-50_FINAL_V2
sample_role = train_seen5_diagnostic_image_only
checkpoint_adapter_sha256 = 439d0962ea650071bef1a6bd74d2a6852e60156155ec36eb3c395549fcaf3a96
samples_total = 5
parse_ok = 2
final_v2_valid = 2
parse_or_final_v2_failures = 3
target_used = false
```

train-seen5 failures：

```text
KATL_R09R: JSONDecodeError('No complete JSON object found: line 1 column 1 (char 0)')
KEMV_L34: JSONDecodeError('Illegal trailing comma before end of object: line 1 column 587 (char 586)')
KCPP_L25: JSONDecodeError('No complete JSON object found: line 1 column 1 (char 0)')
```

## 8. 推理边界

推理输入：

```text
full_chart_image
final_v2_d_prompt
```

推理禁止读取：

```text
target_JSON
score_file
raw_CIFP
human_answer
other_method_prediction
comparison_policy
```

parser / generation：

```text
extract_first_complete_json_object = true
semantic_repair_allowed = false
assistant_prefill = {
max_new_tokens = 1536
decoding = greedy_do_sample_false
```

## 9. 环境细节

训练报告记录的环境：

```text
python = 3.13.11
torch = 2.6.0+cu124
transformers = 5.3.0
peft = 0.19.1
bitsandbytes = 0.49.2
Pillow = 12.1.0
jsonschema = 4.26.0
cuda_available = true
gpu = NVIDIA GeForce RTX 4060 Laptop GPU
max_memory_allocated_gb = 7.4217
```

2026-05-07 在同机补采的 GPU/driver 状态：

```text
NVIDIA-SMI = 566.24
Driver Version = 566.24
CUDA Version shown by nvidia-smi = 12.7
GPU = NVIDIA GeForce RTX 4060 Laptop GPU
GPU memory = 8188 MiB
```

关键 pip package snapshot：

```text
accelerate==1.13.0
bitsandbytes==0.49.2
huggingface_hub==1.7.1
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
numpy==2.3.5
peft==0.19.1
pillow==12.1.0
qwen-vl-utils==0.0.14
safetensors==0.7.0
tokenizers==0.22.2
torch==2.6.0+cu124
torchvision==0.21.0+cu124
transformers==5.3.0
```

## 10. 训练命令

构造 final-v2 数据：

```powershell
python scripts\d_sft\build_d1_final_v2_training_jsonl.py `
  --train-jsonl <external-artifact-root>\d_sft\training_jsonl\d_sft_train500_dev100.prompt_v2.train.jsonl `
  --dev-jsonl <external-artifact-root>\d_sft\training_jsonl\d_sft_train500_dev100.prompt_v2.dev.jsonl `
  --prompt training\d_sft\prompts\d_sft_image_to_canonical.final_v2.md `
  --output-dir <external-artifact-root>\d_sft\final_v2_training_jsonl\d1_final_v2_20260506 `
  --subset-size 50 `
  --subset-seed 260506
```

训练 LoRA：

```powershell
python scripts\d_sft_train_qwen2vl_lora.py `
  --config <external-artifact-root>\d_sft\configs\d1_50_final_v2_qwen2vl_lora_20260506_r1.local.json `
  --output-root <external-artifact-root>\d_sft `
  --run-id d1_50_final_v2_qwen2vl_lora_20260506_r1
```

formal smoke5 推理：

```powershell
python scripts\d_sft\run_d_sft_final_v2_inference.py `
  --config <external-artifact-root>\d_sft\configs\d1_50_final_v2_qwen2vl_lora_20260506_r1.local.json `
  --checkpoint <external-artifact-root>\d_sft\checkpoints\d1_50_final_v2_qwen2vl_lora_20260506_r1\checkpoint-final `
  --method-id D1-50_FINAL_V2 `
  --manifest <external-artifact-root>\d_sft\final_v2_formal_manifests\formal200_evaluation_image_only_smoke5_manifest.jsonl `
  --output-root <external-artifact-root>\d_sft `
  --run-id d1_50_final_v2_smoke5_20260506_r1 `
  --sample-role formal200_evaluation_smoke5_image_only
```

train-seen5 诊断推理：

```powershell
python scripts\d_sft\run_d_sft_final_v2_inference.py `
  --config <external-artifact-root>\d_sft\configs\d1_50_final_v2_qwen2vl_lora_20260506_r1.local.json `
  --checkpoint <external-artifact-root>\d_sft\checkpoints\d1_50_final_v2_qwen2vl_lora_20260506_r1\checkpoint-final `
  --method-id D1-50_FINAL_V2 `
  --manifest <external-artifact-root>\d_sft\final_v2_formal_manifests\d1_50_train_seen5_diagnostic_manifest.jsonl `
  --output-root <external-artifact-root>\d_sft `
  --run-id d1_50_final_v2_train_seen5_diag_20260506_r1 `
  --sample-role train_seen5_diagnostic_image_only
```

## 11. 结论

```text
D1-50_FINAL_V2 的 50 样本 LoRA 已训练完成。
训练数据、prompt、脚本、环境、checkpoint hash、推理参数和 smoke 诊断已经记录。
formal smoke5 = 1/5 parse-valid。
train-seen5 diagnostic = 2/5 parse-valid。
因此该 checkpoint 没有被提升为 formal200 正式结果。
```

如果要在另一台机器拿到完全相同模型，必须从外部 artifact root 拿到 `checkpoint-final` 整目录，尤其是 `adapter_model.safetensors`，并用本附录的 SHA256 校验。
