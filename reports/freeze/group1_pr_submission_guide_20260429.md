# 实验组1 preflight PR 提交说明 - 2026-04-29

状态：供用户审阅，尚未提交 PR。

目标仓库：`https://github.com/reshihihihi/faa-chart-to-424-benchmark`

## 1. 本次 PR 的定位

本次 PR 建议定位为：

> 实验组1 formal300 正式运行前审查包。

它用于让审查者在正式运行 formal300 之前检查方法边界、冻结/预冻结参数、runner 隔离、formal300 manifest、scorer/validator、pilot100 证据和剩余 blocker。

本次 PR 不应该包含 formal300 方法推理结果，也不应该包含为了正式实验产生的预测分数。

## 2. 推荐提交内容

### 2.1 核心说明、策略、配置

建议提交：

- `docs/method_registry.md`
- `docs/group1_method_boundary_audit_20260428.md`
- `docs/group1_ocr_boundary_correction_20260428.md`
- `docs/formal_freeze_checklist.md`
- `docs/no_leakage_policy.md`
- `docs/rerun_policy.md`
- `docs/b1_prime_link_method_card.md`
- `docs/d_sft_method_card.md`
- `docs/group1_a1_a2_rules_candidate_v1.md`
- `docs/group1_c2_qa_aggregator_candidate_v1.md`
- `docs/field_candidates_schema_v1_candidate.md`
- `configs/group1_formal_freeze_manifest_20260429.json`
- `configs/group1_freeze_candidate_manifest_20260429.json`
- `configs/frozen_experiment_manifest.json`
- `configs/model_config_manifest.json`
- `configs/ocr_source_manifest.json`
- `configs/prompt_manifest.json`
- `configs/output_control_policy.md`
- `configs/parser_repair_policy.md`
- `configs/invalid_output_scoring_policy.md`
- `configs/degree_360_policy.md`
- `configs/scorer_validator_manifest.json`

### 2.2 schema、prompt、runner、scorer

建议提交：

- `schemas/field_candidates.schema.candidate.json`
- `schemas/field_to_leg_links.schema.candidate.json`
- `schemas/c3_questionnaire.schema.candidate.json`
- `schemas/d_sft_manifest.schema.json`
- `prompts/paper_v2/b1_ocr_to_canonical_pilot10.zh_v1_candidate.md`
- `prompts/paper_v2/b1_prime_ocr_field_candidates_to_canonical_pilot10.zh_v0_candidate.md`
- `prompts/paper_v2/b1_prime_link_ocr_candidates_links_to_canonical.zh_v0_candidate.md`
- `prompts/paper_v2/c1_image_to_canonical_pilot10.zh_v1_candidate.md`
- `prompts/paper_v2/c3_questionnaire_pilot10.zh_v1_candidate.md`
- `prompts/paper_v2/c4_image_ocr_to_canonical_pilot10.zh_v1_candidate.md`
- `prompts/path_c_qa_v2/q0_leg_count.txt`
- `prompts/path_c_qa_v2/q1_fix_ident.txt`
- `prompts/path_c_qa_v2/q2_altitude_constraint.txt`
- `prompts/path_c_qa_v2/q3_turn.txt`
- `prompts/path_c_qa_v2/q4_course_or_radial.txt`
- `prompts/path_c_qa_v2/q5_hold_params.txt`
- `prompts/path_c_qa_v2/q_terminator.txt`
- `scripts/model_clients.py`
- `scripts/scorers/group1_canonical_field_scorer.py`
- `scripts/prepare_group1_formal_run.py`
- `scripts/materialize_formal300_dataset.py`
- `scripts/sync_formal300_annotation_images.py`
- `scripts/run_group1_pilot10_gpt54.py`
- `scripts/run_a1_a2_rules_pilot10.py`
- `scripts/run_c2_qa_pilot10.py`
- `scripts/aggregate_c2_qa_candidate.py`
- `scripts/run_b1prime_c4_pilot10.py`
- `scripts/run_pilot10_anthropic.py`
- `scripts/run_pilot10_ordinary_ocr.py`
- `scripts/run_b1_c1_pilot10_ocr1.py`
- `scripts/d_sft_prepare_dataset.py`
- `scripts/d_sft_train_qwen2vl_lora.py`
- `scripts/d_sft_infer_qwen2vl_lora.py`

