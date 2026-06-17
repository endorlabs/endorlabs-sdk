---
id: list-parameters
tags: [list, mask, filter]
---

# List parameters

- **filter:** Which rows match (MQL-style expressions).

## Filter operators (common)

| Operator | Typical field type | Example |
| -------- | ------------------ | ------- |
| `==` | Scalar | `meta.name == "my-rule"` |
| `matches` | String (regex) | `meta.name matches "endor-sdk.*"` |
| `contains` | Array / enum list | `spec.finding_tags contains [FINDING_TAGS_REACHABLE_FUNCTION]` |

**String fields:** use **`F("field").matches(...)`** (or raw `field matches "pattern"`).
Do **not** use `contains` for substring search on scalar strings —
`meta.name contains "substring"` (without bracket list syntax) often returns
**zero rows with no error**.

**Array fields:** use **`F("field").contains(...)`**, which emits bracket syntax
(`field contains [VALUE]`).

See also [docs/guides/examples.md](../../docs/guides/examples.md) (SDK examples).
- **mask:** Which fields are returned in list responses.

## Return shape

When **mask** is non-empty after strip, `list()` returns **`list[dict[str, Any]]`** (wire JSON rows).
When mask is absent or whitespace-only, full Pydantic models are returned.

**`search_by_*`** and **`list()`** / **`list_iter()`** accept the same list kwargs including **`mask=`**; with a non-empty mask, rows are **`dict`**, not typed models.

## Consumer UX

Common list params are flat kwargs on `client.<ResourceKind>.list(...)`. Use
`list_params=ListParameters(...)` for advanced controls. Unknown flat kwargs raise **`TypeError`**.

## Pagination and sort

- **page_size**, **page_token**, **page_id**
- **`limit`** — alias for **`page_size`** on `.list()` / `.list_iter()` (same normalization as `list_by_project(..., limit=)` on `ScanResultFacade`)
- **sort_by**, **desc**
- **traverse:** tenant-wide discovery (`list_parameters.traverse=true`)

**Performance:** Do not set **`page_size`** unless explicitly requested. Prefer
defaults, selective **`filter`**, and **`max_pages`** caps. See bootstrap contract
`rules/endor-list-query-performance.md`.

Common filter literals (examples, codegen-verified): [reference/filter-enum-snippets.md](../reference/filter-enum-snippets.md).

## Update vs list mask

`update_mask` and list `mask` are separate concepts. Do not confuse them.
