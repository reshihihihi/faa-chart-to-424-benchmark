# Formal300 PDF Duplicate Pre-Run Disposition - 2026-04-29

Status: **documented_not_missing_artifact_review_before_final_claims**

This note records the disposition of the `300 samples / 299 unique PDF files`
issue before deciding whether to start Group 1 formal300 method inference.

## Finding

The earlier audit found:

```text
sample rows: 300
unique sample_id: 300
unique chart_id: 300
unique pdf_file: 299
unique pdf_path: 299
missing referenced PDFs: 0
PDF hash mismatches: 0
rows with pdf_status != available: 0
```

Therefore, this is **not** a missing PDF materialization failure.

## Duplicate Pair

The duplicate visual input pair is:

```text
formal300_133 KAPC_R01LY
formal300_134 KAPC_R01LZ
```

Both rows reference:

```text
00281R6.PDF
pdf_sha256 = 0e711dda064b2f78dfc5e69b5f3c48d85734e39197f149bff37afa64c0412762
image_sha256 = 5912a94e98be08bcd9bbe2a1ea50774bc720bdf2c438c29037d635d22414de10
```

The two samples have byte-identical rendered images but different
CIFP-derived targets. The known target difference is:

```text
leg1.Q2_altitude_constraint.value
KAPC_R01LY: {"desc":"AT_OR_ABOVE","altitude_ft":436,"altitude_2_ft":null}
KAPC_R01LZ: {"desc":"AT_OR_ABOVE","altitude_ft":217,"altitude_2_ft":null}
```

## Pre-Run Disposition

For technical readiness, this issue is not counted as a missing-input blocker:

- both PDFs are available;
- both images are available;
- both target JSON files are schema-valid;
- both samples are in the development split, not the evaluation split.

For scientific interpretation, this remains a review item:

- if full formal300 aggregate results include development samples, this pair
  must be reported as a duplicate-image / divergent-target case;
- image-only methods should not be described as purely pixel-only unless
  procedure metadata use is explicitly documented;
- if final claims depend on unique visual inputs, one of the two development
  samples should be replaced or excluded before final reporting.

## Decision For This No-Eval Preparation Step

Keep both samples in the generated no-eval run manifests, because this step only
prepares inputs and does not run or report formal model scores.

Before starting final reported formal evaluation, the user should decide whether
to:

1. keep both samples and document the duplicate-image case;
2. exclude one sample from aggregate scoring;
3. replace one sample and regenerate the affected formal300 manifests.
