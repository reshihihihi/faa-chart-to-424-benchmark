# C4 semantic regression review - 2026-04-27

Compared runs:

```text
r1: pilot10_exp1_b1prime_c4_strict_json_prefill_20260427_r1
r2: pilot10_exp1_b1prime_c4_field_candidates_v1_20260427_r2
method: C4
```

## Purpose

C4 r2 remained strict-JSON and schema-valid on all ten samples, but its score dropped from r1. This review checks whether the drop is a structural/schema issue, a prompt-induced semantic issue, or an expected method limitation.

## Overall change

```text
C4 r1: 114/220 = 51.82%
C4 r2:  83/220 = 37.73%
```

Largest drops:

```text
KDIJ_RNV-A: 19/31 -> 7/31
KDAG_R22:  16/31 -> 6/31
KFKL_V21:  15/19 -> 10/19
```

## KDIJ_RNV-A

Relevant OCR:

```text
MISSED APPROACH: (Do not exceed 185K until TOGRE)
Climb to 7500, then climbing right turn to 10000 direct
PIKEQ and hold.
Holding Pattern 002 / 029
```

Target has 5 legs:

```text
L1 CA climb to 7500
L2 DF TOGRE
L3 TF BRELD
L4 TF PIKEQ
L5 HM PIKEQ hold, 10000, inbound about 153, 7 NM
```

C4 r2 output has 4 legs:

```text
L1 CF TOGRE, 7500, RIGHT
L2 CF BRELD, 10000, course 002
L3 CF PIKEQ, course 029
L4 HF PIKEQ hold, 10000-17500
```

Main issue:

- r2 collapsed the initial climb-to-altitude leg into a fix-bearing leg.
- r2 shifted altitude 10000 from the hold/direct-climb context onto the wrong intermediate leg.
- r2 used CF for several track/fix legs and missed the CA/DF/TF/HM structure.

Likely cause:

- C4 prompt does not give enough general guidance to preserve an initial climb segment before a `then` transition.
- The model overuses visible fixes/course labels from image/OCR as leg anchors.

## KDAG_R22

Relevant OCR:

```text
MISSED APPROACH: Climb to 8000 direct CIKVI and on track 275 to BINTE and on track 192 to NULMN and hold, continue climb-in-hold to 8000.
```

Target has 5 legs:

```text
L1 CA initial climb
L2 DF CIKVI direct
L3 TF BINTE
L4 TF NULMN with 8000
L5 HM NULMN hold, 8000
```

C4 r2 output has 3 legs:

```text
L1 DF CIKVI, 8000, direct
L2 CF BINTE, track 275
L3 HF NULMN, 8000, track 192, hold
```

Main issue:

- r2 omitted the initial climb leg.
- r2 merged the NULMN track-to-fix leg and the holding leg.
- r2 treated track legs as CF rather than preserving a separate track-to-fix structure.

Likely cause:

- The prompt does not explicitly warn against collapsing sequential `direct ... and on track ... and on track ... and hold` clauses into fewer legs.

## KFKL_V21

Relevant OCR:

```text
MISSED APPROACH: Climb to
2200, then climbing right turn to
3300 direct FKL VOR and hold.
```

Target has 3 legs:

```text
L1 CA climb to 2200
L2 DF FKL, 3300, RIGHT, direct
L3 HM FKL hold, 3300
```

C4 r2 output has 4 legs:

```text
L1 CF climb to 2200, course 007
L2 DF FKL, 3300, RIGHT
L3 CF FKL, 3300, course 187
L4 HF FKL, 3300, hold
```

Main issue:

- r2 created an extra pre-hold FKL leg.
- r2 changed `climb to` altitude semantics from `AT_OR_ABOVE` to `AT`.
- r2 used a localizer/radial/course visual cue as the initial missed-approach course.

Likely cause:

- The prompt does not distinguish a hold depiction/course cue from a separate flown leg strongly enough.
- The prompt does not state that natural-language `climb to X` is an altitude constraint, not necessarily exact `AT`.

## Cross-sample pattern

C4 r2 is structurally valid but semantically unstable in three areas:

1. Leg decomposition:
   - misses initial climb legs;
   - collapses track-to-fix and hold legs;
   - sometimes creates extra pre-hold legs.

2. Field semantics:
   - overuses `CF`;
   - weak `Q_terminator`;
   - confuses `AT` and `AT_OR_ABOVE`;
   - assigns course/radial cues to the wrong leg.

3. Image/OCR conflict handling:
   - tends to use visible route/fix/course marks from the image without anchoring them to the missed-approach prose sequence.

## Prompt-change constraints

Allowed:

- clarify general flown-order decomposition;
- clarify that a climb segment before `then` may be a separate leg;
- clarify not to merge hold and track-to-fix legs;
- clarify altitude wording such as `climb to` as `AT_OR_ABOVE`;
- clarify to use `unknown` for path terminator when not inferable.

Forbidden:

- target-specific answers;
- score-driven examples from these samples;
- B1_prime `field_candidates`;
- gold observable evidence;
- CIFP or ARINC 424 records;
- scorer rows.

## Recommendation

Create a C4 prompt candidate revision that adds method-neutral semantic guidance:

- first derive the flown missed-approach sequence from OCR prose;
- use image evidence only to resolve or supplement that sequence;
- preserve initial climb segments, direct-to-fix segments, track-to-fix segments, and hold segments as separate legs when indicated;
- do not create extra legs solely from hold depiction/course labels;
- use `AT_OR_ABOVE` for natural-language `climb to X`;
- use `unknown` rather than hard-guessing path terminators when evidence is insufficient.

This does not change C4's allowed inputs or method boundary.
