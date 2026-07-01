# Facade list helpers

Normative catalog for SDK facade helpers. Wire logic lives in `operations/`; workflows orchestrate only.

See also [resource-discovery contract](../../agent-knowledge/contracts/resource-discovery.md) (shipped in wheel).

> **Inventory vs patterns:** Full generated tables live in [resource-routes.md](../generated-reference/resource-routes.md), [api-surfaces.md](../generated-reference/api-surfaces.md), and per-resource pages under [resources/](../generated-reference/resources/README.md). This guide covers **when and how** to use helpers.

## Layer placement

| Layer | Owns |
|-------|------|
| `facade/` | Public helpers on resource facades + `CallGraphData` custom facade |
| `facade/search.py` | Shared `search_by_*` helpers (identity lane) |
| `facade/context_partition.py` | Scan-plane list filters (`context_partition_filter`, `main_context_filter`) |
| `operations/routes.py` | Generated accessor executors (`RouteExecutor`, `RouteResult`) |
| `operations/` | Pagination, group wire parsing |
| `resources/call_graph_data.py` | CallGraphData fetch/decode wire helpers |
| `api_client.py` | `get_all` — single low-level pagination loop |
| `workflows/` | Orchestration — **must not** duplicate list/count/group pagination or hand-built relationship filters when a generated accessor exists |
| `tools/` | Composition (`list_sharding`) — parallel list over project shards |
| `utils/` | Infra (`parallel`, namespace) — not domain list composition |

## Facade naming rules

1. **`client.<Kind>`** matches the endorctl resource kind (PascalCase).
2. **CRUD** (`list`, `get`) return **`<Kind>` models** (or masked `dict` rows).
3. **`list_by_*` / `list_for_context`** return **`list[T]`**; **`to_*`** stitch accessors return **`RouteResult`**. Normative map: [resource-discovery contract](../../agent-knowledge/contracts/resource-discovery.md). Inventory: [resource-routes.md](../generated-reference/resource-routes.md), [api-surfaces.md](../generated-reference/api-surfaces.md).
4. **`search_by_*`** return **`list[T]`** (bounded discovery; forwards `mask`, `filter`, etc.).
5. **Wire/auxiliary helpers** — custom decode/fetch, log POST (below).
6. **Custom facades** only when the kind is not yet on `registry_contract` — today: **`CallGraphData`** only.

## Identity lane (`search_by_*`)

| Method | Resource | Returns |
|--------|----------|---------|
| `Project.search_by_name(query, …)` | Project | `list[Project]` |
| `VectorStore.search_by_name(query, …)` | VectorStore | `list[VectorStore]` |
| `AuthorizationPolicy.search_by_claims(query, …)` | AuthorizationPolicy | `list[AuthorizationPolicy]` |
| `Vulnerability.search_by_vuln_alias(query, …)` | Vulnerability (OSS) | `list[Vulnerability]` |

Discovery always returns a **bounded list**; callers disambiguate. Supports `namespace=`, `traverse=`, `max_pages=`, `mask=`, `filter=` (including `F()`), and other `list()` kwargs. **`count=True` is rejected.**

```python
import endorlabs
from endorlabs import F

client = endorlabs.Client(tenant="tenant.root")

# Fuzzy repo URL
projects = client.Project.search_by_name(
    "github.com/org/repo",
    traverse=True,
    max_pages=2,
)

# Server-side pre-filter + fuzzy match
projects = client.Project.search_by_name(
    "repo",
    traverse=True,
    filter=F("meta.tags").contains("production"),
    max_pages=2,
)

# Known UUID
project = client.Project.get(project_uuid, namespace="tenant.child")
```

## Generated accessor helpers (codegen)

From `route_contract_overlay.yaml` + `route_partition_targets.yaml` → [resource-routes.md](../generated-reference/resource-routes.md) and [api-surfaces.md](../generated-reference/api-surfaces.md).

Regenerate: `uv run python devtools/generate_route_contract.py`.

**When to use:** Prefer generated accessors over hand-built `spec.project_uuid==…` or `context.scan_uuid==…` filters when the edge exists in the contract. Return-type semantics and stitch `RouteResult` protocol: [resource-discovery contract](../../agent-knowledge/contracts/resource-discovery.md).

`ScanResult.list_by_project` adds a workflow preset (newest-first, default `max_pages=1`, optional `limit` → `page_size`, client-side `status_filter`). For the latest scan: `ScanResult.list_by_project(project, limit=1)[0]`.

For manual scan-plane composition:

```python
from endorlabs.facade import context_partition_filter

findings = client.Finding.list_by_project(
    project,
    filter=context_partition_filter(scan.context),
    max_pages=5,
)
```

For exact finding UUIDs on a scan record, use `ScanResult.spec.findings` + `Finding.get(uuid)`.

**Removed (0.3.0):** `Finding.list_by_scan`, `Finding.list_for_scan`, `ScanResult.list_for_project`, `Project.resolve()` — see [changelog.md](../changelog.md).

## Project inventory (`ProjectFacade`)

| Method | Purpose |
|--------|---------|
| `is_sbom(project)` | `spec.sbom` set (SBOM import row) |
| `is_app(project)` | SCM app registration (`spec.git.external_installation_id` present) |
| `is_cli(project)` | CLI registration (no app installation id; exclude SBOM first) |

