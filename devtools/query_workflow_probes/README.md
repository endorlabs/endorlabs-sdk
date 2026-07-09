# Query workflow probes

Live experiments mapping workflows to `Query.create` graph joins. The platform Query API is **kind-agnostic**; these probes include both **`client.Query.Project.*`** estate recipes and namespace-scoped / non-Project patterns.

See [query_workflow_map.md](../query_workflow_map.md) and [docs/guides/query-recipes.md](../../docs/guides/query-recipes.md) for counterexamples by resource.

## Auth (browser once)

**Browser SSO is only for refreshing `.env-admin`** — not for each probe:

```bash
uv run endor-auth refresh --env-file .env-admin --method sso -n endor-admin
```

Then run probes with **token from `.env-admin` only** (one shared `Client`, no browser):

```bash
# Idealized facade validation (recommended first)
uv run --env-file .env-admin python devtools/query_workflow_probes/validate_query_facade.py -n <tenant> --max-projects 8

# Workflow-shaped probes
uv run --env-file .env-admin python devtools/query_workflow_probes/probe_workflows.py all -n <tenant> --max-projects 3 --findinglog-days 7
```

Do **not** invent auth env vars (e.g. `ENDOR_AUTH_METHOD`) in the shell when running probes.

## Scripts

| Script | Purpose |
| ------ | ------- |
| **`validate_query_facade.py`** | Idealized parity: `Query.Project.discover`, `validate_sample` (pv/dm/findings/severity), `count_pv` / `count_dm`, `collect_estate_findings` smoke |
| **`probe_workflows.py`** | Workflow-shaped probes — counts, joins, collect row parity, mask traps, namespace traps, documented Query gaps |

## Pagination

| Query mode | Pagination |
| ---------- | ---------- |
| `count: true` on a reference | Not required |
| `group` | Bucket response, not object pages |
| `group_by_time` on Query | **Unsupported** — use facade `list_groups` |
| Masked **list** refs | Yes when rows exceed page size — `collect_*` paginates nested `reference.list.response.next_page_token`; optional `max_reference_pages` |

## `probe_workflows.py` subcommands

| Probe | Workflow | Status | Notes |
| ----- | -------- | ------ | ----- |
| `recipe-parity` | Dashboard / preflight | Validate | `validate_sample` + `count_pv` |
| `prf-counts` | PRF analysis totals | Validate | Project → Finding count × ecosystem |
| `finding-list-join` | Estate findings collect | Validate | Count ref parity only (not list rows) |
| `collect-row-parity` | Estate findings collect | **Validated** | Full row count + uuid set vs `Finding.list` |
| `collect-prf-rows` | PRF collect | **Validate on sample** | Row parity vs per-ecosystem facade lists |
| `malware-category-split` | Dashboard MALWARE category | **Validate on sample** | Does not skip malware-only mismatches (unlike CI) |
| `severity-validate-sample` | Dashboard severity | Validate | `validate_sample(recipe="severity")` |
| `tenant-finding-totals` | Tenant-wide denominators | **Validated** | Per-project leaf POST + traverse parity; tenant root no-traverse under-counts |
| `findinglog-group` | New-vs-resolved chart | **Expected unsupported** | Query → `list.objects`; use `FindingLog.list_groups` |
| `query-escape-hatch-group-by-time` | Removed builder gap | **Expected unsupported** | `QuerySpec.list_parameters(group_by_time=...)` |
| `authlog-group-by-time` | Auth login trends | **Expected unsupported** | Same routing gap as FindingLog |
| `dm-group` | DM version cardinality | Validate | Root `DependencyMetadata` + `group` |
| `nested-list` | Platform doc example | Smoke | Project → RV → Metric lists |
| `nested-finding-mask` | Estate collect mask | **Validate on sample** | Sub-field masks on nested Finding list refs |
| `scan-latest-join` | CI endorctl audit | Validate | Query mask: `spec.environment` (not sub-fields) |

Probes marked **Expected unsupported** set `expected_unsupported: true` in JSON — they log `FAIL` but do **not** fail `all` exit code (documented platform gaps).

```bash
uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py collect-row-parity -n <tenant> --max-projects 5
uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py malware-category-split -n <tenant>
uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py nested-finding-mask -n <tenant>
```

**Mask trap:** Query nested list refs may need parent struct masks (`spec.environment`) instead of deep sub-fields (`config.RunBySystem`). See `scan-latest-join` and `nested-finding-mask`.

Results JSON: `results/<namespace>_<timestamp>.json` or `validate_query_facade_<namespace>_<timestamp>.json`
