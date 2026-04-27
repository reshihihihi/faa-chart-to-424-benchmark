# Repository Governance

This repository is private during active paper-v2 preparation. Because GitHub
currently does not allow branch protection on this private repository without a
paid plan or making the repository public, governance is enforced through a
combination of CI, PR templates, CODEOWNERS, issue gates, and manual discipline.

GitHub secret scanning is also unavailable for this private repository under
the current account settings. The repository integrity CI therefore includes a
basic secret-pattern scan, but this is not a substitute for full GitHub secret
scanning.

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
  account supports private branch protection
- GitHub secret scanning is enabled if repository visibility or account features
  make it available

## Current Known Governance Limitations

- Branch protection could not be enabled while the repository is private under
  the current account settings.
- GitHub secret scanning and push protection could not be enabled while the
  repository is private under the current account settings.
- Until those features become available, do not treat `main` as mechanically
  protected. Use PRs and run `repository-integrity` before merging or pushing.
