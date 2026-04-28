# Method Registry

Status: partial registry freeze for B1 and C3 on 2026-04-27.

This registry is the source of truth for method boundaries, allowed inputs, forbidden inputs, intermediate artifacts, and final output types. Only B1 and C3 are frozen in this revision. Other methods will be added in later freeze steps.

## Summary

| Method | Experiment Group | Frozen Status | Main Leaderboard | Intermediate Output | Final Output |
|---|---:|---|---:|---|---|
| B1 | 1 | boundary frozen | yes | full-chart OCR text | canonical JSON |
| C3 | 1 | boundary frozen | yes | questionnaire JSON | canonical JSON |
| B1_prime | 1 | not frozen | yes | flat automatic field candidates | canonical JSON |
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

## B1_prime Placeholder

B1_prime is not frozen in this revision.

Current intended boundary:

```text
full-chart OCR text
  -> automatic field matching
  -> OCR text + flat field candidates
  -> LLM
  -> canonical JSON
```

B1_prime must remain distinct from B1_link. Flat field candidates must not encode gold leg mappings or expected values.

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

B1 and C3 use strict raw JSON v1:

```text
assistant_prefill_json: true
assistant_prefill_value: "{"
parser: trim whitespace -> JSON parse -> schema validation
```

Markdown code fences are format violations. Parser semantic repair is forbidden.
