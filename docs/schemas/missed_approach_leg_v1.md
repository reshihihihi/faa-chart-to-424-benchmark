# Missed-Approach Leg Canonical Schema v1

**Status**: draft for Issue #3
**Scope**: canonical JSON + three surface questionnaire forms + composite scoring rules
**Cycle context**: FAA CIFP 2604 (effective 16 APR 2026)

## 1. Purpose

This document freezes the canonical leg-level structure that every ABCDE method must
project into, regardless of its internal representation (flat fields for OCR+rules, JSON
from LLM, per-question aggregation for VLM QA, etc.). The same structure is produced by
the CIFP→proxy-GT pipeline (Issue #4) from raw ARINC 424 records.

Three surface questionnaire forms are defined on top of the canonical structure:

- **Canonical JSON** — target final form consumed by the evaluator
- **QA prompt bundle** — Method C's multi-turn question set (per leg, per question type)
- **Structured form template** — Method E's form-fill questionnaire

All three surfaces project to the same canonical JSON; the evaluator only sees
canonical JSON.

## 2. Top-level envelope

```json
{
  "chart_id": "KCOE_L06",
  "procedure": {
    "airport": "KCOE",
    "approach_ident": "L06",
    "chart_name": "ILS OR LOC RWY 06"
  },
  "missed_approach": {
    "leg_count": { "status": "present", "value": 4 },
    "legs": [ ... ]
  }
}
```

- `chart_id` is the dataset primary key (`{airport}_{approach_ident}`)
- `procedure.*` fields are data keys copied from the committed manifest; not method outputs
- `missed_approach.leg_count` is a **procedure-level** question; `missed_approach.legs` is the ordered sequence of per-leg answer bundles

## 3. Status enum

Every answered field carries a `status`:

| Status | Meaning |
|---|---|
| `present` | Chart publishes (or implies via standard convention) a definite value; value field is populated |
| `not_applicable` | This field has no meaning for this leg type (e.g., hold_params on a CA leg) |
| `not_observable` | Regulation allows chart to omit this + chart does not show it. See Issue #6 regulatory matrix |
| `unknown` | Method could not determine the value (with or without confidence) |

Inferable-by-convention values (1-min hold, standard LOC-aligned hold inbound course,
LEFT turn implied by preceding "climbing left turn" wording) **are `present`**, not
`not_observable`; reading comprehension expected.

## 4. Per-leg answer schema

Each leg = `{ leg_index: int, answers: { 6 keys } }`.

### 4.1 Q_terminator — ARINC 2-letter path terminator

Issue #26 requires exact ARINC code output, no semantic merging.

Value domain:
`CA CF CI CR DF FA FM HA HF HM IF RF TF VA VD VI VM VR AF CD FC FD VC PI` (24 codes)

Typical missed-approach distribution (from `missed_approach_extracted/_summary.json` on
the 100-sample set): HM, CA, DF, TF, CF, VI, FA. Others permitted by spec but rare.

### 4.2 Q1_fix_ident — the fix this leg references

The fix associated with this leg's geometry. Role implicit from `Q_terminator`:

| Terminator | Fix role |
|---|---|
| CF / DF / TF / AF | Terminator fix |
| FA / FC / FD / FM | Origin fix |
| HA / HF / HM | Hold fix |
| IF | Initial fix |
| CA / VA / VD / VI / VM / VR / CD / CI / CR / VC / RF / PI | no fix reference; status = `not_applicable` |

Value = ident string (5 chars max, e.g., `"COE"`, `"MUDRE"`, `"RW06"`) or `null`.

### 4.3 Q2_altitude_constraint — **composite**

Entire answer scores as one atom: `desc` + `altitude_ft` (+ optional `altitude_2_ft` for
BETWEEN) **must all match** or it's `contradicted`.

```json
{
  "status": "present",
  "value": {
    "desc": "AT_OR_ABOVE",
    "altitude_ft": 2900,
    "altitude_2_ft": null
  }
}
```

`desc` domain: `AT`, `AT_OR_ABOVE`, `AT_OR_BELOW`, `BETWEEN`.

ARINC 5.29 raw → canonical mapping:

| 5.29 raw | canonical `desc` |
|---|---|
| blank, `@` | `AT` |
| `+` | `AT_OR_ABOVE` |
| `-`, `V` | `AT_OR_BELOW` |
| `B` | `BETWEEN` (uses both `altitude_ft` and `altitude_2_ft`) |
| `G`, `H`, `I`, `J`, `X`, `Y`, `C` | `AT` (glideslope-specific; rare in missed-approach legs) |

`altitude_ft` is integer feet. `FL180` → `18000`.

Method outputs `{ "status": "not_applicable", "value": null }` when leg has no altitude
constraint at all (rare; most missed-approach legs have at least a climb-to target).

### 4.4 Q3_turn — turn direction during this leg

| Leg shape | Expected answer |
|---|---|
| Straight leg (CA, VA, TF without curvature, IF) | `not_applicable` |
| Turning leg (DF, CF with preceding turn text, FA with turn text, RF) | `"LEFT"` or `"RIGHT"` |
| Hold leg (HA/HF/HM) | `not_applicable`; hold turn direction lives in Q5_hold_params |

### 4.5 Q4_course_or_radial — course / heading / radial reference for this leg

Discriminated union on `type`:

```jsonc
// Variant A — magnetic course / track
{ "type": "course_deg", "course_deg": 51 }

// Variant B — navaid radial reference
{ "type": "navaid_radial", "navaid": "COE", "radial_deg": 350, "direction": "outbound" }
// direction ∈ { "outbound", "inbound" }

```

`course_deg` is float, 1 decimal, range `[0.0, 359.9]`. Magnetic by default; a true-course
flag is recorded in extraction-schema but not in canonical output.
DF/direct-to-fix legs do not populate Q4; the direct-to fix is represented by
`Q_terminator = DF` plus `Q1_fix_ident`, so Q4 is `not_applicable`.

Hold legs: `not_applicable`; hold's inbound course lives in Q5_hold_params.

### 4.6 Q5_hold_params — **composite**, only for HA / HF / HM

All four sub-fields scored jointly:

```json
{
  "status": "present",
  "value": {
    "inbound_course_deg": 51,
    "leg_time_min": 1.0,
    "leg_distance_nm": null,
    "turn": "LEFT"
  }
}
```

- `inbound_course_deg` float, magnetic
- Exactly ONE of `leg_time_min` (typical) / `leg_distance_nm` (RNAV distance-based) is
  non-null; the other is null
- `turn` ∈ `{ "LEFT", "RIGHT" }`

For non-hold legs: `{ "status": "not_applicable", "value": null }`.

## 5. Worked example — KCOE_L06 (complete canonical JSON)

The chart, CIFP raw records, and extraction output live in
`data/v2604_100/missed_approach_review/KCOE_L06/`.

```json
{
  "chart_id": "KCOE_L06",
  "procedure": {
    "airport": "KCOE",
    "approach_ident": "L06",
    "chart_name": "ILS OR LOC RWY 06"
  },
  "missed_approach": {
    "leg_count": { "status": "present", "value": 4 },
    "legs": [
      {
        "leg_index": 1,
        "answers": {
          "Q_terminator": { "status": "present", "value": "CA" },
          "Q1_fix_ident": { "status": "not_applicable", "value": null },
          "Q2_altitude_constraint": {
            "status": "present",
            "value": { "desc": "AT_OR_ABOVE", "altitude_ft": 2900, "altitude_2_ft": null }
          },
          "Q3_turn": { "status": "not_applicable", "value": null },
          "Q4_course_or_radial": {
            "status": "present",
            "value": { "type": "course_deg", "course_deg": 51 }
          },
          "Q5_hold_params": { "status": "not_applicable", "value": null }
        }
      },
      {
        "leg_index": 2,
        "answers": {
          "Q_terminator": { "status": "present", "value": "FA" },
          "Q1_fix_ident": { "status": "present", "value": "COE" },
          "Q2_altitude_constraint": {
            "status": "present",
            "value": { "desc": "AT_OR_ABOVE", "altitude_ft": 6000, "altitude_2_ft": null }
          },
          "Q3_turn": { "status": "present", "value": "LEFT" },
          "Q4_course_or_radial": {
            "status": "present",
            "value": { "type": "navaid_radial", "navaid": "COE", "radial_deg": 350, "direction": "outbound" }
          },
          "Q5_hold_params": { "status": "not_applicable", "value": null }
        }
      },
      {
        "leg_index": 3,
        "answers": {
          "Q_terminator": { "status": "present", "value": "CF" },
          "Q1_fix_ident": { "status": "present", "value": "COE" },
          "Q2_altitude_constraint": {
            "status": "present",
            "value": { "desc": "AT_OR_ABOVE", "altitude_ft": 6500, "altitude_2_ft": null }
          },
          "Q3_turn": { "status": "present", "value": "LEFT" },
          "Q4_course_or_radial": {
            "status": "present",
            "value": { "type": "navaid_radial", "navaid": "COE", "radial_deg": 350, "direction": "inbound" }
          },
          "Q5_hold_params": { "status": "not_applicable", "value": null }
        }
      },
      {
        "leg_index": 4,
        "answers": {
          "Q_terminator": { "status": "present", "value": "HM" },
          "Q1_fix_ident": { "status": "present", "value": "COE" },
          "Q2_altitude_constraint": {
            "status": "present",
            "value": { "desc": "AT_OR_ABOVE", "altitude_ft": 6500, "altitude_2_ft": null }
          },
          "Q3_turn": { "status": "not_applicable", "value": null },
          "Q4_course_or_radial": { "status": "not_applicable", "value": null },
          "Q5_hold_params": {
            "status": "present",
            "value": {
              "inbound_course_deg": 51,
              "leg_time_min": 1.0,
              "leg_distance_nm": null,
              "turn": "LEFT"
            }
          }
        }
      }
    ]
  }
}
```

## 6. Extraction-schema vs canonical-schema

Two schemas coexist in the project:

| Aspect | Extraction schema | Canonical (this doc) |
|---|---|---|
| Where | `data/v2604_100/missed_approach_extracted/{chart_id}.json` | `data/v2604_100/missed_approach/{chart_id}.json` |
| Producer | `scripts/extract_missed_approach.py` (Issue #4) | projection from extraction schema via deterministic mapper |
| Purpose | Preserve all ARINC 424 per-leg fields + `raw_record` for evidence | Evaluator-facing; aligned 1:1 with method outputs |
| Field count per leg | ~22 (ARINC fields minus hygiene) | 6 composite questions + leg_index |
| Includes `raw_record`? | Yes | No |
| Includes path_terminator? | Yes (`path_terminator`) | Yes (`Q_terminator`) |
| Includes FAA-synthesized altitudes flagged? | Yes (raw) | As `status: not_observable` when applicable (per Issue #6 matrix) |

The projection rules live in the companion script `scripts/project_canonical.py` (to be
added alongside Issue #4). Projection is deterministic; no human judgment.

## 7. Questionnaire surface forms

Method-specific surfaces, all targeting the same canonical JSON:

- **Canonical JSON form** (this file's main subject) — final form
- **QA prompt bundle** — `prompts/path_c_qa_v2/` — 7 files: `q0_leg_count.txt`,
  `q_terminator.txt`, `q1_fix_ident.txt`, `q2_altitude_constraint.txt`, `q3_turn.txt`,
  `q4_course_or_radial.txt`, `q5_hold_params.txt`
- **Structured form template** — `prompts/path_e_v2/structured_form_template.txt` —
  single file; VLM fills slots

Both prompt bundles are sources of truth for their respective methods; any change here
that affects the prompts must update the prompts.

## 8. Composite scoring rules (for Issue #9 scorer)

Fields that score as one atom (desc + value must all match):

- `Q2_altitude_constraint` — `desc` + `altitude_ft` + `altitude_2_ft`
- `Q4_course_or_radial` — `type` + all sub-fields for that variant
- `Q5_hold_params` — `inbound_course_deg` + (`leg_time_min` or `leg_distance_nm`) + `turn`

Leg-level end-to-end correctness (for Issue #14 per-leg F1):
- Hit: every Q has status match AND (for `present` status) value match
- Partial: ≥ 1 Q correct, ≥ 1 Q wrong
- Contradicted: ≥ 1 Q value mismatch under `present` status
- Missing: leg absent from method output where GT expects one
- Extra: leg present in method output where GT has none

Numeric tolerances (to be finalized in error_taxonomy.md during Issue #9):

| Field | Tolerance |
|---|---|
| `altitude_ft` | exact |
| `course_deg`, `radial_deg`, `inbound_course_deg` | ±1.0° |
| `leg_time_min` | exact (values are always 0.5-min multiples in practice) |
| `leg_distance_nm` | ±0.1 NM |

## 9. Open points

- Issue #6 regulatory matrix determines which per-field cases trigger `not_observable`
- Issue #9 scorer may revise numeric tolerances based on pilot data
- Issue #14 will finalize whether `Q_terminator` shares the same F1 bucket as
  other fields or is reported as its own score
