# final-v2 字段合法性与 unknown target 清理记录

日期：2026-05-06

本 PR 只记录本次 final-v2 target/scoring contract 变更，供 D1 重新训练、formal200 重评分和论文结果统一验收使用。实际大批量 JSON target 与 SFT JSONL 已在 release draft / artifact package 中更新，本 PR 不把 225 个 formal target 文件和 600 条 SFT paired examples 复制进代码仓。

## 结论

这次变更不是简单改一个 scorer 函数，而是统一了 formal reference target、scoring-equivalence target、annotation target 和 auxiliary SFT paired answers 的字段合法性语义：

- formal references 不再使用开放式 `unknown` 作为目标答案。
- CF/DF leg 在图上没有限制转弯方向且两向均可时，`Q3_turn` 的目标答案为 `present/BOTH`。
- DF leg 的 direct-to-fix 已由 `Q_terminator=DF` 和 `Q1_fix_ident` 表达，`Q4_course_or_radial` 不再用合成的 `{type: direct}`，而是 `not_applicable/null`。
- TF leg 的 course/radial 若不需要作为独立编码字段，则 `Q4_course_or_radial` 为 `not_applicable/null`；TF 的轨迹由端点几何限定。
- `not_applicable/null` 是字段合法性答案，不是 wildcard。模型输出 `unknown` 不会因为目标为 unknown 获得通配 credit。

## formal300 target 变更

来自 `unknown_cleanup_report_20260506.json`：

| target asset | before sha256 | after sha256 | changed items |
| --- | --- | --- | --- |
| `NIPS-AIP-Dataset-v1.0-draft/formal300/targets/canonical_targets.json` | `92479f26b62069ad45d0f3dfd6934b08277464dd898e26b5448f85d73a7d88af` | `4be407691c1bbdf10deacb78164df3d45363078b3652430fb2dc84d92f77a9ed` | `turn_to_both=222`, `tf_q4_to_not_applicable=50`, `fa_q3_to_not_applicable=1` |
| `NIPS-AIP-Dataset-v1.0-draft/formal300/targets/canonical_proxy_gt_combined.json` | `5da93b39cca7a8d7f5b3d1cf3e388af8cc472898c59be5468e1750eb4eedf969` | `a41beb38a9c9d824c9725e49e32ab86a0d134b1d13ae217bfd889813df4ba210` | `turn_to_both=222`, `tf_q4_to_not_applicable=50`, `fa_q3_to_not_applicable=1` |
| `NIPS-AIP-Dataset-v1.0-draft/formal300/targets/canonical_proxy_gt/*.json` | per-file | per-file | 225 files touched; same aggregate counts |
| `NIPS-AIP-Dataset-v1.0-draft/formal300/annotations/final_annotations_by_chart/*.json` | per-file | per-file | 225 files touched; same aggregate counts |

The scoring-equivalence v2 exports were also updated:

| scoring-equivalence asset | before sha256 | after sha256 |
| --- | --- | --- |
| `_fig4_extract_20260505/benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/canonical_proxy_gt_chart_display_v2.json` | `514bad37ccf3a39655e71b01d2e533c6d89d8d9b7d863407e408a654cbf98ce5` | `7d66478d51b898f1b9ca9a3de1fabb2b1d31c87ccd38c3211e5385bb6e5e20fe` |
| `_fig4_extract_20260505/benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/field_targets_chart_display_v2.jsonl` | `bd107e272cff8d50a5f3c789f0bb07294f860cbc7a4efe29e1c5edd52ce0f914` | `e421aaa748d06c9e59d22dcaa0f43436882752429785521d20044d9e5683fd5b` |
| `_fig4_extract_20260505/benchmark_exports/derived/v2/formal300/targets/scoring_equivalence_v2/comparison_policy_v2.jsonl` | `4af3745662429d2f830c49a5d6048e36093ddea9dc646767554164013779124f` | `8054cf9e938a5479bbf08a65e5097d9ab4ee9a1b117db05d362ea8f4bf833954` |

## auxiliary SFT package 变更

The auxiliary SFT paired targets were synchronized with the same final-v2 contract.

From `NIPS-AIP-Dataset-v1.0-draft/sft/d_sft_train500_dev100.artifact_manifest.json`:

- `updated_at`: `2026-05-06T09:28:24.766571+08:00`
- `reason`: Align auxiliary SFT paired targets with corrected formal evaluation contract: CF/DF unrestricted turns use BOTH; DF Q4 course/radial is not_applicable.
- `target_files_touched`: 583
- `df_q4_direct_to_not_applicable`: 426
- `df_cf_q3_not_applicable_to_both`: 417
- `prompt_v2_path`: `sft/prompts/d_sft_image_to_canonical.v2.md`

The SFT prompt now instructs:

- CF/DF unrestricted turns use `BOTH` for `Q3_turn`.
- DF legs do not have an independent course/radial answer; set `Q4_course_or_radial` to `not_applicable` unless an explicit charted course/radial belongs to another leg type.

## Impact on experiments

All paper-facing numbers must use the same final-v2 target/scorer contract.

- Existing C-series and other non-SFT predictions may be re-scored against final-v2 targets if their raw predictions are unchanged. If a protocol prompt itself relied on the old synthetic `direct` semantics, rerun that protocol only if the result will be reported as a final leaderboard number.
- D1/SFT must be retrained from the corrected auxiliary SFT train/dev JSONL before the final D1 row is claimed. Re-scoring an old LoRA checkpoint is useful only as a diagnostic, not as the final D1 result.
- The formal-train-only SFT pilot, if reported, should also use the final-v2 target/scorer contract and should be marked as a small pilot rather than a formal200 leaderboard row unless run on the full formal200 test set.
- The noSFT/same-backbone control belongs to the D-group boundary analysis, not the C-group baseline matrix. It tests whether the bare backbone plus the D output interface already solves the canonical-JSON task; it does not replace the strong open-weight C-series non-SFT baseline.

## Acceptance checklist for downstream reruns

- The run manifest identifies the target/scorer as final-v2 field-legality/display-equivalence.
- The run uses formal references with zero open-ended `unknown` target answers.
- D1 retraining uses corrected SFT paired answers, not the pre-cleanup train/dev JSONL.
- Reported scores are all recomputed from final-v2 targets; old 77.94-era numbers are not mixed with final-v2 tables or figures.
- Any inserted missing/null values in canonicalization are logged and interpreted as part of the legality-prior floor, not as recovered chart evidence.