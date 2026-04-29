# formal300 PDF / Image Reuse Audit - 2026-04-29

Status: **review decision required before formal300 freeze**.

## Summary

The formal300 package has 300 samples and 299 unique PDF files. This is **not** a missing-PDF materialization failure:

- sample rows: 300
- unique `sample_id`: 300
- unique `chart_id`: 300
- unique `pdf_file`: 299
- unique `pdf_path`: 299
- missing referenced PDFs: 0
- PDF hash mismatches: 0
- rows with `pdf_status != available`: 0

However, the duplicate PDF case is not a harmless file-count issue. The duplicated PDF renders to the same image hash for two different samples, while the target JSON differs.

## Duplicate Case

Duplicated PDF:

```text
00281R6.PDF
https://aeronav.faa.gov/d-tpp/2604/00281R6.PDF
pdf_sha256 = 0e711dda064b2f78dfc5e69b5f3c48d85734e39197f149bff37afa64c0412762
```

Affected samples:

| sample_id | chart_id | airport | proc_ident | chart_name | split | image_file | image_sha256 | target_sha256 |
|---|---|---|---|---|---|---|---|---|
| formal300_133 | KAPC_R01LY | KAPC | R01LY | RNAV (GPS) RWY 06 | development | 133__KAPC_R01LY__00281R6_p0.png | 5912a94e98be08bcd9bbe2a1ea50774bc720bdf2c438c29037d635d22414de10 | 1eb8306e988c635d2f2ab4ccb3f149188acd8b0f066c9fa170dd6e5f3f1f774b |
| formal300_134 | KAPC_R01LZ | KAPC | R01LZ | RNAV (GPS) RWY 06 | development | 134__KAPC_R01LZ__00281R6_p0.png | 5912a94e98be08bcd9bbe2a1ea50774bc720bdf2c438c29037d635d22414de10 | 7fb1d65eda61bbb7445eea4cdda7104ad374d5fa6853287b432ebc5426a84f84 |

The rendered image is byte-identical for the two samples, but the target JSON is different.

## Target Difference

Besides metadata (`chart_id` and `approach_ident`), the canonical target difference found by the audit is:

| Field | KAPC_R01LY | KAPC_R01LZ |
|---|---|---|
| `leg1.Q2_altitude_constraint.value` | `{"desc":"AT_OR_ABOVE","altitude_ft":436,"altitude_2_ft":null}` | `{"desc":"AT_OR_ABOVE","altitude_ft":217,"altitude_2_ft":null}` |

The raw CIFP records are also different:

- `KAPC_R01LY` raw CIFP sha256: `5185cb2ee264c9342393d7abb326666364f1ea536632e4f92fc2749b937ceea7`
- `KAPC_R01LZ` raw CIFP sha256: `a7cca39fec68c3a6b56bb8d244494697bcd260c3967af50764478c454decd204`

## Interpretation

This is not a missing artifact problem. It is a **duplicate visual input with divergent CIFP-derived target** problem.

For image-only methods, two samples with the exact same chart image but different target values can create an ambiguous evaluation unless metadata such as `chart_id` / `proc_ident` is treated as an allowed disambiguating input. Even then, the benchmark must explicitly state that the task is not purely "pixels only"; it is "chart image plus registered chart/procedure metadata".

The affected pair is currently in the `development` split, not the `evaluation` split, but it still needs a formal decision before freezing if development/probe/formal300 aggregate results are reported.

## Recommendation

Preferred before formal freeze:

1. Replace one of the two samples with another non-overlapping chart/procedure so formal300 has 300 unique image hashes and 300 unique targets.

Acceptable only if explicitly documented:

2. Keep both samples, but mark this as an intentional shared-chart/multi-procedure case and require all method manifests to specify whether `proc_ident` metadata is an allowed inference input.

If keeping both:

- report duplicate-image groups separately in dataset statistics;
- do not describe C1/C2/C3/D-SFT as "image pixels only" unless metadata use is clearly stated;
- ensure inference runners provide the same metadata fields to every method that needs to output `chart_id` / `approach_ident`;
- consider excluding one sample from aggregate formal scoring if the scientific claim is chart-image extraction rather than procedure-metadata-conditioned extraction.

## Audit Conclusion

`300 samples / 299 PDFs` is expected from file availability perspective, but it reveals one duplicate-image / divergent-target pair:

```text
formal300_133 KAPC_R01LY
formal300_134 KAPC_R01LZ
```

This should remain an open formal300 freeze blocker until the reviewer decides whether to replace, exclude, or explicitly keep and document the pair.
