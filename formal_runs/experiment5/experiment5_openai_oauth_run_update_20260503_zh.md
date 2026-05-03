# 实验组5 openai-oauth 补跑状态

更新时间：2026-05-03

## 本轮做了什么

已按要求使用 `openai-oauth` 把本机 Codex OAuth 包装成 OpenAI-compatible API，并用它完成实验组5 dev50 与 eval200 的 LLM 方法补跑。

- 新 base URL：`http://127.0.0.1:10531/v1`
- 模型：`gpt-5.4`
- Windows 系统代理：`127.0.0.1:10808`
- Node 代理注入：`openai-oauth/proxy-bootstrap.mjs`
- 最小 chat probe 已成功返回 `pong`

原来的 `http://127.0.0.1:8080/v1` 不再作为本轮 LLM 方法入口。

## dev50 当前结果

dev50 admin-relation 线已经跑齐：

| 方法 | 状态 | v2 正确/总数 | accuracy | failure_count |
|---|---|---:|---:|---:|
| A3_GoldText_Rules | completed | 303/1010 | 30.00% | 0 |
| B2a_GoldText_LLM | completed | 606/1010 | 60.00% | 0 |
| B2b_GoldText_FieldCandidates_LLM | completed | 509/1010 | 50.40% | 0 |
| B3_T | completed | 722/1010 | 71.49% | 0 |
| B3_PD | completed | 171/1010 | 16.93% | 0 |
| B3_TPD | completed | 660/1010 | 65.35% | 0 |
| B4_TPD | completed | 303/1010 | 30.00% | 0 |
| G0_Direct | completed in r1 | 274/1010 | 27.13% | 0 |
| G1_Rules | completed in r1 | 600/1010 | 59.41% | 0 |
| G3_LLM_Rules | completed in r1 | 76/1010 | 7.52% | 0 |

## eval200 当前结果

eval200 admin-relation 线也已经跑齐：

| 方法 | 状态 | v2 正确/总数 | accuracy | failure_count |
|---|---|---:|---:|---:|
| A3_GoldText_Rules | completed | 1245/4052 | 30.73% | 0 |
| B2a_GoldText_LLM | completed | 2552/4052 | 62.98% | 0 |
| B2b_GoldText_FieldCandidates_LLM | completed | 1963/4052 | 48.45% | 0 |
| B3_T | completed | 2930/4052 | 72.31% | 0 |
| B3_PD | completed | 719/4052 | 17.74% | 0 |
| B3_TPD | completed | 2657/4052 | 65.57% | 0 |
| B4_TPD | completed | 1245/4052 | 30.73% | 0 |
| G0_Direct | completed in r1 | 1079/4052 | 26.63% | 0 |
| G1_Rules | completed in r1 | 2380/4052 | 58.74% | 0 |
| G3_LLM_Rules | completed in r1 | 284/4052 | 7.01% | 0 |

## 过程记录

eval200 B2b 曾在第 23 个有效样本后遇到上游 usage-limit 错误。后续确认 `openai-oauth` 恢复后，使用 `--resume-existing` 补完 B2b，并继续跑完 B3_T、B3_PD、B3_TPD。最终 A/B/G 全部方法均完成，且最终汇总中的 `failure_count` 均为 0。

为加快速度，同时保持实验输入、prompt、schema 和评分逻辑不变，`scripts/experiment5/run_experiment5_smoke_b3_b4.py` 增加了：

- `--resume-existing`
- `--max-workers`
- 对 LLM 方法的并发执行
- 对已有 `canonical_json` 的复用与重新评分

这些改动只改变运行调度与断点续跑，不改变方法输入边界。

## 下一步

1. 做最终 no-leakage 和敏感信息扫描。
2. 提交并推送包含 dev50/eval200 输入、输出、报告与 runner 加速补丁的 git commit。
3. 基于 `experiment5_*_combined_summary.json` 写最终实验组5结果解读。
