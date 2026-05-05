# 实验组1 PR 提交包清单 - 2026-04-29

状态：**供用户审阅的草稿，尚未提交 PR**

目的：准备一个用于 GitHub 审查的 PR 包，让学长/审查者在正式运行 formal300 之前检查实验组1的方法边界、冻结版本、无泄漏设计、scorer/validator、formal300 资产与 target，以及 pilot 证据。本 PR 不应包含 formal300 方法推理结果。

## PR 目标

- 让审查者先确认实验组1没有方法串组、输入泄漏或评测流程混淆。
- 透明记录已经做过的 pilot 结果、被降级为 debug 的历史结果，以及当前采用的候选版本。
- 在仓库策略明确前，不把大型原始 artifact、checkpoint、PDF/PNG 直接塞进普通 Git PR。
- 把 formal300 正式运行前还缺什么写清楚，避免后续直接跑正式实验时出现不可复现或不公平的问题。

## 当前方法摘要

| 方法 | 当前流程 | 状态 | pilot 证据 |
|---|---|---|---|
| A1 | 完整航图图像 -> OCR-1 PaddleOCR -> 确定性规则 -> canonical JSON | 候选/预冻结 | pilot100: 100/100 schema-valid，741/2344 = 0.3161 |
| A2 | 完整航图图像 -> OCR-2 Tesseract -> 同一套确定性规则 -> canonical JSON | 候选/预冻结 | pilot100: 100/100 schema-valid，521/2344 = 0.2223 |
| B1 | OCR-1 文本 -> GPT-5.4 -> canonical JSON | 候选/预冻结 | pilot100: 100/100 schema-valid，728/2344 = 0.3106 |
| B1_prime | OCR-1 文本 + field_candidates -> GPT-5.4 -> canonical JSON | 候选/预冻结 | pilot100: 100/100 schema-valid，674/2344 = 0.2875 |
| B1_prime_link | OCR-1 文本 + field_candidates + field_to_leg_links -> GPT-5.4 -> canonical JSON | 候选/预冻结 | pilot100: 100/100 schema-valid，1031/2344 = 0.4398 |
| C1 | 完整航图图像 -> Claude VLM -> canonical JSON | 候选/预冻结 | pilot100: 99/100 schema-valid，902/2313 = 0.3900 |
| C2 | 完整航图图像 -> Claude VLM QA prompts -> 确定性聚合器 -> canonical JSON | 候选/预冻结 | pilot100: 100/100 schema-valid，457/2344 = 0.1950 |
| C3 | 完整航图图像 -> Claude VLM questionnaire -> 确定性 parser -> canonical JSON | 候选/预冻结 | pilot100: 99/100 schema-valid，874/2313 = 0.3779 |
| C4 | 完整航图图像 + OCR-1 文本 -> Claude VLM -> canonical JSON | 候选/预冻结，已完成输出控制修正 | API 故障恢复后 pilot100: 100/100 schema-valid，1248/2344 = 0.5324，retry=0 |
| D_SFT | 完整航图图像 -> SFT VLM -> canonical JSON | 下一轮 formal300 评测的冻结候选 | pilot100: 94/100 schema-valid；已评分样本 1014/2200 = 0.4609 |

## 核心文件：建议提交或审查后提交

