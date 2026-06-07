---
id: list-parameters
tags:
- list
- mask
- filter
---

# List parameters

- **filter:** Which rows match (MQL-style expressions).
- **mask:** Which fields are returned in list responses.

## Return shape

When **mask** is non-empty after strip, `list()` returns **`list[dict[str, Any]]`** (wire JSON rows).
When mask is absent or whitespace-only, full Pydantic models are returned.

**`lookup()`** requires a typed resource and raises **`ValueError`** when an effective non-empty
mask is present. Use **`list()`** / **`list_iter()`** for masked dict rows.

## Consumer UX

Common list params are flat kwargs on `client.<ResourceKind>.list(...)`. Use
`list_params=ListParameters(...)` for advanced controls. Unknown flat kwargs raise **`TypeError`**.

## Pagination and sort

- **page_size**, **page_token**, **page_id**
- **sort_by**, **desc**
- **traverse:** tenant-wide discovery (`list_parameters.traverse=true`)

**Performance:** Do not set **`page_size`** unless explicitly requested. Prefer
defaults, selective **`filter`**, and **`max_pages`** caps. See bootstrap contract
`rules/endor-list-query-performance.md`.

## Update vs list mask

`update_mask` and list `mask` are separate concepts. Do not confuse them.
