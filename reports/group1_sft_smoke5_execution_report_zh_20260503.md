# 实验组 1 SFT 扩展 5 条 smoke 执行报告

日期：2026-05-03

分支：`group1-sft-extension-plan-20260503`

当前 commit：`57d5c86e41f993a2c833d7309f0b9501d2f123d9`

## 本轮目标

本轮不是直接跑全量正式实验，而是先把实验组 1 增加的 SFT 方法跑通 5 条 smoke，确认：

- 五种方法都有可执行入口。
- 训练数据来自 50 条 development 样本，不使用 200 条 evaluation 和 50 条 probe 的答案。
- 推理输入不读取 target JSON、score、raw 424/CIFP、其他方法预测。
- `scoring_manifest.jsonl` 只在预测完成后用于评分。
- run package 优先使用 `scoring_equivalence_v2` target 和 `comparison_policy_v2`。

## 五种方法

| 方法 | 输入 | 输出 | 是否需要本轮新训练 | 作用 |
|---|---|---|---|---|
| `D_BASE_SAME_BACKBONE` | 完整航图图片 | canonical JSON | 否 | 同底座未微调对照，判断 D1 的提升是否来自 SFT |
| `D1` | 完整航图图片 | canonical JSON | 否，复用既有 D1 checkpoint | 当前端到端 SFT baseline |
| `CHART_TO_EVIDENCE_SFT` | 完整航图图片 | 图上证据记录 JSON | 是 | 先让模型从航图中找出复飞相关可见证据 |
| `EVIDENCE_TO_SEMANTICS_SFT` | 人工确认图上证据记录 | 复飞语义问卷 JSON，再确定性转成 canonical JSON 评分 | 是 | 诊断“证据已给定时，模型能不能组织语义” |
| `TWO_STAGE_AUTO_SFT` | 完整航图图片 | canonical JSON | 使用两个新 checkpoint | 第一阶段自动抽证据，第二阶段把自动证据转语义 |

## 已完成事项

1. 已确认仓库在目标分支，并已拉到最新 run-package 补丁。
2. 已确认四个要求文件存在：
   - `scripts/group1_sft/prepare_group1_sft_run_package.py`
   - `scripts/group1_sft/run_qwen2vl_group1_sft_inference.py`
   - `training/group1_sft/manifests/evidence_record.schema.json`
   - `training/group1_sft/manifests/evidence_questionnaire.schema.json`
3. 已创建并填写 `training/group1_sft/configs/local_paths.local.json`。
4. 已从标注导出生成 development 50 的训练 JSONL：
   - `chart_to_evidence_train.jsonl`：40 条
   - `chart_to_evidence_dev.jsonl`：10 条
   - `evidence_to_semantics_train.jsonl`：40 条
   - `evidence_to_semantics_dev.jsonl`：10 条
   - 两个 evaluation 输入 JSONL：各 200 条，无 assistant label
5. 已训练两个新增 SFT checkpoint：
   - `CHART_TO_EVIDENCE_SFT`：best dev loss `0.7538297712802887`
   - `EVIDENCE_TO_SEMANTICS_SFT`：best dev loss `0.4198920339345932`
6. 已重新生成 `group1_sft_smoke5` run package，preflight blocker 为 0。
7. 已完成五种方法的 5 条 smoke 推理。

## 5 条 smoke 结果

run package：`<group1_sft-artifact-root>\runs\group1_sft_smoke5`

preflight blocker 数量：`0`

| 方法 | summary_report.json | 可评分样本 | parse/schema failure | 分数 |
|---|---|---:|---:|---:|
| `D_BASE_SAME_BACKBONE` | `<group1_sft-artifact-root>\runs\group1_sft_smoke5\D_BASE_SAME_BACKBONE\summary_report.json` | 0/5 | 5 | 无可评分结果 |
| `D1` | `<group1_sft-artifact-root>\runs\group1_sft_smoke5\D1\summary_report.json` | 4/5 | 1 | `54/82 = 0.6585365853658537` |
| `CHART_TO_EVIDENCE_SFT` | `<group1_sft-artifact-root>\runs\group1_sft_smoke5\CHART_TO_EVIDENCE_SFT\summary_report.json` | 不直接评分 | 1 | 不直接产生 canonical 分数 |
| `EVIDENCE_TO_SEMANTICS_SFT` | `<group1_sft-artifact-root>\runs\group1_sft_smoke5\EVIDENCE_TO_SEMANTICS_SFT\summary_report.json` | 5/5 | 0 | `0/101 = 0.0` |
| `TWO_STAGE_AUTO_SFT` | `<group1_sft-artifact-root>\runs\group1_sft_smoke5\TWO_STAGE_AUTO_SFT\summary_report.json` | 4/5 | 1 | `0/82 = 0.0` |

