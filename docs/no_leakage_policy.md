# No-Leakage Policy

This document defines the default no-leakage boundary for paper-v2.

## General Rule

Model and rule runners may read only the inputs explicitly registered for their
method in the method registry and run manifest. They must not read target files,
CIFP raw records, scorer outputs, validation labels, or previous model outputs.

## Default Forbidden Inputs

Unless a method is explicitly registered as an oracle or verification method,
the following are forbidden:

- canonical proxy targets
- CIFP-derived raw or extracted records
- answer keys
- scorer outputs
- validation reports
- counterfactual labels
- error fields for scoring
- evaluation split error-analysis notes
- prior predictions for the same chart

## Method-Specific Notes

- `A1/A2`: OCR and rules may read chart-derived OCR only, not targets.
- `B1`: LLM may read OCR text only, not gold text or target fields.
- `C3`: VLM may read chart image and questionnaire contract only, not OCR text.
- `C4`: image plus OCR is allowed only if registered; OCR source must be recorded.
- `Direct verifier`: candidate records are allowed, but scoring-only labels are not.
- `Candidate-only baseline`: may read candidate record only, not chart or OCR.
- `Metadata-only baseline`: may read metadata string only, not chart, OCR, or target.

## Enforcement

Each formal run should produce an input manifest containing:

- run id
- method id
- chart id or case id
- allowed input fields
- input file paths
- forbidden field scan result
- target access status
- validator result

Any method that fails no-leakage validation must not enter main paper tables
until fixed and rerun under a new run id.

