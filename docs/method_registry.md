# Method Registry

Status: partial registry freeze for B1 and C3 on 2026-04-27, with Group 1 candidate boundary audit added on 2026-04-28 and B1_prime_link added as a Group 1 candidate on 2026-04-29.

This registry is the source of truth for method boundaries, allowed inputs, forbidden inputs, intermediate artifacts, and final output types. Only B1 and C3 are frozen in this revision. Other methods are candidate definitions until a later formal freeze step.

Current Group 1 boundary audit: `docs/group1_method_boundary_audit_20260428.md`.

Current expanded B1/B1_prime validation report:
`reports/pilot/pilot100_b1_b1prime_expanded_validation_20260428.md`.

B1_prime decision report:
`reports/pilot/b1prime_method_decision_20260428.md`.

B1_prime_link Group 1 candidate report:
`reports/pilot/b1_prime_link_group1_candidate_pilot100_20260429.md`.

## Summary

| Method | Experiment Group | Frozen Status | Main Leaderboard | Intermediate Output | Final Output |
|---|---:|---|---:|---|---|
| A1 | 1 | candidate, not frozen | yes | OCR-1 text + rule diagnostics | canonical JSON |
| A2 | 1 | candidate, not frozen | yes | OCR-2 text + rule diagnostics | canonical JSON |
| B1 | 1 | boundary frozen | yes | full-chart OCR text | canonical JSON |
| B1_prime | 1 | candidate / pre-freeze, not frozen | yes | flat automatic field candidates | canonical JSON |
| B1_prime_link | 1 | candidate / pre-freeze, not frozen | yes | automatic field candidates + automatic field-to-leg links | canonical JSON |
| C1 | 1 | candidate, not frozen | yes | raw VLM JSON | canonical JSON |
| C2 | 1 | candidate, not frozen | yes | per-question QA JSON | canonical JSON |
| C3 | 1 | boundary frozen | yes | questionnaire JSON | canonical JSON |
| C4 | 1 | candidate, not frozen | yes | image + OCR-1 side input | canonical JSON |
| D_SFT | 1 | frozen after pilot100 feasibility | yes | full chart image only | canonical JSON |
| B1_link | 5 | setup started, not frozen | no | field-to-leg candidate table | canonical JSON |

## Group 1 Candidate Addendum - 2026-04-28

### A1/A2

A1 and A2 are candidate OCR+Rules baselines:

```text
A1 = full chart image -> OCR-1 -> deterministic rules -> canonical JSON
A2 = full chart image -> OCR-2 -> deterministic rules -> canonical JSON
```

Candidate rules spec: `docs/group1_a1_a2_rules_candidate_v1.md`.

The rules must be identical for A1 and A2. The only intended experimental difference is OCR source.

### C1/C2/C4

Candidate C-family methods:

```text
C1 = full chart image -> VLM/MLLM -> canonical JSON
C2 = full chart image -> fixed QA prompt bundle -> deterministic aggregator -> canonical JSON
C4 = full chart image + OCR-1 text -> VLM/MLLM -> canonical JSON
```

C1/C2/C3 do not receive OCR text. C4 may receive OCR text only from registered OCR-1.

C2 uses the existing QA prompt bundle in `prompts/path_c_qa_v2/` and the candidate aggregator in `scripts/aggregate_c2_qa_candidate.py`.

## Group 1 Final Pre-Freeze Optimization - 2026-04-29

Status: completed as method-mechanism hardening, not formal freeze and not pilot100 score tuning.

Changes:

- B1, B1_prime, C1, C3, and C4 prompts now explicitly require exact metadata copying from input metadata.
- The same prompts now include a final internal schema check for status/value separation, degree ranges, fix-ident length/facility-word filtering, leg_count consistency, and one-based leg indexing.
- A1/A2 rules now use a source-agnostic schema-safe degree policy: `360` is encoded as `359.9`; other out-of-range degree values are not forced into the schema.
- `configs/output_control_policy.md` now documents the Anthropic-compatible tool-use candidate policy used by C1/C2/C3/C4 pilot validation.
- B1_prime remains candidate / pre-freeze only. Automatic field-to-leg linking is not allowed inside B1_prime; it is registered as the separate Group 1 candidate `B1_prime_link` after B1_prime. Any manual, gold, oracle, or target-aware linking variant remains outside Group 1.

