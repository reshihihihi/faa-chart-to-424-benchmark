# 下一个对话输入

可以直接粘贴下面这段：

```text
请继续实验组5。

repo: https://github.com/reshihihihi/faa-chart-to-424-benchmark.git
branch: experiment5-diagnostic-20260503

请先 pull 最新分支，然后读取：
formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation/reports/experiment5_dev50_admin_relation_run_status_zh.md
formal_runs/experiment5/experiment5_dev50_20260503_r2_admin_relation/reports/experiment5_dev50_admin_relation_combined_summary.json
formal_runs/experiment5/experiment5_eval200_20260503_r2_admin_relation/reports/experiment5_eval200_admin_relation_run_status_zh.md
formal_runs/experiment5/experiment5_eval200_20260503_r2_admin_relation/reports/experiment5_eval200_admin_relation_combined_summary.json

当前理解：实验组5输入来自 shujuji 后台完整人工审核关系，包括框、航段、字段、证据关系、最终字段答案。不要把 OCR 当成 blocker。

已完成：
- dev50 A3_GoldText_Rules: 303/1010, 30.00%, 0 failures
- dev50 B4_TPD: 303/1010, 30.00%, 0 failures
- dev50 G0/G1/G3 reference 已完成
- eval200 A3_GoldText_Rules: 1245/4052, 30.73%, 0 failures
- eval200 B4_TPD: 1245/4052, 30.73%, 0 failures
- eval200 G0/G1/G3 reference 已完成

当前阻塞：
本地模型代理 /v1/chat/completions 返回 HTTP 500: Encountered invalidated oauth token for user, failing request。
因此 B2a/B2b/B3_T/B3_PD/B3_TPD 尚未完成。这不是输入、schema 或 runner 错误。

下一步：
1. 先确认 http://127.0.0.1:8080/v1/chat/completions 是否恢复。
2. 恢复后先补跑 dev50 的 B2a/B2b/B3_T/B3_PD/B3_TPD。
3. 再补跑 eval200 的 B2a/B2b/B3_T/B3_PD/B3_TPD。
4. 更新 reports 并提交 git。

注意严禁把 target、score、canonical_answer、canonical_leg_index、Q_terminator、leg_type、field_review_v2 作为方法输入。
```