### 2.3 pilot / freeze 报告

建议提交整理后的报告，不提交原始预测大目录：

- `reports/freeze/group1_pr_package_checklist_20260429.md`
- `reports/freeze/group1_pr_draft_body_20260429.md`
- `reports/freeze/group1_pr_package_file_manifest_20260429.json`
- `reports/freeze/group1_pr_submission_guide_20260429.md`
- `reports/freeze/group1_formal_freeze_ready_no_eval_20260429.md`
- `reports/freeze/group1_formal_freeze_package_BLOCKED_20260429.md`
- `reports/freeze/group1_freeze_readiness_audit_20260429.md`
- `reports/freeze/group1_freeze_readiness_audit_20260429.json`
- `reports/freeze/group1_runner_gap_audit_20260429.md`
- `reports/freeze/group1_model_rerun_policy_audit_20260429.md`
- `reports/freeze/group1_c_methods_pilot100_evidence_20260429.md`
- `reports/freeze/c4_output_control_fix_20260429.md`
- `reports/freeze/c4_output_control_fix_20260429.json`
- `reports/pilot/c4_output_control_fix_pilot100_20260429.md`
- `reports/pilot/c4_output_control_fix_pilot100_20260429.json`
- `reports/pilot/b1_prime_link_group1_candidate_pilot100_20260429.md`
- `reports/pilot/b1_prime_link_group1_candidate_pilot100_revalidation_20260429.json`
- `reports/pilot/pilot100_b1_b1prime_expanded_validation_20260428.md`
- `reports/pilot/pilot100_b1_b1prime_result_summary_20260428_r1.json`
- `reports/pilot/group1_prefreeze_final_optimization_20260429.md`
- `reports/pilot/group1_pilot10_ordinary_ocr_gpt54_claude_20260428.md`
- `reports/pilot/group1_non_b1prime_auditfix_pilot10_20260428.md`
- `reports/pilot/ordinary_ocr_pilot10_artifacts_20260428.md`
- `reports/pilot/b1prime_method_decision_20260428.md`
- `training/d_sft/reports/d_sft_freeze_report_20260428_r1.md`

### 2.4 formal300 manifest 和小文件

建议提交这些 manifest / checksum / report / 小型分析文件：

- `benchmark_exports/derived/v2/formal300/manifest.json`
- `benchmark_exports/derived/v2/formal300/sample_manifest.jsonl`
- `benchmark_exports/derived/v2/formal300/splits.json`
- `benchmark_exports/derived/v2/formal300/checksums.sha256`
- `benchmark_exports/derived/v2/formal300/challenge_tags.jsonl`
- `benchmark_exports/derived/v2/formal300/source/formal300_source_manifest.json`
- `benchmark_exports/derived/v2/formal300/targets/field_targets.jsonl`
- `benchmark_exports/derived/v2/formal300/targets/evidence_provenance.jsonl`
- `benchmark_exports/derived/v2/formal300/reports/formal300_materialization_report.json`
- `benchmark_exports/derived/v2/formal300/reports/annotation_image_alignment_report.json`
- `benchmark_exports/derived/v2/formal300_source_lock_20260429/BLOCKERS.md`
- `benchmark_exports/derived/v2/formal300_source_lock_20260429/MANIFEST.json`
- `benchmark_exports/derived/v2/formal300_source_lock_20260429/sample_manifest.jsonl`
- `benchmark_exports/derived/v2/formal300_source_lock_20260429/splits.json`

## 3. 暂时不要提交的内容

不要提交：

