---
id: list-parameters
tags:
- list
- mask
- filter
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

See also [docs/guides/examples.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/guides/examples.md) (SDK examples).
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

**`page_id` and sort are mutually exclusive.** The platform rejects follow-up
list requests that send `list_parameters.page_id` together with
`list_parameters.sort.*` (HTTP 400: "page id cannot be provided with sort
method"). The SDK raises `ValidationError` before that call when
pagination would advance a sorted list via `page_id`.

For **N newest rows**, keep sort and stay on one page: `max_pages=1` with
`limit=` / `page_size=N` (e.g. `ScanResult.list_by_project(project, limit=N)`).
Do **not** raise `max_pages` above 1 while `sort_by` is set. To paginate a full
set, omit sort and order client-side if needed.

**Performance:** Do not set **`page_size`** unless explicitly requested. Prefer
defaults, selective **`filter`**, and **`max_pages`** caps. See bootstrap contract
`rules/endor-list-query-performance.md`.

Common filter literals (examples, codegen-verified): [reference/filter-enum-snippets.md](../reference/filter-enum-snippets.md).

## Update vs list mask

`update_mask` and list `mask` are separate concepts. Do not confuse them.

## Group by time (`list_groups`)

When **`group_by_time=True`**, the SDK serializes nested OpenAPI keys (not the
legacy flat `list_parameters.group_by_time_interval` form):

| SDK / `ListParameters` | Wire query param |
| ---------------------- | ---------------- |
| `group_aggregation_paths` or `group_by_time_field_value` | `list_parameters.group_by_time.aggregation_paths` (comma-separated) |
| `group_by_time_interval` (`week`, `day`, …) | `list_parameters.group_by_time.interval` (`GROUP_BY_TIME_INTERVAL_WEEK`, …) |
| `group_by_time_mode` | `list_parameters.group_by_time.mode` |

**Interval aliases:** `week`, `day`, `month`, `quarter`, `year`, `hour`,
`minute`, `second` map to `GROUP_BY_TIME_INTERVAL_*` enum values (same aliases
as endorctl). **Filter bounds** for the window are separate — use
`meta.create_time>=date(<iso-z>)` on the list `filter`, not the interval name.

**Field grouping without time:** `group_by_time=False` with
`group_aggregation_paths` uses `list_parameters.group.aggregation_paths`.

**Bucket counts:** `list_groups` group values are
`{ "aggregation_count": { "count": N } }`. `GroupBucket.count` and
`group_bucket_count()` read that field. Do not expect a top-level `count`.

**Not on Query.create:** `group_by_time` and field `group` aggregation via
`list_groups` are **facade list** features. `Query.create` supports root `group`
for limited namespace-scoped joins only — see
[query-vs-list-semantics.md](query-vs-list-semantics.md).