These changes are intended to reduce format/schema instability before freezing. They do not add target JSON, scorer output, CIFP records, human labels, OCR text to no-OCR methods, image input to text-only methods, or any sample-specific correction.

### D_SFT

D_SFT is the paper-v2 supervised fine-tuned visual model:

```text
full chart image -> SFT VLM -> canonical JSON
```

It is distinct from the legacy repository `D` image single-pass JSON baseline.
D_SFT inference must not receive OCR text, field candidates, CIFP/424 records,
target JSON, scorer output, human answers, or other method predictions.

Frozen candidate method card: `docs/d_sft_method_card.md`.
Frozen config: `training/d_sft/configs/d_sft_training_config.frozen_20260428_r1.json`.
Freeze report: `training/d_sft/reports/d_sft_freeze_report_20260428_r1.md`.

Pilot100 feasibility run `d_sft_pilot100_promptv2_prefill_20260428_r1`
completed with 94/100 schema-valid outputs and field-level score
1014/2200 = 0.460909 over scored samples. This is not a formal300 result.

## B1

| Field | Value |
|---|---|
| `method_id` | `B1` |
| `paper_alias` | Full-chart OCR + LLM |
| `experiment_group` | 1 |
| `method_family` | text_llm_from_full_chart_ocr |
| `freeze_status` | boundary frozen |
| `main_leaderboard` | yes |
| `oracle` | no |
| `diagnostic` | no |
| `prompt_required` | yes, final prompt not frozen yet |
| `model_required` | yes, final model not frozen yet |
| `parser_required` | strict JSON parser + schema validator |
| `final_output_type` | extraction canonical JSON |
| `final_output_schema` | `schemas/missed_approach_leg.schema.json` |

### B1 Method Equation

```text
full chart image
  -> registered full-chart OCR
  -> OCR text only
  -> LLM
  -> canonical JSON
```

### B1 Allowed Inputs

- `chart_id`
- `airport`
- `approach_ident`
- `chart_name`
- full-chart OCR text
- canonical output contract

### B1 Forbidden Inputs

- chart image pixels at LLM stage
- OCR bbox / coordinates
- ROI / prelabels / human annotation boxes
- automatic field candidates
- field-to-leg candidates
- gold MA prose
- gold observable evidence
- canonical target / answer key
- `field_targets.jsonl`
- `evidence_provenance.jsonl`
- `challenge_tags.jsonl`
- scorer outputs
- CIFP / ARINC 424 records
- historical model output for the same chart

### B1 Frozen Notes

B1 tests whether an LLM can recover the missed approach canonical schema from full-chart OCR text alone. If field candidates are added, the method becomes B1_prime or another registered variant, not B1.

For formal Experiment Group 1, the B1 OCR text must come from the registered
ordinary OCR-1 source in `configs/ocr_source_manifest.json`. MLLM/VLM-generated
transcription is not valid OCR-1 evidence for B1.

### B1 Expanded Pilot Evidence

Pilot100 external expanded validation:

- run_id: `pilot100_b1_b1prime_gpt54_toolcall_schema_retry1_ordinary_ocr_20260428_r1`
- sample role: expanded feasibility only, excluded from formal300
- OCR-1: PaddleOCR PP-OCRv5 ordinary OCR
- output control: OpenAI-compatible forced tool call to canonical schema
- schema-valid: 100/100
- parser repair: 0
- schema-only retries: 7/100
- score: 723/2344 = 0.308447

Interpretation: the B1 boundary and output path are stable on the expanded pilot set, but prompt/model/max_tokens remain candidate rather than formally frozen.

## C3

