# C2 QA Prompt Bundle Manifest

This file is the repository-level manifest for the C2 fixed QA prompt bundle.
It is used as the hashable `prompt_path` in `configs/prompt_manifest.json`.

The C2 method consumes the following bundle files from `prompts/path_c_qa_v2/`:

- `q0_leg_count.txt`
- `q1_fix_ident.txt`
- `q2_altitude_constraint.txt`
- `q3_turn.txt`
- `q4_course_or_radial.txt`
- `q5_hold_params.txt`
- `q_terminator.txt`

Boundary:

- Input: full chart image plus this fixed QA prompt bundle.
- Intermediate output: per-question QA JSON.
- Aggregation: `scripts/aggregate_c2_qa_candidate.py`.
- Final output: `schemas/missed_approach_leg.schema.json`.

This manifest does not freeze C2 for formal evaluation. It only makes the
candidate prompt bundle addressable and hash-checkable by repository CI.
