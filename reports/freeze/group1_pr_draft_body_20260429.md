# 准备实验组1 formal300 正式运行前审查包

## 摘要

这个 PR 用于准备实验组1的 formal300 正式评测前审查。它不包含 formal300 方法推理结果，也不代表已经开始正式实验。

本 PR 的主审查入口是：

- `reports/freeze/group1_experiment_plan_methods_pilot100_summary_20260429.md`

该总报告集中说明了实验组1试验方案、A1/A2/B1/B1_prime/B1_prime_link/C1/C2/C3/C4/D-SFT 的方法内容、输入边界、禁止项、pilot100 schema-valid、retry、score、已知问题和 formal300 前置 blocker。

## 本 PR 包含

- 实验组1 method registry 和方法边界审计；
- OCR 边界纠偏，以及 OCR-1/OCR-2 普通 OCR 来源定义；
- A1/A2/B1/B1_prime/B1_prime_link/C1/C2/C3/C4/D-SFT 的方法说明、prompt、schema、runner、scorer 和策略文件；
- B1/B1_prime/B1_prime_link/C1/C2/C3/C4/D-SFT 的 pilot100 结果，以及 A1/A2/B1 的 final pre-freeze recheck 结果；
- formal300 asset/target manifest、checksum、field_targets、evidence_provenance、challenge_tags 和 materialization/alignment reports；
- no-leakage、rerun、parser repair、invalid-output scoring、360-degree、output-control 等正式运行前策略；
- D-SFT 方法卡、冻结候选配置/报告，以及 pilot100 可行性结果；
- C4 输出控制修正证据：API 故障恢复后 pilot100 为 100/100 schema-valid，schema retry 为 0，且不做机械 unwrap。

## 不包含内容

- 不包含 formal300 方法推理输出。
- 不包含 formal300 正式 predictions/scores。
- 不包含 API token、密钥或凭证。
- 不直接提交大型原始 pilot artifact、原始预测、checkpoint、PDF/PNG。
- 不直接提交 formal300 `canonical_proxy_gt/` 或 raw CIFP 目录；这些是正式答案或答案来源证据，是否提交需要审查者决定。

## 方法证据摘要

| 方法 | 流程 | pilot100 / pre-freeze 证据 |
|---|---|---|
| `A1` | 完整航图图像 -> OCR-1 PaddleOCR -> 确定性规则 -> canonical JSON | pilot100: 100/100 schema-valid，741/2344 = 0.316126 |
| `A2` | 完整航图图像 -> OCR-2 Tesseract -> 同一套确定性规则 -> canonical JSON | pilot100: 100/100 schema-valid，521/2344 = 0.222270 |
| `B1` | OCR-1 文本 -> GPT-5.4 -> canonical JSON | pilot100: 100/100 schema-valid，728/2344 = 0.310580 |
| `B1_prime` | OCR-1 文本 + field_candidates -> GPT-5.4 -> canonical JSON | pilot100: 100/100 schema-valid，674/2344 = 0.287543 |
| `B1_prime_link` | OCR-1 文本 + field_candidates + field_to_leg_links -> GPT-5.4 -> canonical JSON | pilot100: 100/100 schema-valid，1031/2344 = 0.439846 |
| `C1` | 完整航图图像 -> Claude VLM -> canonical JSON | pilot100: 99/100 schema-valid，902/2313 = 0.389970 |
| `C2` | 完整航图图像 -> Claude VLM QA prompts -> 确定性聚合器 -> canonical JSON | pilot100: 100/100 schema-valid，457/2344 = 0.194966 |
| `C3` | 完整航图图像 -> Claude VLM questionnaire -> 确定性 parser -> canonical JSON | pilot100: 99/100 schema-valid，874/2313 = 0.377864 |
| `C4` | 完整航图图像 + OCR-1 文本 -> Claude VLM -> canonical JSON | API 故障恢复后 pilot100: 100/100 schema-valid，1248/2344 = 0.532423，schema retry=0 |
| `D_SFT` | 完整航图图像 -> SFT VLM -> canonical JSON | pilot100: 94/100 schema-valid；已评分样本 1014/2200 = 0.460909 |

这些结果是 external pilot100 / pre-freeze feasibility evidence，不是 formal300 正式结果。

## 正式运行前仍需完成或确认

- [ ] 生成并冻结 formal300 OCR-1 PaddleOCR artifact，用于 A1/B1/B1_prime/B1_prime_link/C4。
- [ ] 生成并冻结 formal300 OCR-2 Tesseract artifact，用于 A2。
- [ ] 确认 300 个 formal300 样本对应 299 个 PDF 是正常 PDF 复用，还是 materialization 缺口。
- [ ] 确认 formal300 image/PDF/canonical_proxy_gt/raw CIFP 的提交与存储策略。
- [ ] 确认 B1_prime_link 是否正式纳入实验组1 candidate。
- [ ] 只有在方法边界、runner 隔离、manifest、policy 经审查通过后，才运行 formal300。

## 希望审查者重点确认

- [ ] 实验组1中每个方法都没有接收禁止输入。
- [ ] 推理 runner 与 scoring/target 文件严格隔离。
- [ ] retry 和 invalid-output scoring policy 是预注册的，不按分数选择性重跑。
- [ ] C4 输出控制修正只处理 provider/tool 传输层问题，不改变 C4 的方法输入。
- [ ] D-SFT 推理阶段仍然只使用完整航图图像，不使用 OCR、target、score 或其他方法预测结果。

## 当前状态

尚未运行 formal300 evaluation。本 PR 只用于正式运行前审查。
