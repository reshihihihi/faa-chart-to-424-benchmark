# FAA Chart-to-424 Benchmark

This repository is a clean paper-v2 workspace for the NeurIPS 2026 Evaluations
and Datasets submission around FAA missed-approach chart-to-ARINC-424
evaluation.

This repository is intentionally not a full copy of
`reshihihihi/faa-missed-approach-experiment`. The old repository remains the
upstream source of history, exploratory work, issues, and pull requests. This
repository should contain only the frozen assets, code, manifests, prompts,
outputs, and artifact documents needed for the paper-v2 experiment.

## Core Rule

Formal evaluation must use only files registered in:

- `configs/frozen_experiment_manifest.json`
- `metadata/upstream_provenance_manifest.json`
- `benchmark_exports/derived/v2/MANIFEST.json`

If a file is not registered there, it is not part of the formal experiment.

## Repository Layout

- `docs/`
  Experiment policies, migration protocol, no-leakage rules, rerun rules, and
  submission documents.
- `schemas/`
  Frozen canonical JSON schemas.
- `configs/`
  Frozen model, prompt, parser, scorer, and run configuration manifests.
- `prompts/`
  Versioned prompts used by formal methods.
- `scripts/`
  Validators, scorers, runners, export builders, and CI checks.
- `benchmark_exports/derived/v2/`
  Read-only paper-v2 benchmark export view.
- `predictions/`
  Model outputs and parsed/final predictions.
- `reports/`
  Validation, scoring, statistical, and paper-table reports.
- `metadata/`
  Upstream provenance, Croissant metadata, artifact manifests, and checksums.

## Upstream Source

Primary upstream repository:

<https://github.com/reshihihihi/faa-missed-approach-experiment>

Important upstream references currently expected:

- upstream issue #4: leg-level canonical schema definition
- upstream PR #28: canonical schema and questionnaire templates
- upstream PR #29: CIFP-to-proxy-target projection pipeline
- upstream PR #32: formal300 annotation platform and data assets
- upstream issue #33 through #51: paper-v2 planning and freeze issues
- upstream PR #52: paper-v2 scaffold namespace

## Current State

This initial commit creates the clean workspace and audit guardrails only. It
does not yet import large data assets, formal targets, model predictions, or
final paper-v2 results.

## Governance Status

The repository is currently private. GitHub branch protection for this private
repository is not available under the current account settings, so PR discipline
is enforced by repository policy, CODEOWNERS, pull request templates, issue
gates, and the `repository-integrity` GitHub Actions check. See
`docs/repository_governance.md`.

Before formal evaluation, complete `docs/formal_freeze_checklist.md`.

Current bootstrap audit: `docs/bootstrap_audit_20260427.md`.