| 检查 | 文件/路径 | 建议动作 | 原因 |
|---|---|---|---|
| [x] | `docs/method_registry.md` | 提交 | 实验组1的方法边界总表，定义每个方法允许输入、禁止输入和最终输出类型。 |
| [x] | `docs/group1_method_boundary_audit_20260428.md` | 提交 | 实验组1方法边界审计，用于让审查者确认各方法没有串组或混用输入。 |
| [x] | `docs/group1_ocr_boundary_correction_20260428.md` | 提交 | 历史纠偏说明，解释为什么之前把 Claude 当 OCR 的结果只能降级为 debug 证据，不能作为正式 OCR 实验。 |
| [x] | `docs/formal_freeze_checklist.md` | 提交 | 正式评测前的冻结门槛清单。 |
| [x] | `docs/no_leakage_policy.md` | 提交 | 无泄漏约束，规定推理、target、scoring 必须隔离。 |
| [x] | `docs/rerun_policy.md` | 提交 | 重跑策略，区分允许的 API 故障恢复和禁止的按分数选择性重跑。 |
| [x] | `configs/group1_formal_freeze_manifest_20260429.json` | 提交 | 当前“未运行 formal300”的实验组1冻结 manifest，绑定资产、策略、模型、prompt 和 runner 计划。 |
| [x] | `configs/group1_freeze_candidate_manifest_20260429.json` | 提交 | 冻结候选 manifest，说明哪些已经可作为候选冻结，哪些仍有 blocker。 |
| [x] | `configs/frozen_experiment_manifest.json` | 审查后提交 | 已有全局冻结 manifest；如果本次改动已经与它同步，就可以一起提交审查。 |
| [x] | `configs/model_config_manifest.json` | 审查后提交 | 模型、provider、调用参数的候选登记表。 |
| [x] | `configs/ocr_source_manifest.json` | 提交 | OCR-1/OCR-2 来源定义，以及普通 OCR 边界纠偏。 |
| [x] | `configs/prompt_manifest.json` | 审查后提交 | prompt 路径和 hash 登记表。 |
| [x] | `configs/output_control_policy.md` | 提交 | 输出控制策略，包括 C4 的 Anthropic tool 传输层加固。 |
| [x] | `configs/parser_repair_policy.md` | 提交 | 严格 parser/no-repair 策略，说明正式实验中允许和禁止的格式处理。 |
| [x] | `configs/invalid_output_scoring_policy.md` | 提交 | parse/schema/API 失败在正式评分中的处理策略。 |
| [x] | `configs/degree_360_policy.md` | 提交 | 360 度航向这一 schema 边界情况的预注册处理策略。 |
| [x] | `configs/scorer_validator_manifest.json` | 提交 | scorer/validator 的版本和 hash manifest。 |
| [x] | `scripts/scorers/group1_canonical_field_scorer.py` | 提交 | 实验组1 field-level scorer/validator 候选实现。 |
| [x] | `scripts/prepare_group1_formal_run.py` | 提交 | 正式运行准备脚本，用于生成不含 formal300 推理结果的运行计划。 |
| [x] | `scripts/materialize_formal300_dataset.py` | 提交 | formal300 资产 materialization 脚本。 |
| [x] | `scripts/sync_formal300_annotation_images.py` | 提交 | formal300 标注图片对齐和同步脚本。 |
| [x] | `scripts/model_clients.py` | 提交 | 模型客户端层，包含 C4 Anthropic tool 传输层输出控制修正。 |
| [x] | `scripts/run_group1_pilot10_gpt54.py` | 审查后提交 | B/C 类方法使用过的 pilot runner，可作为 pilot 证据；它本身不等于正式 formal runner。 |
| [x] | `scripts/run_a1_a2_rules_pilot10.py` | 审查后提交 | A1/A2 规则系统候选 runner。 |
| [x] | `scripts/run_c2_qa_pilot10.py` | 审查后提交 | C2 QA prompt runner。 |
| [x] | `scripts/aggregate_c2_qa_candidate.py` | 审查后提交 | C2 确定性 QA 聚合器。 |
| [x] | `schemas/field_candidates.schema.candidate.json` | 提交 | B1_prime 的 field_candidates 候选 schema。 |
| [x] | `schemas/field_to_leg_links.schema.candidate.json` | 提交 | B1_prime_link 的 field-to-leg link 候选 schema。 |
| [x] | `schemas/c3_questionnaire.schema.candidate.json` | 提交 | C3 问卷中间结果候选 schema。 |
| [x] | `schemas/d_sft_manifest.schema.json` | 提交 | D-SFT manifest schema。 |
| [x] | `docs/b1_prime_link_method_card.md` | 提交 | B1_prime_link 方法卡。 |
| [x] | `docs/d_sft_method_card.md` | 提交 | D-SFT 方法卡，与当前训练候选版本对应。 |
| [x] | `docs/group1_a1_a2_rules_candidate_v1.md` | 提交 | A1/A2 规则系统候选方法细节。 |
| [x] | `docs/group1_c2_qa_aggregator_candidate_v1.md` | 提交 | C2 QA 聚合器候选方法细节。 |

