# AGENTS.md

This repository is a clean paper-v2 experiment package for FAA missed-approach
chart-to-424 evaluation. When reviewing pull requests, prioritize scientific
validity, reproducibility, data integrity, leakage control, and traceability.

## Review Priorities

Focus on:

- changes that alter the formal schema, scorer, split, prompt, model config, or
  parser repair policy
- target leakage or accidental access to canonical targets, CIFP records,
  scorer outputs, or answer keys from method runners
- unregistered inputs that bypass `benchmark_exports/derived/v2/MANIFEST.json`
- untracked changes to prompt hashes, model settings, or rerun policy
- result files that appear without raw outputs, parser logs, validation reports,
  or run manifests
- files copied from the upstream repository without provenance records and
  sha256 hashes
- committed secrets, local absolute paths, and hidden environment assumptions

## Repository Map

- `configs/frozen_experiment_manifest.json`
  Top-level freeze state for schema, data, prompts, models, parsers, scorers,
  and output locations.
- `metadata/upstream_provenance_manifest.json`
  Required source-of-truth for every imported upstream asset.
- `docs/migration_protocol.md`
  Rules for importing from the upstream repository without changing experiment
  definitions.
- `benchmark_exports/derived/v2/`
  Only formal data entry point for paper-v2.
- `scripts/ci/check_repository_integrity.py`
  CI guard for manifest consistency, obvious secrets, forbidden local paths, and
  required audit files.

## High-Risk Changes

Treat these as high risk:

- changing a schema after pilot or evaluation results are known
- changing prompt text without updating `configs/prompt_manifest.json`
- changing model settings without a new run id
- adding parser repair beyond pre-registered mechanical normalization
- copying data from local drives or upstream branches without provenance
- mixing pilot samples with formal evaluation samples
- deleting failed samples, invalid JSON, or parse errors from prediction outputs
- summarizing results without bootstrap or paired-delta reporting when required

## Pull Request Expectations

Each PR should explain:

- which frozen object it affects
- whether it imports anything from upstream
- whether it changes formal evaluation inputs
- whether a new run id is required
- which validation commands were run
- whether Codex review should focus on leakage, reproducibility, or schema drift

## Preferred Review Style

- Lead with correctness and reproducibility findings.
- Require provenance for imported assets.
- Require a clear reason for every rerun.
- Do not approve evaluation changes that only preserve successful samples.
- Ask for updated checksums when any registered asset changes.

