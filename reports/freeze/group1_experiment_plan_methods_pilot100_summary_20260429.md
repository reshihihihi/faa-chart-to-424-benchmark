# 实验组1试验方案、方法内容与 pilot100 结果汇总 - 2026-04-29

状态：**formal300 正式运行前审查材料**。本文档不是 formal300 正式结果。

## 1. 本文件目的

本文件用于随 PR 一起提交，集中说明实验组1的试验方案、各方法边界、当前候选实现，以及 100 张外部 pilot 样本的跑通结果。

pilot100 的作用是验证方法能否在非 formal300、非 pilot10 的外部样本上稳定运行，检查 schema-valid、parser repair、retry、scorer 和主要失败模式。它不能替代 formal300 正式实验，也不能作为论文正式主结果。

## 2. 实验组1总体方案

实验组1用于比较从 FAA 航图中抽取 missed approach 信息并输出 canonical JSON 的不同路径。所有方法最终都输出同一套 canonical schema，因此可以用同一个 validator/scorer 做 field-level 对比。

共同约束：

- 输出必须是 canonical JSON。
- 评分只能发生在推理结束之后。
- 推理阶段禁止访问 target JSON、score 文件、CIFP/ARINC 424 原始记录、人工答案或其他方法预测结果。
- 不允许根据分数选择性重跑。
- parser repair 默认禁止；若出现 API 传输故障，只能按预注册 rerun policy 处理。
- pilot100 结果只作为运行可行性证据，不作为 formal300 论文结果。

## 3. 方法内容与边界

| 方法 | 实验目的 | 输入 | 模型/规则 | 输出 | 禁止项 |
|---|---|---|---|---|---|
| A1 | 普通 OCR-1 + 规则系统 baseline | 完整航图图像，经 OCR-1 PaddleOCR PP-OCRv5 得到文本 | 确定性 rules | canonical JSON | LLM/VLM、target、score、CIFP、人工答案 |
| A2 | 替换 OCR 引擎后的规则系统 baseline | 完整航图图像，经 OCR-2 Tesseract 5.x 得到文本 | 与 A1 同一套确定性 rules | canonical JSON | LLM/VLM、target、score、CIFP、人工答案 |
| B1 | OCR 文本到 JSON 的 text LLM baseline | OCR-1 full-chart text | GPT-5.4 | canonical JSON | 图像像素、field_candidates、field_to_leg_links、target、score、CIFP |
| B1_prime | 加入 OCR 派生扁平字段候选 | OCR-1 text + field_candidates | GPT-5.4 | canonical JSON | 图像像素、gold/oracle linking、target、score、CIFP |
| B1_prime_link | 加入非 target-aware 的字段到航段候选链接 | OCR-1 text + field_candidates + field_to_leg_links | GPT-5.4 | canonical JSON | 图像像素、人工 linking、target-aware linking、target、score、CIFP |
| C1 | 图像直接到 JSON 的 VLM baseline | 完整航图图像 | Claude VLM | canonical JSON | OCR 文本、field_candidates、target、score、CIFP |
| C2 | 图像到 QA，再由确定性聚合器生成 JSON | 完整航图图像 | Claude VLM QA prompts + deterministic aggregator | QA JSON -> canonical JSON | OCR 文本、target、score、CIFP、人工答案 |
| C3 | 图像到问卷，再解析为 JSON | 完整航图图像 | Claude VLM questionnaire + deterministic parser | questionnaire JSON -> canonical JSON | OCR 文本、target、score、CIFP、人工答案 |
| C4 | 图像 + 普通 OCR 文本的多模态方法 | 完整航图图像 + OCR-1 text | Claude VLM | canonical JSON | target、score、CIFP、其他方法预测 |
| D-SFT | 训练后的图像到 JSON 方法 | 完整航图图像 | SFT VLM，当前候选为 Qwen2-VL-2B-Instruct QLoRA | canonical JSON | OCR 文本、field_candidates、target、score、CIFP、其他方法预测 |

## 4. 当前 pilot100 结果

下表中的 accuracy 是 field-level scorer 的 `correct / total`。它来自方法输出的 canonical JSON 与 pilot100 的 canonical proxy target 的字段级比较。

