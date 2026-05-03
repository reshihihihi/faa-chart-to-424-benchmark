# 实验组 1 新增 SFT 方法详细实验计划与当前状态

本文记录实验组 1 在既有方法之外新增 SFT 方法的实验方案、训练集来源、输入输出、当前已完成工作、发现的问题、下一步计划，以及给下一轮 Codex 对话的执行指令。

本文只记录可复现实验定义和执行状态，不记录本地绝对路径、后台访问 token、模型权重、checkpoint、图片、raw outputs 或大结果文件。

## 1. 实验目标

实验组 1 原目标是从 FAA missed-approach 航图抽取可评分的 missed approach 语义 JSON。新增 SFT 内容的目标不是替代既有 D1/D_SFT formal200 结果，而是在已有实验组 1 基础上增加三类 SFT 相关方法，验证：

1. 人工标注中的“框到航段、框到字段”的信息能否转成 SFT 训练集。
2. 模型能否从完整航图生成结构化图上证据记录。
3. 模型能否从图上证据记录生成 missed approach 问卷式语义 JSON。
4. 自动两阶段链路能否从完整航图端到端输出可评分 JSON。

这些新增方法必须继续遵守实验组 1 的防泄漏边界：推理阶段不能读取 target JSON、score、raw 424/CIFP 或其他方法预测；`scoring_manifest.jsonl` 只能在预测完成后用于评分。

## 2. 数据划分

实验组 1 的 300 张正式图片已经固定为：

1. 第一个 50 张：development split，用于开发、训练和 checkpoint 选择。
2. 中间 200 张：formal evaluation split，用于正式评估。
3. 最后 50 张：probe / holdout，本轮新增 SFT 不使用。

新增 SFT 的训练只使用第一个 50 张 development split，并在脚本内固定切成：

1. 40 张训练样本。
2. 10 张验证样本。

formal evaluation 的 200 张只生成无答案评估输入。评估输入中不能包含 `canonical_answer`、target、score、raw 424/CIFP 或其他方法预测。

## 3. 标注数据来源和可用信息

训练 JSONL 来自后台标注导出的 JSON 文件。该导出文件本身不提交到 Git。

导出文件需要包含以下信息：

1. 每张图的 `chart_id`、图片关联信息和标注状态。
2. `regions`：图上框列表，包括框类型、坐标、文字、人工确认状态等。
3. `regions[].accepted_mappings`：每个被确认框对应到哪个 missed approach 航段、哪个字段、字段值是什么。
4. `field_reviews`：每个航段字段的人工复核信息，包括字段名、航段编号、证据框 id、支持方式和训练标签。

新增脚本会从这些内容构造两类训练集：

1. 完整航图到图上证据记录。
2. 图上证据记录到问卷式语义 JSON。

## 4. 方法列表

### 4.1 同底座未微调对照：`D_BASE_SAME_BACKBONE`

目的：确认同一个 Qwen2-VL 底座模型在不加载 LoRA 的情况下，直接从完整航图输出 missed approach JSON 的能力。

输入：

1. 完整航图图片。
2. 冻结的 D_SFT 图像到 canonical JSON prompt。
3. 输出 schema。

输出：

1. strict JSON。
2. schema validation report。
3. 预测完成后再用 scoring manifest 评分。

训练：不训练。

定位：对照方法，不是新增 SFT 方法。

### 4.2 已有 D1 / D_SFT 基线

目的：复用之前实验组 1 已完成的 formal200 D_SFT 基线，作为新增 SFT 方法的主要对照。

输入：

1. 完整航图图片。
2. D_SFT frozen prompt。
3. 已有 D_SFT LoRA checkpoint。

输出：

1. canonical missed approach JSON。
2. strict schema validation。
3. 预测完成后评分。

训练：已经在之前实验中完成，不在本轮新增 SFT 中重新训练。

已有 formal200 结果：

1. 方法名：`D_SFT`。
2. formal200 可评分样本：184 / 200。
3. parse/schema failure：16。
4. 分数：2739 / 3724 = 0.735499462943072。

注意：后续不要再重跑 D1/D_SFT formal200，除非明确要做复现实验。新增 SFT 的重点是新增三种方法。

### 4.3 完整航图到图上证据记录：`CHART_TO_EVIDENCE_SFT`

目的：训练模型从完整航图图片直接输出图上证据记录。这个方法本身不直接输出最终 missed approach canonical JSON，因此不直接参与最终字段评分。

训练输入：

1. 完整航图图片。
2. `training/group1_sft/prompts/chart_to_evidence.zh.md`。

