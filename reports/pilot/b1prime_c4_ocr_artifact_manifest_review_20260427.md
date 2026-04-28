# OCR artifact manifest review - 2026-04-27

Created manifest:

```text
metadata/ocr_artifacts/pilot10_ocr_artifact_manifest_20260427.jsonl
metadata/ocr_artifacts/pilot10_ocr_artifact_manifest_20260427.summary.json
```

## Purpose

B1, B1_prime, and C4 all depend on full-chart OCR text. This manifest records which OCR text artifact belongs to which chart image so later pilot and formal runs can trace OCR provenance.

## Recorded fields

Each JSONL row records:

- `chart_id`
- `pilot_sample_id`
- `image_path`
- `image_sha256`
- `ocr_text_path`
- `ocr_text_sha256`
- `ocr_prompt_path`
- `ocr_prompt_sha256`
- `ocr_model`
- `ocr_provider`
- `ocr_run_id`
- `source_role`

## Source

OCR artifacts come from:

```text
pilot10_exp1_b1_c3_strict_json_prefill_20260427_r1/OCR/full_chart_text
```

OCR prompt hash:

```text
35c82663b4f1e6a1f38a9df9538ed27076a224f935fc74e6955f84e097075af7
```

Model/provider:

```text
claude-sonnet-4-5-20250929
anthropic_compatible
```

## Validation

```text
row_count: 10
all_images_hashed: true
all_ocr_text_hashed: true
```

## Status

This manifest is suitable for pilot provenance. It is not yet a formal OCR freeze for formal300.
