# D1-50_FINAL_V2 LoRA 下午 50 样本运行全细节记录

日期：2026-05-07

本文只记录 2026-05-06 下午在本机训练出来的 `D1-50_FINAL_V2` LoRA：

```text
run_id = d1_50_final_v2_qwen2vl_lora_20260506_r1
method_id = D1-50_FINAL_V2
训练样本数 = 50
训练开始/报告创建时间 = 2026-05-06 14:34:59 Asia/Shanghai
```

它不是最初实验组 1 的 `D1` / `D_SFT` formal LoRA，也不是计划中的 `D1-500_FINAL_V2`。这次要提交的是下午那 50 个样本训练出来的 LoRA 的环境、参数、数据、推理、结果和问题记录。

## 1. 这次 50 样本方法是什么

`D1-50_FINAL_V2` 是实验组 1 D 系列 final-v2 方案中的小样本 SFT 方法。

输入：

```text
完整 FAA 航图 PNG
final-v2 D prompt
```

训练标签：

```text
CIFP / 424 派生 canonical proxy label
经过 final-v2 field-legality 规则清洗
不允许 unknown 作为正式 status
```

输出：

```text
final-v2 canonical missed-approach JSON
```

目的：

```text
和 D_BASE_SAME_BACKBONE_FINAL_V2 对比，观察同底座未微调模型和 50 样本 LoRA 的差异。
和 D1-500_FINAL_V2 对比，观察 50 样本与 500 样本 SFT 的差异。
```

边界：

```text
训练阶段允许使用训练 split 的航图 PNG 和训练 label。
训练阶段禁止使用 formal300、pilot10、pilot100 external、OCR、field candidates、scorer output、其他方法预测。
推理阶段只允许读取完整航图 PNG 和 final-v2 D prompt。
推理阶段禁止读取 target JSON、score、raw CIFP/424、人类答案、其他方法预测、comparison policy。
scoring manifest / target / comparison policy 只能在预测完成后评分时使用。
```

## 2. 底座模型来源

底座模型：

```text
Qwen/Qwen2-VL-2B-Instruct
```

公开下载地址：

```text
https://huggingface.co/Qwen/Qwen2-VL-2B-Instruct
```

官方代码地址：

```text
https://github.com/QwenLM/Qwen2-VL
```

本机训练时使用本地 Hugging Face cache，不在训练过程中联网下载：

```text
local_files_only = true
observed_huggingface_cache_revision = 895c3a49bc3fa70a340399125c650a463535e71c
```

本机观测到的底座模型关键文件 hash：

| 文件 | 大小 | SHA256 |
| --- | ---: | --- |
| `model-00001-of-00002.safetensors` | 3988609112 | `994ac2b03f97de8bc647d0fe5eba2e4b632b3e28dc03574c29bdfc36cf47e1b9` |
| `model-00002-of-00002.safetensors` | 429441656 | `92540d8353c8d226a589a3b179bdb33851c970ee2cc2ac7ba035f79425e7b833` |
| `model.safetensors.index.json` | 56411 | `260ab9fa1418d6d6ab79daa1d9da2c47264f3b72edb4630fc799077ac67d27c6` |
| `config.json` | 1196 | `422adefa19e62dd175961cec85bc0400344fe5bf9b22bd1182e05aaae78556e0` |
| `tokenizer.json` | 7029741 | `cb63a0a23eef3d5b01063a9880a1925a65aaf4d1591d519910ee3527852950a0` |

## 3. 训练数据从哪里来

原始来源是本机已有的 D-SFT 数据：

```text
d_sft_train500_dev100
source_train_sha256 = 8d9434e499c5f0151711ad7a5d93466f1c1707f537e2066416247425d309a7cb
source_dev_sha256 = d21000873c2be3bee7963d25f92d2f1dcd0242778f5c98c43b2291ed340b9cfa
```