- `OpenAI`
- `formal_runs/`
- `ocr_artifacts/`
- `predictions/pilot10_external/`
- `benchmark_exports/derived/v2/formal300/images/`
- `benchmark_exports/derived/v2/formal300/pdfs/`
- `benchmark_exports/derived/v2/formal300/targets/canonical_proxy_gt/`
- `benchmark_exports/derived/v2/formal300/targets/raw_cifp_per_procedure/`
- `scripts/__pycache__/`
- `*.pyc`
- 任何 API key、token、credential、代理配置文件

其中 `canonical_proxy_gt/` 和 `raw_cifp_per_procedure/` 是否提交，需要学长/审查者先决定。它们是正式答案或答案来源证据，不能被 inference runner 访问。

## 4. 推荐提交步骤

### 4.1 切到仓库并重命名分支

```powershell
Set-Location <repo-root>
git branch -m group1-formal300-preflight-review-20260429
```

### 4.2 清空暂存区

这一步不会删除工作区文件，只是避免之前误 stage 的文件混进 PR。

```powershell
git restore --staged .
```

### 4.3 只按白名单 stage 文件

不要使用 `git add .`。

可以把上面“推荐提交内容”中的文件逐项 `git add -- <path>`。如果要批量 stage，建议先把路径写入一个临时文件，再用下面命令：

```powershell
Get-Content .\reports\freeze\group1_pr_submission_paths_20260429.txt | ForEach-Object {
  if ($_ -and (Test-Path $_)) {
    git add -- $_
  }
}
```

注意：`group1_pr_submission_paths_20260429.txt` 需要只包含白名单路径，不能包含大目录、密钥文件、raw predictions 或 formal run outputs。

### 4.4 检查 staged 内容

```powershell
git diff --cached --name-only
git diff --cached --stat
```

确认 staged 列表里没有：

- `OpenAI`
- `formal_runs/`
- `ocr_artifacts/`
- `predictions/pilot10_external/`
- `benchmark_exports/derived/v2/formal300/images/`
- `benchmark_exports/derived/v2/formal300/pdfs/`
- `benchmark_exports/derived/v2/formal300/targets/canonical_proxy_gt/`
- `benchmark_exports/derived/v2/formal300/targets/raw_cifp_per_procedure/`
- API token 或 credential

### 4.5 做敏感信息扫描

只扫描 staged 文件名和 staged diff，不要把 token 打印出来。

```powershell
git diff --cached --name-only | Select-String -Pattern "OpenAI|token|secret|credential|key|ANTHROPIC|OPENAI"
git diff --cached | Select-String -Pattern "sk-|ck_|ANTHROPIC_AUTH_TOKEN|OPENAI_API_KEY|Bearer"
```

如果有输出，先停止，检查原因。

### 4.6 commit

```powershell
git commit -m "Prepare Group 1 formal300 preflight review package"
```

### 4.7 push

```powershell
git push -u origin group1-formal300-preflight-review-20260429
```

### 4.8 开 PR

如果安装了 GitHub CLI：

```powershell
gh pr create `
  --repo reshihihihi/faa-chart-to-424-benchmark `
  --base main `
  --head group1-formal300-preflight-review-20260429 `
  --title "Prepare Group 1 formal300 preflight review package" `
  --body-file reports/freeze/group1_pr_draft_body_20260429.md
```

如果没有 GitHub CLI，就 push 后在 GitHub 网页上打开 PR，把 `reports/freeze/group1_pr_draft_body_20260429.md` 的内容复制到 PR description。

## 5. 开 PR 前必须向审查者说明的点

- 本 PR 没有运行 formal300。
- 本 PR 不包含 formal300 正式推理结果。
- 当前 formal300 是 300 个样本，但只有 299 个 PDF，需要确认是正常 PDF 复用还是 materialization 缺口。
- C4 已做输出控制修正，API 故障恢复后 pilot100 为 100/100 schema-valid，retry=0。
- `B1_prime_link` 是否正式纳入实验组1，需要审查者确认。
- formal300 的 PNG/PDF/canonical_proxy_gt/raw CIFP 是否进入仓库，需要审查者确认。