## 失败类型

`D_BASE_SAME_BACKBONE` 的 5 个失败主要是裸底座输出不是严格 JSON 或缺 schema 字段，这符合未微调对照的预期风险。

`D1` 有 1 条 JSON parse failure：`KAMA_I04` 输出出现 `Extra data`。

`CHART_TO_EVIDENCE_SFT` 和 `TWO_STAGE_AUTO_SFT` 的失败都来自 `KAMA_I04` 的第一阶段证据 JSON：`evidence_items.0.notes` 输出成了数组，但 schema 要求 string 或 null。

`EVIDENCE_TO_SEMANTICS_SFT` 没有 parse/schema failure，但分数为 0。抽查 `KABE_I06` 后确认评分桥接不是主要问题，模型输出了 1 条 leg 且所有字段为 unknown，而目标是 3 条 leg 且有具体复飞语义。

## 当前关键问题

新增方法已经跑通，但现在不能直接进入全量正式实验，因为 `EVIDENCE_TO_SEMANTICS_SFT` 和 `TWO_STAGE_AUTO_SFT` 的语义分数为 0。

原因不是推理程序没跑通，而是第二阶段训练输入的信息量不足：当前由人工标注转出的 evidence record 主要包含区域框、region 类型和少量元素标签，很多关键文本是类似 `missed-approach text block` 的占位描述，不包含完整可见复飞文本。这样第二阶段模型在训练时没有学到“从真实复飞文本到 canonical 语义”的映射。

这也解释了为什么 `CHART_TO_EVIDENCE_SFT` 在 smoke 中能从图片读出实际复飞文本，但 `EVIDENCE_TO_SEMANTICS_SFT` 看到这类真实文本后仍然倾向输出 unknown：第二阶段训练时没见过足够的真实文本证据输入。

## 下一步建议

不要直接跑 200 条全量。先修第二阶段训练输入，再重新 5 条 smoke。

具体顺序：

1. 生成第二阶段训练用的“真实文本证据”输入。
   - 优先从人工标注系统导出中找是否存在人工录入的可见文本字段。
   - 如果没有，就在 development 50 上运行 `CHART_TO_EVIDENCE_SFT`，用它生成的图上证据记录作为第二阶段训练输入。
   - 只允许使用 development 50 的语义标签训练，不使用 evaluation 200 或 probe 50 的答案。
2. 用新的第二阶段训练 JSONL 重新训练 `EVIDENCE_TO_SEMANTICS_SFT`。
3. 重新跑 `EVIDENCE_TO_SEMANTICS_SFT` 和 `TWO_STAGE_AUTO_SFT` 的 5 条 smoke。
4. 如果第二阶段不再是 0 分，并且 parse/schema failure 可接受，再启动 200 条 evaluation 的五方法全量正式实验。

## 代码改动状态

本轮有代码改动，但没有提交 Git。

已新增或修改的代码主要用于：

- 从标注导出生成 Group 1 SFT 训练 JSONL。
- 训练 `CHART_TO_EVIDENCE_SFT` 和 `EVIDENCE_TO_SEMANTICS_SFT`。
- 运行文本型 `EVIDENCE_TO_SEMANTICS_SFT` 推理。
- 运行 `TWO_STAGE_AUTO_SFT` 两阶段自动流水线。
- 修正推理脚本的评分边界，使 `scoring_manifest.jsonl` 在预测完成后才读取用于评分。

未提交、也不应提交的本地内容：

- `training/group1_sft/configs/local_paths.local.json`
- 模型目录
- checkpoint
- PNG 图片
- raw outputs
- 大结果目录
