# Bootstrap Audit - 2026-04-27

## Scope

This audit reviews the initial clean repository setup for
`reshihihihi/faa-chart-to-424-benchmark`.

The repository is a paper-v2 execution workspace. It is not yet a formal
evaluation package.

## What Is Complete

- Clean repository created and pushed.
- Repository is private.
- Initial CI workflow `repository-integrity` is active and has passed.
- `AGENTS.md` and PR template define Codex/reviewer expectations.
- Issue templates exist for paper-v2 tasks and upstream imports.
- Labels and clean paper-v2 issues #1-#9 exist.
- Merge commit and rebase merge are disabled.
- Squash merge is enabled.
- Delete branch on merge is enabled.
- Migration protocol, no-leakage policy, rerun policy, governance policy, and
  formal freeze checklist exist.
- Initial frozen experiment manifest and upstream provenance manifest exist.

## Not Yet Complete

- No upstream schema has been imported yet.
- No benchmark export has been built yet.
- No formal split is frozen in this repository yet.
- No method registry is frozen yet.
- No prompt or model entry is frozen yet.
- No scorer, validator, or no-leakage input manifest builder is implemented yet.
- No pilot or formal results exist in this repository yet.

## Risk Register

| Risk | Severity | Current Mitigation | Remaining Action |
|---|---:|---|---|
| Private repo branch protection unavailable | High | Governance doc, PR template, CODEOWNERS, CI | Enable branch protection if repo becomes public or account supports it |
| GitHub secret scanning unavailable | High | CI basic secret regex scan | Enable secret scanning when available; never commit local env files |
| Upstream PR #28/#29 are draft/open | High | Provenance manifest marks imports as planned, not frozen | Do not freeze schema/target until source commit and hash are accepted |
| Formal300 assets not imported | High | PV2-02 issue and benchmark export scaffold | Build `benchmark_exports/derived/v2/` from fixed upstream commit |
| Pilot and formal evaluation could be mixed | High | Formal freeze checklist and migration protocol | Add split validator before any formal run |
| Prompt/model/parser drift | High | Prompt/model/parser manifests and rerun policy | Fill hashes and make CI enforce them once prompts exist |
| Target leakage through runner paths | High | No-leakage policy | Implement input manifest builder and no-leakage validator |
| Parser repair bias | Medium | Parser repair policy disallows semantic repair | Freeze exact mechanical repair before formal run |
| Result cherry-picking | Medium | Prediction README requires preserving failures | Add run manifest validator and scoring report generator |

## Readiness Judgment

The repository is ready as a clean scaffold and migration target.

It is not ready for formal experiment execution.

The next safe step is to import the canonical schema from a fixed upstream
commit, record sha256, and update the provenance manifest. After that, import or
rebuild the target/export pipeline and build the immutable benchmark export.

