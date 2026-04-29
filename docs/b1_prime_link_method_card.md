# B1_prime_link Method Card

Status: Experiment Group 1 candidate / pre-freeze, not formally frozen

Local date: 2026-04-29

## Purpose

`B1_prime_link` tests whether an automatic field-to-leg linking stage improves an OCR+LLM extraction method beyond flat OCR-text-derived field candidates.

This method is distinct from:

- `B1`: OCR-1 full-chart text -> LLM -> canonical JSON
- `B1_prime`: OCR-1 full-chart text -> flat field candidates -> LLM -> canonical JSON
- Group 5 diagnostic/oracle linking variants

## Method Equation

```text
full chart image
  -> registered OCR-1 full-chart text
  -> automatic OCR-text-only flat field candidates
  -> automatic non-target-aware field-to-leg candidate linking
  -> OCR text + field_to_leg_links
  -> text LLM
  -> canonical JSON
```

## Allowed Inputs

- `chart_id`
- `airport`
- `approach_ident`
- `chart_name`
- registered OCR-1 full-chart text
- flat `field_candidates` derived only from the same OCR-1 text
- automatic `field_to_leg_links` derived only from the same OCR-1 text and flat `field_candidates`
- canonical output schema contract

## Forbidden Inputs

- chart image pixels at LLM stage
- OCR bbox / coordinates
- ROI or visual cells
- gold missed-approach prose
- canonical target / answer key
- expected values
- manual or gold field-to-leg mappings
- target-aware PR32 mappings
- `field_targets.jsonl`
- `evidence_provenance.jsonl`
- `challenge_tags.jsonl`
- scorer outputs
- CIFP / ARINC 424 records
- human annotation
- historical model outputs for the same chart

## Registered Candidate Files

- prompt: `prompts/paper_v2/b1_prime_link_ocr_candidates_links_to_canonical.zh_v0_candidate.md`
- prompt sha256 in repository and pilot100 validation run: `2b135d82928e3963a5b37ad5ebcee82e2e079aa94d34c88cf33b1d215c8909c2`
- field-to-leg schema: `schemas/field_to_leg_links.schema.candidate.json`
- field-to-leg schema sha256: `1085f187055f1e6b7b78bb9958643ed4eb06bfa7d8a4a65870537bd34f704262`
- canonical schema: `schemas/missed_approach_leg.schema.json`
- canonical schema sha256 at validation: `cd62edf995344d73ae45fcfad4e9bff3412f58a42f9fb591f9ca08e399e26be9`
- external pilot100 linking script: `E:\experiment3\B1'_link\scripts\build_field_to_leg_links.py`, sha256 `132c90afc38f12d1c50a1930a44ba519afb33d40e0da5059a630d4eb71944dd9`
- external pilot100 runner script: `E:\experiment3\B1'_link\scripts\run_b1prime_link_smoke.py`, sha256 `1e61a1c5f7130d8cabb51deb0baaefb4725374aff8b1fc55636e9a4e01cb87a9`

## Pilot100 Validation

Pilot100 validation is recorded in:

- external artifact root: `E:\experiment3\B1'_link`
- run id: `b1prime_link_v2_pilot100_gpt54_toolcall_promptfix_20260428_r2`
- revalidation JSON: `reports/pilot/b1_prime_link_group1_candidate_pilot100_revalidation_20260429.json`
- report: `reports/pilot/b1_prime_link_group1_candidate_pilot100_20260429.md`

Result:

- samples: 100/100
- canonical schema-valid outputs: 100/100
- field-to-leg sample links schema-valid: 100/100
- parser repair count: 0
- schema-only retries: 1/100
- field-level score: 1031/2344 = 0.439846

The pilot100 set is an expanded feasibility set and remains excluded from formal300.

## Candidate Decision

`B1_prime_link` is allowed into Experiment Group 1 as a candidate method after `B1_prime`.

It is not formally frozen here. Formal freeze still requires final decisions for formal300 split/targets, model/provider/call parameters, rerun policy, scorer implementation, and formal run artifact layout.
