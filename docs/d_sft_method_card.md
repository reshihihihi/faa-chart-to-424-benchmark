# D-SFT Method Card

Status: frozen candidate for next formal300 evaluation, not a formal300 result.

Freeze report: `training/d_sft/reports/d_sft_freeze_report_20260428_r1.md`.
Training config: `training/d_sft/configs/d_sft_training_config.frozen_20260428_r1.json`.

## Method Identity

`D-SFT` is the paper-v2 supervised fine-tuned visual model baseline.

```text
full chart image
  -> supervised fine-tuned VLM
  -> canonical missed approach JSON
```

This method is not the legacy repository `D`. The legacy repository `D`
was an image single-pass JSON baseline and maps to the paper-facing C1-style
zero-shot image-to-JSON setting. `D-SFT` is a new supervised fine-tuning
method.

## Allowed Inputs At Inference

- full chart image pixels
- chart metadata needed only to route and name artifacts, such as `chart_id`
  and image path
- fixed D-SFT inference prompt
- canonical output contract and schema

## Forbidden Inputs At Inference

- OCR text
- OCR bounding boxes
- field candidates
- field-to-leg candidates
- CIFP or ARINC 424 records
- canonical target JSON
- score files or scorer feedback
- human answers or annotation fields
- other method predictions for the same chart
- any held-out evaluation label or target-derived hint

## Training Inputs

Training may use only training-split chart images and their training-split
canonical labels. Development labels may be used only for checkpoint selection
and diagnostic reporting. Held-out evaluation labels must not enter the training
JSONL, prompt tuning, hyperparameter choice, or checkpoint selection.

## Output

The assistant output must be canonical JSON conforming to:

```text
schemas/missed_approach_leg.schema.json
```

The output must be bare JSON. Markdown code fences, explanations, target
metadata, score metadata, and provenance notes are not valid assistant outputs.

## Leakage Policy

Before training, a no-leakage check must pass for:

- `chart_id`
- PDF file name
- exact airport/procedure key
- procedure family key
- image path
- target path

The forbidden set includes formal300, pilot10, pilot100 external feasibility
samples, and any future final evaluation samples. If hard leakage is found,
training must stop and the data must be rebuilt.

## Evaluation Role

Pilot100 external may be used only as a held-out feasibility check after
training. It must not be used for training, development, prompt tuning,
hyperparameter tuning, or checkpoint selection. Formal300 evaluation remains
the future formal paper result set.

The 2026-04-28 pilot100 feasibility run had 94/100 schema-valid outputs.
The six parse/schema failures are method failures and must not be selectively
rerun or repaired. A formal Group 1 freeze still needs the final formal300
artifact package and an invalid-output scoring rule before leaderboard
reporting.