| Field | Value |
|---|---|
| `method_id` | `C3` |
| `paper_alias` | Full-chart image -> VLM questionnaire -> canonical JSON |
| `experiment_group` | 1 |
| `method_family` | vlm_questionnaire |
| `freeze_status` | boundary frozen |
| `main_leaderboard` | yes |
| `oracle` | no |
| `diagnostic` | no |
| `prompt_required` | yes, final prompt not frozen yet |
| `model_required` | yes, final model not frozen yet |
| `parser_required` | questionnaire-to-canonical deterministic parser |
| `intermediate_output_type` | questionnaire JSON |
| `final_output_type` | extraction canonical JSON |
| `final_output_schema` | `schemas/missed_approach_leg.schema.json` |

### C3 Method Equation

```text
full chart image
  -> VLM fixed questionnaire JSON
  -> deterministic questionnaire-to-canonical parser
  -> canonical JSON
```

### C3 Allowed Inputs

- `chart_id`
- `airport`
- `approach_ident`
- `chart_name`
- full chart image
- questionnaire output contract
- deterministic questionnaire-to-canonical parser

### C3 Forbidden Inputs

- OCR text
- OCR bbox / coordinates
- ROI / prelabels / human annotation boxes
- automatic field candidates
- field-to-leg candidates
- gold MA prose
- gold observable evidence
- canonical target / answer key
- `field_targets.jsonl`
- `evidence_provenance.jsonl`
- `challenge_tags.jsonl`
- scorer outputs
- CIFP / ARINC 424 records
- historical model output for the same chart

### C3 Frozen Notes

C3 questionnaire JSON is an intermediate artifact only. The final prediction for scoring must be canonical JSON produced by the deterministic parser. The parser may only rearrange questionnaire fields into the canonical schema; it must not repair semantics, consult targets, or infer missing values.

C3 does not receive OCR text in the registered Group 1 boundary.

## B1_prime Placeholder

B1_prime is not frozen in this revision. The current method decision is recorded in:

```text
reports/pilot/b1prime_method_decision_20260428.md
```

External B1_prime artifacts are stored under:

```text
E:\experiment3\try_B1_B1'
```

Current intended boundary:

```text
full-chart OCR text
  -> automatic field matching
  -> OCR text + flat field candidates
  -> LLM
  -> canonical JSON
```

B1_prime must remain distinct from B1_link. Flat field candidates must not encode gold leg mappings or expected values.

Current decision:

- B1_prime v8 is candidate / pre-freeze only.
- It can be used for pilot comparisons and boundary discussion.
- It is not formally frozen for formal300.
- Further leg-indexed or schema-field-linked repairs must move to B1_link / Group 5.

### B1_prime Expanded Pilot Evidence

Pilot100 external expanded validation:

- run_id: `pilot100_b1_b1prime_gpt54_toolcall_schema_retry1_ordinary_ocr_20260428_r1`
- sample role: expanded feasibility only, excluded from formal300
- OCR-1: PaddleOCR PP-OCRv5 ordinary OCR
- field_candidates: OCR-text-derived flat candidates only
- field_candidates schema-valid: 100/100
- output control: OpenAI-compatible forced tool call to canonical schema
- final schema-valid: 100/100
- parser repair: 0
- schema-only retries: 11/100
- score: 674/2344 = 0.287543

Interpretation: B1_prime is runnable and schema-stable, but it underperformed B1 on pilot100. Do not formally freeze the matcher/prompt until error analysis explains when the flat field_candidates help or hurt.

### B1_prime v4 Candidate Smoke Evidence

Boundary-safe repair report:
`reports/pilot/pilot100_b1prime_v4_smoke18_20260428.md`.

- matcher: `ocr_text_only_regex_field_matcher_pilot_v4`
- prompt: weak-evidence candidate policy added to the B1_prime prompt
- local candidate audit: `pilot100_b1prime_field_matcher_v4_candidate_audit_20260428_r3`, 100/100 `field_candidates` schema-valid, 0 model calls
- smoke run: `pilot100_b1prime_v4_smoke18_gpt54_toolcall_schema_retry1_ordinary_ocr_20260428_r1`
- smoke output: 18/18 schema-valid, 0 parser repair, 0 schema retries, 118/438 = 0.269406
- comparison on the smoke subset: B1 old 114/438, B1_prime v3 old 89/438, B1_prime v4 118/438
- decision: do not run the 30-chart probe yet; v4 remains candidate because 5/18 smoke outputs still produced empty legs, including 4 of the original 7 v3 empty-leg failures and one new failure.

