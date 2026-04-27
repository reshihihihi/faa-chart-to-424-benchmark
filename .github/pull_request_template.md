## Summary

Describe the change in 2-5 sentences.

## Affected Freeze Surface

- [ ] schema
- [ ] benchmark export / sample manifest / split
- [ ] target / proxy ground truth
- [ ] method registry
- [ ] prompt
- [ ] model config
- [ ] parser repair policy
- [ ] scorer / validator
- [ ] runner / input packer
- [ ] reports / paper tables
- [ ] docs only

## Upstream Provenance

- [ ] no upstream files imported
- [ ] imports or updates upstream-derived files
- [ ] `metadata/upstream_provenance_manifest.json` updated
- [ ] sha256 checksums updated

Upstream references:

- source repo:
- issue / PR:
- source commit:

## Reproducibility Impact

- [ ] no formal experiment impact
- [ ] changes pilot-only workflow
- [ ] changes formal evaluation inputs
- [ ] changes formal scoring or metrics
- [ ] requires new run id
- [ ] invalidates previous results

Explain:

## Leakage And Bias Check

- [ ] runners cannot read canonical targets
- [ ] evaluation split is not used for prompt tuning
- [ ] parser repair remains pre-registered and mechanical only
- [ ] failed / invalid outputs are preserved
- [ ] no local absolute paths or credentials committed

## Validation

- [ ] `python scripts/ci/check_repository_integrity.py`
- [ ] schema validation
- [ ] no-leakage validation
- [ ] scorer validation
- [ ] not run

Exact commands:

## Codex Review

Recommended request:

`@codex review for leakage, schema drift, and reproducibility regressions`

