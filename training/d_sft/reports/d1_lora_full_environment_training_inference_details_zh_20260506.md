# D1 / D-SFT LoRA 全量细节整理 20260506

本文整理实验组 1 最初 D1 所使用的 D-SFT LoRA 实验。目标是把 LoRA 运行环境、底座模型来源、训练数据、训练参数、推理参数、checkpoint 文件、hash、正式结果和复现边界全部集中记录。

本文是 Git 可提交版本，不包含本机绝对路径，不提交模型权重、LoRA checkpoint、PNG、raw outputs 或大结果。真实权重和本机大文件应保存在外部 artifact root。

## 0. 本次提交范围

本次提交的目标是把 D1 / D-SFT LoRA 相关的可复现实验细节全部放入 Git，包括：

```text
底座模型公开来源
底座模型 cache revision
底座模型关键文件大小和 SHA256
LoRA checkpoint 目录结构
LoRA adapter 文件大小和 SHA256
adapter_config.json 中的 LoRA / PEFT 参数
训练集、开发集、manifest、prompt、schema、脚本及其 hash
训练输入和禁止输入
训练超参数
4bit QLoRA / bitsandbytes / PEFT 加载方式
训练环境
推理环境
推理 generation 参数
pilot100 feasibility 结果
formal200 D1 正式结果
复现命令形态
仍无法从现有记录恢复的缺口
```

不进入 Git 的内容不是“省略实验细节”，而是不能进入公开代码仓库的 artifact：

```text
本机绝对路径
完整模型权重
LoRA checkpoint 二进制权重
PNG 图像
raw outputs
大结果目录
可能暴露机器结构或权限信息的 shell history
```

这些内容用文件清单、SHA256、大小、run_id、公开来源、目录模板和复现命令替代记录。这样另一台机器可以按 hash 和目录模板核对 artifact 是否一致，同时不会把大文件、私有路径或隐藏环境假设提交进仓库。

本次 PR 中与 D1 / D-SFT LoRA 复现直接相关的提交文件包括：

```text
training/d_sft/reports/d1_lora_full_environment_training_inference_details_zh_20260506.md
training/d_sft/manifests/d1_lora_artifact_manifest_20260506.json
training/d_sft/configs/d1_lora_artifact_paths.template.json
training/d_sft/reports/d1_lora_reproduction_commands_zh_20260506.md
training/d_sft/reports/d1_lora_environment_and_gap_record_zh_20260506.md
```

其中 Markdown 报告用于人工阅读，JSON manifest 用于逐项核对 artifact、hash、参数和结果，template 用于另一台机器填写本机路径，复现命令文档用于照着跑，环境缺口文档用于区分已恢复事实和仍无法从现有记录恢复的内容。

## 1. D1 和 LoRA 的关系

```text
公开底座模型 Qwen/Qwen2-VL-2B-Instruct
  + D-SFT LoRA adapter
  + D-SFT prompt v2
  = 实验组 1 最初的 D1 / D-SFT 模型
```

D1 不是从零训练完整大模型。D1 是在公开视觉语言模型 `Qwen/Qwen2-VL-2B-Instruct` 上，用 500 条 D-SFT 训练样本训练出的 LoRA adapter。推理时必须同时加载底座模型和 LoRA adapter。

## 2. 底座模型来源

底座模型：

```text
Qwen/Qwen2-VL-2B-Instruct
```

公开源地址：

```text
https://huggingface.co/Qwen/Qwen2-VL-2B-Instruct
```

官方代码仓库：

```text
https://github.com/QwenLM/Qwen2-VL
```

本机调查时确认的 Hugging Face cache revision：

```text
895c3a49bc3fa70a340399125c650a463535e71c
```

Git 中不写本机 cache 绝对路径。复现时可按以下逻辑定位：

```text
<huggingface-cache>/hub/models--Qwen--Qwen2-VL-2B-Instruct
<huggingface-cache>/hub/models--Qwen--Qwen2-VL-2B-Instruct/refs/main
<huggingface-cache>/hub/models--Qwen--Qwen2-VL-2B-Instruct/snapshots/895c3a49bc3fa70a340399125c650a463535e71c
```

底座模型主要文件和大小：

```text
model-00001-of-00002.safetensors       3,988,609,112 bytes
model-00002-of-00002.safetensors         429,441,656 bytes
model.safetensors.index.json                  56,411 bytes
config.json                                  1,196 bytes
generation_config.json                         272 bytes
preprocessor_config.json                       347 bytes
tokenizer.json                            7,029,741 bytes
tokenizer_config.json                        4,190 bytes
vocab.json                               2,776,833 bytes
merges.txt                               1,671,839 bytes
LICENSE                                    11,343 bytes
README.md                                  17,392 bytes
```

