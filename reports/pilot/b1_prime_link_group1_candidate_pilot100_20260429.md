# B1_prime_link Group 1 Candidate Pilot100 Validation

Status: passes pilot100 feasibility as Group 1 candidate / pre-freeze, not formally frozen

Local date: 2026-04-29

## Decision

`B1_prime_link` is now registered as an Experiment Group 1 candidate method placed after `B1_prime`.

This method is not `B1_prime`; it adds an automatic, non-target-aware field-to-leg candidate linking stage. The purpose is to test whether linking OCR-derived field candidates to candidate legs helps extraction, without using target JSON, scorer output, CIFP/424 records, human annotation, or image pixels at the LLM stage.

Manual, gold, oracle, or target-aware linking variants remain outside Group 1 and belong to diagnostic/ablation analysis.

## Method Boundary

```text
full chart image
  -> registered OCR-1 full-chart text
  -> automatic OCR-text-only flat field candidates
  -> automatic non-target-aware field-to-leg candidate linking
  -> OCR text + field_to_leg_links
  -> text LLM
  -> canonical JSON
```

Allowed evidence:

- OCR-1 full-chart text from the same chart
- flat `field_candidates` derived only from OCR-1 text
- `field_to_leg_links` derived only from OCR-1 text and flat `field_candidates`
- metadata and canonical output contract

Forbidden evidence:

- canonical target, expected value, scorer output, CIFP / ARINC 424, human annotation, gold field-to-leg mapping, PR32 target-aware mapping, OCR bbox, ROI, or chart image pixels at LLM stage

## Registered Files

- method card: `docs/b1_prime_link_method_card.md`
- prompt candidate: `prompts/paper_v2/b1_prime_link_ocr_candidates_links_to_canonical.zh_v0_candidate.md`
- prompt sha256 in repository and pilot100 validation run: `2b135d82928e3963a5b37ad5ebcee82e2e079aa94d34c88cf33b1d215c8909c2`
- field-to-leg schema: `schemas/field_to_leg_links.schema.candidate.json`
- field-to-leg schema sha256: `1085f187055f1e6b7b78bb9958643ed4eb06bfa7d8a4a65870537bd34f704262`
- external pilot100 linking script: `E:\experiment3\B1'_link\scripts\build_field_to_leg_links.py`, sha256 `132c90afc38f12d1c50a1930a44ba519afb33d40e0da5059a630d4eb71944dd9`
- external pilot100 runner script: `E:\experiment3\B1'_link\scripts\run_b1prime_link_smoke.py`, sha256 `1e61a1c5f7130d8cabb51deb0baaefb4725374aff8b1fc55636e9a4e01cb87a9`
- local revalidation JSON: `reports/pilot/b1_prime_link_group1_candidate_pilot100_revalidation_20260429.json`

## Pilot100 Run

- run id: `b1prime_link_v2_pilot100_gpt54_toolcall_promptfix_20260428_r2`
- external artifact root: `E:\experiment3\B1'_link`
- sample manifest: `E:\experiment3\B1'_link\data\manifests\b1prime_link_pilot100_20260428.jsonl`
- sample role: pilot100 external feasibility only, excluded from formal300
- OCR-1: PaddleOCR PP-OCRv5 ordinary OCR
- text LLM: `gpt-5.4`
- output control: OpenAI-compatible forced tool call
- schema retry policy in run: 1 schema-only retry, no target/scorer use

## Revalidation Result

The repository-side revalidation checked the existing full pilot100 artifacts and did not make new model calls.

- samples: 100
- canonical JSON files: 100/100 present
- validation files: 100/100 present
- score files: 100/100 present
- field-to-leg link files: 100/100 present
- canonical schema errors: 0
- field-to-leg link schema errors: 0
- validation errors from run results: 0
- parser repair count: 0
- schema retry count: 1
- score: 1031/2344 = 0.439846

Comparison on the same pilot100 set:

| Method | Schema-valid | Score | Accuracy | Schema retries |
|---|---:|---:|---:|---:|
| B1 | 100/100 | 723/2344 | 0.308447 | 7 |
| B1_prime | 100/100 | 674/2344 | 0.287543 | 11 |
| B1_prime_link | 100/100 | 1031/2344 | 0.439846 | 1 |

## Remaining Limitations

- This is a candidate method, not a formal freeze.
- The pilot100 run proves feasibility on the external pilot set, not formal300 performance.
- `candidate_legs` are weak evidence; they are not gold legs and must not be mechanically copied into canonical legs.
- Formal300 split, canonical proxy targets, model/provider/call parameters, formal rerun policy, and scorer implementation still need separate freeze.
