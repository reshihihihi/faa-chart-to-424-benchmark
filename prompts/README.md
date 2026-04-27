# Prompts

All prompts used in formal runs must be versioned and recorded in
`configs/prompt_manifest.json` with sha256 hashes.

Do not edit a prompt in place after a run. Create a new version and a new run id.

Imported upstream prompt/template snapshots:

- `path_c_qa_v2/`: upstream PR #28 Method C QA bundle
- `path_e_v2/structured_form_template.txt`: upstream PR #28 structured form template

These are imported candidate assets. They are not automatically formal prompts
until registered in `configs/prompt_manifest.json`.