## pilot / 冻结报告：建议提交

| 检查 | 文件/路径 | 建议动作 | 原因 |
|---|---|---|---|
| [x] | `reports/freeze/group1_formal_freeze_ready_no_eval_20260429.md` | 提交 | 当前“未运行 formal300”的冻结准备摘要。 |
| [x] | `reports/freeze/group1_formal_freeze_package_BLOCKED_20260429.md` | 审查后提交 | 较早的 blocked 版本；如保留历史，应标明已被当前 no-eval freeze package 替代。 |
| [x] | `reports/freeze/group1_freeze_readiness_audit_20260429.md` | 提交 | 冻结 readiness 审计。 |
| [x] | `reports/freeze/group1_runner_gap_audit_20260429.md` | 提交 | 正式 runner 缺口审计。 |
| [x] | `reports/freeze/group1_model_rerun_policy_audit_20260429.md` | 提交 | 模型和重跑策略审计。 |
| [x] | `reports/freeze/group1_c_methods_pilot100_evidence_20260429.md` | 提交 | C 系列方法 pilot100 证据汇总。 |
| [x] | `reports/freeze/c4_output_control_fix_20260429.md` | 提交 | C4 输出控制修正记录。 |
| [x] | `reports/pilot/c4_output_control_fix_pilot100_20260429.md` | 提交 | C4 输出控制修正后的 pilot100 验证报告。 |
| [x] | `reports/pilot/b1_prime_link_group1_candidate_pilot100_20260429.md` | 提交 | B1_prime_link pilot100 候选证据。 |
| [x] | `reports/pilot/pilot100_b1_b1prime_expanded_validation_20260428.md` | 提交 | B1/B1_prime 扩大到 pilot100 的验证证据。 |
| [x] | `reports/pilot/group1_prefreeze_final_optimization_20260429.md` | 提交 | 正式冻结前最后一轮优化摘要。 |
| [x] | `training/d_sft/reports/d_sft_freeze_report_20260428_r1.md` | 提交 | D-SFT 训练、冻结和 pilot100 可行性报告。 |

## formal300 manifest 与小型分析文件

| 检查 | 文件/路径 | 建议动作 | 原因 |
|---|---|---|---|
| [x] | `benchmark_exports/derived/v2/formal300/manifest.json` | 体积可接受则提交 | formal300 每个样本的 image/PDF/target hash 总 manifest。 |
| [x] | `benchmark_exports/derived/v2/formal300/sample_manifest.jsonl` | 提交 | formal300 样本 manifest，共 300 行。 |
| [x] | `benchmark_exports/derived/v2/formal300/splits.json` | 提交 | formal300 split 文件。 |
| [x] | `benchmark_exports/derived/v2/formal300/checksums.sha256` | 提交 | formal300 包的 checksum 文件。 |
| [x] | `benchmark_exports/derived/v2/formal300/challenge_tags.jsonl` | 提交 | 用于论文分析的 challenge tags。 |
| [x] | `benchmark_exports/derived/v2/formal300/targets/field_targets.jsonl` | 提交 | 用于 scoring/analysis 的字段级 target 导出。 |
| [x] | `benchmark_exports/derived/v2/formal300/targets/evidence_provenance.jsonl` | 提交 | target 来源证据导出，用于审计。 |
| [x] | `benchmark_exports/derived/v2/formal300/reports/formal300_materialization_report.json` | 提交 | formal300 materialization 报告。 |
| [x] | `benchmark_exports/derived/v2/formal300/reports/annotation_image_alignment_report.json` | 提交 | 标注图片对齐报告。 |

## 大文件、外部目录与敏感 artifact

