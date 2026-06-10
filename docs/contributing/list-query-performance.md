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

## Sharded parallel lists

For large **project-scoped** resources (`DependencyMetadata`, `Finding`, `ScanResult`, grouped DM shards), one namespace-wide `list()` can return the same rows but force a long sequential pagination chain. Prefer **discover shard keys** (usually `Project` rows in the target namespace) → **parallel `list()` per shard** with a selective filter (`spec.importer_data.project_uuid==…`, `spec.project_uuid==…`) and **`namespace=project.namespace`**.

Use `ThreadPoolExecutor` / `--max-workers` (typical 8–16), `list_resource_count()` per shard for progress denominators, and spike with [`estate/collect/benchmark.py`](../../src/endorlabs/workflows/estate/collect/benchmark.py) before changing defaults. Do **not** assume namespace-wide list is faster — benchmark when row counts are high. Still prefer **one** `traverse=True` list when the resource is not naturally project-sharded or row counts are small.

**Primitives:** [`parallel_map_shards()`](../../src/endorlabs/workflows/estate/collect/shards.py), [`list_resource_count()`](../../src/endorlabs/workflows/estate/collect/bounds.py), [`format_progress()`](../../src/endorlabs/workflows/estate/collect/bounds.py), [`execute_across_namespaces()`](../../src/endorlabs/utils/parallel.py), [`main_context_filter()`](../../src/endorlabs/workflows/estate/filters/main_context.py). Estate context: [estate/README.md](../estate/README.md).

### Workflow applicability

| Area | Module / skill | Shard key | Parallel? | Notes |
| ---- | -------------- | --------- | ----------- | ----- |
| Compile graph collect | [`estate/collect/runner.py`](../../src/endorlabs/workflows/estate/collect/runner.py) | `spec.importer_data.project_uuid` | **Yes** | `endor-estate pull` → `data/`; `--resume` via `collect_manifest.json` |
| Relationship map | [`estate/analyze/project_map/map.py`](../../src/endorlabs/workflows/estate/analyze/project_map/map.py) | `spec.importer_data.project_uuid` | **Yes** | Uses [`estate/collect/shards.py`](../../src/endorlabs/workflows/estate/collect/shards.py) |
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
