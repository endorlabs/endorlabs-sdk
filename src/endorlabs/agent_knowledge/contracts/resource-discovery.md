---
id: resource-discovery
tags:
- discovery
- search
- list
- facade
---

# Resource discovery

Normative guidance for finding resources before relationship accessors (`list_by_project`, …).

## API summary

| API | Returns | When |
| --- | ------- | ---- |
| `search_by_*(query, …)` | `list[T]` or `list[dict]` with `mask=` | Fuzzy human/LLM input; always bounded |
| `list(**kwargs)` | Same as today | Custom MQL, grouping, masked rows |
| `get(uuid)` | Single model | Known UUID |
| `list_by_*` / `list_for_context` | `list[T]` or `list[dict]` with `mask=` | Cross-kind list edges from route contract |
| `to_*` | `RouteResult` | Stitch / GET-with-fallback — `.value`, `.edge_used`, `.warnings`; iterable |

Filter enum literals (examples): [reference/filter-enum-snippets.md](../reference/filter-enum-snippets.md). Relationship edge inventory: [reference/resource-routes.md](../reference/resource-routes.md).

**Removed (breaking):** `lookup()`, `Project.resolve()` — no shims. Use `search_by_*` + explicit disambiguation or `get(uuid)`.

## `RouteResult` (stitch accessors only)

`list_by_*` and `list_for_context` return **`list[T]`** at the facade (same as `.list()`). **`to_*`** stitch accessors return **`RouteResult[T]`** (`endorlabs.operations.routes`).

| Field / protocol | Use |
| --- | --- |
| `for row in result` | Iterate `.values` when set; else one item from `.value` |
| `len(result)` | Row count (0 when empty) |
| `bool(result)` | False when no `.value` and no `.values` |
| `.value` / `.single` | Preferred on stitch call sites — one resolved row |
| `.edge_used` | Which contract edge ran (useful when a method has fallback paths) |
| `.warnings` | Non-fatal issues (ambiguous attribute match, list-only fields on GET paths) |
| `.truncated` | Hint when stitch resolution picked one of many rows |

Namespace on list/stitch accessors is taken from the **source resource** unless `namespace=` is passed. Forward `filter`, `mask`, `max_pages`, and other list kwargs like `list()`.

## `search_by_*` parameters

All search methods delegate to `list()` then apply client-side substring matching.

Supported kwargs (forwarded to `list()`): `namespace`, `traverse`, `max_pages`, `page_size`, `filter`, `mask`, `sort_by`, `desc`, `list_params`, `from_date`, `to_date`, `archive`, `ci_run_uuid`.

**Not supported:** `count=True` (raises `ValueError`).

Optional `warnings_out: list[str]` receives truncation hints when the underlying list may be capped.

## Namespace

- `namespace=` — scope to one path segment (default: client tenant).
- `traverse=True` — fan out to child namespaces when the target namespace is unknown.

## Resource methods

| Method | Resource | Match |
| ------ | -------- | ----- |
| `Project.search_by_name` | Project | Substring on `meta.name`; partial UUID |
| `VectorStore.search_by_name` | VectorStore | Substring on `meta.name` |
| `AuthorizationPolicy.search_by_claims` | AuthorizationPolicy | Substring on policy name and claim-mapping fields |
| `Vulnerability.search_by_vuln_alias` | Vulnerability (OSS) | Substring on `meta.name`, `spec.aliases` |

## Examples — base and `F()`

### Discover project (bounded list)

```python
import endorlabs

client = endorlabs.Client(tenant="tenant.root")

# Fuzzy repo URL — may return multiple rows across child namespaces
projects = client.Project.search_by_name(
    "github.com/org/repo",
    traverse=True,
    max_pages=2,
)

# Server-side pre-filter before fuzzy match
from endorlabs import F

projects = client.Project.search_by_name(
    "repo",
    traverse=True,
    filter=F("meta.tags").contains("production"),
    max_pages=2,
)

# Masked dict rows (same rules as list)
projects = client.Project.search_by_name(
    "endor-sdk",
    traverse=True,
    mask="uuid,meta.name,tenant_meta.namespace",
    max_pages=1,
)
```

### Known UUID

```python
project = client.Project.get(project_uuid, namespace="tenant.child")
```

### Relationship accessors + refinement

```python
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
```

### Scan-plane partition (same `context.type` + `context.id`)

```python
from endorlabs.facade import context_partition_filter

scans = client.ScanResult.list_by_project(project, limit=1)
if scans:
    scan = scans[0]
    findings = client.Finding.list_for_context(scan, max_pages=5)

# Manual composition
findings = client.Finding.list_by_project(
    project,
    filter=context_partition_filter(scan.context),
    max_pages=5,
)
```

Do **not** filter on `context.scan_uuid` — OpenAPI `v1Context` exposes `type`, `id`, `tags`, `will_be_deleted_at` only.

For exact finding UUIDs on a scan record, use `ScanResult.spec.findings` + `Finding.get(uuid)`.

### Stitch accessor (`to_*`)

```python
route = client.Finding.to_dependency_metadata(finding)
dm = route.value  # or route.single
# RouteResult is iterable when you need fallback rows:
for row in route:
    ...
```

When `.values` is populated, `for row in route` matches those rows; a single-row GET path iterates one item via `.value`.

## Disambiguation

`search_by_*` follows the same split as Django ORM **`filter()`** vs **`get()`**: search returns a **bounded candidate list**; `get(uuid)` returns one row or raises. Method names are intentional — do not expect a single object from `search_by_name`.

When `search_by_name` returns multiple projects (same URL in different namespaces), workflows must pick a row, narrow `namespace=`, or fail explicitly — not rely on facade cardinality enforcement.

See bootstrap rule `endor-namespace-scoping` and [facade-helpers.md](../../docs/guides/facade-helpers.md).