训练标签：

1. 从 development 50 的后台标注导出中生成。
2. 标签包含图上证据项，包括 `source_region`、`item_type`、`text`、`value`、`bbox`、`confidence`、`notes`。
3. `value.linked_fields` 保留框对应的航段编号、字段名、字段值、leg type 和证据角色。

推理输入：

1. formal evaluation 图像。
2. 同一 prompt。
3. 不读取任何 target 或评分内容。

推理输出：

1. evidence record JSON。
2. schema validation result。

当前 smoke5 结果：

1. 5 条样本。
2. failure count：4。
3. 主要问题：输出 evidence JSON 的 schema 不稳定，包含 schema validation 和 parse failure。

当前结论：第一阶段图像到证据记录还没达到可全量运行标准，是自动两阶段方法的主要瓶颈。

### 4.4 人工确认证据到语义问卷：`EVIDENCE_TO_SEMANTICS_SFT`

目的：验证如果已经拥有人工确认的图上证据记录，模型能否把证据转换为 missed approach 问卷式语义 JSON。

训练输入：

1. 人工确认的 evidence bundle。
2. `training/group1_sft/prompts/evidence_to_questionnaire.zh.md`。

训练标签：

1. 从 `field_reviews[].canonical_answer` 生成。
2. 每个航段包含以下字段：
   - `Q_terminator`
   - `Q1_fix_ident`
   - `Q2_altitude_constraint`
   - `Q3_turn`
   - `Q4_course_or_radial`
   - `Q5_hold_params`

推理输入：

1. formal evaluation 的人工确认证据 bundle。
2. 不输入图片。
3. 不输入 target JSON、score、raw 424/CIFP 或其他方法预测。

推理输出：

1. 问卷式语义 JSON。
2. 转换为 canonical JSON 后评分。

重要定位：这是 diagnostic / oracle second-stage 方法，因为推理时使用人工确认的图上证据记录。它不能和端到端方法直接公平排名，只能作为第二阶段能力上界或诊断实验。

当前修正：

1. 初始版本的 evidence bundle 过长，导致训练验证时 4096 token 截断后标签被截没。
2. 已在 commit `2293a2e` 中压缩第二阶段输入，只保留有 accepted mapping 的证据项，并保留核心“框到航段、框到字段”关系。
3. 压缩后 tokenizer 检查通过，最长 dev 样本低于 4096 token。

当前 smoke5 结果：

1. 5 条样本。
2. 3 条可评分。
3. failure count：2。
4. 分数：3 / 57 = 0.05263157894736842。

当前结论：第二阶段已能跑通一部分，但准确率很低，说明训练标签和输出 schema 对齐仍需改进。

### 4.5 自动两阶段：`TWO_STAGE_AUTO_SFT`

目的：构建完整自动链路：

1. 第一阶段：完整航图图片 -> 图上证据记录。
2. 第二阶段：自动生成的图上证据记录 -> 问卷式语义 JSON。
3. 最后转换为 canonical JSON 并评分。

推理输入：

1. 完整航图图片。
2. 第一阶段 prompt。
3. 第二阶段 prompt。
4. 两个 SFT checkpoint。

推理阶段禁止输入：

1. 人工确认证据。
2. target JSON。
3. raw 424/CIFP。
4. score。
5. 其他方法预测。

当前 smoke5 结果：

1. 5 条样本。
2. 0 条可评分。
3. failure count：5。
4. 失败主要来自第一阶段 evidence JSON schema validation / parse，另有第二阶段 schema failure。

当前结论：自动两阶段暂时不能进入 formal200，必须先修第一阶段 evidence JSON 稳定性。

## 5. 已新增和提交的代码

已提交到分支 `group1-sft-extension-plan-20260503`：

1. `41b04c1 Add group1 SFT extension training and runners`

   新增训练数据转换、SFT 训练脚本、文本推理脚本、自动两阶段 runner，并更新 run package 生成逻辑。

2. `2293a2e Compact group1 semantics evidence inputs`

   压缩第二阶段 evidence bundle，避免训练时标签被截断。

关键新增脚本：

1. `scripts/group1_sft/build_group1_sft_training_jsonl_from_annotations.py`
2. `scripts/group1_sft/train_qwen2vl_group1_sft_lora.py`
3. `scripts/group1_sft/run_qwen2vl_group1_sft_text_inference.py`
4. `scripts/group1_sft/run_group1_sft_two_stage_auto.py`

关键更新脚本：

