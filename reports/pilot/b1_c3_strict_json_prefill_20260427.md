# B1 / C3 Strict JSON + Prefill Pilot Evidence

Date: 2026-04-27

Run id:

```text
pilot10_exp1_b1_c3_strict_json_prefill_20260427_r1
```

Purpose:

- verify that B1 and C3 can run under strict raw JSON parsing;
- verify that assistant prefill with `{` prevents markdown code fences;
- preserve pilot evidence for pre-freeze decisions;
- avoid treating pilot scores as formal evaluation results.

## Sample Role

The run used 10 external pilot samples.

Decision:

```text
pilot10_external = pilot-only / external / excluded from formal evaluation
```

These samples must not be included in the formal 300-chart evaluation split.

## Frozen-Or-Candidate Context

Frozen by this evidence:

- strict raw JSON output policy;
- no parser semantic repair;
- no markdown code-fence stripping;
- assistant prefill JSON output control;
- B1/C3 artifact layout;
- B1/C3 method boundaries.

Not frozen by this evidence:

- final B1/C3 prompt text;
- final model/provider/max token settings;
- formal OCR artifact policy;
- formal targets and scorer.

## Call-Level Output Control

```text
assistant_prefill_json: true
assistant_prefill_value: "{"
```

This is a formatting control only. It is not a semantic hint and does not provide target, scorer, CIFP, ROI, or annotation information.

## Prompt Candidate Hashes

| Method | Prompt SHA256 | Status |
|---|---|---|
| B1 | `F2A2C27B534F93BB33D90834CC9FDDE4726E8AE267BB3D1134679827D1E2F2E3` | candidate, not formal frozen |
| C3 | `49E2BA9134E9C7737D98374786963424546123129C6FAA7D648DE8224E468E4E` | candidate, not formal frozen |

## Pilot Results

| Method | strict JSON | schema-valid | scored | parser repair count | failures | score | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| B1 | 10/10 | 10/10 | 10/10 | 0 | 0 | 94/220 | 42.73% |
| C3 | 10/10 | 10/10 | 10/10 | 0 | 0 | 66/220 | 30.00% |

Interpretation:

- The strict output chain worked for all 10 pilot samples.
- Raw model outputs were parseable as bare JSON.
- No markdown code fences were present in saved B1/C3 raw outputs.
- No parser repair was required.
- Low or high scores are pilot observations only and must not be used as formal evaluation conclusions.

## Contrast With Prompt-Only Strict Run

A prior strict run without assistant prefill failed parsing for both methods:

```text
run_id: pilot10_exp1_b1_c3_strict_json_20260427_r1
B1: 0/10 strict parse
C3: 0/10 strict parse
failure mode: model still emitted markdown code fences
```

This supports freezing assistant prefill as part of the strict JSON output protocol, rather than relying on prompt wording alone.

## Saved Artifact Layout

The pilot run preserved:

```text
raw_text/
raw_responses/
questionnaire_json/    # C3 only
canonical_json/
validation/
scores/
run_manifest.json
summary_report.json
logs/
```

Future formal-style runs should preserve the same classes of artifacts and must preserve failures instead of overwriting them.
