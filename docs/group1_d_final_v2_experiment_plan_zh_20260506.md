# 实验组 1 D 系列 final-v2 补充实验方案

日期：2026-05-06

本文档定义实验组 1 中 D 相关方法在 final-v2 口径下的最终补充实验方案。重点是重新设计并运行 `D_BASE_SAME_BACKBONE_FINAL_V2`、`D1-50_FINAL_V2`、`D1-500_FINAL_V2`。旧 D1 结果保留为历史诊断结果，但不再作为 final-v2 正式表格中的最终 D1 结果。

本文档不写入本机绝对路径、Dataverse 预览 token、模型 checkpoint、PNG、raw output 或大结果文件。所有本机路径应放入本地配置文件或运行报告中，不提交到 Git。

## 1. 背景和原因

原来的 D1 是端到端 SFT 方法：输入完整航图图片，输出 missed approach canonical JSON。它的训练 label 来自 424/CIFP 结构化编码投影得到的 canonical JSON。

现在 D 系列需要重做，原因有两个：

1. PR #39 引入了 final-v2 字段合法性、comparison policy 和 SFT 输出评分入口。最终论文表格必须使用同一个 final-v2 target/scorer contract。
2. Dataverse final-v2 release/artifact package 中的 formal target、annotation target、scoring-equivalence target、auxiliary SFT paired answers 需要和 PR #39 的 final-v2 规则一致。旧 D1 训练数据中可能保留旧字段语义，例如开放式 `unknown` target、DF direct-to-fix 写成 `Q4_course_or_radial={type: direct}` 等。

因此，不能把旧 D1 checkpoint 重新评分后直接当作 final-v2 D1。旧 checkpoint 可以作为诊断，但正式 D1 必须使用 corrected auxiliary SFT JSONL 重新训练。

## 2. 总体目标

实验组 1 的 D 系列 final-v2 实验回答三个问题：

1. 同一底座模型在不 SFT 时，使用 D 系列输出接口能达到什么水平。
2. 只用 50 条 corrected SFT 样本训练，能否明显改善完整航图到 canonical JSON 的能力。
3. 使用 500 条 corrected SFT 样本训练，相比 50 条和未微调底座能提升多少。

最终 D 系列主表应包含：

| 方法名 | 是否训练 | 训练样本数 | 输入 | 输出 | 作用 |
| --- | --- | ---: | --- | --- | --- |
| `D_BASE_SAME_BACKBONE_FINAL_V2` | 否 | 0 | 完整航图 PNG + final-v2 D prompt | final-v2 canonical JSON | 同底座未微调对照 |
| `D1-50_FINAL_V2` | 是 | 50 | 完整航图 PNG + final-v2 D prompt | final-v2 canonical JSON | 小数据 SFT 对照 |
| `D1-500_FINAL_V2` | 是 | 500 | 完整航图 PNG + final-v2 D prompt | final-v2 canonical JSON | D1 主结果 |

旧 D1 的定位：

| 方法名 | 定位 |
| --- | --- |
| old D1 | 旧 target/scorer contract 下的历史诊断结果，不和 final-v2 分数混入同一正式表格 |

## 3. 方法定义

### 3.1 D_BASE_SAME_BACKBONE_FINAL_V2

`D_BASE_SAME_BACKBONE_FINAL_V2` 是 D1-50 和 D1-500 的同底座未微调对照。

定义：

```text
底座模型：与 D1-50 / D1-500 完全一致，例如 Qwen2-VL-2B-Instruct
LoRA/checkpoint：不加载
输入：完整航图 PNG + final-v2 D prompt
输出：final-v2 missed approach canonical JSON
训练：无
推理边界：不能读取 target JSON、score、raw 424/CIFP、其他方法预测
评分：PR #39 的 final-v2 scorer 和 comparison policy
```

D-base 必须重新跑。原因是旧 D-base 可能使用旧 prompt、旧 parser repair、旧 schema 或旧 scoring policy，不能作为 D1-50/D1-500 的 final-v2 对照。

### 3.2 D1-50_FINAL_V2

`D1-50_FINAL_V2` 是 50 条训练样本的端到端 SFT。

