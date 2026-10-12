# Findings export (`endor-findings-export`)

Scheduleable **current-state** MAIN-context Finding JSONL export for CI and
downstream analysis.

Collects findings with per-project parallel `Finding.list` shards (same safety
shape as license-export inventory): mandatory MAIN + `spec.project_uuid`, resume
checkpoints, keyed JSONL upserts. **Not** an `endor-estate pull` IR path and
**not** a category-filtered Query join — prefer this CLI when you need full
Finding bodies (or an optional field mask) for every MAIN finding under a
namespace.

## Why MAIN + project shards matter

Unfiltered or tenant-root Finding lists without a project UUID are slow and can
504. This workflow always applies:

```text
(context.type=="CONTEXT_TYPE_MAIN") and (spec.project_uuid=="<uuid>")
```

Optional `--filter` is **AND-ed** with that mandatory clause — callers cannot drop
MAIN / project safety. There is **no** category filter by default (all MAIN
findings). Shard failures are isolated; use `--resume` to retry only incomplete
projects (JSONL upsert by finding `uuid`).

**Default mask = none** (full Finding payloads as JSON objects). Pass `--mask` to
project fields; a non-empty mask yields dict rows (SDK list-mask contract).

HTTP **504** retries stay implicit via the SDK `APIClient` status forcelist — no
CLI retry knobs.

## Auth

Non-interactive only. Refresh first, then run with env or shared CLI overrides
(`endorlabs.workflows.common.cli_client`):

| Source | How |
|--------|-----|
| Env | `uv run --env-file .env endor-findings-export -n example-tenant.child` |
| Bearer | `--token` (else `ENDOR_TOKEN`) |
| API key | `--api-key` + `--api-secret` (else `ENDOR_API_CREDENTIALS_*`) |
| Host | `--api` (else `ENDOR_API`) |

```bash
uv run endor-auth refresh --method sso -n <tenant>
uv run --env-file .env endor-findings-export -n example-tenant.child
```

Interactive SSO/browser stays on `endor-auth refresh` — this CLI does not open a
browser. One auth mode per dotenv (token **or** key pair).

## CLI

```bash
uv run --env-file .env endor-findings-export -n example-tenant.child

uv run endor-findings-export -n example-tenant.child --resume --max-workers 12

uv run endor-findings-export -n example-tenant.child \
  --mask "uuid,spec.level,spec.finding_categories"

uv run endor-findings-export -n example-tenant.child \
  --filter 'spec.level==FINDING_LEVEL_CRITICAL'

# Multi-namespace
uv run endor-findings-export \
  -n example-tenant.child-a \
  -n example-tenant.child-b \
  --max-workers 12
```

| Flag | Role |
|------|------|
| `-n` / `--namespaces-file` | One or more namespace paths |
| `-o/--output-dir` | Base dir (default `.endorlabs/tasks/<slug>-<date>/findings/`) |
| `--resume` / `--overwrite` | Shard checkpoint + keyed JSONL upsert |
| `--filter` | Extra Finding filter AND-ed with MAIN + project_uuid |
| `--mask` | Optional field mask (default: none / full bodies) |
| `--page-size` | Finding list page size (default `500`) |
| `--max-workers` / `--max-pages` | Parallelism / per-shard page cap |

## Output layout

```text
.endorlabs/tasks/<slug>-<YYYY-MM-DD>/findings/
  export_summary.json
  <ns_slug>/
    projects.jsonl
    findings.jsonl
    checkpoint.json
```

`projects.jsonl` is a thin operational index (`uuid`, namespace, name).
`findings.jsonl` holds one Finding object per line (full body unless `--mask`).

## Library

```python
from endorlabs import Client
from endorlabs.workflows.findings_export import (
    collect_findings_export,
    compose_finding_filter,
    run_findings_export,
)

client = Client(tenant="example-tenant.child")
result = run_findings_export(
    client,
    namespaces=["example-tenant.child"],
    resume=True,
)
# Or single-namespace collect:
# collect_findings_export(client, namespace=..., output_dir=...)
```

## Related

- [license-export.md](license-export.md) — parallel MAIN inventory + SPDX join
- Estate pull Finding IR — different Query/SCA∪VULN path; do not substitute this CLI
- Workspace layout — `tasks/<slug>-<date>/findings/`
