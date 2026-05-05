# Group 1 A1/A2 OCR + Rules Candidate v1

Status: candidate implementation spec, final pre-freeze optimization applied 2026-04-29, not formal frozen.

This document defines the first deterministic OCR + Rules baseline for Experiment Group 1.

## Method Boundary

| Method | Pipeline | OCR source | Rule source |
|---|---|---|---|
| A1 | full chart image -> OCR-1 -> Rules -> canonical JSON | registered OCR-1 | this deterministic rule set |
| A2 | full chart image -> OCR-2 -> Rules -> canonical JSON | registered OCR-2 | the same deterministic rule set |

A1 and A2 differ only in the registered OCR source. The rules, schema, parser, output layout, and scoring procedure must be identical. This makes A1/A2 an OCR-source comparison, not a rules comparison.

## Allowed Inputs

The rules runner may read only:

- `chart_id`
- `airport`
- `approach_ident`
- `chart_name`
- full-chart OCR text from the registered OCR source for the method
- OCR block confidence and bbox artifacts from the same registered OCR source, only for provenance sidecars
- the canonical JSON schema contract

## Forbidden Inputs

The rules runner must not read:

- chart image pixels after OCR has completed
- OCR from a different OCR source
- LLM or VLM output
- automatic field candidates from B1_prime
- field-to-leg candidates from diagnostic Group 5 methods
- gold missed-approach prose
- canonical target or answer key
- `field_targets.jsonl`
- `evidence_provenance.jsonl`
- `challenge_tags.jsonl`
- scorer outputs
- CIFP or ARINC 424 records
- human annotations
- previous model or rule outputs for the same chart
- web search or external aviation databases

## Deterministic Rule Set

The rules are intentionally conservative. Low score is acceptable if OCR text is noisy; the purpose is to measure what a fixed non-LLM rules baseline can extract from ordinary OCR.

### 1. Text Normalization

Allowed normalization:

- uppercase conversion
- whitespace collapse
- punctuation spacing normalization
- dash normalization
- removal of duplicated blank lines

Forbidden normalization:

- target-aware correction
- airport/procedure database lookup
- CIFP lookup
- manual correction
- LLM/VLM correction

### 2. Missed-Approach Window Detection

Search for the first occurrence of `MISSED APPROACH` or `MISSED APCH`.

If found, use the text window from that phrase to the first later boundary among:

- `CATEGORY`
- `CIRCLING`
- `APT ELEV`
- `TDZE`
- `TCH`
- `MIRL`
- `REIL`
- `HIRL`
- `NOTE:`
- `PROFILE`
- `CHART`

If no boundary is found, cap the window at 900 characters. If no missed-approach phrase is found, output `leg_count.status = unknown`, `leg_count.value = null`, and `legs = []`.

### 3. Clause Segmentation

Within the missed-approach window, split candidate clauses in flown order using:

- semicolon
- period
- ` THEN `
- `, THEN `

Do not reorder clauses by score or by target similarity. Do not merge clauses using target information.

### 4. Leg Creation

Create at most one canonical leg per candidate clause when the clause contains at least one of:

- climb / altitude phrase
- direct-to-fix phrase
- course / heading / radial phrase
- hold phrase

If no candidate clause is usable, output unknown leg count and empty legs.

### 5. Field Extraction

Extract only explicit OCR evidence from the clause.

Q_terminator:

- `DIRECT <IDENT>` -> `DF`
- `HOLD` or `HOLDING` -> `HM`
- `CLIMB TO <ALTITUDE>` with no fix or course -> `CA`
- `ON <NAVAID> R-<DEG>` with a named fix in the clause -> `CF`
- otherwise `unknown`

Q1_fix_ident:

- from `DIRECT <IDENT>`
- from `HOLD AT <IDENT>` or `HOLDING AT <IDENT>`
- from `TO <IDENT>` when the ident is not an altitude and is not a stopword
- otherwise `not_applicable` for CA-like climb-only legs, else `unknown`

