# Group 1 Model And Rerun Policy Audit - 2026-04-29

Status: **candidate_parameters_recorded_not_formal_frozen**

## Candidate Parameters

- B1/B1_prime/B1_prime_link: `gpt-5.4`, OpenAI-compatible, temperature 0, max_tokens 4096, forced `emit_canonical_json` tool call, schema retry count 1, parser repair false.
- C1/C2/C3/C4: `claude-sonnet-4-5-20250929`, Anthropic-compatible, temperature 0, tool use, max_tokens 4096 for C1/C3/C4 and 2048 per C2 QA call, schema retry count 1, parser repair false.
- A1/A2: deterministic rules; A1 uses OCR-1 PaddleOCR PP-OCRv5, A2 uses OCR-2 Tesseract 5.x.
- D-SFT: Qwen/Qwen2-VL-2B-Instruct QLoRA adapter, already frozen as a candidate for next formal300 evaluation, not a formal300 result.

## Rerun Meaning

A retry is a pre-registered recovery attempt for parse/schema/API failure. It must not use target, scorer, CIFP, human labels, or score information. Low accuracy is not a retry reason.

## Remaining Blockers
- Final base URL/provider identity must be recorded without credentials and tied to formal run ids.
- Retry policy must state how parse/schema failures score in formal tables, not only when rerun is allowed.
- Each formal runner must write per-sample attempt_count, retry reason, model config hash, prompt hash, parser hash, and scorer hash.
- C1/C3 pilot100 schema failures still need a pre-registered decision. The previous C4 high retry count was resolved by the 2026-04-29 output-control fix pilot100 validation, with 0 schema retries after API-failure recovery.

## Files
- JSON: `reports/freeze/group1_model_rerun_policy_audit_20260429.json`