### B1_prime v7 Candidate Smoke and Probe Evidence

Boundary-safe repair report:
`reports/pilot/pilot100_b1prime_v7_smoke18_probe30_20260428.md`.

- matcher: `ocr_text_only_regex_field_matcher_pilot_v7`
- schema addition: `instruction_snippets`, an OCR-only continuous span around the published missed approach instruction
- prompt: weak-evidence policy plus conservative non-empty leg skeleton rule when OCR contains a usable missed approach instruction
- local candidate audit: `pilot100_b1prime_field_matcher_v7_candidate_audit_20260428_r1`, 100/100 `field_candidates` schema-valid, 0 model calls
- smoke run: `pilot100_b1prime_v7_smoke18_gpt54_toolcall_schema_retry1_ordinary_ocr_20260428_r1`
- smoke output: 18/18 schema-valid, 0 parser repair, 0 schema retries, 0 empty-leg outputs, 159/438 = 0.363014
- smoke comparison: B1 old 114/438, B1_prime v3 old 89/438, B1_prime v4 118/438, B1_prime v7 159/438
- probe run: `pilot100_b1prime_v7_probe30_gpt54_toolcall_schema_retry1_ordinary_ocr_20260428_r1`
- probe output: 30/30 schema-valid, 0 parser repair, 2 schema-only retries, 0 empty-leg outputs, 191/606 = 0.315182
- probe comparison: B1 old 216/606, B1_prime v3 old 179/606, B1_prime v7 191/606
- decision: v7 fixes the catastrophic empty-leg failure mode but is not formally frozen. Probe30 remains below B1 old, and hard RNAV/LOC multi-leg cases are still under-segmented.

Hard-case error analysis:
`reports/pilot/pilot100_b1prime_v7_hard_case_error_analysis_20260428.md`.

Decision from hard-case analysis: one more B1_prime candidate repair is allowed only if it remains OCR-text-only and flat, for example degree-symbol parsing and flat `track_to_fix_snippets` / `route_sequence_snippets`. Any leg-indexed or schema-field-assigned linking belongs to B1_link / Experiment Group 5, not B1_prime.

### B1_prime v8 Candidate Hard4 Evidence

Boundary-safe v8 report:
`reports/pilot/pilot100_b1prime_v8_hard4_20260428.md`.

- matcher: `ocr_text_only_regex_field_matcher_pilot_v8`
- schema addition: flat `track_to_fix_snippets` and `route_sequence_snippets`
- local candidate audit: `pilot100_b1prime_field_matcher_v8_candidate_audit_20260428_r2`, 100/100 `field_candidates` schema-valid, 0 model calls
- hard4 smoke run: `pilot100_b1prime_v8_hard4_gpt54_toolcall_schema_retry1_ordinary_ocr_20260428_r1`
- hard4 output: 4/4 schema-valid, 0 parser repair, 0 schema retries, 27/160 = 0.16875
- hard4 comparison: v7 same cases 13/160, v8 27/160
- interpretation: v8 helps explicit track-to-fix prose cases (`KPVU_R13`, `KAVO_R05`, `KEGE_RNV-D`) but does not solve route-table-only RNAV (`KLLJ_RNV-A`)
- decision: v8 remains candidate, not formal freeze. Do not introduce leg-indexed linking into B1_prime; use the separately registered `B1_prime_link` candidate for automatic non-target-aware linking, and reserve any manual/gold/oracle linking variants for Group 5 diagnostics.

## B1_prime_link Candidate

`B1_prime_link` is added to Experiment Group 1 as a separate candidate method after `B1_prime`.

It is not a replacement for `B1_prime` and it must not be reported as `B1_prime`. The scientific question is whether an automatic, non-target-aware field-to-leg linking stage helps an OCR+LLM method beyond flat OCR-text-derived field candidates.

```text
full chart image
  -> registered OCR-1 full-chart text
  -> automatic OCR-text-only flat field candidates
  -> automatic non-target-aware field-to-leg candidate linking
  -> OCR text + field_to_leg_links
  -> text LLM
  -> canonical JSON
```

