# D1 / D-SFT LoRA 环境与缺口记录 20260506

本文把 D1 / D-SFT LoRA 已恢复的环境信息和仍缺失的信息单独列出，避免把“已经查到的事实”和“无法从现有记录恢复的内容”混在一起。

## 1. 训练报告中已记录的环境

```text
python = 3.11.15 Anaconda
torch = 2.6.0+cu124
transformers = 5.5.4
peft = 0.19.1
bitsandbytes = 0.49.2
Pillow = 11.1.0
jsonschema = 4.26.0
gpu = NVIDIA GeForce RTX 4060 Laptop GPU
peak_memory = 7.1405 GB
```

这些信息来自 D-SFT 训练报告或训练产物记录，是目前最接近原始训练环境的记录。

## 2. 当前机器后补观察到的环境

```text
NVIDIA-SMI = 566.24
driver = 566.24
CUDA shown by nvidia-smi = 12.7
GPU total memory = 8188 MiB
python = 3.13.11
transformers = 5.3.0
```

这部分不是原始 D1 训练环境，只是 2026-05-06 在当前机器上后补调查时的环境观察，不能等同于训练当时环境。

## 3. 训练设置中已恢复的关键软件路径逻辑

```text
base_model_source = Hugging Face local cache
base_model_id = Qwen/Qwen2-VL-2B-Instruct
base_model_revision_observed = 895c3a49bc3fa70a340399125c650a463535e71c
local_files_only = true
load_in_4bit = true
bnb_4bit_quant_type = nf4
bnb_4bit_use_double_quant = true
device_map = auto
compute_dtype = float16
peft_load = PeftModel.from_pretrained(checkpoint-final)
```

## 4. 已恢复的训练产物事实

```text
run_id = d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1
dataset = d_sft_train500_dev100
train_samples = 500
dev_samples = 100
global_steps = 500
optimizer_steps = 63
best_dev_loss = 0.04459553452208638
observed_truncation_count = 0
observed_max_seq_len = 1931
adapter_model_size = 36,986,952 bytes
adapter_model_sha256 = df5e5eb5e97ffb5b86368fb966705cddffe09e4dfaa622959859d2da9fc412e0
```

## 5. 仍缺失但不能伪造的原始记录

```text
训练当时完整 conda env export
训练当时完整 pip freeze
训练实际 shell history
推理实际 shell history
训练 wall-clock 起止时间
formal200 raw inference 的原始本机运行命令全文
```

这些信息如果后续从日志、终端历史、环境导出文件或 run manifest 中找到，应作为补充 commit 提交；在找到前不能凭记忆或推测补成“事实”。

## 6. 为什么不提交二进制权重和本机路径

```text
完整底座模型权重大约 4.4 GB
LoRA adapter 是二进制 checkpoint artifact
PNG 和 raw outputs 属于大数据/运行产物
本机绝对路径会暴露机器结构，并且不能在另一台机器直接复用
```

因此 Git 中提交的是 hash、大小、目录模板、来源 URL、run_id、参数和命令形态。真正的大文件放在外部 artifact root，复现时按 manifest 校验一致性。
