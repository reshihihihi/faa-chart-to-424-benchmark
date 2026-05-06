# 实验组1 D1-50 final-v2 smoke 诊断记录

日期：2026-05-06

关联分支：`codex/group1-d-final-v2-d1-50-20260506`

关联代码提交：`5d58caa91 Add pure final-v2 D-SFT inference runner`

## 目的

本记录只保存 D1-50 final-v2 在本机完成训练后的 smoke 诊断结论，不保存本地路径、模型权重、checkpoint、PNG、raw output 或大结果文件。

D1-50 final-v2 的实验定义是：输入完整航图图片和 final-v2 D prompt，输出 missed approach canonical JSON。训练标签来自原 D-SFT train/dev JSONL 中的 CIFP/424 canonical proxy label，并按 PR #39 的 final-v2 字段合法性要求做转换：不再允许 `unknown`，DF direct 不再放在 `Q4_course_or_radial={"type":"direct"}`，未限制左右转的 CF/DF 转为 `Q3_turn=BOTH`。

## 已完成内容

已经生成 final-v2 训练 JSONL：

- `train500`：500 条，sha256 `836dcf2390b1a151068be59f9d99c4f37f32d6bc8759f940555131c8fc455baf`
- `dev100`：100 条，sha256 `2c457bb90d53fa783b619eb76ca035f9c8bdd8f1b6a4720ac4df2dffd78a8ef0`
- `train50`：50 条，seed `260506`，sha256 `fd9106f5850dd91aaeedd142e4b7e8ddd90df17cc771fb5597186838e55cfd62`

已经完成 D1-50 final-v2 训练：

- run id：`d1_50_final_v2_qwen2vl_lora_20260506_r1`
- method id：`D1-50_FINAL_V2`
- base model：`Qwen/Qwen2-VL-2B-Instruct`
- train samples：50
- dev samples：100
- epochs：1
- global steps：50
- optimizer steps：7
- best dev loss：`0.19552553363144398`
- checkpoint adapter sha256：`439d0962ea650071bef1a6bd74d2a6852e60156155ec36eb3c395549fcaf3a96`

## smoke 结果

正式 formal200 的前 5 条 image-only smoke：

- run id：`d1_50_final_v2_smoke5_20260506_r1`
- samples：5
- parse ok：1
- final-v2 valid：1
- parse or final-v2 failures：4
- 失败类型：3 条没有形成完整 JSON 对象，1 条存在对象末尾前的非法尾逗号

训练集已见样本 5 条诊断：

- run id：`d1_50_final_v2_train_seen5_diag_20260506_r1`
- samples：5
- parse ok：2
- final-v2 valid：2
- parse or final-v2 failures：3
- 失败类型：2 条没有形成完整 JSON 对象，1 条存在对象末尾前的非法尾逗号

## 判断

训练 JSONL 与 final-v2 prompt 结构一致，标签本身是顶层 `chart_id`、`procedure`、`missed_approach` 三段式 JSON，且没有 `unknown`。smoke 失败不是因为训练标签仍是旧结构。

D1-50 在训练集已见样本上也未稳定输出可解析 final-v2 JSON，说明当前 `50 samples / 1 epoch / 7 optimizer steps` 的设定还没有让模型稳定学会输出格式。formal200 smoke 因此没有清零 blocker，不应在“先 smoke 再 full”的规则下直接进入正式 200 样本推理。

本次没有修改推理边界：推理阶段只读取完整航图图片和 final-v2 D prompt，没有读取 target JSON、score、raw CIFP、人类答案、其他方法预测或 comparison policy。当前 parser 仍然不做语义修复，也没有为了通过 smoke 去改写 raw output。

## 下一步

建议并行推进：

1. 另一台机器可以立即开始 D1-500 final-v2 训练。D1-500 使用同一套脚本、prompt、字段转换规则和推理 runner，只把训练 JSONL 从 `train50` 换成 `train500`，用于检验同一方法在 500 条训练样本下是否能稳定通过 smoke。
2. 本机保留当前 D1-50 r1 结果作为“严格同配置、仅 50 条训练样本”的 smoke 失败证据。不要静默增加 epoch 后仍称为同一个 D1-50 主结果。
3. 如果需要让 50 条样本版本也形成可评分 formal200 结果，应先明确新增一个单独变体，例如 D1-50 additional-epoch 版本，并在文档中声明它和 D1-500 的差异不仅是训练样本数，还包括重复训练轮数或总优化步数。
4. 不建议通过宽松 parser、补括号、去尾逗号、强制模板填充等方式把 D1-50 r1 转成可评分结果，除非先冻结为独立的 parser-repair policy；否则会改变方法定义并影响与 D-base、D1-500 的可比性。
