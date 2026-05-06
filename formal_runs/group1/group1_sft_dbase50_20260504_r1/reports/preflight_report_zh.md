# 实验组 1 SFT 扩展 run package preflight

- run_id: `group1_sft_dbase50_20260504_r1`
- split_subset: `evaluation`
- ready_for_remote_execution: `True`
- blockers: `0`

## 方法清单

- `D_BASE_SAME_BACKBONE`: rows=50, manifest=`formal_runs/group1/group1_sft_dbase50_20260504_r1\D_BASE_SAME_BACKBONE\input_manifest.jsonl`

## Blockers

- None

## 边界

- input manifests 不包含 target JSON、score、CIFP/424 原始记录或其他方法预测。
- scoring manifest 只允许在预测完成后用于评分。
- 新增默认方法只比较 `canonical_prediction` 的正式分数；`evidence_boxes` 只做诊断分析。
- 旧的人工证据/自动两阶段方法不再是本轮默认方法。
