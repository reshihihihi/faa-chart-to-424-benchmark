# 实验组 1 新增 SFT 方法远程继续执行说明

本文用于把实验组 1 新增的 SFT 方法迁移到另一台有模型、GPU、图片和后台标注导出文件的电脑继续执行。Git 只同步代码、模板和说明；本地路径配置、模型、checkpoint、图片、raw outputs 和大结果文件不能提交到 Git。

## 当前新增内容

本次新增或补齐的是实验组 1 的三类 SFT 相关方法支持：

1. `CHART_TO_EVIDENCE_SFT`

   输入是完整航图图片。模型输出人工标注格式的图上证据记录，包括框、框类型、可见文字、框对应的航段和字段链接。训练标签来自发展集 50 张中的人工标注记录。

2. `EVIDENCE_TO_SEMANTICS_SFT`

   输入是人工确认的图上证据记录，不输入图片。模型输出固定问卷式语义 JSON。这个方法是诊断性质的第二阶段上界实验，因为它使用人工确认的证据记录，不能和端到端方法直接公平排名。

3. `TWO_STAGE_AUTO_SFT`

   输入是完整航图图片。第一阶段用 `CHART_TO_EVIDENCE_SFT` 自动生成图上证据记录，第二阶段用 `EVIDENCE_TO_SEMANTICS_SFT` 把自动证据记录转成固定问卷式语义 JSON。推理时只能使用第一阶段自动生成的证据，不能使用人工答案、target JSON、score、raw 424/CIFP 或其他方法预测。

同时保留两个对照：

1. `D_BASE_SAME_BACKBONE`：同一底座模型，不加载 LoRA，用完整航图直接预测固定格式 JSON。
2. `D1`：复跑已有 D1 checkpoint，用同一 run package 和同一评分入口。

## 训练集来源

训练数据来自实验组 1 的第一个 50 张发展集。脚本会按固定规则切成：

1. 40 张训练
2. 10 张验证
3. formal evaluation 的 200 张只生成无答案评估输入

后台标注导出文件中需要包含：

1. 每张图的框列表
2. 每个框的类型、坐标、文字或说明
3. `accepted_mappings` 中的框到航段、字段、值的对应关系
4. `field_reviews` 中的字段到证据框对应关系和训练标签

不要把后台导出文件、后台地址、token 或本地绝对路径提交到 Git。

## 另一台电脑执行顺序

1. 拉取分支

```powershell
git clone https://github.com/reshihihihi/faa-chart-to-424-benchmark.git
cd faa-chart-to-424-benchmark
git switch group1-sft-extension-plan-20260503
git pull
```

2. 确认关键脚本和 schema 存在

```powershell
Test-Path scripts\group1_sft\build_group1_sft_training_jsonl_from_annotations.py
Test-Path scripts\group1_sft\train_qwen2vl_group1_sft_lora.py
Test-Path scripts\group1_sft\run_qwen2vl_group1_sft_text_inference.py
Test-Path scripts\group1_sft\run_group1_sft_two_stage_auto.py
Test-Path training\group1_sft\manifests\evidence_record.schema.json
Test-Path training\group1_sft\manifests\evidence_questionnaire.schema.json
```

3. 创建本地路径配置

```powershell
Copy-Item training\group1_sft\configs\local_paths.template.json training\group1_sft\configs\local_paths.local.json
```

编辑 `training\group1_sft\configs\local_paths.local.json`，至少填入：

```text
repo_root
formal_manifest
formal_images_dir
canonical_targets_dir
group1_formal_split
group1_formal_scoring_manifest
base_vlm_model_dir
d1_lora_or_checkpoint_dir
output_root
reports_dir
chart_to_evidence_train_jsonl
chart_to_evidence_dev_jsonl
chart_to_evidence_eval_jsonl
evidence_to_semantics_train_jsonl
evidence_to_semantics_dev_jsonl
evidence_to_semantics_eval_jsonl
```

4. 从后台标注导出文件生成训练和评估 JSONL

```powershell
python scripts\group1_sft\build_group1_sft_training_jsonl_from_annotations.py `
  --export-json <ANNOTATION_EXPORT_JSON> `
  --paths training\group1_sft\configs\local_paths.local.json
```

成功标准：

```text
ready = true
schema_error_count = 0
eval_input_violation_count = 0
train_count = 40
dev_count = 10
eval_count = 200
```

5. 验证 workspace

```powershell
python scripts\group1_sft\validate_group1_sft_workspace.py --paths training\group1_sft\configs\local_paths.local.json
```

6. 训练两个 SFT checkpoint

```powershell
python scripts\group1_sft\train_qwen2vl_group1_sft_lora.py `
  --method CHART_TO_EVIDENCE_SFT `
  --paths training\group1_sft\configs\local_paths.local.json `
  --run-id chart_to_evidence_sft_dev50_with_field_links_20260503_r1 `
  --epochs 1
```

```powershell
python scripts\group1_sft\train_qwen2vl_group1_sft_lora.py `
  --method EVIDENCE_TO_SEMANTICS_SFT `
  --paths training\group1_sft\configs\local_paths.local.json `
  --run-id evidence_to_semantics_sft_dev50_with_field_links_20260503_r1 `
  --epochs 1
```

训练完成后，把 `local_paths.local.json` 中这两个字段指向对应的 `checkpoint-final`：

```text
chart_to_evidence_lora_or_checkpoint_dir
evidence_to_semantics_lora_or_checkpoint_dir
```

7. 先生成 5 条 smoke run package

```powershell
python scripts\group1_sft\prepare_group1_sft_run_package.py `
  --paths training\group1_sft\configs\local_paths.local.json `
  --limit 5 `
  --run-id group1_sft_smoke5
```

打开生成目录中的：

```text
reports/preflight_report_zh.md
RUN_COMMANDS.md
```

如果 blocker 不为 0，只修路径或缺文件，不改实验定义。

8. blocker 清零后按同一个 `RUN_COMMANDS.md` 跑五种方法

建议顺序：

```text
D_BASE_SAME_BACKBONE
D1
CHART_TO_EVIDENCE_SFT
EVIDENCE_TO_SEMANTICS_SFT
TWO_STAGE_AUTO_SFT
```

所有方法都先只跑 5 条 smoke。smoke 通过后，再生成 formal200 的 run package 并统一跑全量。

## 必须遵守的边界

1. 推理阶段禁止读取 target JSON、score、raw 424/CIFP、其他方法预测。
2. `scoring_manifest.jsonl` 只能在预测完成后用于评分。
3. run package 必须优先使用 `scoring_equivalence_v2` target 和 `comparison_policy_v2`。
4. 不提交 `local_paths.local.json`、模型、checkpoint、PNG、raw outputs 或大结果。
5. `EVIDENCE_TO_SEMANTICS_SFT` 必须报告为使用人工确认证据记录的诊断/上界第二阶段实验。
