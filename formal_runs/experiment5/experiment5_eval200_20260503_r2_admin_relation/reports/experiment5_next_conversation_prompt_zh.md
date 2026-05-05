# 下一个对话输入

可以直接粘贴下面这段：

```text
请继续实验组5结果审阅。

repo: https://github.com/reshihihihi/faa-chart-to-424-benchmark.git
branch: experiment5-diagnostic-20260503

请先 pull 最新分支，然后读取：
formal_runs/experiment5/experiment5_openai_oauth_run_update_20260503_zh.md
formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation/reports/experiment5_dev50_admin_relation_run_status_zh.md
formal_runs/experiment5/experiment5_eval200_20260503_r2_admin_relation/reports/experiment5_eval200_admin_relation_run_status_zh.md
formal_runs/experiment5/experiment5_eval200_20260503_r2_admin_relation/reports/experiment5_eval200_admin_relation_combined_summary.json

当前状态：
- openai-oauth 已可用，base URL 是 http://127.0.0.1:10531/v1
- dev50 已经跑齐 A3/B2/B3/B4/G，全部 failure_count = 0
- eval200 已经跑齐 A3/B2/B3/B4/G，全部 failure_count = 0
- eval200 B2b 曾在 23/200 后遇到 usage limit，但已用 --resume-existing 补完
- B3_T/B3_PD/B3_TPD 也已完成

eval200 结果：
- A3_GoldText_Rules: 1245/4052, 30.73%
- B2a_GoldText_LLM: 2552/4052, 62.98%
- B2b_GoldText_FieldCandidates_LLM: 1963/4052, 48.45%
- B3_T: 2930/4052, 72.31%
- B3_PD: 719/4052, 17.74%
- B3_TPD: 2657/4052, 65.57%
- B4_TPD: 1245/4052, 30.73%
- G0_Direct: 1079/4052, 26.63%
- G1_Rules: 2380/4052, 58.74%
- G3_LLM_Rules: 284/4052, 7.01%

下一步：
1. 审阅 no-leakage 报告和方法输入边界。
2. 基于 dev50/eval200 combined summary 写最终实验组5结果分析。
3. 如有必要，再抽样看错误案例；核心方法不需要补跑。

注意严禁把 target、score、canonical_answer、canonical_leg_index、Q_terminator、leg_type、field_review_v2 作为方法输入。
```