这些样本的用户输入是完整航图图片加 prompt，assistant label 是 CIFP/424 投影得到的 canonical JSON。final-v2 不是重新标注一套数据，而是在原有 D-SFT JSONL 上做字段合法性清洗：

```text
contract = final_v2_field_legality_no_open_unknown
status_unknown_allowed = false
```

final-v2 转换规则产生的统计：

| 项 | 数量 |
| --- | ---: |
| `df_q4_direct_to_not_applicable` | 426 |
| `df_cf_q3_not_applicable_to_both` | 417 |
| input validation error rows | 0 |
| output validation error rows | 0 |

输出文件 hash：

| 文件 | 行数/样本数 | SHA256 |
| --- | ---: | --- |
| `d_sft_train500_dev100.final_v2.train500.jsonl` | 500 | `836dcf2390b1a151068be59f9d99c4f37f32d6bc8759f940555131c8fc455baf` |
| `d_sft_train500_dev100.final_v2.dev100.jsonl` | 100 | `2c457bb90d53fa783b619eb76ca035f9c8bdd8f1b6a4720ac4df2dffd78a8ef0` |
| `d_sft_train500_dev100.final_v2.train50_seed260506.jsonl` | 50 | `fd9106f5850dd91aaeedd142e4b7e8ddd90df17cc771fb5597186838e55cfd62` |

50 样本子集固定为：

```text
subset_seed = 260506
subset_size = 50
```

50 个 `chart_id`：

```text
KATL_R09R
KEMV_L34
KCQX_RNV-B
KBAM_R22
KCPP_L25
KHRJ_L05
KARR_I09
KHJO_RNV-B
KSEA_I34L
KAGS_I17
KAGS_I35
KCWF_I15
KMGY_L20
KEDN_R05
KMIA_L26R
KALB_I01
KDFW_I35C
KAND_R35
KFAR_I36
KFYJ_L10
KGIC_R26
KARR_R33
KBLF_R23
KAUS_I18R
KGAI_RNV-A
KARW_R25
KBOS_R15R
KHQM_I24
KBFD_I32
KMKE_L25L
KMGJ_R26
KCCR_R19R
KBGM_I34
KBMI_I02
KASX_R13
KBHM_I06
KCIU_R10
KBKW_I19
KMCO_I17R
KPDX_L21
KPHF_L20
KBWI_I33L
KOLS_RNV-A
KCIC_I13L
KRBW_R17
KPHH_RNV-A
KATY_R12
KCLE_I24L
KSAD_R30
KCPS_R12R
```

## 4. 相关 prompt、脚本和 schema

| 文件 | SHA256 |
| --- | --- |
| `training/d_sft/prompts/d_sft_image_to_canonical.final_v2.md` | `df513ba5391b96c126b86f61abb7a2b1a10fbfdac9a79ff7f242f9fe506eafb6` |
| `scripts/d_sft/build_d1_final_v2_training_jsonl.py` | `b609397067d294e82cc31bd57db29bed8ba729451118ae03cffae2363f1b0d35` |
| `scripts/d_sft_train_qwen2vl_lora.py` | `f87d67987d4f1a14b78756e77100d58b365ca09162fc73b5aa37f62722c8a74f` |
| `scripts/d_sft/run_d_sft_final_v2_inference.py` | `a36c975f974a27d3cc4bcfdb5e2198fbccbbfcefb0bad14ca02d0ff156ac26e0` |
| `scripts/score_final_v2_sft_outputs.py` | `e0cf3f1ce70ad20b0e264af9fdfc018e8bd2b235b56016776e060fa60d98bde6` |
| `schemas/missed_approach_leg.schema.json` | `cd62edf995344d73ae45fcfad4e9bff3412f58a42f9fb591f9ca08e399e26be9` |

final-v2 prompt 的关键要求：