Allowed inputs:

- `chart_id`
- `airport`
- `approach_ident`
- `chart_name`
- registered OCR-1 full-chart text
- OCR-text-derived flat `field_candidates`
- automatic `field_to_leg_links` derived only from the same OCR text and flat field candidates
- canonical output contract

Forbidden inputs:

- chart image pixels at LLM stage
- OCR bbox / coordinates
- ROI / visual cells
- gold MA prose
- gold observable evidence
- canonical target / answer key
- expected value fields
- PR32 target-aware mapping
- manual or gold field-to-leg mapping
- `field_targets.jsonl`
- `evidence_provenance.jsonl`
- `challenge_tags.jsonl`
- scorer outputs
- CIFP / ARINC 424 records
- human annotation
- historical model output for the same chart

Candidate artifacts registered in this repository:

- prompt: `prompts/paper_v2/b1_prime_link_ocr_candidates_links_to_canonical.zh_v0_candidate.md`
- field-to-leg schema: `schemas/field_to_leg_links.schema.candidate.json`
- method card: `docs/b1_prime_link_method_card.md`
- pilot100 revalidation JSON: `reports/pilot/b1_prime_link_group1_candidate_pilot100_revalidation_20260429.json`
- pilot100 report: `reports/pilot/b1_prime_link_group1_candidate_pilot100_20260429.md`

Pilot100 external validation, excluded from formal300:

- run_id: `b1prime_link_v2_pilot100_gpt54_toolcall_promptfix_20260428_r2`
- artifact root: `E:\experiment3\B1'_link`
- OCR-1: PaddleOCR PP-OCRv5 ordinary OCR, inherited from the pilot100 OCR-1 artifact set
- text LLM: `gpt-5.4`
- output control: OpenAI-compatible forced tool call to canonical schema
- schema-valid: 100/100
- field-to-leg link schema-valid: 100/100 sample files
- parser repair: 0
- schema-only retries: 1/100
- score: 1031/2344 = 0.439846
- comparison on the same pilot100 set: B1 723/2344 = 0.308447; B1_prime 674/2344 = 0.287543

Decision: `B1_prime_link` passes pilot100 feasibility as a Group 1 candidate / pre-freeze method. It is not formally frozen here because formal300 split/targets, final model/provider parameters, final rerun policy, and formal scorer still need separate freeze.

## B1_link Placeholder

B1_link was originally defined by issue #10 as an experiment group 5 diagnostic variant. The automatic, non-target-aware version is now separately registered as the Group 1 candidate `B1_prime_link`.

Any B1_link variant that uses manual links, gold links, target-aware mappings, scorer feedback, or oracle evidence remains an experiment group 5 diagnostic/ablation variant. Such variants are not main leaderboard methods and are not frozen in this revision.

Historical setup workspace that produced the now-registered `B1_prime_link` pilot100 artifacts:

```text
E:\experiment3\B1'_link
```

Historical setup artifacts:

- method manifest: `E:\experiment3\B1'_link\configs\method_manifest.json`
- field-to-leg schema: `E:\experiment3\B1'_link\schemas\field_to_leg_links.schema.json`
- linking-only report: `E:\experiment3\B1'_link\reports\b1prime_link_hard4_linking_only_20260428.md`

Residual Group 5 boundary, if later used for diagnostic variants, must be declared separately from `B1_prime_link`. The non-oracle automatic boundary already registered for Group 1 is:

```text
full-chart OCR text
  -> automatic field matching
  -> automatic field-to-leg candidate linking
  -> LLM
  -> canonical JSON
```

The field-to-leg table in the Group 1 candidate must remain a non-target-aware candidate artifact. It must not use canonical target, expected value, PR32 target-aware mapping, or human gold field-to-leg mapping.

## Strict Output Policy For Registered Extraction Methods

B1 and C3 use strict raw JSON v1:

```text
assistant_prefill_json: true
assistant_prefill_value: "{"
parser: trim whitespace -> JSON parse -> schema validation
```

Markdown code fences are format violations. Parser semantic repair is forbidden.
