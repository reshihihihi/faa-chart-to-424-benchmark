# Admin Export

The annotation platform supports an administrator-only export page when
`SHUJUJI_ADMIN_TOKEN` is configured.

Admin page:

```text
/admin/?admin_token=your-admin-token
```

The admin page can:

- Generate a fresh server-side export of current annotation results.
- Save the export under `$SHUJUJI_DATA_ROOT/exports/`.
- Download the generated JSON export in the browser.
- List previously generated exports.

The regular annotation token is intentionally not enough for export APIs. This
keeps ordinary annotators limited to annotation work while allowing the project
owner to download all saved drafts, final annotations, submission snapshots, and
claim state.

For production servers, `scripts/server_export_web_results.sh` can be installed
as a cron job to generate this same export automatically, for example once per
hour. See `docs/服务器部署维护与导出说明.md` for the deployment and retention
conventions.

Export JSON schema:

```text
shujuji_annotation_export_v1
```

Included data:

- `practice10.annotations.drafts`
- `practice10.annotations.by_annotator`
- `practice10.annotations.submissions`
- `formal300.annotations.claims`
- `formal300.annotations.drafts`
- `formal300.annotations.by_annotator`
- `formal300.annotations.submissions`
