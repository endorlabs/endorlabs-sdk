# Consumer UX: Filter vs Field Mask vs Update Mask

Recommendation for SDK consumer UX when working with list and update operations. See also [contracts.md](../contracts.md) (List parameters, Update and update_mask).

## Do not combine Filter and Field Mask

Keep **filter** and **mask** as separate concepts and separate parameters:

| Concept        | Role                                      | Where    |
|----------------|-------------------------------------------|----------|
| **filter**     | Which **rows** match (query)              | List only |
| **mask**       | Which **fields** are returned (projection)| List only |
| **update_mask**| Which **fields** are patched              | Update only |

- **filter** = "which resources" (e.g. `spec.level==FINDING_LEVEL_CRITICAL`).
- **mask** (on list) = "which fields in the response" (e.g. `meta.name,spec.level`).
- **List return type:** With a **non-empty** mask (after strip), `list()` returns **`list[dict[str, Any]]`**. With no effective mask, rows are full **Pydantic** models. **`list_iter()`** yields **`T | dict[str, Any]`** per item under the same mask rule. **`lookup()`** always returns a model and **raises `ValueError`** if a non-empty mask would apply—use **`list()`** / **`list_iter()`** for masked dict rows.
- `filter` and list `mask` semantics mirror MongoDB-style MQL query/projection conventions.
- **update_mask** = "which fields to send in the PATCH body"; only for `.update()`, not list.

Combining filter and list mask would blur "what to return" with "which subset of that to show" and would be confusing. Keeping them separate matches the API (`list_parameters.filter` vs `list_parameters.mask`) and keeps list vs update semantics clear.

## What to expose as arguments (ideal UX)

Definitions: [contracts.md](../contracts.md) (List parameters, Update and update_mask). The ideal UX exposes the set of attributes and types defined by the spec while documenting SDK-only convenience behavior. The registry-based entrypoint (`client.Namespace`, `client.Project`, etc.) exposes **flat kwargs** so consumers do not have to construct `ListParameters` by hand.

**For `.list()`:**

- Expose as **top-level kwargs** (no combined "filter+mask" object):
  - **filter** — row filter expression.
  - **mask** — response field mask (comma-separated paths).
  - **traverse**, **page_size**, **page_token**, **sort_by**, **desc**, **count**, **from_date**, **to_date** (all from `ListParameters`).
  - **ci_run_uuid** — PR scan context id (OpenAPI `list_parameters.ci_run_uuid`); use for PR-scoped lists when supported. **pr_uuid** is a deprecated alias for the same wire field.
  - **namespace** — override default namespace.
  - **list_params** — optional; to pass a full `ListParameters` instead of kwargs.
  - **max_pages** — pagination cap.
  - **Identity kwargs** — for resources that support them (e.g. projects, repositories), pass `name`, `vcs_url`/`git_url`; they are translated into a filter (e.g. `meta.name == 'backend'`) and merged with an explicit `filter` if provided. Use `.lookup(name="...")` to get the single matching resource or raise `NotFoundError`/`AmbiguousError`. **List/lookup by identity** is supported only for resources that have an identity filter map (see [reference/create-update-payloads.md](../reference/create-update-payloads.md)); for other resources use `filter=` explicitly.

Recommended style:

```python
client.Project.list(traverse=True)
client.Project.list(filter='meta.name=="https://github.com/org/repo.git"', max_pages=1)
client.Project.list(filter="spec.level==FINDING_LEVEL_CRITICAL", mask="meta.name,spec.level")
client.ScanResult.list(filter="...", sort_by="meta.create_time", desc=True, page_size=5)
```

**For `.create()`:**

- Prefer **kwargs** when the resource supports a builder: `client.<resource>.create(name="...", namespace="...", ...)`. The facade builds the CreateXPayload internally. Alternatively, `client.<resource>.create(payload=CreateXPayload(...))` remains supported. See [reference/create-update-payloads.md](../reference/create-update-payloads.md) and the per-resource pages under [generated-reference/resources/README.md](../generated-reference/resources/README.md).
- **Unknown flat create kwargs** raise **`TypeError`** (OpenAPI-aligned allowlist). Use `payload=` or nested `spec=` / `meta=` for fields outside the flat list.

**For `.list()` — strict kwargs:**

- Unknown flat kwargs (typos or unsupported names) raise **`TypeError`** with an allowed-key hint. Use `list_params=ListParameters(...)` for full control.

**For `.update()`:**

- **UUID + payload update path:** `update_mask` is required. Pass a comma-separated list of field paths (for example `"meta.description,meta.tags"`). Sparse PATCH is always used. Missing or empty mask raises a validation error.
- **Resource-instance field-kwargs path:** when you pass a resource object and mutable field kwargs, the SDK derives `update_mask` automatically.

## Summary

- **Do not combine** filter and field mask; keep **filter** (rows) and **mask** (list response fields) as two distinct kwargs on `.list()`.
- **Expose both** as flat kwargs on the facade (already supported), along with other list parameters and **namespace** / **max_pages**.
- **update_mask** stays only on `.update()`, and is a different concept from list **mask**.
- **Contract source:** See [contracts.md](../contracts.md) (List parameters, Update and update_mask).
- **filter** = which rows, **mask** = which fields in list responses, **update_mask** = which fields to patch on update.
