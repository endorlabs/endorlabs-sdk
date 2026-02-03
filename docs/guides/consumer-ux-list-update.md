# Consumer UX: Filter vs Field Mask vs Update Mask

Recommendation for SDK consumer UX when working with list and update operations. See also [conventions.md](../conventions.md) (List parameters, Update and update_mask).

## Do not combine Filter and Field Mask

Keep **filter** and **mask** as separate concepts and separate parameters:

| Concept        | Role                                      | Where    |
|----------------|-------------------------------------------|----------|
| **filter**     | Which **rows** match (query)              | List only |
| **mask**       | Which **fields** are returned (projection)| List only |
| **update_mask**| Which **fields** are patched              | Update only |

- **filter** = "which resources" (e.g. `spec.level==FINDING_LEVEL_CRITICAL`).
- **mask** (on list) = "which fields in the response" (e.g. `meta.name,spec.level`).
- **update_mask** = "which fields to send in the PATCH body"; only for `.update()`, not list.

Combining filter and list mask would blur "what to return" with "which subset of that to show" and would be confusing. Keeping them separate matches the API (`list_parameters.filter` vs `list_parameters.mask`) and keeps list vs update semantics clear.

## What to expose as arguments (ideal UX)

Definitions: [conventions.md](../conventions.md) (List parameters, Update and update_mask). The ideal UX exposes the set of attributes and types defined by the spec; see [conventions.md](../conventions.md) and [rules-of-engagement](../rules-of-engagement/) (resource-implementation, architecture). The registry-based entrypoint (`client.namespace`, `client.project`, etc.) should expose **flat kwargs** so consumers do not have to construct `ListParameters` by hand.

**For `.list()`:**

- Expose as **top-level kwargs** (no combined "filter+mask" object):
  - **filter** — row filter expression.
  - **mask** — response field mask (comma-separated paths).
  - **traverse**, **page_size**, **page_token**, **sort_by**, **desc**, **count**, **from_date**, **to_date** (all from `ListParameters`).
  - **namespace** — override default namespace.
  - **list_params** — optional; for power users who want to pass a full `ListParameters` instead of kwargs.
  - **max_pages** — pagination cap.
  - **Identity kwargs** — for resources that support them (e.g. projects, repositories), pass `name`, `vcs_url`/`git_url`; they are translated into a filter (e.g. `meta.name == 'backend'`) and merged with an explicit `filter` if provided. Use `.lookup(name="...")` to get the single matching resource or raise `NotFoundError`/`AmbiguousError`.

Recommended style (see `main.py`):

```python
client.project.list(traverse=True)
client.project.list(filter="meta.name==https://github.com/org/repo.git", max_pages=1)
client.project.list(filter="spec.level==FINDING_LEVEL_CRITICAL", mask="meta.name,spec.level")
client.scan_result.list(filter="...", sort_by="meta.create_time", desc=True, page_size=5)
```

**For `.create()`:**

- Prefer **kwargs** when the resource supports a builder: `client.<resource>.create(name="...", namespace="...", ...)`. The facade builds the CreateXPayload internally. For power users, `client.<resource>.create(payload=CreateXPayload(...))` remains supported. See [reference/create-update-payloads.md](../reference/create-update-payloads.md).

**For `.update()`:**

- **update_mask** is **required** for all update-capable resources. Pass a comma-separated list of field paths (e.g. `"meta.description,meta.tags"`). Sparse PATCH is always used. Missing or empty mask raises `ValidationError`. Do not merge it with list semantics or with the list **mask**.

## Summary

- **Do not combine** filter and field mask; keep **filter** (rows) and **mask** (list response fields) as two distinct kwargs on `.list()`.
- **Expose both** as flat kwargs on the facade (already supported), along with other list parameters and **namespace** / **max_pages**.
- **update_mask** stays only on `.update()`, is **required**, and is a different concept from list **mask**.
- **Spec as source of truth:** See [conventions.md](../conventions.md) (List parameters, Update and update_mask) and [rules-of-engagement](../rules-of-engagement/) (resource-implementation, architecture).
- **filter** = which rows, **mask** = which fields in list responses, **update_mask** = which fields to patch on update (defined in conventions).
