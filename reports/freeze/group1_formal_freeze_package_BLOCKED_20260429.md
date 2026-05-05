# Group 1 Formal Freeze Package - BLOCKED 2026-04-29

Status: **BLOCKED_NOT_FORMAL_FROZEN**

This package records the current Group 1 freeze state. It does not authorize formal300 evaluation yet.

## Created / Updated In This Pass
- `benchmark_exports/derived/v2/formal300_source_lock_20260429/MANIFEST.json` SHA256 `556993ae5d1bb833343d9629991a9a115ae1869e09ad5f14cea05ea940b3f7c3`
- `configs/scorer_validator_manifest.json` SHA256 `c4b450f0603a049067ac19036e297764a1f141e8abf3a69f36b6dc9ca892d794`
- `scripts/scorers/group1_canonical_field_scorer.py` SHA256 `2bdfb6b999c65684dc3714da52a88f8c23ab49f3bf8a744a7d3b930c9323c520`
- `reports/freeze/group1_freeze_readiness_audit_20260429.md` SHA256 `b8455da7d27a7b68a01dec3608dc629108472448b3ad93cf1ce7c24dbab24a40`
- `reports/freeze/group1_model_rerun_policy_audit_20260429.md` SHA256 `a00fa5c80a9732a24e241abe5e4e3464e7f8009a0ff69fa70e2ee6e25ff57607`
- `reports/freeze/group1_c_methods_pilot100_evidence_20260429.md` SHA256 `3530ed2b8cfefbcb1b146d0edba8b9b3b676767d88f09b9d0d77564990fa58b1`
- `reports/pilot/c4_output_control_fix_pilot100_20260429.md` SHA256 `323735c6e56f8644444c01ad2adcdcd6bb4deb821d16f5751b3b04cf6d9d1bec`
- `reports/freeze/group1_runner_gap_audit_20260429.md` SHA256 `03d3cd1ec20aa5814bbb40c8fcc7b5446ede269d6e38387f1faa13a8fbfda536`
- `configs/group1_freeze_candidate_manifest_20260429.json` SHA256 `fb76554149417a58ed63b863e70313fc0cb2a782590942ba647a689e1932565c`

## Can Be Treated As Already Frozen / Stable
- Canonical schema contract v1: `schemas/missed_approach_leg.schema.json`.
- Strict parser repair policy: no code-fence stripping, no JSON substring extraction, no semantic repair.
- Group 1 method boundaries at the conceptual level, including B1_prime_link as separate candidate after B1_prime.
- Pilot10/pilot100 external sets are excluded from formal evaluation/training where specified.
- D-SFT candidate training config/checkpoint is frozen for next formal300 evaluation, but its pilot100 result is not formal300 evidence.

## Candidate But Not Formally Frozen
- OCR-1 PaddleOCR PP-OCRv5 and OCR-2 Tesseract 5.x artifact policy for formal300.
- B1/B1_prime/B1_prime_link prompts, gpt-5.4 provider/call parameters, and text-LLM tool-call output control.
- C1/C2/C3/C4 prompts, Claude VLM provider/call parameters, QA bundle, C2 aggregator, and Anthropic tool-use policy.
- A1/A2 deterministic rules runner for formal300.
- B1_prime field_candidates matcher and B1_prime_link field_to_leg_links runner consolidation.

## Hard Blockers
- formal300 images/PDFs are not materialized with hashes.
- formal300 canonical proxy targets are not generated/frozen.
- field_targets.jsonl, evidence_provenance.jsonl, and challenge_tags.jsonl are not exported or explicitly waived.
- Invalid-output scoring policy is not finalized. Parse/schema failures must not disappear from denominators.
- Model/provider/max_tokens/tool/retry policy must be bound to final formal run manifests.
- Formal Group 1 runners are not yet consolidated and no-leakage-isolated.
- C1/C3 KMCW_I36 schema failure requires a pre-registered decision before formal freeze. The previous C4 high retry count has a validated pilot100 output-control fix, but C4 still needs final model/tool/OCR artifact freeze before formal300.

## Next Execution Order
1. Materialize formal300 image/PDF artifacts and checksums from the source lock.
2. Generate and validate formal300 canonical proxy targets from the fixed CIFP -> canonical projection pipeline.
3. Freeze invalid-output scoring and scorer/validator version against those targets.
4. Consolidate no-leakage formal runners for A1/A2/B1/B1_prime/B1_prime_link/C1/C2/C3/C4/D_SFT.
5. Freeze final model/provider/call/prompt/rerun manifests.
6. Only then run formal300 evaluation and generate the main Group 1 table.
