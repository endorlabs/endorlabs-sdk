# List query performance

Guidance for SDK users and contributors when choosing **namespace scope**, **`traverse`**, **filters**, and **pagination** so list calls stay reliable. Normative list behavior remains in [contracts.md](../contracts.md); traverse UX patterns are in [namespace-traversal.md](namespace-traversal.md).

**Agent-facing summary (shipped):** `agent-skills/contracts/list-query-performance.md` (`tier: bootstrap` in the wheel bundle).

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

## References

- [contracts.md](../contracts.md) — `ListParameters`, namespace scoping.
- [namespace-traversal.md](namespace-traversal.md) — `traverse` patterns and examples.
- [guides/consumer-ux-list-update.md](../guides/consumer-ux-list-update.md) — filter vs mask vs `max_pages`.