定义：

```text
底座模型：与 D-base / D1-500 相同
训练方式：LoRA 或 QLoRA，沿用旧 D1 的训练框架
训练样本：corrected D1-500 train set 中固定 seed 抽取的 50 条
输入：完整航图 PNG + final-v2 D prompt
训练 label：final-v2 canonical JSON
输出：final-v2 missed approach canonical JSON
评分：PR #39 final-v2 scorer
```

建议 D1-50 从 corrected D1-500 train set 中抽取固定 50 条，而不是使用 formal300 的第一个 50。这样 D1-50 和 D1-500 的唯一实验变量就是训练样本数量。如果改用 formal300 的第一个 50，则数据来源也改变，实验解释会变成“数据来源 + 训练数量”的混合效应。

### 3.3 D1-500_FINAL_V2

`D1-500_FINAL_V2` 是 500 条训练样本的端到端 SFT，是 D 系列 final-v2 主结果。

定义：

```text
底座模型：与 D-base / D1-50 相同
训练方式：LoRA 或 QLoRA，沿用旧 D1 的训练框架
训练样本：corrected auxiliary SFT train500
输入：完整航图 PNG + final-v2 D prompt
训练 label：final-v2 canonical JSON
输出：final-v2 missed approach canonical JSON
评分：PR #39 final-v2 scorer
```

D1-50 和 D1-500 的脚本、prompt、schema、parser/canonicalization policy、训练超参数、推理脚本、评分脚本必须一致。允许不同的只有训练 JSONL 和 run id。

## 4. final-v2 JSON 规则

D 系列 final-v2 输出仍然是 missed approach canonical JSON。顶层结构不变：

```json
{
  "chart_id": "...",
  "procedure": {
    "airport": "...",
    "approach_ident": "...",
    "chart_name": "..."
  },
  "missed_approach": {
    "leg_count": {"status": "present", "value": 3},
    "legs": [
      {
        "leg_index": 1,
        "answers": {
          "Q_terminator": {"status": "present", "value": "DF"},
          "Q1_fix_ident": {"status": "present", "value": "ABC"},
          "Q2_altitude_constraint": {"status": "not_applicable", "value": null},
          "Q3_turn": {"status": "present", "value": "BOTH"},
          "Q4_course_or_radial": {"status": "not_applicable", "value": null},
          "Q5_hold_params": {"status": "not_applicable", "value": null}
        }
      }
    ]
  }
}
```

### 4.1 status 规则

final-v2 D 系列正式输出应使用以下 status：

```text
present
not_applicable
not_observable
```

要求：

```text
status=present 时 value 必须非 null。
status!=present 时 value 必须为 null。
开放式 unknown 不再作为正式 target 答案。
模型输出 unknown 必须被统计为 final-v2 policy violation 或错误，不能因为旧 target 为 unknown 获得通配 credit。
```

如果仓库全局旧 schema 仍允许 `unknown`，D 系列 final-v2 也必须额外添加 no-unknown policy check，不能只依赖旧 schema。

### 4.2 字段合法性规则

PR #39 的核心字段合法性规则如下：

1. formal references 不再使用开放式 `unknown` target。
2. CF/DF leg 如果图上没有限制转弯方向且左右均可，`Q3_turn` 应为：

```json
{"status": "present", "value": "BOTH"}
```

3. DF direct-to-fix 由以下字段表达：

```text
Q_terminator = DF
Q1_fix_ident = 目标 fix
```

DF direct-to-fix 不再用合成的 `Q4_course_or_radial = {"type": "direct"}`。此时 `Q4_course_or_radial` 应为：

```json
{"status": "not_applicable", "value": null}
```

4. TF leg 的 course/radial 如果不需要作为独立编码字段，`Q4_course_or_radial` 应为：

```json
{"status": "not_applicable", "value": null}
```

5. `not_applicable/null` 是字段合法性答案，不是 wildcard。模型输出 `unknown`、错误字段或任意值不能因为 target 为 `not_applicable` 得到通配 credit。

## 5. 数据来源和资产要求

### 5.1 必需数据资产

运行前必须准备 final-v2 Dataverse release/artifact package。该包应至少包含：

