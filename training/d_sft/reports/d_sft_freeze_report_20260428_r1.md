# D-SFT Freeze Report 20260428 r1

Status: frozen for next formal300 evaluation candidate. This is not a formal300 result.

## Method

D-SFT is full chart image -> SFT VLM -> canonical JSON. Inference forbids OCR text, field_candidates, CIFP raw records, target JSON, score files, human answers, and other method predictions.

## Frozen Inputs And Config

- Prompt: `training/d_sft/prompts/d_sft_image_to_canonical.v2.md` SHA256 `8e0f6d36c023e6d23b78655ab1a1910f49880d7bd473db75d4250681ac21445e`
- Schema: `schemas/missed_approach_leg.schema.json` SHA256 `cd62edf995344d73ae45fcfad4e9bff3412f58a42f9fb591f9ca08e399e26be9`
- Train/dev: 500 / 100, no fallback used; skipped source candidates: 8
- No leakage: hard_leakage = False; forbidden overlap counts = {'chart_id': 0, 'pdf_name': 0, 'exact_proc_key': 0, 'family_key': 0, 'image_path': 0, 'target_path': 0}
- Base model: `Qwen/Qwen2-VL-2B-Instruct` with QLoRA r=8, alpha=16
- Image resize: max_pixels=501760
- Output control: assistant prefill `{`, strict JSON only, no parser repair
- Inference max_new_tokens: 1536

## Training

- Run: `d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1`
- Epochs: 1; train samples: 500; dev samples: 100
- Best dev loss: 0.04459553452208638
- Final checkpoint: `E:\experiment3\d_sft\checkpoints\d_sft_formal_qwen2vl_lora_promptv2_prefill_20260428_r1\checkpoint-final`
- Adapter SHA256: `df5e5eb5e97ffb5b86368fb966705cddffe09e4dfaa622959859d2da9fc412e0`
- CUDA peak memory: 7.1405 GB

## Pilot100 Feasibility

- Run: `d_sft_pilot100_promptv2_prefill_20260428_r1`
- Samples: 100
- Schema-valid: 94
- Scored: 94
- Parse/schema failures: 6
- Field-level score: 1014 / 2200 = 0.460909

Failures counted, not repaired:

- pilot100_external_009 `KARR_L33` inference_or_parse: JSONDecodeError('Extra data: line 1 column 1487 (char 1486)')
- pilot100_external_024 `KABR_R35` schema_validation: missed_approach.legs.1.answers.Q1_fix_ident.value: 'FISOPO' is not valid under any of the given schemas
- pilot100_external_034 `KEWR_R11` schema_validation: missed_approach.legs.1.answers.Q1_fix_ident.value: 'JKLINE' is not valid under any of the given schemas
- pilot100_external_053 `KOLY_R11` schema_validation: chart_id: 'OL11_R11' does not match '^[A-Z]{4}_[A-Z0-9\\-]+$'
- pilot100_external_078 `KMCW_I36` schema_validation: missed_approach.legs.0.answers.Q4_course_or_radial.value: {'type': 'course_deg', 'course_deg': 360.0} is not valid under any of the given schemas
- pilot100_external_100 `KCLW_RNV-A` schema_validation: chart_id: 'KLW_RNV-A' does not match '^[A-Z]{4}_[A-Z0-9\\-]+$'

## Decision

Freeze this D-SFT candidate for the next formal300 evaluation. Do not selectively rerun the six failed pilot100 samples. The remaining required step for paper claims is formal300 evaluation under the same frozen method boundary.
