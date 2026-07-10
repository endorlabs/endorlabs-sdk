---
id: endor-list-query-performance
tags:
- list
- pagination
- performance
summary: Do not set page_size unless explicitly asked; scope and filter before raising
  max_pages.
---

# List query performance

Guidance for SDK `list()` / `list_iter()` calls, workflow CLIs, and session scripts.

## Scope first

- Prefer **`Client(tenant="<child-or-leaf-namespace>")`** and **list without `traverse`**
  when you only need resources in that namespace.
- Use **`traverse=True`** from the tenant root only when you intentionally need the
  whole hierarchy.

A single `list(traverse=True)` minimizes round-trips; it does not guarantee a fast
server-side plan for broad unfiltered queries.

## Filters

- Prefer **selective filters** that narrow rows before pagination.
- **Filter** selects rows; **mask** trims returned fields — do not conflate them.
- A non-empty **mask** returns **`dict`** rows, not Pydantic models.

## Pagination

- **Do not set `page_size`** unless the user explicitly asks. Rely on API/SDK defaults.
  Very small `page_size` (especially `1`) can be pathologically slow on log-style resources
  (`AuditLog`, `FindingLog`, `AuthenticationLog`, …).
- **`max_pages`** caps client-side fetch depth — acceptable for bounding cost; it does not
  replace selective `filter` or namespace scope.
- For log resources, cap **`max_pages` only** and leave `page_size` unset.

## Debugging slow lists

1. Narrow to a **child namespace** without `traverse`.
2. Add or tighten **`filter`** when supported.
3. Compare with `endorctl api list` (same resource, namespace, filter, traverse).
4. Use a shorter read timeout when iterating locally.

## Query graph joins

- **`endorlabs.query`** (`client.Query.create`) is the platform **graph join** API — root kind + nested references; each node accepts `list_parameters` (`filter`, `mask`, `count`, `group`, `group_by_time`, pagination).
- Shipped **count recipes** POST to each project's **wire namespace** — not tenant root alone. Run `validate_sample()` on a small mix of namespaces before estate-wide count joins.
- **Custom joins** (masked lists, grouped rollups) use `QuerySpec` / `create(payload=...)` after validating parity — see [query-recipes.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/guides/query-recipes.md) and `tests/integration/client/test_query_recipes.py`.
- **Row export** at estate scale (`endor-estate pull`, JSONL) still uses `list_for_shards` until join-based materialization is validated.
- Classify **`OutputShape`** before estate-scale lists — see `rules/endor-output-shape-routing.md`.

See also `rules/endor-namespace-scoping.md` and `contracts/list-parameters.md`.