```text
输出必须是一个 JSON object。
第一字符必须是 {。
不要 markdown，不要代码块，不要解释。
顶层键固定为 chart_id、procedure、missed_approach。
每个 answer 的 status 只能是 present、not_observable、not_applicable。
永远不要输出 unknown。
DF direct-to-fix leg 不再用 Q4_course_or_radial={"type":"direct"}，Q4 用 not_applicable/null。
CF/DF 没有指定左右转限制时，Q3_turn 用 present/BOTH。
```

## 5. LoRA 和模型加载参数

模型加载：

```text
base_model_id = Qwen/Qwen2-VL-2B-Instruct
local_files_only = true
load_in_4bit = true
bnb_4bit_quant_type = nf4
bnb_4bit_use_double_quant = true
device_map = auto
compute_dtype = float16
```

LoRA / PEFT：

```text
peft_type = LORA
task_type = CAUSAL_LM
peft_version = 0.19.1
r = 8
lora_alpha = 16
lora_dropout = 0.05
bias = none
target_modules = q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
```

图像输入：

```text
input_policy = full_chart_image_only
min_pixels = 3136
max_pixels = 501760
resize_policy = Qwen2VLProcessor dynamic resize capped at max_pixels=501760
```

输出控制：

```text
assistant_prefill = {
parser_repair = false
training masks the prefilled opening brace
inference prepends the same brace before generation
final raw output must still be strict bare JSON
```

## 6. 训练参数

```text
seed = 260428
epochs = 1
train_samples = 50
dev_samples = 100
per_device_batch_size = 1
gradient_accumulation_steps = 8
learning_rate = 0.0002
weight_decay = 0.0
max_grad_norm = 1.0
gradient_checkpointing = true
max_seq_length = 4096
checkpoint_save_policy = save adapter and processor after each epoch plus final
checkpoint_selection_policy = lowest dev loss among epoch checkpoints; dev split only
checkpoint_selection_dev_samples = 100
```

训练报告：

```text
global_steps = 50
optimizer_steps = 7
truncated_train_samples = 0
max_train_seq_length_seen = 2041
best_dev_loss = 0.19552553363144398
best_checkpoint = checkpoint-epoch01
final_checkpoint = checkpoint-final
```

训练 loss 摘要：

| 项 | 值 |
| --- | ---: |
| loss rows | 50 |
| first loss | 0.5000839829444885 |
| last loss | 0.24027012288570404 |
| min loss | 0.18895679712295532 |
| max loss | 0.6174681782722473 |
| mean loss | 0.3509966394305229 |
| min sequence length | 1650 |
| max sequence length | 2041 |
| mean sequence length | 1839.62 |
| truncated count | 0 |

训练环境：

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

## 7. checkpoint 文件和 hash

`checkpoint-final` 文件：

| 文件 | 大小 | SHA256 |
| --- | ---: | --- |
| `adapter_config.json` | 1150 | `cfac22dc2e571284b9347d1f1402bc5c3eacbbbb4272913843911df4c4be7f05` |
| `adapter_model.safetensors` | 36986952 | `439d0962ea650071bef1a6bd74d2a6852e60156155ec36eb3c395549fcaf3a96` |
| `chat_template.jinja` | 1023 | `6edff8eae4ef69923f937be5b1fcf91462227e7c827a0a936a98197f19642388` |
| `processor_config.json` | 1534 | `c2debefbf9071c2389a08126e86b1bb18f666a24c09a0967c8a8779911d8b9a6` |
| `README.md` | 5204 | `f84870e9c330a9a17f01ec27d85bd995fcc22addb5e7f1dd55259f3d1cda6adc` |
| `tokenizer.json` | 11420534 | `312c03cb421e18f41c20c3e35f3302479a3a8f8b1f06779fd900326a0d32c22f` |
| `tokenizer_config.json` | 810 | `b7e922bac4f0585865ed00ad398b25ad14cddf1bef8bb0c7ab2aeaf421e75736` |

注意：`adapter_model.safetensors` 没有提交到 Git，只提交 hash、大小和路径模板。

## 8. 推理参数

推理 runner：

```text
scripts/d_sft/run_d_sft_final_v2_inference.py
```

推理输入：