```text
NIPS-AIP-Dataset-v1.0-draft/
  formal300/
    images/
    targets/
      canonical_targets.json
      canonical_proxy_gt_combined.json
      canonical_proxy_gt/*.json
      scoring_equivalence_v2/
  manifests/
    formal300_split_50_200_50_seed20260437/
      splits_50_200_50_seed20260437.json
  schemas/
    missed_approach_leg.schema.json
  sft/
    d_sft_train500_dev100.artifact_manifest.json
    corrected train/dev JSONL 或 paired target 文件
```

实际文件名以 Dataverse release/artifact package 为准。运行前应读取 artifact manifest，记录 `updated_at`、hash、样本数量和清理统计。

### 5.2 仓库侧必需资产

PR #39 合入或 checkout 后应具备：

```text
scripts/score_final_v2_sft_outputs.py
benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/comparison_policy_v2.jsonl
reports/final_v2_field_legality_unknown_cleanup_zh_20260506.md
```

评分时优先使用 PR #39 的 scorer 和 frozen comparison policy。

### 5.3 不应提交到 Git 的内容

以下内容不能提交：

```text
local_paths.local.json
本机绝对路径配置
模型权重
LoRA checkpoint
PNG/PDF 大数据
raw model outputs
formal200 大结果目录
Dataverse 预览 token
包含 token 的 URL
```

可以提交：

```text
实验方案文档
prompt 文件
schema/policy 补充文件
小型 manifest
审计脚本
聚合报告
不含本机路径和 token 的运行说明
```

## 6. 训练集构造方案

### 6.1 D1-500 train/dev

D1-500 使用 corrected auxiliary SFT train500/dev100。

构造逻辑：

```text
输入图片：完整航图 PNG
输入 prompt：final-v2 D prompt
assistant label：根据 final-v2 规则清理后的 canonical JSON
训练集：500 条
开发集：100 条
```

这些样本不应与 formal300 evaluation/pilot/external heldout 集合泄漏重叠。必须复用或重新执行旧 D1 的 leakage check：

```text
chart_id overlap = 0
pdf_name overlap = 0
exact procedure key overlap = 0
family key overlap = 0
image_path overlap = 0
target_path overlap = 0
train/dev overlap = 0
```

### 6.2 D1-50 train/dev

D1-50 从 corrected D1-500 train set 中用固定 seed 抽取 50 条。

推荐：

```text
sample_source = corrected D1-500 train set
sample_size = 50
seed = 260506
dev set = 与 D1-500 相同 corrected dev100
```

这样 D1-50 和 D1-500 的训练代码和开发验证完全可比。

如果未来决定使用 formal300 的第一个 50 作为训练集，应重命名方法，例如 `D1-FORMAL50_FINAL_V2`，并单独说明它不是 D1-500 的数据量子集对照。

### 6.3 label 清理和审计

训练前必须对 train/dev label 做审计：

```text
assistant JSON parse failure = 0
schema failure = 0
status=unknown 数量 = 0，或有逐项处理记录
DF Q4 direct 旧表达数量 = 0
CF/DF unrestricted turn 未写 BOTH 数量 = 0
非 present 且 value 非 null 数量 = 0
present 且 value 为 null 数量 = 0
leg_count 与 legs 数量不一致 = 0
```

如果发现残留 `unknown`，不能简单全部改成 `not_observable`。处理原则：

```text
字段本来不适用于该 leg -> not_applicable/null
字段理论上需要判断但图上证据不足 -> not_observable/null
CF/DF 两向均可转弯 -> present/BOTH
旧 DF direct Q4 -> not_applicable/null
无法确定来源或语义 -> 单独列入审计报告，人工复核或从训练集排除并补样本
```

训练 JSONL 生成后应写出数据 manifest，至少包含：

```text
run data id
source artifact manifest
train/dev 样本数
D1-50 抽样 seed 和 chart_id 列表
输入图片 hash 或路径相对引用
assistant label hash
prompt hash
schema/policy hash
unknown cleanup 统计
leakage check 结果
```

## 7. prompt、schema 和 parser policy

### 7.1 final-v2 D prompt

