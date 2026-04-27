# B1/C3 Pilot10 Strict JSON Prefill Result - 2026-04-27

Status: pilot result, not formal freeze.

Run id:

```text
pilot10_exp1_b1_c3_strict_json_prefill_20260427_r1
```

Stored outputs:

```text
predictions/pilot10_external/b1_c3_strict_json_prefill_20260427_r1/
```

## What Was Tested

This pilot tested two paper-v2 methods on 10 external FAA charts that are
excluded from the formal evaluation set.

```text
B1: full-chart OCR text -> LLM -> canonical JSON
C3: full-chart image -> fixed questionnaire JSON -> deterministic parser -> canonical JSON
```

The run intentionally tested a strict raw-output protocol:

- raw model output must be one bare JSON object;
- markdown code fences are not accepted;
- no first-JSON-object extraction is accepted;
- no semantic repair is accepted;
- targets are used only after validation for scoring.

Prompt hashes in `configs/prompt_manifest.json` are repository-normalized LF
hashes for future reruns. The stored pilot `run_manifest.json` preserves the
local run-time prompt hashes from the machine that produced the pilot outputs.

## Why Prefill Was Added

A strict parser-only rerun without assistant prefill completed all model calls,
but both B1 and C3 returned markdown JSON code fences for all 10 samples. Those
outputs were correctly rejected as format violations.

A one-sample probe then tested Anthropic Messages assistant prefill with a
single opening brace. That probe produced bare JSON for both B1 and C3. The same
control was then used for all 10 samples.

This is an output-format control, not a semantic method change: the prefill does
not add target values, field candidates, ROI information, OCR text to C3, or
domain-rule content.

## Result Summary

| Method | strict JSON | schema-valid | scored | parser repair | failures | score |
|---|---:|---:|---:|---:|---:|---:|
| B1 | 10/10 | 10/10 | 10/10 | 0 | 0 | 94/220 = 42.73% |
| C3 | 10/10 | 10/10 | 10/10 | 0 | 0 | 66/220 = 30.00% |

Raw text inspection:

| Method | raw files | strict JSON files | files containing code fence |
|---|---:|---:|---:|
| B1 | 10 | 10 | 0 |
| C3 | 10 | 10 | 0 |

## Interpretation

The B1/C3 pipeline is runnable under a strict JSON-only parser when the API call
uses assistant prefill. The pilot does not prove that all 300 formal samples
will be format-stable, but it is stronger than the earlier one-sample probe and
the earlier 10-sample non-prefill run.

The scores should not be used for prompt tuning. Low field accuracy, especially
on path terminators, leg count, and route/course fields, may be a valid result
of these methods rather than a runner defect.

## Freeze Implications

Candidate pieces that can now be considered for later freeze:

- strict JSON-only parser policy;
- markdown code fence as format violation;
- assistant prefill JSON output control;
- B1 and C3 method boundaries;
- prompt and model manifests as pilot candidates;
- output artifact layout for raw text, parsed JSON, validation, scores, run
  manifest, and summary report.

Pieces that are still not formally frozen:

- prompt text for the final 300-sample evaluation;
- OCR artifact policy for formal B1 runs;
- final model/provider choice;
- rerun policy for parse/API/schema failures;
- formal300 sample manifest and split;
- scorer implementation/version.

## Key Files

```text
configs/prompt_manifest.json
configs/model_config_manifest.json
configs/parser_repair_policy.md
docs/method_registry.md
prompts/paper_v2/
scripts/run_b1_c3_pilot10_current.py
scripts/test_anthropic_strict_json_prefill.py
predictions/pilot10_external/b1_c3_strict_json_prefill_20260427_r1/run_manifest.json
predictions/pilot10_external/b1_c3_strict_json_prefill_20260427_r1/summary_report.json
```