底座模型关键文件 SHA256：

```text
model-00001-of-00002.safetensors       994ac2b03f97de8bc647d0fe5eba2e4b632b3e28dc03574c29bdfc36cf47e1b9
model-00002-of-00002.safetensors       92540d8353c8d226a589a3b179bdb33851c970ee2cc2ac7ba035f79425e7b833
model.safetensors.index.json           260ab9fa1418d6d6ab79daa1d9da2c47264f3b72edb4630fc799077ac67d27c6
config.json                            422adefa19e62dd175961cec85bc0400344fe5bf9b22bd1182e05aaae78556e0
generation_config.json                 d2864bf1edea5863d331edfff48106b586a366f5a2c41aa77731fadc53aa25d2
preprocessor_config.json               b5eaad0c2815f07631535dcc58f3c462b0d73693638ad21d19f3c50820eae1cc
tokenizer.json                         cb63a0a23eef3d5b01063a9880a1925a65aaf4d1591d519910ee3527852950a0
tokenizer_config.json                  ff5c4fd898fe8c39591eb70e5d39d2782802d4204d6ae9ba1223252f354842a0
vocab.json                             ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910
merges.txt                             599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3
```

底座模型 `config.json` 关键结构：

```text
architectures = Qwen2VLForConditionalGeneration
model_type = qwen2_vl
hidden_size = 1536
intermediate_size = 8960
num_hidden_layers = 28
num_attention_heads = 12
num_key_value_heads = 2
max_position_embeddings = 32768
torch_dtype = bfloat16
vision_config.depth = 32
vision_config.hidden_size = 1536
```

训练和推理配置中：

```text
local_files_only = true
download_source = local_huggingface_cache
```

含义是运行时使用本机 Hugging Face cache，不在训练过程中实时联网下载。

## 3. LoRA checkpoint

正式训练 run：

```text
run_id = d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1
method_id = D_SFT
run_kind = formal_train
```

外部 artifact checkpoint 目录：

```text
<external-artifact-root>/d_sft/checkpoints/d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1/checkpoint-final
```

核心 LoRA 权重：

```text
<external-artifact-root>/d_sft/checkpoints/d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1/checkpoint-final/adapter_model.safetensors
```

checkpoint-final 文件：

```text
adapter_config.json
adapter_model.safetensors
chat_template.jinja
processor_config.json
README.md
tokenizer.json
tokenizer_config.json
```

checkpoint-final 文件 SHA256：

```text
adapter_config.json                   827975de5af39553fa7da2405ffa9c85cadee6ed34618bd809b01d5894b79ff8
adapter_model.safetensors             df5e5eb5e97ffb5b86368fb966705cddffe09e4dfaa622959859d2da9fc412e0
chat_template.jinja                   6edff8eae4ef69923f937be5b1fcf91462227e7c827a0a936a98197f19642388
processor_config.json                 c244ec5dd62d122710dd7e8cee226cfd90cda85d19f23ce0bb018f5d300afa1c
README.md                             f84870e9c330a9a17f01ec27d85bd995fcc22addb5e7f1dd55259f3d1cda6adc
tokenizer.json                        312c03cb421e18f41c20c3e35f3302479a3a8f8b1f06779fd900326a0d32c22f
tokenizer_config.json                 b7e922bac4f0585865ed00ad398b25ad14cddf1bef8bb0c7ab2aeaf421e75736
```

adapter 文件大小：

```text
adapter_model.safetensors = 36,986,952 bytes
```

仓库中没有提交权重文件。被 Git 跟踪的以下文件数量为 0：

```text
*.safetensors
*.bin
*.pt
*.pth
```

## 4. PEFT / LoRA adapter 配置

来自 `checkpoint-final/adapter_config.json`：

```text
base_model_name_or_path = Qwen/Qwen2-VL-2B-Instruct
revision = null
peft_type = LORA
task_type = CAUSAL_LM
peft_version = 0.19.1
inference_mode = true
r = 8
lora_alpha = 16
lora_dropout = 0.05
bias = none
lora_bias = false
init_lora_weights = true
fan_in_fan_out = false
use_dora = false
use_rslora = false
use_qalora = false
qalora_group_size = 16
```

LoRA target modules：

```text
q_proj
k_proj
v_proj
o_proj
gate_proj
up_proj
down_proj
```

未启用或为空的 adapter 配置项：