应新建或冻结一个 final-v2 D prompt，不要覆盖旧 D1 prompt。

建议命名：

```text
training/d_sft/prompts/d_sft_image_to_canonical.final_v2.md
```

prompt 必须明确：

```text
只输出一个 JSON object。
不要输出解释、Markdown、代码块外文本。
Allowed status values: present, not_applicable, not_observable.
Never output unknown.
CF/DF unrestricted turns use Q3_turn = BOTH.
DF direct-to-fix uses Q_terminator=DF and Q1_fix_ident.
DF direct-to-fix does not use Q4_course_or_radial={type: direct}; set Q4_course_or_radial to not_applicable/null.
If a field does not apply to the leg, use not_applicable/null.
If the information cannot be determined from the chart, use not_observable/null.
```

D-base、D1-50、D1-500 必须使用同一 prompt 和同一 prompt hash。

### 7.2 schema 和 no-unknown policy

如果全局 `schemas/missed_approach_leg.schema.json` 仍允许 `unknown`，不要直接改全局 schema 影响旧实验。应为 D final-v2 添加额外校验：

```text
base schema validation
final-v2 no-unknown validation
field legality validation
```

建议新增方法专用 policy 或 validator：

```text
training/d_sft/manifests/d_sft_final_v2_output_policy.json
```

或在数据审计/评分前运行 no-unknown 检查脚本。

### 7.3 parser/canonicalization policy

三个 D 方法必须使用同一 parser/canonicalization policy。

允许的机械处理：

```text
移除 Markdown code fence
从 raw text 中抽取第一个完整 JSON object
规范化空白
记录 JSON parse 错误
```

禁止的处理：

```text
读取 target JSON 修复输出
读取 scorer 输出修复输出
读取 raw 424/CIFP 修复输出
用其他方法预测修复输出
把缺失字段按 target 猜出来
选择性删除失败样本
```

对于缺字段、类型错误、schema invalid 的输出，应在 parse/schema log 中记录，并由 final-v2 scorer 按规则计入零分或错误。若需要做输出接口层面的机械补齐，必须在三种 D 方法中完全一致，并在 run manifest 里提前声明，不能只对某一个方法使用。

## 8. 训练配置

训练配置应尽量沿用旧 D1，以便主要变量保持为 final-v2 数据口径和训练样本数。

建议配置：

```text
base model: Qwen2-VL-2B-Instruct
training type: LoRA/QLoRA
input image: full chart PNG
epochs: 1
per-device batch size: 1
gradient accumulation: 沿用旧 D1
learning rate: 沿用旧 D1，例如 2e-4
LoRA r / alpha / dropout: 沿用旧 D1
seed: 固定并记录
assistant prefill: 如旧 D1 使用，则三种方法一致记录
```

推荐 run id：

```text
d_base_same_backbone_final_v2_20260506_r1
d1_50_final_v2_qwen2vl_lora_20260506_r1
d1_500_final_v2_qwen2vl_lora_20260506_r1
```

训练产物：

```text
checkpoint-final/
adapter_model.safetensors
trainer_state.json
train_metrics.json
dev_metrics.json
run_manifest.json
```

训练产物只保存在本机或 artifact storage，不提交到 Git。

## 9. 推理方案

### 9.1 推理输入

每个 formal 样本推理时只能读取：

```text
完整航图 PNG
final-v2 D prompt
模型底座
对应 LoRA checkpoint，D-base 无 checkpoint
```

推理时禁止读取：

```text
target JSON
score
raw 424/CIFP
其他方法预测
comparison policy
scoring manifest
```

comparison policy 和 scoring manifest 只能在预测完成后进入评分阶段。

### 9.2 推理输出

每个方法输出目录建议：

```text
runs/group1_d_final_v2/
  d_base_same_backbone_final_v2_20260506_r1/
    raw_text/
    canonical_json/
    parse_logs.jsonl
    run_manifest.json
  d1_50_final_v2_qwen2vl_lora_20260506_r1/
    raw_text/
    canonical_json/
    parse_logs.jsonl
    run_manifest.json
  d1_500_final_v2_qwen2vl_lora_20260506_r1/
    raw_text/
    canonical_json/
    parse_logs.jsonl
    run_manifest.json
```

