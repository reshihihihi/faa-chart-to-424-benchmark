# Upstream Import: PR #28 Canonical Schema Snapshot

Import date: 2026-04-27

## Source

- Source repository: `reshihihihi/faa-missed-approach-experiment`
- Source pull request: upstream PR #28
- Source PR state at import: draft/open
- Source commit: `d2c54172b31184f8c0deb74415f37c239d3e3eca`
- PR title: `feat(schema): 复飞 leg canonical schema v1 + 三张问卷模板 (Issue #3)`

## Imported Files

| Destination | SHA256 |
|---|---|
| `schemas/missed_approach_leg.schema.json` | `7ccb2cb9dcc73e67167d7ae5a8874e73dc201f56ad243615009db620494482d9` |
| `docs/schemas/missed_approach_leg_v1.md` | `c040751aed3222b0fa200955f9bea180fa9160b87e452a092df779d657096727` |
| `prompts/path_c_qa_v2/q0_leg_count.txt` | `bce855961b701e745a8ba4369129a52b4af182779a9d28c508dda1d55effeb77` |
| `prompts/path_c_qa_v2/q_terminator.txt` | `cce89e39f8ce019072ed72d568ad32bc7853239178e3b6d59f34557d9df951e2` |
| `prompts/path_c_qa_v2/q1_fix_ident.txt` | `ec9453a4d6c700b583044eaabeb98860edfdba0d7c0c75f9cf25fe4fd574095b` |
| `prompts/path_c_qa_v2/q2_altitude_constraint.txt` | `98462ba146aaee5747aef4f36437801cdf7e6eff04053673479a71637760b2e1` |
| `prompts/path_c_qa_v2/q3_turn.txt` | `35ab2df1d85b76b95ee072cf78731ef45328293d600928a3e8ca389a5c40fb5b` |
| `prompts/path_c_qa_v2/q4_course_or_radial.txt` | `0c740e2c1c9ec2b0680653d7176886dd40740355a561b18e3d9cb72af489d39d` |
| `prompts/path_c_qa_v2/q5_hold_params.txt` | `b5f31a2868742dea779abab5b4a4fbaca3fa1227ea744fc3ff93e1af46b6e86f` |
| `prompts/path_e_v2/structured_form_template.txt` | `27816a2b5ce45e2a56c0bd9075590396f1db545e63f22ee48b806a23ad5d926b` |

Imported file-set bundle hash:

`5c9973be0baac527390868b3f7200ae4e522b8e9f9921a7fb8f73422e43a2ffc`

Bundle hash semantics:

`sha256` over sorted lines of `<relative_path>\0<file_sha256>\n`.

## Validation

- JSON parse passed for `schemas/missed_approach_leg.schema.json`.
- JSON Schema Draft 2020-12 schema check passed in the local Python environment.

## Formal Freeze Status

This is an imported candidate snapshot, not a formal freeze.

Formal freeze blockers:

- upstream PR #28 is still draft/open;
- schema review must be accepted;
- target projection and scorer must be aligned to this schema;
- paper-v2 method registry must confirm which questionnaire surfaces are used by
  C2/C3/E-style methods.