```text
modules_to_save = null
layers_to_transform = null
layers_pattern = null
rank_pattern = {}
alpha_pattern = {}
exclude_modules = null
target_parameters = null
trainable_token_indices = null
layer_replication = null
loftq_config = {}
eva_config = null
corda_config = null
arrow_config = null
alora_invocation_tokens = null
```

LoRA 关键解释：

```text
LoRA adapter 不是完整模型，只保存任务微调产生的低秩增量参数。
推理时必须加载同一个底座模型，再加载 adapter。
adapter_config.json 中 revision = null，没有在 adapter 内固定 Hugging Face revision。
本机实测底座 revision 由 Hugging Face cache refs/main 记录为 895c3a49bc3fa70a340399125c650a463535e71c。
训练使用 QLoRA：底座 4bit NF4 量化加载，LoRA adapter 训练。
推理使用同一 checkpoint-final，通过 PeftModel.from_pretrained 加载。
```

## 5. 训练数据

数据集：

```text
dataset_name = d_sft_train500_dev100
```

训练 JSONL：

```text
<external-artifact-root>/d_sft/training_jsonl/d_sft_train500_dev100.prompt_v2.train.jsonl
```

开发 JSONL：

```text
<external-artifact-root>/d_sft/training_jsonl/d_sft_train500_dev100.prompt_v2.dev.jsonl
```

combined manifest：

```text
<external-artifact-root>/d_sft/data/d_sft_train500_dev100/combined_manifest.jsonl
```

样本数：

```text
train_samples = 500
dev_samples = 100
```

训练/开发 JSONL SHA256：

```text
train_jsonl_sha256 = 8d9434e499c5f0151711ad7a5d93466f1c1707f537e2066416247425d309a7cb
dev_jsonl_sha256   = d21000873c2be3bee7963d25f92d2f1dcd0242778f5c98c43b2291ed340b9cfa
```

label source：

```text
CIFP_260416_FAACIFP18_to_current_canonical_proxy_projection
```

训练 label 含义：

```text
完整航图 PNG + D-SFT prompt -> CIFP/424 投影得到的 missed approach canonical JSON
```

训练输入允许：

```text
full_chart_image
frozen_d_sft_prompt
training split canonical label
dev split canonical label, only for checkpoint selection and diagnostics
```

训练禁止来源：

```text
formal300
pilot10_external
pilot100_external_heldout_feasibility
OCR_text
field_candidates
scorer_output
other_method_predictions
```

no-leakage 记录：

```text
hard_leakage = false
forbidden overlap counts:
  chart_id = 0
  pdf_name = 0
  exact_proc_key = 0
  family_key = 0
  image_path = 0
  target_path = 0
train/dev overlap counts:
  chart_id = 0
  pdf_name = 0
  family_key = 0
```

## 6. Prompt、schema、脚本和冻结文件

prompt：

```text
training/d_sft/prompts/d_sft_image_to_canonical.v2.md
sha256 = 8e0f6d36c023e6d23b78655ab1a1910f49880d7bd473db75d4250681ac21445e
```

schema：

```text
schemas/missed_approach_leg.schema.json
sha256 = cd62edf995344d73ae45fcfad4e9bff3412f58a42f9fb591f9ca08e399e26be9
```

冻结训练配置：

```text
training/d_sft/configs/d_sft_training_config.frozen_20260428_r1.json
current file sha256 = 378df37d39eda9cd58e8c8cee24dada471d504fa8f242fbc9d892b813f857deb
```

训练脚本：

```text
scripts/d_sft_train_qwen2vl_lora.py
sha256 = f87d67987d4f1a14b78756e77100d58b365ca09162fc73b5aa37f62722c8a74f
```

推理脚本：

```text
scripts/d_sft_infer_qwen2vl_lora.py
sha256 = abd8778aa98fbb11623e1782387c10c8df489e08d781178244daf7aeb39add03
```

数据准备脚本：

```text
scripts/d_sft_prepare_dataset.py
sha256 = 79461f9f439a59e53896667a1d99d03603d5d9fb5e28da43a21a11cab1af7f2e
```

冻结报告：

```text
training/d_sft/reports/d_sft_freeze_report_20260428_r1.md
```

本机训练报告应在外部 artifact root：

```text
<external-artifact-root>/d_sft/reports/d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1_training_report.json
```

## 7. 图像输入设置

```text
input_policy = full_chart_image_only
min_pixels = 3136
max_pixels = 501760
resize_policy = Qwen2VLProcessor dynamic resize capped at max_pixels=501760
```

训练和推理均不使用：

```text
OCR text
field candidates
evidence boxes
cropped region
target JSON during inference
score file during inference
raw CIFP during inference
```

## 8. 量化和模型加载

模型配置：

