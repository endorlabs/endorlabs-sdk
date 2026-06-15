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

From `devtools/model_sync_profiles/route_contract_overlay.yaml` (manual FK/parent edges) plus `route_partition_targets.yaml` (codegen `list_for_context` edges) → `src/endorlabs/generated/route_contract.py` and [resource-routes.md](../generated-reference/resource-routes.md).

Regenerate: `uv run python devtools/generate_route_contract.py` (also refreshes `tests/fixtures/routes/golden_edges.json`).

### `RouteResult`

List and stitch accessors return **`RouteResult[T]`** (`endorlabs.operations.routes`):

| Field | Use |
|-------|-----|
| `.values` | List edges — finding rows, scans, package versions, … |
| `.value` | GET/stitch edges — e.g. one `DependencyMetadata` row from `Finding.to_dependency_metadata` |
| `.edge_used` | Which contract edge ran (tier A/B/C; useful when a method has fallback paths) |
| `.warnings` | Non-fatal issues (e.g. list-only index fields on GET paths) |

Namespace is taken from the **source resource** unless `namespace=` is passed. Forward `filter`, `mask`, `max_pages`, and other list kwargs like `list()`.

### Project-scoped accessors (`list_by_project`)

| Method | Edge id | Wire kind | Returns |
|--------|---------|-----------|---------|
| `Finding.list_by_project(project, …)` | `project.findings` | `list_by_uuid_field` (`spec.project_uuid`) | `.values` → findings |
| `ScanResult.list_by_project(project, …)` | `project.scan_results` | `list_by_parent` | `.values` → scan results |
| `PackageVersion.list_by_project(project, …)` | `project.package_versions` | `list_by_uuid_field` | `.values` → package versions |

### Scan-plane accessors (`list_for_context`)

Pass any row with a `.context` (typically a **`ScanResult`**). Each method filters on OpenAPI **`v1Context`** fields (`context.type`, `context.id`) plus contract `also_filter` when present. Do **not** use `context.scan_uuid` — it is not on the wire filter schema.

| Method | Edge id | Target kind |
|--------|---------|-------------|
| `Finding.list_for_context(source, …)` | `scan.findings` | Finding |
| `PackageVersion.list_for_context(source, …)` | `scan.package_versions` | PackageVersion |
| `DependencyMetadata.list_for_context(source, …)` | `scan.dependency_metadata` | DependencyMetadata |
| `RepositoryVersion.list_for_context(source, …)` | `scan.repository_versions` | RepositoryVersion |
| `FindingLog.list_for_context(source, …)` | `scan.finding_logs` | FindingLog |
| `LinterResult.list_for_context(source, …)` | `scan.linter_results` | LinterResult |
| `Metric.list_for_context(source, …)` | `scan.metrics` | Metric |
| `PackageLicense.list_for_context(source, …)` | `scan.package_licenses` | PackageLicense |
| `ScanWorkflowResult.list_for_context(source, …)` | `scan.scan_workflow_results` | ScanWorkflowResult |
| `VersionUpgrade.list_for_context(source, …)` | `scan.version_upgrades` | VersionUpgrade |

Any facade whose kind appears in the table above inherits `list_for_context` via `RouteHostMixin` when the edge is in [resource-routes.md](../generated-reference/resource-routes.md). **`Finding`**, **`ScanResult`**, and **`PackageVersion`** also expose dedicated `list_by_project` / `to_dependency_metadata` wrappers in `facade/specialized.py`.

### Stitch accessor

| Method | Edge ids (fallback order) | Returns |
|--------|---------------------------|---------|
| `Finding.to_dependency_metadata(finding, …)` | `finding.dependency_metadata.get` → `finding.dependency_metadata.by_package` | `.value` → one `DependencyMetadata` row |

Full edge inventory (tiers, wire kinds, regeneration): [resource-routes.md](../generated-reference/resource-routes.md).

**Removed (0.3.0):** `Finding.list_by_scan`, `Finding.list_for_scan`, `ScanResult.list_for_project`, `Project.resolve()` — use the accessors above or `search_by_*` / `get(uuid)`. See [changelog.md](../changelog.md).

**Prefer these** over hand-built `filter='spec.project_uuid==…'`, `list(parent=project)`, or `filter='context.scan_uuid==…'` when the relationship is in the contract.

For manual composition:

```python
from endorlabs.facade import context_partition_filter

findings = client.Finding.list_by_project(
    project,
    filter=context_partition_filter(scan.context),
    max_pages=5,
).values
```

For exact finding UUIDs attached to one scan record, hydrate from `ScanResult.spec.findings` via `Finding.get(uuid)` — not a list route.

`ScanResult.list_by_project` adds a **workflow preset** on top of the generated edge: newest-first, default `max_pages=1`, optional `limit` (→ `page_size`) and client-side `status_filter`. Pass explicit `sort_by`, `max_pages`, `list_params`, or date bounds to override.

For the latest scan only, use `ScanResult.list_by_project(project, limit=1).values[0]`.

## Wire helpers

| Method | Input | Returns |
|--------|-------|---------|
| `CallGraphData.decode(package_version)` | `PackageVersion` or UUID + `namespace=` | `CallGraphDecoded` |
| `CallGraphData.fetch(package_version)` | same | raw CallGraphData envelope |
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
).values

# F() — composable, injection-safe
findings = client.Finding.list_by_project(
    project,
    filter=F("spec.level") == "FINDING_LEVEL_CRITICAL",
    max_pages=5,
).values

scans = client.ScanResult.list_by_project(project, limit=5)
if scans.values:
    scan_findings = client.Finding.list_for_context(scans.values[0], max_pages=1)

for finding in findings or []:
    dm = client.Finding.to_dependency_metadata(finding)
    if dm.value:
        print(dm.edge_used, dm.value.uuid)
```

## Sharded parallel lists

For tenant-wide collection, use `endorlabs.tools.list_sharding` (`ParentShard`, `parallel_map_shards`, `list_for_shards`) with **`list_by_project`** per shard — see [list-query-performance.md](../contributing/list-query-performance.md) and estate collect workflows.