这些输出目录默认不提交 Git，只在报告中记录路径、hash 和汇总指标。

### 9.3 推理顺序

建议按以下顺序执行：

```text
1. D-base smoke5
2. D-base formal200
3. D1-50 train
4. D1-50 smoke5
5. D1-50 formal200
6. D1-500 train
7. D1-500 smoke5
8. D1-500 formal200
```

如果 GPU 时间有限，也可以在 D1-50 训练完成并确认训练脚本无误后立即启动 D1-500 训练；但评分与报告必须保持独立 run id。

## 10. 评分方案

评分使用 PR #39 的 final-v2 scorer：

```text
scripts/score_final_v2_sft_outputs.py
```

示例命令：

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

主指标：

```text
atom accuracy
95% bootstrap CI
procedure exact match
leg exact match
leg-count accuracy
parse failure count
schema failure count
unknown output count / final-v2 policy violation count
missing prediction count
```

PR #39 中 scorer 的默认 bootstrap 设置为 10000 次、seed 260506。若后续统一 bootstrap 脚本有更新，应在报告中说明采用哪个 bootstrap 入口，不能混用不同统计口径。

## 11. 验收标准

### 11.1 数据验收

训练前必须满足：

```text
corrected D1-500 train 样本数 = 500
corrected dev 样本数 = 100
D1-50 样本数 = 50
D1-50 是 D1-500 train 的固定 seed 子集
assistant JSON parse failure = 0
training label schema failure = 0
training label final-v2 no-unknown violation = 0
leakage overlap = 0
artifact manifest 和 hash 已记录
```

### 11.2 推理验收

每个方法完成 formal200 后必须报告：

```text
expected chart count
prediction file count
missing prediction count
JSON parse failure count
schema failure count
final-v2 policy violation count
unknown output count
raw output 是否完整保存
run manifest 是否完整
```

### 11.3 评分验收

每个方法必须有：

```text
aggregate_summary.json
per_sample_scores.jsonl
field_scores.jsonl
sample_errors.jsonl
scoring run_manifest.json
```

并在最终报告中列出：

```text
git commit hash
PR #39 commit hash 或合入 commit
Dataverse/artifact manifest hash
prompt hash
train/dev JSONL hash
checkpoint path 和 adapter hash
formal200 score
bootstrap CI
parse/schema failure 数量
是否出现 unknown 输出
```

## 12. 对照和结果解释

正式解释应围绕三组比较：

### 12.1 D-base vs D1-50

目的：测试少量 SFT 是否能让同底座模型学会 final-v2 JSON 格式、字段合法性和部分 missed approach 结构。

关注：

```text
atom accuracy 是否提升
parse/schema failure 是否下降
unknown output 是否下降
leg_count accuracy 是否提升
```

### 12.2 D1-50 vs D1-500

目的：测试训练数据规模从 50 增至 500 后的收益。

关注：

```text
field-level atom accuracy
leg exact match
procedure exact match
holding 相关字段表现
Q3_turn=BOTH 和 DF Q4 not_applicable 的错误率
```

### 12.3 old D1 vs D1-500 final-v2

目的：仅作诊断，不能直接放入同一 final-v2 leaderboard。

解释方式：

```text
old D1 使用旧 target/scorer contract
D1-500 final-v2 使用 corrected train/dev 和 final-v2 scorer
两者分数变化不能简单解释为模型能力变化，也包含 target contract 变化
```

## 13. 执行步骤

### Step 1: 同步代码和 PR #39

```powershell
git status --short --branch
git fetch origin
gh pr view 39 --repo reshihihihi/faa-chart-to-424-benchmark
```

确认 PR #39 或其等价 commit 已包含：

```text
scripts/score_final_v2_sft_outputs.py
final-v2 comparison_policy_v2.jsonl
final-v2 cleanup report
```

### Step 2: 准备 Dataverse final-v2 artifact package

下载或挂载 Dataverse final-v2 release/artifact package。

检查：