```text
base_model_id = Qwen/Qwen2-VL-2B-Instruct
base_model_role = local_trainable_vlm
local_files_only = true
download_source = local_huggingface_cache
load_in_4bit = true
bnb_4bit_quant_type = nf4
bnb_4bit_use_double_quant = true
device_map = auto
```

训练 compute dtype：

```text
float16
```

加载逻辑：

```text
AutoProcessor.from_pretrained(
  Qwen/Qwen2-VL-2B-Instruct,
  local_files_only=true,
  min_pixels=3136,
  max_pixels=501760
)

BitsAndBytesConfig(
  load_in_4bit=true,
  bnb_4bit_quant_type=nf4,
  bnb_4bit_compute_dtype=float16,
  bnb_4bit_use_double_quant=true
)

Qwen2VLForConditionalGeneration.from_pretrained(
  Qwen/Qwen2-VL-2B-Instruct,
  local_files_only=true,
  quantization_config=4bit NF4,
  device_map=auto
)

PeftModel.from_pretrained(base_model, checkpoint-final)
```

## 9. 训练超参数

```text
seed = 260428
epochs = 1
per_device_batch_size = 1
gradient_accumulation_steps = 8
learning_rate = 0.0002
weight_decay = 0.0
max_grad_norm = 1.0
compute_dtype = float16
gradient_checkpointing = true
max_seq_length = 4096
checkpoint_save_policy = save adapter and processor after each epoch plus final
checkpoint_selection_policy = lowest dev loss among epoch checkpoints; dev split only
checkpoint_selection_dev_samples = 100
```

输出控制：

```text
assistant_prefill = "{"
training masks the prefilled opening brace
inference prepends the same brace before generation
final raw output must still be strict bare JSON
parser_repair = false
```

训练结果：

```text
created_at = 2026-04-28T17:53:51.316624+00:00
global_steps = 500
optimizer_steps = 63
truncated_train_samples = 0
max_train_seq_length_seen = 1931
best_dev_loss = 0.04459553452208638
best_checkpoint = <external-artifact-root>/d_sft/checkpoints/d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1/checkpoint-epoch01
final_checkpoint = <external-artifact-root>/d_sft/checkpoints/d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1/checkpoint-final
```

## 10. 训练运行环境

训练报告记录的环境：

```text
python = 3.11.15 | packaged by Anaconda, Inc.
torch = 2.6.0+cu124
transformers = 5.5.4
peft = 0.19.1
bitsandbytes = 0.49.2
Pillow = 11.1.0
jsonschema = 4.26.0
CUDA available = true
GPU = NVIDIA GeForce RTX 4060 Laptop GPU
CUDA max_memory_allocated_gb = 7.1405
```

2026-05-06 当前机器 `nvidia-smi` 状态，作为后补环境记录：

```text
NVIDIA-SMI = 566.24
Driver Version = 566.24
CUDA Version shown by nvidia-smi = 12.7
GPU = NVIDIA GeForce RTX 4060 Laptop GPU
Total memory = 8188 MiB
Driver model = WDDM
```

2026-05-06 当前 Codex shell 包版本，作为后补环境记录：

```text
python = 3.13.11
platform = Windows-11-10.0.22631-SP0
torch = 2.6.0+cu124
transformers = 5.3.0
peft = 0.19.1
bitsandbytes = 0.49.2
Pillow = 12.1.0
jsonschema = 4.26.0
accelerate = 1.13.0
safetensors = 0.7.0
qwen-vl-utils = 0.0.14
```

注意：当前 Codex shell 环境和 2026-04-28 训练报告中的环境不完全相同。复现实验时应优先以训练报告环境为准。

## 11. 推理参数

冻结配置中的推理参数：

```text
prompt_policy = same prompt file as SFT training user message
max_new_tokens = 1536
decoding = greedy_do_sample_false
parser_policy = strict_json_only_no_code_fence_no_semantic_repair
rerun_policy = no selective rerun; engineering failure may rerun complete failed run with new run_id
assistant_prefill = "{"
```

parser policy：

```text
strict_json_only = true
code_fence_stripping_allowed = false
semantic_repair_allowed = false
retry_policy = no selective retry
```

重要差异记录：

```text
训练报告内嵌 candidate config 中曾出现 max_new_tokens = 3072。
冻结 config 和 freeze report 的正式推理口径为 max_new_tokens = 1536。
```

推理输入允许：

```text
full_chart_image
frozen_d_sft_prompt
```

推理阶段禁止：

```text
OCR_text
field_candidates
CIFP_raw_record
target_JSON
score_file
human_answer
other_method_prediction
```

target 只允许在预测完成后用于评分。

