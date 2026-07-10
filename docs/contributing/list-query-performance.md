# List query performance

Guidance for SDK users and contributors when choosing **namespace scope**, **`traverse`**, **filters**, and **pagination** so list calls stay reliable. Normative list behavior remains in [contracts.md](../contracts.md); traverse UX patterns are in [namespace-traversal.md](namespace-traversal.md).

**Agent-facing summary (shipped):** `agent-knowledge/rules/endor-list-query-performance.md` (`rules/` in the wheel bundle).

## Scope first

- Prefer **`Client(tenant="<child-or-leaf-namespace>")`** and **list without `traverse`** when you only need resources in that namespace.
- Use **`traverse=True`** from the **tenant root** when you intentionally need resources across the whole tenant hierarchy. See [namespace-traversal.md](namespace-traversal.md) (when to use / avoid traverse).

**Efficiency of traverse:** A single `list(traverse=True)` minimizes **round-trips** to the API. It does **not** guarantee a fast server-side plan for every resource or dataset—unfiltered or broad lists can still be expensive on the backend.

## Filters

- Prefer **selective filters** that narrow rows before pagination (e.g. equality on stable dimensions documented for the resource).
- Avoid relying on **list + filter** for fields that are poor list keys or are known to stress the backend for a given resource; confirm behavior in the OpenAPI spec and, when debugging, compare with `endorctl api list` for the same namespace and filter.
- **Filter** selects rows; **mask** (`list_params.mask`) reduces returned fields. Do not conflate them; see [guides/consumer-ux-list-update.md](../guides/consumer-ux-list-update.md). A **non-empty** mask also changes the SDK row type to **`dict`** (see [contracts.md](../contracts.md)); omit `mask` when you need full models end-to-end.

## Pagination: client bounds vs server work

- **`max_pages`** caps how many pages the SDK will fetch in a loop. It does **not** cap backend work for a single page—one page can still be slow if the query is broad or heavy.
- **`page_size`:** Generic resource integration tests may use **`page_size=1`** with **`max_pages=1`** to bound CI cost; that is **not** a universal recommendation for production scripts. **Log-style tests** (`AuditLog`, `FindingLog`, `AuthenticationLog`, …) cap **`max_pages` only** and omit `page_size` — forcing `page_size=1` on log lists can be pathologically slow on the backend. See `TEST_LOG_LIST_*` in `tests/conftest.py`. Very small page sizes can interact badly with some server plans; prefer defaults or moderate sizes unless you have a specific need. See also [namespace-traversal.md](namespace-traversal.md) (pagination notes).

## Debugging slow or “hanging” lists

1. **Narrow scope:** try a **child namespace** without `traverse` before tenant-wide traverse.
2. **Add or tighten `filter`** if the resource supports it.
3. **Compare wire behavior** with `endorctl api list` (same resource, namespace, filter, traverse, page size) to separate client issues from backend latency.
4. **Timeouts:** A long **read timeout** on `APIClient` (e.g. integration tests) can make a stalled response look indefinite; use a shorter timeout when iterating locally.

Related: [troubleshooting.md](troubleshooting.md) (list `ServerError`, 404 after traverse), [guides/retrieving-scan-results.md](../guides/retrieving-scan-results.md) (Project → ScanResult → Finding workflow).

## Parallel fan-out grains (do not merge)

Three intentional grains — pick by use case; do **not** force-unify into one API:

| Grain | Use case | Primitive |
| ----- | -------- | --------- |
| **Namespace traverse** | Interactive tenant discovery | `list(traverse=True, concurrent=True)` → `_list_concurrent` / [`execute_across_namespaces`](../../src/endorlabs/utils/parallel.py) |
| **Per-project shards** | Estate collect, PRF, FindingLog trends fallback | [`parallel_map_shards`](../../src/endorlabs/tools/list_sharding.py) / `ProjectShard` → [`parallel_over`](../../src/endorlabs/tools/parallel_scopes.py) |
| **Query batching** | Estate counts / validated collect joins | [`QueryScope`](../../src/endorlabs/query/) + `QueryExecutor` pools |

Route estate-scale asks with [`query/routing.py`](../../src/endorlabs/query/routing.py) `OutputShape` + `recommend()` before choosing a grain. See also [query-recipes.md](../guides/query-recipes.md) and rule `endor-output-shape-routing`.

## Sharded parallel lists

For large **project-scoped** resources (`DependencyMetadata`, `Finding`, `ScanResult`, grouped DM shards), one namespace-wide `list()` can return the same rows but force a long sequential pagination chain. Prefer **discover shard keys** (usually `Project` rows in the target namespace) → **parallel `list()` per shard** with a selective filter (`spec.importer_data.project_uuid==…`, `spec.project_uuid==…`) and **`namespace=project.namespace`**. Prefer generated accessors (`Finding.list_by_project`, `ScanResult.list_by_project`) when the route exists.

