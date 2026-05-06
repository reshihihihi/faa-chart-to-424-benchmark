# Group 1 SFT extension run commands

## 1. Validate local paths

```powershell
python scripts\group1_sft\validate_group1_sft_workspace.py --paths training\group1_sft\configs\local_paths.local.json
```

## 2. Rebuild this run package

```powershell
python scripts\group1_sft\prepare_group1_sft_run_package.py --paths training\group1_sft\configs\local_paths.local.json --split-subset evaluation --out-dir formal_runs/group1/group1_sft_dbase50_20260504_r1
```

## 3. Train D1 plus chart evidence boxes on the development-50 train split

```powershell
python scripts\group1_sft\train_qwen2vl_group1_sft_lora.py --method D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL --paths training\group1_sft\configs\local_paths.local.json --run-id d1_chart_to_evidence_boxes_and_canonical_dev50_coarse3_20260504_r4 --epochs 1 --learning-rate 5e-5 --max-seq-length 4096
```

## 4. Same-backbone unfinetuned control

```powershell
python scripts\group1_sft\run_qwen2vl_group1_sft_inference.py --method D_BASE_SAME_BACKBONE --input-manifest formal_runs/group1/group1_sft_dbase50_20260504_r1\D_BASE_SAME_BACKBONE\input_manifest.jsonl --model-dir <base_vlm_model_dir> --prompt training\d_sft\prompts\d_sft_image_to_canonical.v2.md --json-schema schemas\missed_approach_leg.schema.json --scoring-manifest formal_runs/group1/group1_sft_dbase50_20260504_r1\scoring_manifest.jsonl --output-root formal_runs/group1/group1_sft_dbase50_20260504_r1\D_BASE_SAME_BACKBONE --run-id group1_sft_dbase50_20260504_r1_D_BASE_SAME_BACKBONE_raw
```

## 4b. Canonicalize and score the same-backbone control outputs

This post-processing uses the same mechanical D1 canonicalization policy: it fixes the output envelope and schema shape without using targets, scores, raw 424/CIFP records, OCR, or other method predictions to change answer values. Targets are used only after canonical JSON is written, for scoring.

```powershell
python scripts\run_d1_output_canonicalizer.py --sample-manifest formal_runs/group1/group1_sft_dbase50_20260504_r1\scoring_manifest.jsonl --input-manifest formal_runs/group1/group1_sft_dbase50_20260504_r1\D_BASE_SAME_BACKBONE\input_manifest.jsonl --raw-dir formal_runs/group1/group1_sft_dbase50_20260504_r1\D_BASE_SAME_BACKBONE\predictions\group1_sft_dbase50_20260504_r1_D_BASE_SAME_BACKBONE_raw\raw_text --schema schemas\missed_approach_leg.schema.json --scorer scripts\scorers\group1_canonical_field_scorer_v2.py --target-v2 <repo_root>\benchmark_exports\derived\v2\formal300\targets\scoring_equivalence_v2\canonical_proxy_gt_chart_display_v2.json --comparison-policy-v2 <repo_root>\benchmark_exports\derived\v2\formal300\targets\scoring_equivalence_v2\comparison_policy_v2.jsonl --policy <repo_root>\docs\d1_output_canonicalization_policy_zh.md --method-card <repo_root>\docs\d1_method_card_zh.md --out-root formal_runs/group1/group1_sft_dbase50_20260504_r1\D_BASE_SAME_BACKBONE_CANONICALIZED --run-id group1_sft_dbase50_20260504_r1_D_BASE_SAME_BACKBONE_CANONICALIZED --method D_BASE_SAME_BACKBONE --policy-id dbase_output_canonicalization_same_as_d1
```

Notes:

- Do not pass target JSON, score files, raw 424 records, or other method predictions to inference.
- `scoring_manifest.jsonl` is for post-prediction scoring only.
- `D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL` is the only new default method: it starts from the D1 adapter, learns evidence boxes, and still scores only `canonical_prediction`.
- `evidence_boxes` are diagnostic; the formal score uses only the extracted `canonical_prediction` object.
- The parser is strict JSON only; semantic repair is not applied.
