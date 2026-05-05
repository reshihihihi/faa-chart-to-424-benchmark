# Formal V4 SFT Verifier Specification

V4 is optional. It is a trained direct verifier:

full chart image + candidate 424-like record -> audit decision JSON

V4 may only be run if a no-leakage SFT train/dev split and checkpoint are
frozen before formal evaluation.

V4 inference may read:

- full chart image;
- candidate_record;
- non-answer case metadata.

V4 inference must not read:

- OCR text unless the training/inference method card explicitly defines a new
  multimodal SFT variant;
- canonical target;
- raw CIFP;
- labels;
- counterfactual type;
- gold error_fields;
- score files;
- QC decisions.

Output shape: {"consistent": true, "error_fields": []}

If no eligible checkpoint is frozen, report V4 as not run.