Q2_altitude_constraint:

- `CLIMB TO <ALTITUDE>` or `TO <ALTITUDE>` -> `present`, value `{ "desc": "AT_OR_ABOVE", "altitude_ft": <ALTITUDE>, "altitude_2_ft": null }`
- otherwise `not_applicable`

Q3_turn:

- `LEFT TURN` or `LT TURN` -> `present`, value `LEFT`
- `RIGHT TURN` or `RT TURN` -> `present`, value `RIGHT`
- hold legs -> `not_applicable`
- otherwise `not_applicable`

Q4_course_or_radial:

- `DIRECT <IDENT>` -> `present`, value `{ "type": "direct" }`
- `R-<DEG>` or `RADIAL <DEG>` with a navaid -> `present`, value `{ "type": "navaid_radial", "navaid": <NAVAID>, "radial_deg": <DEG>, "direction": "outbound" | "inbound" }`
- `HEADING <DEG>`, `HDG <DEG>`, `COURSE <DEG>`, or `CRS <DEG>` -> `present`, value `{ "type": "course_deg", "course_deg": <DEG> }`
- hold legs -> `not_applicable`
- otherwise `unknown`

Degree policy:

- Degree-valued fields are schema-safe values in the range `0.0` through `359.9`.
- If ordinary OCR text displays `360`, encode it as `359.9`.
- If ordinary OCR text displays an out-of-range degree other than `360`, do not force it into the schema; leave the corresponding answer `unknown`.

Q5_hold_params:

- non-hold legs -> `not_applicable`
- hold legs -> `present` with available OCR-derived/inferable values:
  - inbound course from `INBOUND COURSE <DEG>`, `INBOUND <DEG>`, or nearby course label if present
  - turn from `LEFT TURNS` / `RIGHT TURNS`; otherwise standard right turns
  - leg time from explicit time if present; otherwise 1.0 minute as the standard hold default
  - leg distance from explicit NM distance if present; otherwise null

### 6. Status/Value Contract

Every answer must use the canonical `status/value` contract.

- concrete extracted values always go in `value`
- `status` is only one of `present`, `not_applicable`, `not_observable`, `unknown`
- when status is not `present`, value is null
- metadata fields (`chart_id`, `airport`, `approach_ident`, `chart_name`) are copied from the input manifest, not inferred from OCR

### 7. Schema-Safety Checks

Before writing a prediction, the rules runner must enforce source-agnostic schema safety:

- `leg_index` starts at 1 and increases without gaps.
- `leg_count.status = present` only when `leg_count.value` equals the number of emitted legs.
- `Q1_fix_ident.value`, when present, is at most 5 characters and is not a facility-type word.
- Degree fields use the degree policy above.
- Non-present answers have `value = null`.
- The runner does not add parser repair, semantic repair, scorer feedback, target values, or CIFP-derived corrections.

### 8. Output and Sidecars

The runner writes:

- canonical JSON predictions
- validation results
- optional rule evidence sidecars
- run manifest with OCR source, OCR artifact manifest hashes, rules version, code hash, schema hash, sample manifest, and per-sample OCR text hashes

Targets and scorer outputs are used only after schema validation for pilot analysis.

## Candidate v1 Audit Requirements

Before any promotion from candidate to formal freeze, a pilot run must demonstrate:

- A1 and A2 use byte-for-byte the same rule runner and rule spec.
- A1 and A2 differ only by registered OCR source.
- The run manifest records the OCR full-text path and SHA-256 hash for every sample.
- The run manifest records the OCR artifact run manifest and OCR artifact manifest hash when those files exist.
- Rule diagnostics may quote OCR text snippets, but they must not include target values, score rows, CIFP fields, or human labels.
- Low accuracy must not trigger rule edits unless the edit is justified by a source-agnostic parsing bug and assigned a new candidate version/run id.