| 检查 | 文件/路径 | 建议动作 | 原因 |
|---|---|---|---|
| [x] | `benchmark_exports/derived/v2/formal300/images/` | 优先使用 Git LFS、Release artifact 或只提交 manifest/hash | 300 张 PNG 图片；对 benchmark 有用，但普通 PR 中可能过大，是否提交取决于 Git LFS 或 release artifact 策略。 |
| [x] | `benchmark_exports/derived/v2/formal300/pdfs/` | 优先使用 Git LFS、Release artifact 或只提交 manifest/hash | 299 个 PDF 文件；普通 PR 中通常过大，建议用 manifest+hash 或 Git LFS/release artifact 管理。 |
| [x] | `benchmark_exports/derived/v2/formal300/targets/canonical_proxy_gt/` | 体积可接受则提交，否则只提交 manifest/hash | 300 个 canonical target JSON；文件可能不大，但它们是正式答案，是否随 PR 提交需要审查者决定。 |
| [x] | `benchmark_exports/derived/v2/formal300/targets/raw_cifp_per_procedure/` | 仓库策略允许则提交，否则只提交 manifest/hash | 每个 procedure 的 raw CIFP 记录，是答案/来源证据，不应被推理 runner 访问。 |
| [x] | `<external-artifact-root>/try_B1_B1_prime` | 不要提交原始大文件，只引用 manifest/报告 | B1/B1_prime pilot100 的图片、OCR、预测和 score 等大文件目录；建议只提交摘要和 manifest。 |
| [x] | `<external-artifact-root>/B1_prime_link` | 不要提交原始大文件，只引用 manifest/报告 | B1_prime_link pilot100 大文件目录；建议只提交摘要和报告。 |
| [x] | `<external-artifact-root>/d_sft` | 不要提交原始训练数据或 checkpoint，只提交报告、配置和 manifest | 包含训练数据、checkpoint 和日志，体积大，不应作为普通 PR 内容提交。 |

## 不应提交或需要先检查

| 检查 | 文件/路径 | 建议动作 | 原因 |
|---|---|---|---|
| [x] | `API tokens / ANTHROPIC_AUTH_TOKEN / OPENAI keys` | 绝对不要提交 | 密钥和凭证，绝对不能提交。 |
| [x] | `scripts/__pycache__/ and *.pyc` | 排除 | Python 生成的字节码文件，应排除。 |
| [x] | `predictions/pilot10_external/* raw run directories` | 只提交整理后的摘要 | 原始预测目录通常较大，除非特别要求，否则只提交整理后的摘要。 |
| [x] | `formal_runs/* predictions or future formal outputs` | 不包含 formal300 推理输出，因为本 PR 只做运行前审查 | 本 PR 的目的是真实运行前审查，所以不应包含 formal300 推理输出。 |
| [x] | `OpenAI` | 检查清楚前不要提交 | git status 中出现的未跟踪项，目的不清楚，检查前不要提交。 |

## 开 PR 前的未决问题

- [ ] formal300 的 PDF/PNG 是直接提交、使用 Git LFS，还是作为外部 artifact 并在仓库中只提交 manifest/hash。
- [ ] 300 个 canonical proxy target 是直接放入 PR，还是在正式审查前只提交 hash/manifest 并把答案文件放在受保护 artifact 中。
- [ ] 300 个样本对应 299 个 PDF 是正常的 PDF 复用，还是 materialization 缺口。
- [ ] 如果后续继续修改文件，在开 PR 前重新计算并核对所有 hash。
- [ ] 较早的 blocked 报告是作为历史保留，还是由当前 no-eval freeze package 替代。

## 建议请审查者重点看

- [ ] 实验组1的方法边界是否与 paper-v2 实验方案一致。
- [ ] B1_prime_link 是否应作为 B1_prime 之后的实验组1 candidate 纳入。
- [ ] formal300 的 PDF/PNG 应该提交到仓库、用 Git LFS 管理，还是只作为外部 artifact 引用。
- [ ] formal300 canonical proxy targets 是否适合直接进入 PR，还是只审查 target hash/manifest。
- [ ] invalid-output scoring policy 是否可以在 formal evaluation 前冻结。
- [ ] C4 输出控制修正是否可接受：只修传输层/tool schema，不做机械 unwrap，不改变方法输入。
- [ ] pilot100 证据是否足够支持进入 formal300 运行前审查。

## 配套生成文件

- `reports/freeze/group1_pr_package_file_manifest_20260429.json`
- `reports/freeze/group1_pr_draft_body_20260429.md`
