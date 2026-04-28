# B1/C3 Strict JSON Protocol Update - 2026-04-27

Status: pilot protocol update, not formal freeze.

## Purpose

This update addresses one pilot-only format problem: B1 and C3 raw model
outputs were wrapped in markdown JSON code fences during the first pilot runs.
Formal-style evaluation requires raw model output to be one bare JSON object.

This change does not tune prompts based on score, does not change B1 or C3
method boundaries, and does not add target, CIFP, annotation, field matching,
ROI, or manual repair information.

## Changes

1. B1 and C3 prompts no longer contain literal markdown code-fence sequences.
2. B1 and C3 prompts state a strict raw-output contract.
3. `scripts/run_b1_c3_pilot10_current.py` defaults to strict JSON only.
4. Markdown code fences, explanatory prefixes/suffixes, and first-object
   extraction are not accepted in formal-style runs.
5. `--allow-non-strict-json` remains available only as a pilot compatibility
   switch.
6. The successful pilot run uses assistant prefill with `{` to discourage
   markdown wrappers.

## Repository-Normalized Hashes

The hashes below are LF-normalized repository hashes for future reruns.

| File | SHA256 |
|---|---|
| `prompts/paper_v2/b1_ocr_to_canonical_pilot10.zh_v1_candidate.md` | `75BA4289068B8FE8B3C450C7C611F34E09736C4017BEB03814C9E3348D6F7CF0` |
| `prompts/paper_v2/c3_questionnaire_pilot10.zh_v1_candidate.md` | `6491F5BA621EC5A91256503234CD2A4C87142C32E4D735234E571B84D70DB294` |
| `prompts/paper_v2/ocr_full_chart_text.zh_v1_candidate.md` | `35C82663B4F1E6A1F38A9DF9538ED27076A224F935FC74E6955F84E097075AF7` |
| `scripts/run_b1_c3_pilot10_current.py` | `5F6A927E5DB445C613899B9A8ADA0AA3390EA58202F23CEC1B13D2EA8E9ADD59` |
| `scripts/test_anthropic_strict_json_prefill.py` | `528EA38AE3217AA640BB628DC30748A6EF8C09E59D9767C3358D8F32A05A8BD7` |

The stored pilot `run_manifest.json` preserves the local run-time prompt hashes
from the machine that produced the pilot outputs. The content is semantically
the same, but repository line-ending normalization changes the file hash.

## Validation

- Local repository integrity check passed.
- B1 prompt contains no literal markdown code-fence sequence.
- C3 prompt contains no literal markdown code-fence sequence.
- `pilot10_exp1_b1_c3_strict_json_prefill_20260427_r1` produced strict JSON
  for all B1 and C3 raw outputs.
