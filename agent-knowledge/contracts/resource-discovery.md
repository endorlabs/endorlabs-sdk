---
id: resource-discovery
tags: [discovery, search, list, facade]
---

# Resource discovery

Normative guidance for finding resources before relationship accessors (`list_by_project`, …).

## API summary

| API | Returns | When |
| --- | ------- | ---- |
| `search_by_*(query, …)` | `list[T]` or `list[dict]` with `mask=` | Fuzzy human/LLM input; always bounded |
| `list(**kwargs)` | Same as today | Custom MQL, grouping, masked rows |
| `get(uuid)` | Single model | Known UUID |
| `list_by_*` / `to_*` | `RouteResult` | Cross-kind edges from route contract |

**Removed (breaking):** `lookup()`, `Project.resolve()` — no shims. Use `search_by_*` + explicit disambiguation or `get(uuid)`.

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
).values

# F() — composable, injection-safe
findings = client.Finding.list_by_project(
    project,
    filter=F("spec.level") == "FINDING_LEVEL_CRITICAL",
    max_pages=5,
).values
```

## Disambiguation

When `search_by_name` returns multiple projects (same URL in different namespaces), workflows must pick a row, narrow `namespace=`, or fail explicitly — not rely on facade cardinality enforcement.

See bootstrap rule `endor-namespace-scoping` and [facade-helpers.md](../../docs/guides/facade-helpers.md).
