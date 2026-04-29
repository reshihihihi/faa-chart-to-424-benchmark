# Group 1 Freeze Readiness Audit - 2026-04-29

Status: **not_formal_freeze_ready**

This audit checks Experiment Group 1 before formal freezing. It records what is already available, what is only candidate/pre-freeze, and what blocks formal300 evaluation.

## Global Blockers
- formal300 source sample/split lock exists, but formal300 image/PDF artifacts and checksums are missing locally.
- formal300 canonical proxy targets, field_targets, evidence_provenance, and challenge_tags are not materialized/frozen.
- Scorer/validator is now implemented as a candidate standalone script, but it still needs formal review and lock against formal300 targets.
- Model/provider/base_url/max_tokens/tool policy/retry policy are still candidate, not formal frozen.
- C1 and C3 each have one pilot100 schema failure on KMCW_I36; the previous C4 high schema-only retry count is resolved in the 2026-04-29 output-control fix pilot100 validation.
- A1/A2/B/C runners are mostly pilot/external runners; formal300 no-leakage input manifest and runner wrappers are not consolidated.
- D_SFT pilot100 has 6 parse/schema failures; formal handling of invalid outputs must be specified before leaderboard reporting.

## formal300
- Source lock package: `benchmark_exports/derived/v2/formal300_source_lock_20260429/`
- Status: `source_lock_only_not_formal_eval_ready`
- Rows: 300; split counts: {'evaluation': 75, 'development': 200, 'probe': 25}; kind counts: {'ILS': 13, 'LOC': 25, 'RNAV': 262}
- Meaning: sample IDs and split source are now recorded, but images and targets are not frozen.

## Scorer / Validator
- Candidate scorer: `scripts/scorers/group1_canonical_field_scorer.py`
- SHA256: `2bdfb6b999c65684dc3714da52a88f8c23ab49f3bf8a744a7d3b930c9323c520`
- Rule: exact field-level equality over `leg_count` plus all questionnaire fields for each target leg.
- Status: candidate implemented, still needs formal review and freeze against formal300 targets.

## Method Matrix
| Method | Boundary | Pilot100 evidence | Formal blocker |
|---|---|---|---|
| `A1` | image -> OCR-1 -> deterministic rules -> canonical JSON | 100/100 schema-valid; 741/2344; acc=0.316126 | rules runner is pilot/external oriented; formal300 runner and OCR artifact policy not frozen |
| `A2` | image -> OCR-2 -> same deterministic rules -> canonical JSON | 100/100 schema-valid; 521/2344; acc=0.222270 | rules runner is pilot/external oriented; formal300 runner and OCR-2 artifact policy not frozen |
| `B1` | OCR-1 full-chart text -> text LLM -> canonical JSON | 100/100 schema-valid; 728/2344; acc=0.310580; retry=9 | prompt/model/call params and formal OCR-1 artifact manifest not formally frozen |
| `B1_prime` | OCR-1 text -> automatic flat field_candidates -> text LLM -> canonical JSON | 100/100 schema-valid; 674/2344; acc=0.287543; retry=11 | field_candidates matcher and prompt remain candidate; pilot100 underperformed B1 |
| `B1_prime_link` | OCR-1 text -> automatic field_candidates + automatic field_to_leg_links -> text LLM -> canonical JSON | 100/100 schema-valid; 1031/2344; acc=0.439846; retry=1 | runner not yet consolidated in repo; link schema/prompt are candidate |
| `C1` | full chart image -> VLM/MLLM -> canonical JSON | 99/100 schema-valid; 902/2313; acc=0.389970; retry=7 | pilot100 has 1 schema failure; provider/tool policy/model not formally frozen |
| `C2` | full chart image -> fixed QA prompt bundle -> deterministic aggregator -> canonical JSON | 100/100 schema-valid; 457/2344; acc=0.194966; retry=9 | QA bundle/aggregator are candidate; formal invalid-QA handling and runner not frozen |
| `C3` | full chart image -> VLM questionnaire JSON -> deterministic questionnaire-to-canonical parser -> canonical JSON | 99/100 schema-valid; 874/2313; acc=0.377864; retry=5 | pilot100 has 1 schema failure; questionnaire prompt/model/tool policy not formally frozen |
| `C4` | full chart image + OCR-1 text -> VLM/MLLM -> canonical JSON | current: 100/100 schema-valid after API recovery; 1248/2344; acc=0.532423; retry=0 | output-control retry issue resolved for pilot100; model/tool policy and formal OCR-1 artifact policy still not formally frozen |
| `D_SFT` | full chart image -> SFT VLM -> canonical JSON | 94/100 schema-valid; 1014/2200; acc=0.460909 | pilot100 has 6 parse/schema failures; formal invalid-output scoring policy and checkpoint/report linkage must be locked |

## Decision
Do not freeze Group 1 yet. The current package is a freeze-readiness audit plus formal300 source-lock-only record. Formal freezing should wait until the hard blockers above are closed.

## Files
- JSON audit: `reports/freeze/group1_freeze_readiness_audit_20260429.json`
- Scorer manifest: `configs/scorer_validator_manifest.json`
- formal300 source lock: `benchmark_exports/derived/v2/formal300_source_lock_20260429/`
