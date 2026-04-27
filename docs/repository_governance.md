# Repository Governance

This repository is intended to be public during paper-v2 artifact preparation.
Governance is enforced through a combination of CI, PR templates, CODEOWNERS,
issue gates, and manual discipline.

The repository integrity CI includes a basic secret-pattern scan. If GitHub
secret scanning and push protection are available for the public repository,
they should also be enabled, but they are not a substitute for reviewing files
before publication.

## Required Workflow

Use pull requests for any change that affects:

- schemas
- benchmark exports
- split manifests
- target generation
- method registry
- prompts
- model configuration
- parser repair policy
- scorer or validator behavior
- prediction outputs or reports

Direct pushes to `main` should be limited to repository bootstrap and emergency
metadata fixes. If a direct push is used, the commit message must explain why a
PR was not used.

## Review Expectations

Every evaluation-affecting PR should request:

```text
@codex review for leakage, schema drift, and reproducibility regressions
```

The PR author must also complete the repository PR template, especially:

- affected freeze surface
- upstream provenance
- reproducibility impact
- leakage and bias check
- validation commands

## Merge Policy

Preferred merge style:

- squash merge only
- delete branch after merge
- one logical PR per freeze object

Merge commits and rebase merges are discouraged because they make it harder to
audit which PR changed a frozen experiment object.

Current remote settings have been configured accordingly:

- merge commit: disabled
- rebase merge: disabled
- squash merge: enabled
- delete branch on merge: enabled

## Required Checks Before Formal Evaluation

Before formal evaluation, confirm:

- `repository-integrity` passes on `main`
- all imported upstream assets have provenance and sha256
- formal freeze checklist is complete
- no evaluation split sample has been used for prompt tuning
- branch protection is enabled if the repository has been made public or if the
  account supports branch protection
- GitHub secret scanning and push protection are enabled if repository settings
  make them available

## Current Known Governance Limitations

- Branch protection and secret scanning settings must be checked after the
  visibility transition.
- Until those features are confirmed, do not treat `main` as mechanically
  protected. Use PRs and run `repository-integrity` before merging or pushing.
