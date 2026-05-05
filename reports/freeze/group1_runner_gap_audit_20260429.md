# Group 1 Runner Gap Audit - 2026-04-29

Status: **runner_gaps_recorded_not_formal_frozen**

Formal Group 1 evaluation needs runners that are manifest-driven and separated from scoring. Current scripts are useful pilot/prototype runners, but most are not yet formal300 wrappers.

| Method | Runner | Status | Formal gap |
|---|---|---|---|
| `A1` | `scripts/run_a1_a2_rules_pilot10.py` | candidate_pilot_runner_only | Needs formal300 input-manifest driven wrapper; must write OCR-1 artifact hashes and rule diagnostics. |
| `A2` | `scripts/run_a1_a2_rules_pilot10.py` | candidate_pilot_runner_only | Needs same formal rules wrapper as A1 with OCR-2 artifact manifest and identical rules hash. |
| `B1` | `scripts/run_group1_pilot10_gpt54.py` | candidate_pilot_runner_only | Needs formal runner that reads OCR-1 artifact manifest but cannot read targets/scores during inference. |
| `B1_prime` | `scripts/run_group1_pilot10_gpt54.py` | candidate_pilot_runner_only | Needs frozen field_candidates generator/matcher and formal runner path. |
| `B1_prime_link` | `external only under E:/experiment3/B1'_link` | not_consolidated_in_repo | Need repo runner or wrapper that generates field_candidates and field_to_leg_links without target/scorer access. |
| `C1` | `scripts/run_b1_c1_pilot10_ocr1.py` | candidate_pilot_runner_only | Needs image-only formal runner using VLM tool schema and no OCR text. |
| `C2` | `scripts/run_c2_qa_pilot10.py + scripts/aggregate_c2_qa_candidate.py` | candidate_pilot_runner_only | Needs formal QA call manifest, QA schema hash, aggregator hash, and invalid QA handling. |
| `C3` | `scripts/run_pilot10_anthropic.py` | candidate_pilot_runner_only | Needs formal image-only C3 wrapper; current script has pilot10-oriented constants. |
| `C4` | `scripts/run_b1prime_c4_pilot10.py` | candidate_pilot_runner_only | Needs formal image+OCR-1 runner with high-retry decision documented. |
| `D_SFT` | `scripts/d_sft_infer_qwen2vl_lora.py` | candidate/frozen D-SFT runner exists | Needs formal300 run wrapper and invalid output denominator policy. |

Required formal runner properties:
- accepts a frozen sample/input manifest
- writes run_manifest with prompt/model/schema/scorer/parser hashes
- writes per-sample raw output, parsed output, validation, attempt_count, retry reason
- cannot read target/scorer directories during inference
- separates inference from scoring
- preserves parse/schema/API failures rather than dropping samples
