# field_candidates schema v1 candidate

Status: candidate, not formally frozen

Date: 2026-04-27

Scope: B1_prime pilot and future B-family methods that use automatic field matching as an input.

## Purpose

`field_candidates` is an automatically generated, same-chart OCR-derived candidate table. It is used by B1_prime as an auxiliary input:

```text
full chart image -> OCR text -> automatic field candidate extraction -> OCR text + field_candidates -> LLM -> canonical JSON
```

It is not a target, not a scorer artifact, and not an oracle answer. It should help the model notice possible values in OCR text, while still requiring the model to decide procedure structure and leg order.

## Alignment With Experiment Plan

The experiment plan defines B1_prime as:

```text
full chart -> OCR -> automatic field matching -> LLM -> canonical JSON
```

The same plan also requires no-leakage controls: B1_prime must not use target-aware candidate mapping, and the matcher should read only OCR text or OCR artifacts. This schema follows that requirement by allowing only flat OCR-derived candidates and by forbidding field-to-leg linking.

## Required Boundary

B1_prime `field_candidates` may contain:

- candidate values found in the same chart's OCR text;
- OCR snippets around those values;
- source character offsets in the OCR text;
- rule identifiers for the automatic extractor;
- candidate type labels such as `fix_ident`, `altitude_ft`, or `turn_direction`.

B1_prime `field_candidates` must not contain:

- canonical target values;
- expected values;
- scorer output;
- CIFP or ARINC 424 records;
- human accepted evidence mapping;
- gold observable evidence;
- field-to-leg linking;
- schema slot assignment;
- `leg_index`, `candidate_leg_id`, `source_seq_no`, or any equivalent leg binding;
- `Q_terminator` answers or path terminator labels.

## Candidate Object Format

Each candidate item is an object:

```json
{
  "value": "TRUNT",
  "field_type": "fix_ident",
  "source": "ocr_text",
  "source_section": "missed_approach_text",
  "source_snippet": "Climb to 1900 then climbing right turn to 3200 direct TRUNT and hold.",
  "source_start_char": 325,
  "source_end_char": 330,
  "rule_id": "fix_ident_regex_v1",
  "confidence": null,
  "notes": null
}
```

The object records why a value is visible as a candidate. It does not say where that value belongs in the canonical missed approach legs.

## Top-Level Format

```json
{
  "schema_version": "field_candidates_schema_v1_candidate",
  "chart_id": "KDKK_RNV-A",
  "candidate_source": "ocr_text_only_regex_field_matcher_pilot_v1",
  "source_contract": {
    "source": "same_chart_full_chart_ocr_text",
    "allows_ocr_bbox": false,
    "allows_chart_image_pixels": false
  },
  "leakage_policy": {
    "uses_canonical_target": false,
    "uses_expected_value": false,
    "uses_gold_field_to_leg_mapping": false,
    "uses_human_evidence_provenance": false,
    "uses_gold_observable_evidence": false,
    "uses_cifp_or_arinc_424": false,
    "uses_scorer_output": false
  },
  "field_candidates": {
    "fix_candidates": [],
    "altitude_candidates": [],
    "turn_candidates": [],
    "course_candidates": [],
    "hold_candidates": [],
    "direct_phrase_snippets": [],
    "climb_phrase_snippets": []
  }
}
```

## Relationship To Experiment Group 5

Experiment Group 5 may use stronger oracle or diagnostic inputs to locate OCR, ROI, field matching, and rule reasoning bottlenecks. Those stronger inputs must be clearly labeled and must not be mixed into B1_prime.

Therefore:

- B1_prime uses flat candidates only.
- Group 5 may introduce parsed-field or field-to-leg diagnostic variants.
- If a method provides `leg_index`, schema-slot assignment, accepted evidence mapping, or expected values, it is not B1_prime and must be named as an oracle or diagnostic method.

## Current Candidate Status

This candidate schema is suitable for pilot reruns. It is not yet a formal freeze because the matcher rules, stopwords, candidate ordering, source-section detection, and final OCR artifact policy still need review before formal300 evaluation.
