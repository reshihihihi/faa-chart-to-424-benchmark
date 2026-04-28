# Method Registry

Status: partial registry freeze for B1 and C3 on 2026-04-27.

This registry is the source of truth for method boundaries, allowed inputs, forbidden inputs, intermediate artifacts, and final output types. Only B1 and C3 are frozen in this revision. Other methods will be added in later freeze steps.

## Summary

| Method | Experiment Group | Frozen Status | Main Leaderboard | Intermediate Output | Final Output |
|---|---:|---|---:|---|---|
| B1 | 1 | boundary frozen | yes | full-chart OCR text | canonical JSON |
| C3 | 1 | boundary frozen | yes | questionnaire JSON | canonical JSON |
| B1_prime | 1 | candidate prefreeze | yes | flat automatic field candidates | canonical JSON |
| C4 | 1 | candidate prefreeze | yes | full-chart image + full-chart OCR text | canonical JSON |
| B1_link | 5 | issue-defined, not implemented | no | field-to-leg candidate table | canonical JSON |

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

## B1_prime

| Field | Value |
|---|---|
| `method_id` | `B1_prime` |
| `paper_alias` | Full-chart OCR + automatic field candidates + LLM |
| `experiment_group` | 1 |
| `method_family` | text_llm_from_full_chart_ocr_with_flat_field_candidates |
| `freeze_status` | candidate prefreeze, not formal |
| `main_leaderboard` | yes |
| `oracle` | no |
| `diagnostic` | no |
| `prompt_required` | yes, final prompt not frozen yet |
| `model_required` | yes, final model not frozen yet |
| `parser_required` | strict JSON parser + schema validator |
| `intermediate_output_type` | flat automatic field candidates |
| `final_output_type` | extraction canonical JSON |
| `final_output_schema` | `schemas/missed_approach_leg.schema.json` |

### B1_prime Method Equation

```text
full-chart OCR text
  -> automatic field matching
  -> OCR text + flat field candidates
  -> LLM
  -> canonical JSON
```

### B1_prime Allowed Inputs

- `chart_id`
- `airport`
- `approach_ident`
- `chart_name`
- full-chart OCR text
- flat automatic field candidates generated from the same OCR text
- canonical output contract

### B1_prime Forbidden Inputs

- chart image pixels at LLM stage
- OCR bbox / coordinates
- ROI / prelabels / human annotation boxes
- gold MA prose
- gold observable evidence
- canonical target / answer key
- `field_targets.jsonl`
- `evidence_provenance.jsonl`
- `challenge_tags.jsonl`
- scorer outputs
- CIFP / ARINC 424 records
- field-to-leg candidates
- gold field-to-leg mapping
- historical model output for the same chart

### B1_prime Candidate Notes

B1_prime is candidate-prefrozen for pilot reruns only. Its `field_candidates` artifact is an OCR-only flat candidate object defined in `schemas/field_candidates.schema.candidate.json`. It must remain distinct from B1_link: flat candidates must not encode leg mappings, schema-slot assignments, expected values, or target-aware hints.

The committed historical r3 result used matcher v2. The committed runner contains matcher v3 for the next candidate rerun, so matcher v3 needs a new run id before any score claim.

## C4

| Field | Value |
|---|---|
| `method_id` | `C4` |
| `paper_alias` | Full-chart image + full-chart OCR text -> VLM/MLLM -> canonical JSON |
| `experiment_group` | 1 |
| `method_family` | multimodal_llm_from_image_and_ocr |
| `freeze_status` | candidate prefreeze, not formal |
| `main_leaderboard` | yes |
| `oracle` | no |
| `diagnostic` | no |
| `prompt_required` | yes, final prompt not frozen yet |
| `model_required` | yes, final model not frozen yet |
| `parser_required` | strict JSON parser + schema validator |
| `intermediate_output_type` | none |
| `final_output_type` | extraction canonical JSON |
| `final_output_schema` | `schemas/missed_approach_leg.schema.json` |

### C4 Method Equation

```text
full chart image + registered full-chart OCR text
  -> VLM/MLLM
  -> canonical JSON
```

### C4 Allowed Inputs

- `chart_id`
- `airport`
- `approach_ident`
- `chart_name`
- full chart image
- full-chart OCR text from the same chart
- canonical output contract

### C4 Forbidden Inputs

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

### C4 Candidate Notes

C4 is candidate-prefrozen for pilot reruns only. It is a direct multimodal extraction method and must not be converted into a questionnaire method or a field-candidate method unless it is registered as a separate variant.

## B1_link Placeholder

B1_link is defined by issue #10 as an experiment group 5 diagnostic variant. It is not a main leaderboard method and is not frozen in this revision.

Current intended boundary:

```text
full-chart OCR text
  -> automatic field matching
  -> automatic field-to-leg candidate linking
  -> LLM
  -> canonical JSON
```

The field-to-leg table must remain a non-target-aware candidate artifact. It must not use canonical target, expected value, PR32 target-aware mapping, or human gold field-to-leg mapping.

## Strict Output Policy For Registered Extraction Methods

B1, C3, B1_prime, and C4 use strict raw JSON v1 in the current pilot artifacts:

```text
assistant_prefill_json: true
assistant_prefill_value: "{"
parser: trim whitespace -> JSON parse -> schema validation
```

Markdown code fences are format violations. Parser semantic repair is forbidden.
