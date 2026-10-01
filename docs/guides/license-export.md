# Dependency + license export (`endor-license-export`)

Scheduleable **current-state** dependency inventory with SPDX license resolution
for open-source compliance / OSO pipelines.

Reuses estate collect patterns: project topology discovery, parallel MAIN-context
`DependencyMetadata` lists per project shard, resume checkpoints, then a shared
license cache via `PackageLicenseQuery` / `BatchPackageLicenseQuery` at the
**export namespace** (catalog data + overrides for that namespace chain).

**Not** an `endor-estate pull` IR resource and **not** SBOM export. Prefer this
CLI when you need one row per `(project, package-version)` with Query-faithful
`primary_spdx`.

## Why MAIN context matters

Unfiltered `DependencyMetadata` lists include historical / multi-path rows and
can explode into millions of rows (and 504s). This workflow always applies:

```text
(context.type=="CONTEXT_TYPE_MAIN") and (spec.importer_data.project_uuid=="<uuid>")
```

Optional `--filter` is **AND-ed** with that mandatory clause — callers cannot drop
MAIN / importer safety. Shard failures are isolated; use `--resume` to retry only
incomplete projects (JSONL upsert by primary key).

HTTP **504** retries stay implicit via the SDK `APIClient` status forcelist — no
CLI retry knobs.

## Auth

Non-interactive only. Refresh first, then run with env or shared CLI overrides
(`endorlabs.workflows.common.cli_client`):

| Source | How |
|--------|-----|
| Env | `uv run --env-file .env endor-license-export -n example-tenant.child` |
| Bearer | `--token` (else `ENDOR_TOKEN`) |
| API key | `--api-key` + `--api-secret` (else `ENDOR_API_CREDENTIALS_*`) |
| Host | `--api` (else `ENDOR_API`) |

```bash
uv run endor-auth refresh --method sso -n <tenant>
uv run --env-file .env endor-license-export -n example-tenant.child
```

Interactive SSO/browser stays on `endor-auth refresh` — this CLI does not open a
browser. One auth mode per dotenv (token **or** key pair).

## CLI

```bash
# Full pipeline (default subcommand is run)
uv run --env-file .env endor-license-export -n example-tenant.child

# Explicit phases
uv run endor-license-export inventory -n example-tenant.child --resume
uv run endor-license-export resolve -n example-tenant.child
uv run endor-license-export join -n example-tenant.child --format csv

# Extra DM filter / mask, full license objects on JSONL join
uv run endor-license-export run -n example-tenant.child \
  --filter 'spec.dependency_data.direct==true' \
  --format jsonl --include-license-object

# Multi-namespace scheduled job (shared license cache)
uv run endor-license-export run \
  -n example-tenant.child-a \
  -n example-tenant.child-b \
  --format csv \
  --max-workers 12
```

| Flag | Role |
|------|------|
| `-n` / `--namespaces-file` | One or more namespace paths |
| `--format {csv,jsonl}` | Joined deliverable (default `csv`) |
| `-o/--output-dir` | Base dir (default `.endorlabs/tasks/<slug>-<date>/licenses/`) |
| `--resume` / `--overwrite` | Inventory shard checkpoint + keyed JSONL upsert |
| `--filter` | Extra MQL AND-ed with MAIN + importer (inventory/run) |
| `--mask` | Replace default DM list mask (omitting join fields → empty CSV columns) |
| `--include-license-object` | Sidecar `license_objects.jsonl`; embed on JSONL join rows |
| `--page-size` | Lower on stubborn 504 shards (default 500) |
| `--license-cache` | Shared PV→SPDX JSONL across namespaces |
| `--batch-size` | `BatchPackageLicenseQuery` chunk size (default 100) |
| `--token` / `--api-key` / `--api-secret` / `--api` | Credential / host overrides |

## Output layout

```text
.endorlabs/tasks/<slug>-<YYYY-MM-DD>/licenses/
  export_summary.json                 # coverage summary (also printed)
  license_cache.jsonl                 # shared across -n values in one run
  license_objects.jsonl               # optional (--include-license-object)
  <ns_slug>/
    dependency_inventory.jsonl
    projects.jsonl
    checkpoint.json
    <ns_slug>-dep-licenses.csv        # or .jsonl
```

### Primary keys (resume / upsert)

| Artifact | Primary key |
|----------|-------------|
| `projects.jsonl` | `uuid` (Project) |
| `dependency_inventory.jsonl` | `(project_uuid, package_version_uuid)` |
| `license_cache.jsonl` | `package_version_uuid` |
| `license_objects.jsonl` | `package_version_uuid` |
| Joined CSV/JSONL | full rewrite after join; grain `(namespace, project_uuid, package_version_uuid)` |

Platform resource identity note: Project / Finding / PackageVersion /
DependencyMetadata wire identity is **`uuid`**; the license join uses dependency
`package_version_uuid`.

`project_name` comes from **`Project.meta.name`** (repo URL / registration name).
If empty, the field stays `""` — the exporter does not invent names.

Joined CSV columns: `namespace`, `project_uuid`, `project_name`, `package_name`,
`package_version_uuid`, `purl`, `ecosystem`, `direct`, `reachable`, `scope`,
`public`, `pinned`, `internal`, `vendored`, `last_commit`, `primary_spdx`,
`all_spdx`, `source_count`, `has_declared`, `has_code`, `has_package_manager`.

With `--format jsonl --include-license-object`, each joined row may also include
`license_object` (full PackageLicenseQuery body). CSV stays flat.

### Coverage summary

After `run` (and phase CLIs), `export_summary.json` records namespaces, workers,
elapsed time, project shard totals, inventory/join row counts, unique PVs, and
license query / missing / with-`primary_spdx` counts, plus paths.

## License resolution

Resolve only on the **export namespace** (tenant plane):

1. POST `BatchPackageLicenseQuery` in chunks (`--batch-size`) under that
   namespace. Each item is a `PackageLicenseQuery` for one
   `package_version_uuid`. The server merges catalog license data with any
   `PackageLicenseOverride` along the namespace chain (UI-faithful view).
2. If a whole batch returns **404** (platform behavior when any PV in the chunk
   has no license data), fall back to per-PV `PackageLicenseQuery`.
3. Per-PV **404** → empty cache row (`primary_spdx=""`), not an error.
4. `primary_spdx` prefers `package_manager`, then `declared`, then `code` among
   selected Query entries.

Do **not** list `PackageLicense` under a hardcoded catalog namespace for this
export — Query is the supported customer-plane merge.

## Library

```python
from endorlabs.workflows.license_export import run_license_export

result = run_license_export(
    client,
    namespaces=["example-tenant.child"],
    export_format="csv",
    resume=True,
)
print(result.summary_path)
```

## Out of scope

- Platform S3 / GCS upload
- `--extra-columns` / default mask menus / license-tier classification
- Per-namespace `ENDOR_<NS>_API_*` credential invention
- Incremental “since last scan” deltas
- Migrating every workflow CLI onto shared auth flags in one change
  (`license-export` + `log-export` adopt; others follow-on)