Accepts a `Project` model or masked `dict` row from `list(mask=...)`.

```python
for row in client.Project.list_iter(traverse=True, mask="meta.name,spec.git.external_installation_id,spec.sbom"):
    if client.Project.is_sbom(row):
        continue
    label = "Cloud Scan" if client.Project.is_app(row) else "CLI"
```

Installation lookup: `endorlabs.workflows.projects.inventory.fetch_installation_lookup`.

Per-**scan** CLI vs cloud execution uses `ScanResult.spec.environment.config.RunBySystem` (see product KB) — not the same as project registration above.

## FindingLog new-vs-resolved trends

```python
import endorlabs
from endorlabs.workflows.findings.finding_log_trends import (
    build_finding_log_new_vs_resolved_analysis,
)

client = endorlabs.Client(tenant="tenant.root", timeout=120.0)
analysis = build_finding_log_new_vs_resolved_analysis(client, "tenant.root", traverse=True)
```

Shared filters: `endorlabs.workflows.findings.filters` (`reachable_vuln_log_base_filter`, `prf_vuln_filter`, …).

Generic log aggregation: `endorlabs.workflows.logs.group_by_time.group_by_time_counts` (any listable log facade).

### Example: `FindingLog.list_groups` + `group_by_time`

```python
from endorlabs.core.types import ListParameters

for bucket in client.FindingLog.list_groups(
    namespace="tenant.root",
    traverse=True,
    filter="spec.operation==OPERATION_CREATE and ...",
    list_params=ListParameters(
        group_by_time=True,
        group_aggregation_paths=["meta.create_time"],
        group_by_time_interval="week",
        group_by_time_mode="count",
    ),
):
    print(bucket.parsed, bucket.count)
```

## Wire helpers

| Method | Input | Returns |
|--------|-------|---------|
| `CallGraphData.decode(package_version)` | `PackageVersion` or UUID + `namespace=` | `CallGraphDecoded` (searchable callables/edges) |
| `CallGraphData.fetch(package_version)` | same | raw envelope only — prefer `decode` or `resolve_package_version_with_callgraph` |
| `ScanResult.get_logs(scan_result, …)` | `ScanResult` or UUID + `namespace=` | `ScanLogRequestLogMessage[]` |

**Call graph path search:** Prefer `endor-agent-context --callgraph-export --decode-zstd` then `endor-callgraph-search` (`--path-from` / `--path-to` for multi-hop BFS) or `endor-callgraph-path` for live probes. Zero direct edges between two symbols often means a **multi-hop** wrapper chain — see shipped skill **endor-fetch-and-search-call-graph** (`call-graph-format-and-search.md` → path search protocol). Semantic function summaries: `endor-vector-query` or `VectorStore.query` (separate from call-graph export). Not for Finding/CVE reachability (use `endor-reachability-context`).

## Pagination

- `list(max_pages=None)` fetches **all pages** via `get_all()`.
- Generated accessors forward `max_pages`, `filter`, `list_params`, `mask`, and other list kwargs to the underlying wire op.
- Do **not** set `page_size` unless the user asks.

## Universal helpers (`ListableFacade`)

| Method | Purpose |
|--------|---------|
| `count(**list_kwargs) -> int` | Server-side count (replaces broken `list(count=True)`) |
| `list_groups(*, paths, **kwargs)` | Yield `GroupBucket` rows from `group_response` |
| `latest(sort_by=..., **kwargs) -> T \| None` | Newest row; always `max_pages=1` |
| `latest_created(**kwargs)` | Sugar for `sort_by="meta.create_time"` |
| `latest_updated(**kwargs)` | Sugar for `sort_by="meta.update_time"` |
| `parent(resource) -> ParentModel` | Registry `parent_kind` → parent GET (today: `"project"`) |

`list(count=True)` emits `DeprecationWarning` and delegates to `count()`.

### Example: project-scoped retrieval (base + `F()`)

```python
import endorlabs
from endorlabs import F

client = endorlabs.Client(tenant="tenant.child")
matches = client.Project.search_by_name(
    "https://github.com/org/repo",
    namespace="tenant.child",
    max_pages=2,
)
project = matches[0] if matches else None

# String filter
findings = client.Finding.list_by_project(
    project,
    filter='spec.level=="FINDING_LEVEL_CRITICAL"',
    max_pages=5,
)

# F() — composable, injection-safe
findings = client.Finding.list_by_project(
    project,
    filter=F("spec.level") == "FINDING_LEVEL_CRITICAL",
    max_pages=5,
)

scans = client.ScanResult.list_by_project(project, limit=5)
if scans:
    scan_findings = client.Finding.list_for_context(scans[0], max_pages=1)

for finding in findings or []:
    dm = client.Finding.to_dependency_metadata(finding)
    if dm.value:
        print(dm.edge_used, dm.value.uuid)
```

## Sharded parallel lists

For tenant-wide collection, use `endorlabs.tools.list_sharding` (`ParentShard`, `parallel_map_shards`, `list_for_shards`) with **`list_by_project`** per shard — see [list-query-performance.md](../contributing/list-query-performance.md) and estate collect workflows.