1. `scripts/group1_sft/prepare_group1_sft_run_package.py`
2. `scripts/group1_sft/run_qwen2vl_group1_sft_inference.py`
3. `training/group1_sft/configs/local_paths.template.json`

## 6. 本轮已经完成的实验执行

已完成：

1. 从后台标注导出生成训练 JSONL、dev JSONL 和 formal200 eval JSONL。
2. 检查生成结果：
   - `ready = true`
   - `schema_error_count = 0`
   - `eval_input_violation_count = 0`
   - `train_count = 40`
   - `dev_count = 10`
   - `eval_count = 200`
3. 训练 `CHART_TO_EVIDENCE_SFT`：
   - 40 train / 10 dev
   - 1 epoch
   - best dev loss: 0.8321933746337891
4. 训练 `EVIDENCE_TO_SEMANTICS_SFT`：
   - 40 train / 10 dev
   - 1 epoch
   - best dev loss: 0.10848832949995994
5. 生成 `group1_sft_smoke5` run package。
6. preflight blocker 数量为 0。
7. 跑完新增三种方法的 5 条 smoke。
8. 确认已有 formal200 D_SFT 基线结果，不再重跑 D1/D_SFT。

## 7. smoke5 结果汇总

`group1_sft_smoke5` 使用 5 条样本，仅用于检查方法是否能跑通，不代表正式性能。

| 方法 | 样本数 | 可评分 | failure | score |
|---|---:|---:|---:|---:|
| `D_BASE_SAME_BACKBONE` | 5 | 0 | 5 | 不可评分 |
| `D1` smoke | 5 | 4 | 1 | 54 / 82 = 0.6585365853658537 |
| `CHART_TO_EVIDENCE_SFT` | 5 | 不直接评分 | 4 | 不直接评分 |
| `EVIDENCE_TO_SEMANTICS_SFT` | 5 | 3 | 2 | 3 / 57 = 0.05263157894736842 |
| `TWO_STAGE_AUTO_SFT` | 5 | 0 | 5 | 不可评分 |

已有 formal200 D_SFT 基线：

| 方法 | 样本数 | 可评分 | parse/schema failure | score |
|---|---:|---:|---:|---:|
| `D_SFT` | 200 | 184 | 16 | 2739 / 3724 = 0.735499462943072 |

## 8. 当前主要问题

### 8.1 第一阶段 evidence JSON 不稳定

`CHART_TO_EVIDENCE_SFT` 在 smoke5 中 4/5 失败，主要是 schema validation / parse 问题。这会直接导致 `TWO_STAGE_AUTO_SFT` 失败。

可能原因：

1. 训练样本只有 40 条，证据记录 schema 较复杂。
2. 标签中 `value`、`notes`、`bbox` 等字段可变性较高。
3. prompt 对 evidence schema 的字段约束不够强。
4. 当前严格 JSON policy 不允许 repair，模型轻微格式错误也会失败。

### 8.2 第二阶段准确率很低

`EVIDENCE_TO_SEMANTICS_SFT` 虽然能跑出 3 条可评分结果，但分数只有 3 / 57。

可能原因：

1. 问卷式输出 schema 和训练标签仍然需要更强约束。
2. 字段值的规范化规则没有完全进入训练或 prompt。
3. 部分字段是 rule_default_completion，不完全来自可见图上证据，模型难以泛化。
4. 40 条训练样本不足以稳定学习多 leg、多字段结构。

### 8.3 自动两阶段不能直接进入 formal200

`TWO_STAGE_AUTO_SFT` smoke5 0/5 可评分，主要卡在第一阶段。因此现在直接跑 formal200 会浪费 GPU，并产生大量不可评分结果。

## 9. 下一步建议

下一步不应该直接跑新增 SFT 的 formal200。建议先做一个小修复循环：

1. 固定第一阶段 evidence record 输出格式。

   重点检查 `CHART_TO_EVIDENCE_SFT` 的 raw outputs 和 schema failures，找出常见错误，例如：
   - `notes` 输出成数组而不是 string/null。
   - `value` 类型不一致。
   - JSON 未闭合。
   - 多余字段。

2. 修改 prompt 或训练标签，而不是引入未注册语义 repair。

   首选：
   - 简化 evidence schema。
   - 在 prompt 中明确字段类型。
   - 在训练标签中减少容易漂移的自由文本字段。

   谨慎：
   - 如果要加 parser normalization，只能是预注册的机械规范化，不能根据 target 或 score 修输出。

3. 重新生成训练 JSONL。