Use `ThreadPoolExecutor` / `--max-workers` (typical 8–16), `facade.count()` or `count_for_progress()` per shard for progress denominators, and spike with [`estate/collect/benchmark.py`](../../src/endorlabs/workflows/estate/collect/benchmark.py) before changing defaults. Do **not** assume namespace-wide list is faster — benchmark when row counts are high. Still prefer **one** `traverse=True` list when the resource is not naturally project-sharded or row counts are small.

### SDK helper (`endorlabs.tools.list_sharding`)

```python
from endorlabs.tools.list_sharding import list_for_shards, project_model_to_shard

projects = client.Project.list(namespace=child_ns)
shards = [project_model_to_shard(p, child_ns) for p in projects]
rows = list_for_shards(
    client.Finding,
    shards,
    filter_fn=lambda s: f'spec.project_uuid=="{s.project_uuid}"',
    max_workers=12,
)
```

Estate-scale bulk collect remains in `endor-estate` workflows; see `AGENTS.md` for measured speedup notes.

**Primitives:** [`endorlabs.tools.list_sharding`](../../src/endorlabs/tools/list_sharding.py) (`ProjectShard`, `parallel_map_shards`, `topology_to_project_shards`), [`endorlabs.query`](../../src/endorlabs/query/__init__.py) (`discover_topology`, `preflight_count`), [`client.Query.Project`](../../src/endorlabs/query/project_facade.py) (count/collect recipes), [`facade.count()`](../../src/endorlabs/facade/) / [`count_for_progress()`](../../src/endorlabs/tools/list_bounds.py), [`format_progress()`](../../src/endorlabs/tools/list_bounds.py), [`execute_across_namespaces()`](../../src/endorlabs/utils/parallel.py), [`endorlabs.filters`](../../src/endorlabs/filters/__init__.py). Catalog: [facade-helpers.md](../guides/facade-helpers.md), [query-recipes.md](../guides/query-recipes.md). Estate context: [estate/README.md](../estate/README.md).

### Workflow applicability

| Area | Module / skill | Shard key | Parallel? | Notes |
| ---- | -------------- | --------- | ----------- | ----- |
| Compile graph collect | [`estate/collect/runner.py`](../../src/endorlabs/workflows/estate/collect/runner.py) | `spec.importer_data.project_uuid` | **Yes** | `endor-estate pull` → `data/`; `--resume` via `collect_manifest.json` |
| Relationship map | [`estate/analyze/project_map/run.py`](../../src/endorlabs/workflows/estate/analyze/project_map/run.py) | `spec.importer_data.project_uuid` | **Yes** | `discover_topology` → `topology.project_shards()` |
| Estate cardinality | [`estate/analyze/cardinality/export.py`](../../src/endorlabs/workflows/estate/analyze/cardinality/export.py) | — | **No** | Disk rollup from pulled JSONL |
| Tenant traverse | `Client.*.list(traverse=True, concurrent=True)` | namespace path | **Yes** | Per child namespace, not per project |
| Scan RCA (all projects) | [`fetch_scan_results.py`](../../src/endorlabs/workflows/troubleshooting_scans/fetch_scan_results.py) | `meta.parent_uuid` | **Yes** | Prefer `--project-uuid` for interactive RCA |
| Scan error search | [`search_scan_errors.py`](../../src/endorlabs/workflows/troubleshooting_scans/search_scan_errors.py) | `project_uuid` | **Yes** | Same pattern when `--all-projects` |
| Agent context export | [`agent_context/export.py`](../../src/endorlabs/workflows/agent_context/export.py) | `spec.project_uuid` | Partial | Single project per run |
| Findings / policies session | [`session_artifacts.py`](../../src/endorlabs/workflows/agent_context/session_artifacts.py) | `spec.project_uuid` | **No** | Low volume per project |
| Publisher index / PV sweep | [`estate/collect/runner.py`](../../src/endorlabs/workflows/estate/collect/runner.py) | — | Traverse | `PackageVersion.list(traverse=True)` on pull |
| SemgrepRule metadata inventory | [`semgrep/inventory.py`](../../src/endorlabs/workflows/semgrep/inventory.py) | — | **No** | `SemgrepRule.list(traverse=True)` via `endor-semgrep-inventory`; not project-scoped |
| Reachability / call graph | [`reachability/`](../../src/endorlabs/workflows/reachability/) | project / PV UUID | Partial | Bounded artifact fetch |

## References

- [contracts.md](../contracts.md) — `ListParameters`, namespace scoping.
- [namespace-traversal.md](namespace-traversal.md) — `traverse` patterns and examples.
- [guides/consumer-ux-list-update.md](../guides/consumer-ux-list-update.md) — filter vs mask vs `max_pages`.
