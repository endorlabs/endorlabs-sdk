# Facade list helpers

Normative catalog for SDK facade helpers. Wire logic lives in `operations/`; workflows orchestrate only.

See also [resource-discovery contract](../agent-knowledge/contracts/resource-discovery.md) (shipped in wheel).

## Layer placement

| Layer | Owns |
|-------|------|
| `facade/` | Public helpers on resource facades + `CallGraphData` custom facade |
| `facade/search.py` | Shared `search_by_*` helpers (identity lane) |
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
3. **Generated accessor helpers** return **`RouteResult`** with `.values` / `.value`, `.edge_used`, `.warnings`. See [resource-routes.md](../generated-reference/resource-routes.md).
4. **`search_by_*`** return **`list[T]`** (same as `list()` for return shape; forwards `mask`, `filter`, etc.).
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

From `devtools/model_sync_profiles/route_contract_overlay.yaml` → `src/endorlabs/generated/route_contract.py` and [resource-routes.md](../generated-reference/resource-routes.md).

Regenerate: `uv run python devtools/generate_route_contract.py`

| Method | From → To | Returns |
|--------|-----------|---------|
| `Finding.list_by_project(project, …)` | Project → Finding | `RouteResult` → findings |
| `Finding.list_by_scan(scan, …)` | ScanResult → Finding | `RouteResult` → findings |
| `ScanResult.list_by_project(project, …)` | Project → ScanResult | `RouteResult` → scan results |
| `PackageVersion.list_by_project(project, …)` | Project → PackageVersion | `RouteResult` → package versions |
| `Finding.to_dependency_metadata(finding, …)` | Finding → DependencyMetadata | `RouteResult` → dependency row |

**Prefer these** over hand-built `filter='spec.project_uuid==…'`, `list(parent=project)`, or `filter='context.scan_uuid==…'` when the relationship is in the contract.

`ScanResult.list_by_project` adds a **workflow preset** on top of the generated edge: newest-first, default `max_pages=1`, optional `limit` (→ `page_size`) and client-side `status_filter`. Pass explicit `sort_by`, `max_pages`, `list_params`, or date bounds to override.

For the latest scan only, use `ScanResult.list_by_project(project, limit=1).values[0]`.

## Wire helpers

| Method | Input | Returns |
|--------|-------|---------|
| `CallGraphData.decode(package_version)` | `PackageVersion` or UUID + `namespace=` | `CallGraphDecoded` |
| `CallGraphData.fetch(package_version)` | same | raw CallGraphData envelope |
| `ScanResult.get_logs(scan_result, …)` | `ScanResult` or UUID + `namespace=` | `ScanLogRequestLogMessage[]` |

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
).values

# F() — composable, injection-safe
findings = client.Finding.list_by_project(
    project,
    filter=F("spec.level") == "FINDING_LEVEL_CRITICAL",
    max_pages=5,
).values

scans = client.ScanResult.list_by_project(project, limit=5)
if scans.values:
    scan_findings = client.Finding.list_by_scan(scans.values[0], max_pages=1)
    print(scan_findings.warnings)

for finding in findings or []:
    dm = client.Finding.to_dependency_metadata(finding)
    if dm.value:
        print(dm.edge_used, dm.value.uuid)
```

## Sharded parallel lists

For tenant-wide collection, use `endorlabs.tools.list_sharding` (`ParentShard`, `parallel_map_shards`, `list_for_shards`) with **`list_by_project`** per shard — see [list-query-performance.md](../contributing/list-query-performance.md) and estate collect workflows.
