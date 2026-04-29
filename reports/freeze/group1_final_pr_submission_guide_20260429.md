# 实验组1最终 PR 提交说明 - 2026-04-29

目标仓库：`https://github.com/reshihihihi/faa-chart-to-424-benchmark`

## 1. 这次最终要提交什么

这次 PR 应提交“实验组1 formal300 正式运行前审查包”，并且包含：

- 实验组1试验方案与方法边界；
- 各方法的 prompt、schema、runner、scorer、method card；
- OCR 边界纠正和 OCR-1/OCR-2 来源定义；
- B1/B1_prime/B1_prime_link/C1/C2/C3/C4/D-SFT 的 pilot100 结果；
- A1/A2/B1 的 final pre-freeze recheck 结果；
- formal300 的 manifest、checksum、field_targets、evidence_provenance、challenge_tags；
- no-leakage、rerun、parser repair、invalid-output scoring、360-degree、output-control 等策略；
- PR 中文正文草稿和提交清单。

最重要的总说明文件是：

- `reports/freeze/group1_experiment_plan_methods_pilot100_summary_20260429.md`

真正 stage 时使用最终白名单：

- `reports/freeze/group1_final_pr_submission_paths_20260429.txt`

## 2. 这次仍然不要提交什么

不要提交：

- `OpenAI`
- `formal_runs/`
- `ocr_artifacts/`
- `predictions/pilot10_external/`
- `benchmark_exports/derived/v2/formal300/images/`
- `benchmark_exports/derived/v2/formal300/pdfs/`
- `benchmark_exports/derived/v2/formal300/targets/canonical_proxy_gt/`
- `benchmark_exports/derived/v2/formal300/targets/raw_cifp_per_procedure/`
- checkpoint、原始训练数据、API key、token、credential、缓存文件。

`canonical_proxy_gt/` 和 `raw_cifp_per_procedure/` 是正式答案或答案来源证据。除非审查者明确要求并决定管理方式，否则本 PR 只提交 manifest/hash 和分析文件。

## 3. 推荐提交命令

```powershell
Set-Location E:\experiment3\github_work\faa-chart-to-424-benchmark

git branch -m group1-formal300-preflight-review-20260429
git restore --staged .

Get-Content .\reports\freeze\group1_final_pr_submission_paths_20260429.txt | ForEach-Object {
  if ($_ -and (Test-Path $_)) {
    git add -- $_
  } else {
    Write-Host "MISSING: $_"
  }
}

git diff --cached --name-only
git diff --cached --stat
```

检查 staged 列表里没有不该提交的大目录或敏感文件后，再执行：

```powershell
git commit -m "Prepare Group 1 formal300 preflight review package"
git push -u origin group1-formal300-preflight-review-20260429
```

如果有 GitHub CLI：

```powershell
gh pr create `
  --repo reshihihihi/faa-chart-to-424-benchmark `
  --base main `
  --head group1-formal300-preflight-review-20260429 `
  --title "Prepare Group 1 formal300 preflight review package" `
  --body-file reports/freeze/group1_pr_draft_body_20260429.md
```

没有 GitHub CLI 时，push 后在 GitHub 网页上开 PR，把 `reports/freeze/group1_pr_draft_body_20260429.md` 的内容复制到 PR description。

## 4. 开 PR 时必须说明

- 本 PR 没有运行 formal300。
- 本 PR 不包含 formal300 正式推理结果。
- pilot100 是外部可行性验证，不是 formal300 结果。
- formal300 现在是 300 个样本但 299 个 PDF，需要确认是否为正常 PDF 复用。
- B1_prime_link 是否正式纳入实验组1，需要审查者确认。
- formal300 PNG/PDF/canonical_proxy_gt/raw CIFP 的提交方式需要审查者确认。