```text
完整航图 PNG
final-v2 D prompt
```

推理禁止输入：

```text
target JSON
score file
raw CIFP
human answer
other method prediction
comparison policy
```

generation：

```text
max_new_tokens = 1536
decoding = greedy_do_sample_false
assistant_prefill = {
parser_policy = strict_json_only_no_code_fence_no_semantic_repair
```

## 9. 下午 50-run 的 smoke 结果

formal200 smoke5：

```text
run_id = d1_50_final_v2_smoke5_20260506_r1
sample_role = formal200_evaluation_smoke5_image_only
samples_total = 5
parse_ok = 1
final_v2_valid = 1
parse_or_final_v2_failures = 4
```

5 个样本：

| chart_id | 状态 |
| --- | --- |
| `KABE_I06` | parse failure: no complete JSON object |
| `KALS_I02` | parse ok, final-v2 valid |
| `KAMA_I04` | parse failure: no complete JSON object |
| `KAPC_I01L` | parse failure: trailing comma |
| `KATL_I09R` | parse failure: no complete JSON object |

训练集已见样本 5 条诊断：

```text
run_id = d1_50_final_v2_train_seen5_diag_20260506_r1
sample_role = train_seen5_diagnostic_image_only
samples_total = 5
parse_ok = 2
final_v2_valid = 2
parse_or_final_v2_failures = 3
```

5 个样本：

| chart_id | 状态 |
| --- | --- |
| `KATL_R09R` | parse failure: no complete JSON object |
| `KEMV_L34` | parse failure: trailing comma |
| `KCQX_RNV-B` | parse ok, final-v2 valid |
| `KBAM_R22` | parse ok, final-v2 valid |
| `KCPP_L25` | parse failure: no complete JSON object |

结论：

```text
这个下午 50 样本 LoRA 已经完成训练和两个 smoke/diagnostic 推理。
它没有通过 smoke 门槛。
formal smoke5 只有 1/5 parse-valid。
train-seen5 只有 2/5 parse-valid。
因此没有继续用该 checkpoint 跑 formal200，也没有把它当正式 score 结果。
```

## 10. 复现命令形态

构造 final-v2 train500/dev100/train50：

```powershell
python scripts\d_sft\build_d1_final_v2_training_jsonl.py `
  --train-jsonl <external-artifact-root>\d_sft\training_jsonl\d_sft_train500_dev100.prompt_v2.train.jsonl `
  --dev-jsonl <external-artifact-root>\d_sft\training_jsonl\d_sft_train500_dev100.prompt_v2.dev.jsonl `
  --prompt training\d_sft\prompts\d_sft_image_to_canonical.final_v2.md `
  --output-dir <external-artifact-root>\d_sft\final_v2_training_jsonl\d1_final_v2_20260506 `
  --subset-size 50 `
  --subset-seed 260506
```

训练 D1-50：

```powershell
python scripts\d_sft_train_qwen2vl_lora.py `
  --config <external-artifact-root>\d_sft\configs\d1_50_final_v2_qwen2vl_lora_20260506_r1.local.json `
  --output-root <external-artifact-root>\d_sft `
  --run-id d1_50_final_v2_qwen2vl_lora_20260506_r1
```

formal200 smoke5 推理：

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

训练集已见样本诊断推理：

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

## 11. 没有提交到 Git 的内容

以下内容保留在外部 artifact root，不进入 Git：

```text
local config with absolute paths
adapter_model.safetensors
base model weights
PNG/PDF chart assets
raw_text model outputs
canonical_json prediction directories
parse_or_infer_errors directories
large score/result directories
```

Git 中提交的是：

```text
prompt
脚本
中文方案
中文细节报告
sanitized artifact manifest
路径模板
hash
参数
smoke 结论
```

这能说明下午 50 个样本到底怎么训练、用什么模型、参数是什么、结果是什么、为什么不能把它当成已经跑通的 formal200 结果，同时不把权重和大文件塞进仓库。
