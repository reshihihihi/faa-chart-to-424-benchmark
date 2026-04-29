# formal300 Source Lock Blockers

Status: source_lock_only_not_formal_eval_ready

This directory records the currently available formal300 source sample IDs and split assignments from the external manifest. It does not make Group 1 formal-evaluation ready.

Hard blockers before formal freeze:

- formal300 PNG/PDF artifacts must be materialized with render/download policy and hashes.
- formal300 canonical proxy targets must be generated with the frozen CIFP -> canonical projection pipeline and schema-validated.
- field_targets.jsonl, evidence_provenance.jsonl, and challenge_tags.jsonl must be exported or explicitly waived by the experiment plan.
- scorer/validator, model configs, rerun policy, and method runners must be frozen against these exact artifacts.