```text
artifact manifest 存在
formal300 images 存在
formal300 final-v2 targets 存在
formal300 split 50+200+50 存在
corrected SFT train500/dev100 存在
hash 与 manifest 一致
```

### Step 3: 写本地路径配置

本地路径配置只保存在 `local_paths.local.json` 或等价本地文件中，不提交 Git。

至少需要：

```text
repo_root
dataset_root
formal_images_dir
formal_targets_dir
formal_split_file
final_v2_policy_path
base_vlm_model_dir
d1_50_output_root
d1_500_output_root
dbase_output_root
reports_dir
```

### Step 4: 数据审计

对 corrected D1-500 train/dev 执行：

```text
JSONL parse
assistant JSON parse
schema validation
final-v2 no-unknown validation
field legality validation
image existence check
leakage check
hash generation
```

产物：

```text
reports/group1_d_final_v2_data_audit_zh_20260506.md
training/d_sft/manifests/d1_final_v2_train500_dev100_manifest.json
training/d_sft/manifests/d1_final_v2_subset50_seed260506_manifest.json
```

### Step 5: 生成 D1-50 子集

从 corrected D1-500 train 中固定 seed 抽样 50 条。

记录：

```text
seed
chart_id 列表
source train500 hash
subset JSONL hash
```

### Step 6: 冻结 prompt 和 policy

新建或确认：

```text
training/d_sft/prompts/d_sft_image_to_canonical.final_v2.md
training/d_sft/manifests/d_sft_final_v2_output_policy.json
```

记录 hash，并确保 D-base、D1-50、D1-500 共用。

### Step 7: D-base final-v2 推理与评分

先跑 smoke5。若 parse/schema failure 不是由模型自然失败导致，而是路径、prompt、脚本错误，先修流程。

smoke 通过后跑 formal200，并用 PR #39 scorer 评分。

### Step 8: D1-50 训练、推理、评分

训练 50 条版本。

先 dev100 检查：

```text
loss 是否正常
输出是否可 parse
unknown 输出数量
schema failure 数量
```

再跑 smoke5 和 formal200。

### Step 9: D1-500 训练、推理、评分

训练 500 条版本。

流程与 D1-50 完全一致，只更换训练 JSONL 和 run id。

### Step 10: 汇总报告

最终输出：

```text
reports/group1_d_final_v2_experiment_results_zh_20260506.md
reports/group1_d_final_v2_score_table_20260506.csv
reports/group1_d_final_v2_error_audit_zh_20260506.md
```

报告应说明：

```text
D-base、D1-50、D1-500 分别是什么
训练数据从哪里来
final-v2 JSON 改了什么
评分使用什么 target/scorer/policy
每个方法的分数和 CI
每个方法的 parse/schema/unknown failure
是否有代码改动
哪些文件提交 Git，哪些文件只在本地或 artifact storage
```

## 14. 风险和注意事项

1. 不要把旧 D1 分数和 final-v2 分数混在同一张最终表格里。
2. 不要只改 scorer，不改训练 label。D1 final-v2 必须重新训练。
3. 不要让 D1-50 使用不同数据来源后仍声称只比较训练数量。
4. 不要在推理阶段读取 target、score、424/CIFP 或其他方法预测。
5. 不要把模型输出失败样本删除后再评分。
6. 不要把 missing、parse failed、schema invalid 样本从 denominator 中移除。
7. 不要把 `not_applicable` 当 wildcard。
8. 不要把 `unknown` 当正式 target 或输出默认值。
9. 不要把 Dataverse preview token、local paths、checkpoint、raw outputs 提交到 Git。
10. 所有 final-v2 数据和 policy 都要有 hash/provenance，避免后续无法复现。

## 15. 最终一句话定义

实验组 1 D 系列 final-v2 补充实验是：使用 PR #39 和 Dataverse final-v2 artifact package 中统一后的字段合法性与评分口径，重新定义 D-base、D1-50、D1-500。三者都输入完整航图并输出 final-v2 canonical JSON；D-base 不训练，D1-50 和 D1-500 使用同一套脚本分别训练 50 条和 500 条 corrected SFT 样本；最终全部用 PR #39 的 final-v2 scorer 在 formal200 evaluation split 上评分。