## 12. pilot100 feasibility 推理

pilot100 run：

```text
run_id = d_sft_pilot100_promptv2_prefill_20260428_r1
checkpoint = <external-artifact-root>/d_sft/checkpoints/d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1/checkpoint-final
sample_role = pilot100_external_heldout_feasibility_only_not_formal300
samples_total = 100
schema_valid = 94
samples_scored = 94
parse_or_schema_failures = 6
field-level score = 1014 / 2200 = 0.46090909090909093
```

pilot100 不是 formal300 result，也不是最终论文 formal result，只是 heldout feasibility。

## 13. 实验组 1 formal200 D1 结果

formal200 D1 canonicalization run：

```text
run_id = group1_formal200_D1_20260502_r4
method = D1
policy_id = d1_output_canonicalization_20260502_r4
samples_total = 200
raw_outputs_found = 200
canonical_json_written = 200
schema_valid = 200
schema_invalid = 0
samples_scored = 200
failures = 0
```

仓库内结果目录：

```text
formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/D1
```

summary：

```text
formal_runs/group1/group1_formal_eval_50_200_50_seed20260437_20260430_r1_scoring_equivalence_v2/D1/reports/D1_summary.json
```

score：

```text
strict field-level score = 2972 / 4052 = 73.35%
v2 field-level score = 3158 / 4052 = 77.93682132280355%
```

chart_id 审计：

```text
raw_chart_id_mismatch_count = 54
final_chart_id_mismatch_count = 0
```

D1 canonicalization action counts：

```text
parse_entire_raw_as_json_object = 196
extract_json_object_candidates:1 = 3
extract_json_object_candidates:2 = 1
wrap_short_raw_format_to_canonical = 3
set_manifest_chart_id_envelope = 55
drop_extra_top_level_fields:approach,chart_name = 1
merge_raw_internal_metadata_and_body = 1
raw_object_not_convertible_to_canonical_shape = 1
fallback_invalid_fix_ident on leg 2 = 3
fallback_invalid_fix_ident on leg 3 = 3
```

解释：formal200 的 D1 结果使用 D-SFT raw outputs，再通过 D1 canonicalization policy 转成统一 canonical JSON 接口后评分。canonicalization 不使用 target JSON、raw 424/CIFP、score、人类答案、OCR、field candidates 或其他方法预测来修正字段答案。模型字段识别错误仍然计错。

## 14. 复现命令形态

训练命令形态：

```powershell
python scripts\d_sft_train_qwen2vl_lora.py `
  --config training\d_sft\configs\d_sft_training_config.candidate.json `
  --output-root <external-artifact-root>\d_sft `
  --run-id d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1
```

pilot100 推理命令形态：

```powershell
python scripts\d_sft_infer_qwen2vl_lora.py `
  --config training\d_sft\configs\d_sft_training_config.frozen_20260428_r1.json `
  --checkpoint <external-artifact-root>\d_sft\checkpoints\d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1\checkpoint-final `
  --manifest <external-artifact-root>\pilot100_external\pilot100_external_manifest.jsonl `
  --schema schemas\missed_approach_leg.schema.json `
  --output-root <external-artifact-root>\d_sft `
  --run-id d_sft_pilot100_promptv2_prefill_20260428_r1
```

另一台机器复现所需文件：

```text
1. Hugging Face 底座模型 Qwen/Qwen2-VL-2B-Instruct
2. checkpoint-final 整个目录，不只是 adapter_model.safetensors
3. training/d_sft/prompts/d_sft_image_to_canonical.v2.md
4. schemas/missed_approach_leg.schema.json
5. scripts/d_sft_infer_qwen2vl_lora.py
6. 对应 image manifest
7. 预测完成后才可使用 target/scoring manifest 评分
```

## 15. 仍无法从现有记录完全恢复的内容

已经整理出的内容包括：

```text
底座模型来源
底座模型文件大小和 SHA256
LoRA checkpoint 文件和 SHA256
adapter_config 全部核心参数
训练数据、prompt、schema、脚本和 hash
图像输入参数
4bit QLoRA 加载参数
训练超参数
推理参数
训练报告环境
当前机器环境后补记录
pilot100 feasibility 结果
formal200 D1 结果
复现命令形态
```

仍无法只靠当前仓库和训练报告恢复的内容：

```text
训练当时完整 conda env export
训练当时完整 pip freeze
训练和推理实际 shell history
训练 wall-clock 起止时间
formal200 raw inference 的原始本机运行命令全文
```

这些没有完整写入冻结报告或训练报告，不能凭空补。若后续能找到当时 shell history、conda export、pip freeze 或 raw run manifest，应继续追加。
