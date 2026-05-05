# Annotation Tools

This directory contains standalone human-annotation tooling used to build or
audit benchmark evidence labels.

- `shujuji_annotation/`: web app, dataset slices, prelabels, and deployment
  notes for the missed-approach chart evidence annotation workflow.

Runtime claim state, drafts, submissions, and admin exports are intentionally
ignored. Use `SHUJUJI_DATA_ROOT` to point the web app at a writable local or
server-side data directory when collecting annotations.