| 方法 | pilot100 schema-valid | parser repair | retry / 特殊情况 | field-level score | accuracy | 当前解释 |
|---|---:|---:|---|---:|---:|---|
| A1 | 100/100 | 0 | 0 | 741/2344 | 0.316126 | OCR-1 + rules 可稳定运行，结果作为规则 baseline。 |
| A2 | 100/100 | 0 | 0 | 521/2344 | 0.222270 | OCR-2 + 同一 rules 可稳定运行，低于 A1，符合 OCR 引擎对 baseline 的影响。 |
| B1 | 100/100 | 0 | schema retry 9 | 728/2344 | 0.310580 | OCR-1 text -> GPT-5.4 路径可跑通；retry 策略正式冻结前仍需最终确认。 |
| B1_prime | 100/100 | 0 | schema retry 11 | 674/2344 | 0.287543 | 可跑通，但在 pilot100 上低于 B1；field_candidates/matcher 不应因分数调 target-aware 规则。 |
| B1_prime_link | 100/100 | 0 | schema retry 1 | 1031/2344 | 0.439846 | 加入非 target-aware field-to-leg linking 后 pilot100 表现提升；仍是 candidate，需要审查方法边界。 |
| C1 | 99/100 | 0 | retry 7；KMCW_I36 360-degree schema failure | 902/2313 | 0.389970 | 图像直接 VLM 可运行；360 度 schema 边界需预注册处理。 |
| C2 | 100/100 | 0 | QA retry 9 | 457/2344 | 0.194966 | QA + 聚合器可运行，低分属于方法表现，不是格式 blocker。 |
| C3 | 99/100 | 0 | retry 5；KMCW_I36 360-degree schema failure | 874/2313 | 0.377864 | 问卷路径可运行；同样受 360-degree schema 边界影响。 |
| C4 | 100/100 | 0 | API 524 后按 policy 恢复；schema retry 0 | 1248/2344 | 0.532423 | 输出控制修正后 wrapper/retry 问题消除，是当前 pilot100 表现最强的非 SFT 方法。 |
| D-SFT | 94/100 | 0 | 6 个 parse/schema failure，未选择性修复 | 1014/2200 | 0.460909 | SFT 路径已训练并可运行，但 6 个失败样本计入结果，formal300 前仍需保留同一边界。 |

## 5. pilot100 样本与 formal300 的关系

pilot100 是外部可行性验证集，不属于 formal300，也不与 pilot10 重合。它用于提前发现流程、schema、runner、retry 和输出格式问题。

当前 B1/B1_prime pilot100 报告记录：

- sample count: 100
- unique chart_id: 100
- unique PDF: 100
- formal300 chart_id overlap: 0
- formal300 PDF overlap: 0
- pilot10 chart_id overlap: 0
- pilot10 PDF overlap: 0

因此 pilot100 可以作为运行可行性证据随 PR 提交，但不能作为 formal300 正式评测证据。

## 6. 关键已完成事项

- OCR 边界已纠正：OCR-1 为 PaddleOCR PP-OCRv5，OCR-2 为 Tesseract 5.x；不再把 Claude transcription 当作普通 OCR。
- B1/B1_prime 已完成 100 张外部样本验证。
- B1_prime_link 已纳入实验组1 candidate，并完成 pilot100 验证。
- C1/C2/C3/C4 已完成 C-family pilot100 证据汇总。
- C4 已完成 Anthropic tool transport 输出控制修正，API 恢复后 pilot100 schema-valid 100/100，schema retry 0。
- D-SFT 已完成 train/dev 数据准备、no-leakage 检查、训练、pilot100 可行性验证和冻结候选报告。
- formal300 manifest、checksum、field_targets、evidence_provenance、challenge_tags 等前置文件已生成用于审查。

## 7. 仍需审查或冻结的事项

- formal300 尚未正式运行。
- formal300 OCR-1/OCR-2 artifact 尚未作为正式输入冻结。
- formal300 有 300 个样本但 299 个 PDF，需要确认是正常 PDF 复用还是 materialization 缺口。
- B1_prime_link 是否正式作为实验组1 candidate 纳入，需要审查者确认。
- formal300 PNG/PDF/canonical_proxy_gt/raw CIFP 是否进入仓库，需要决定 Git、Git LFS、Release artifact 或外部 artifact 策略。
- model/provider/max_tokens/tool policy/retry policy 需要在 formal run manifest 中最终绑定。
- C1/C3 对 360-degree schema 边界的处理需要按 `configs/degree_360_policy.md` 预注册执行。

## 8. 本 PR 建议提交的配套证据

本文件应与以下材料一起提交：

- `reports/freeze/group1_pr_package_checklist_20260429.md`
- `reports/freeze/group1_pr_draft_body_20260429.md`
- `reports/freeze/group1_pr_package_file_manifest_20260429.json`
- `reports/freeze/group1_final_pr_submission_paths_20260429.txt`
- `reports/pilot/pilot100_b1_b1prime_expanded_validation_20260428.md`
- `reports/pilot/b1_prime_link_group1_candidate_pilot100_20260429.md`
- `reports/freeze/group1_c_methods_pilot100_evidence_20260429.md`
- `reports/pilot/c4_output_control_fix_pilot100_20260429.md`
- `training/d_sft/reports/d_sft_freeze_report_20260428_r1.md`

这些文件共同覆盖：实验方案、方法内容、pilot100 结果、冻结状态、已知问题和正式运行前 blocker。