4. 重新训练至少 `CHART_TO_EVIDENCE_SFT`。

5. 重新跑 `group1_sft_smoke5`。

6. 只有当以下条件满足时，才进入 formal200：
   - `CHART_TO_EVIDENCE_SFT` smoke5 schema failure 明显下降。
   - `TWO_STAGE_AUTO_SFT` smoke5 至少能产生可评分样本。
   - `EVIDENCE_TO_SEMANTICS_SFT` schema failure 不再是主要问题。

## 10. 全量 formal200 计划

当 smoke 修复通过后，formal200 应该一次性生成同一 run package，然后统一跑新增方法，而不是一个方法一套 split。

推荐 formal200 方法集合：

1. `D_BASE_SAME_BACKBONE`：可选对照，如果已有足够对照结果，可不重复跑。
2. `D_SFT` / D1：复用已有 formal200 基线，不重跑。
3. `CHART_TO_EVIDENCE_SFT`：诊断第一阶段质量，不直接评分。
4. `EVIDENCE_TO_SEMANTICS_SFT`：人工确认证据的 diagnostic/oracle second-stage，不和端到端方法直接公平排名。
5. `TWO_STAGE_AUTO_SFT`：真正新增的端到端自动两阶段 SFT 方法。

formal200 最终报告必须分别报告：

1. 每个方法的 sample count。
2. parse/schema failure count。
3. 可评分样本数。
4. score correct / total / accuracy。
5. 是否使用人工确认证据。
6. 是否为端到端方法。
7. 使用的 commit hash、prompt hash、schema hash、checkpoint run id。

## 11. 下一个对话可以直接使用的指令

下面这段可以直接复制给下一个 Codex 对话：

```text
请继续实验组 1 新增 SFT 方法的修复和 smoke 验证。

仓库：
https://github.com/reshihihihi/faa-chart-to-424-benchmark.git

分支：
group1-sft-extension-plan-20260503

先执行：
1. git status --short --branch
2. git pull
3. git rev-parse HEAD

请先阅读：
docs/group1_sft_extension_experiment_plan_zh_20260503.md

当前已知状态：
1. 新增 SFT 代码已提交，最新关键 commit 是 2293a2e。
2. 后台标注导出已经能生成训练 JSONL，ready=true、schema_error_count=0、eval_input_violation_count=0。
3. CHART_TO_EVIDENCE_SFT 已训练完成，但 smoke5 里 4/5 schema 或 parse 失败。
4. EVIDENCE_TO_SEMANTICS_SFT 已训练完成，smoke5 里 3/5 可评分，分数 3/57=0.0526。
5. TWO_STAGE_AUTO_SFT smoke5 里 0/5 可评分，主要被第一阶段 evidence JSON 失败卡住。
6. D1 在之前实验组 1 formal200 里已经作为 D_SFT 跑完，不要重跑 D1 formal200。已有 formal200 D_SFT 结果是 184/200 可评分，2739/3724=0.7355，parse/schema failure=16。

严格要求：
1. 不要提交 local_paths.local.json、模型、checkpoint、PNG、raw outputs、大结果。
2. 推理阶段禁止读取 target JSON、score、raw 424/CIFP、其他方法预测。
3. scoring_manifest 只能在预测完成后用于评分。
4. run package 必须优先使用 scoring_equivalence_v2 target 和 comparison_policy_v2。
5. 不要直接跑新增 SFT formal200；先修 smoke。
6. 不要重跑已有 D1/D_SFT formal200，除非我明确要求复现实验。

下一步任务：
1. 打开 group1_sft_smoke5 的 CHART_TO_EVIDENCE_SFT summary_report.json、raw_text、parsed_json、validation，统计第一阶段 evidence JSON 失败类型。
2. 根据失败类型优先修 prompt 或训练标签生成逻辑，让 evidence record 输出更稳定。
3. 如果修改训练数据生成逻辑，重新生成 JSONL，并确认 eval_input_violation_count=0。
4. 重新训练 CHART_TO_EVIDENCE_SFT，必要时也重新训练 EVIDENCE_TO_SEMANTICS_SFT。
5. 重新生成 group1_sft_smoke5 run package。
6. 只重跑新增 SFT 方法：CHART_TO_EVIDENCE_SFT、EVIDENCE_TO_SEMANTICS_SFT、TWO_STAGE_AUTO_SFT。
7. 最后汇报 smoke5 的 schema failure、parse failure、可评分样本数、score，以及是否可以进入 formal200。

请边做边说明你看到的问题，不要跳过诊断直接全量跑。
```

