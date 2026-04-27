# Migration Protocol

This repository is a clean paper-v2 workspace. Migration from the upstream
experiment repository must be treated as a freeze operation, not a broad copy.

## Upstream Repository

`reshihihihi/faa-missed-approach-experiment`

## Allowed Imports

Only import assets that are necessary for paper-v2:

- canonical schema files
- validator and scorer code
- benchmark export builders
- frozen sample manifests and split manifests
- frozen prompts and prompt manifests
- model configuration manifests
- parser repair policies
- no-leakage validators
- bootstrap and paired-delta scripts
- artifact documents required for NeurIPS E&D review

## Disallowed Imports

Do not import:

- whole upstream repository history
- obsolete formal100 results unless explicitly needed as historical reference
- pilot outputs unless marked pilot-only
- local drive paths
- API tokens or local environment files
- exploratory notebooks or ad hoc debug scripts
- unregistered target files outside the v2 benchmark export
- failed private attempts that cannot be reproduced

## Required Provenance For Every Import

Every upstream-derived asset must be recorded in
`metadata/upstream_provenance_manifest.json` with:

- source repository
- source issue or pull request
- source commit
- source path
- destination path
- sha256 of imported content
- import date
- import reason
- whether it is frozen for formal evaluation

## No-Leakage Rule

Formal method runners may not read canonical targets, CIFP raw records, scorer
outputs, answer keys, or validation labels unless the method is explicitly an
oracle or verification baseline and this is registered in the method registry.

## Freeze Rule

After a pilot informs a prompt, parser, schema, scorer, or model configuration,
the changed file must receive a new version, a new hash, and a new run id. Old
outputs must not be overwritten.

## Formal Evaluation Rule

Formal evaluation may start only after these are frozen:

- schema path and hash
- benchmark export manifest and hash
- split manifest and hash
- method registry
- model config manifest
- prompt manifest
- parser repair policy
- scorer version
- rerun policy
- output root

