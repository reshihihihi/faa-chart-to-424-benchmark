# field_candidates schema upgrade review - 2026-04-27

## What changed

B1_prime `field_candidates` was upgraded from flat primitive lists to flat candidate object arrays for future reruns.

Old pilot r1 format:

```json
{
  "fix_candidates": ["TRUNT"],
  "altitude_candidates": [1900, 3200],
  "turn_candidates": ["RIGHT"]
}
```

New candidate format:

```json
{
  "value": "TRUNT",
  "field_type": "fix_ident",
  "source": "ocr_text",
  "source_section": "missed_approach_text",
  "source_snippet": "Climb to 1900 then climbing right turn to 3200 direct TRUNT and hold.",
  "source_start_char": 325,
  "source_end_char": 330,
  "rule_id": "fix_ident_token_regex_v1",
  "confidence": null,
  "notes": null
}
```

This is still a flat candidate format. It does not contain leg binding.

## Files changed

- `docs/field_candidates_schema_v1_candidate.md`
- `schemas/field_candidates.schema.candidate.json`
- `scripts/run_b1prime_c4_pilot10.py`
- `prompts/paper_v2/b1_prime_ocr_field_candidates_to_canonical_pilot10.zh_v0_candidate.md`
- `configs/b1prime_c4_temporary_prefreeze_20260427.json`
- `README.md`

## Experiment plan alignment

The experiment plan defines B1_prime as:

```text
full chart -> OCR -> automatic field matching -> LLM -> canonical JSON
```

The schema upgrade matches this because the matcher still reads only the same chart's OCR text and produces automatic field candidates.

The plan also states that main experiments may use only information available to a real automatic system, and that scoring answers or target-aware annotation must not enter ordinary method inputs. The new schema explicitly records no-leakage flags and forbids target, scorer output, CIFP/ARINC 424, gold observable evidence, and human evidence mapping.

The plan's no-leakage checklist warns B1_prime against target-aware candidate mapping. The new format avoids this by not allowing `leg_index`, `candidate_leg_id`, `source_seq_no`, `schema_field`, `expected_value`, `target_value`, `Q_terminator`, or path terminator labels inside candidate objects.

## Relationship to Experiment Group 5

B1_prime remains a main extraction method with automatic OCR-derived flat candidates.

Experiment Group 5 may later introduce stronger diagnostic or oracle inputs, including parsed fields or field-to-leg linking, but those must be separately labeled. They should not be mixed into B1_prime.

## Validation performed

One generated KDKK_RNV-A object-format candidate file was validated against `schemas/field_candidates.schema.candidate.json`.

Result:

```text
schema_errors = 0
has_forbidden_keys = False
```

Saved example:

```text
examples/field_candidates/KDKK_RNV-A.field_candidates.v1_candidate.json
```

A dry run also confirmed that future run manifests record:

- `field_candidates_schema.path`
- `field_candidates_schema.sha256`
- `field_matcher.sha256`
- current B1_prime prompt hash
- current C4 prompt hash

## Remaining issues

The object format is better for auditability, but the matcher is still a simple pilot regex matcher. It still over-includes noisy tokens such as `OCR`, `FAA`, or place names. This is acceptable for pilot chain testing, but the matcher rules and stopwords should not be formally frozen yet.

Before formal300, decide whether to:

- keep noisy candidates as a deliberate weak automatic matcher;
- improve stopwords and source-section heuristics;
- add an OCR artifact manifest with OCR text hash and image hash;
- freeze candidate ordering and per-category limits.

## Current status

`field_candidates_schema_v1_candidate` is suitable for the next B1_prime/C4 pilot rerun, but it is not yet a formal freeze.
