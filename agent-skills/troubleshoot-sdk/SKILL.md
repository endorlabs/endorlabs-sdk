---
name: troubleshoot-sdk
description: >-
  Debug Endor Labs SDK errors, API failures, and test issues. Use when
  encountering 404 Not Found after traverse, 500 Server Error on list,
  "Spec is not full" errors, update_mask validation failures, namespace
  mismatches, or unexpected test skips. Covers platform-specific gotchas
  and resolution patterns.
---

# Troubleshoot SDK Issues

Systematic workflow for diagnosing and resolving Endor Labs SDK and API
integration failures.

## Workflow

1. **Document** -- capture the task, context, approach, and full error (including stack trace and `response.text`).
2. **Research** -- search codebase, docs, and API spec. Local spec: `.endorlabs-context/platform/openapi/openapiv2.swagger.json`; local user docs: `.endorlabs-context/platform/user-docs/`. Online fallback: <https://api.endorlabs.com/download/openapiv2.swagger.json>.
3. **Investigate** -- read SDK code and spec; test with `endorctl`; validate theories with live API calls.
4. **Resolve** -- implement fix; document signatures and learnings.

## Common Issues and Solutions

### 404 Not Found after `list(traverse=True)`

**Cause:** When you list with traverse and then call `get`/`update`/`delete` using just the UUID, the SDK uses the client's default namespace. If the resource lives in a child namespace, the path won't match.

**Fix:** Pass the **resource object** instead of just a UUID:

```python
# Correct
client.Project.delete(target)

# Wrong -- may 404
client.Project.delete(target.uuid)
```

The SDK extracts the namespace from `resource.tenant_meta.namespace`.

### 500 Server Error: "Spec is not full" / "not fully defined"

**Cause:** The backend may return 500 with messages like `FindingSpec is not full` when listing at certain namespaces (e.g., tenant root).

**Resolution:**
- If the API returns 5xx, the SDK is correct to surface it as `ServerError`
- Try listing at a child namespace (or different scope) instead
- Optional: a non-empty list `mask=` reduces payload size; it does not reliably fix backend “spec not full” 5xx by itself

### Path namespace vs body UUID mismatch

**Cause:** For endpoints that take a resource UUID in the body and a namespace in the path (e.g., scan-log-request with `scan_result_uuid`), the path namespace must be the **owning** namespace of that resource (`resource.tenant_meta.namespace`). Using a parent namespace can return 500 even with a valid UUID.

**Fix:** Always use the resource's own namespace:

```python
namespace = resource.tenant_meta.namespace  # or resource.namespace
```

### `update_mask` validation errors

**Cause:** `update(uuid, payload=...)` requires a non-empty `update_mask` (and paths must be mutable). Wrong or empty mask raises `ValidationError` / `ValueError`. When you pass **field kwargs** with a **resource instance**, the facade derives the mask—`update_mask` is not required in that form.

**Fix:** UUID + payload: provide a comma-separated field path list:

```python
client.Namespace.update(ns.uuid, payload=updated_payload, update_mask="meta.description")
```

Or pass the resource and kwargs (mask derived automatically):

```python
client.Namespace.update(ns, meta_description="new description")
```

### List field mask (dict rows) vs partial **model** responses

**Masked list (non-empty `mask`):** `list()` / `list_iter()` return **dict**
rows (shallow wire JSON), not Pydantic models—no “partial model” validation path.

**Unmasked list:** Rows are models. The API may still omit fields at some
scopes; the SDK applies leniency when **constructing models** (e.g.
`Finding.context`, `Project.spec.platform_source`, `BaseMeta.name` may be
`None` when absent on the wire).

**Callers:** Use `isinstance(row, dict)` after `list(..., mask=...)`; use dict
keys or omit `mask` for typed resources. Do not pass masked `dict` rows to
`delete`/`update` expecting a model—`get` by UUID or list without `mask` first.

### Tenant-context read-only resources

Resources `authentication_log`, `endor_license`, and `policy_template` are
tenant-context resources. Use tenant clients and `traverse=True` when broad
visibility is needed.

The SDK Client exposes `list()` and `get()` for these resources.
`create`/`update`/`delete` remain unsupported.

## Test Debugging

### Common test skips

| Skip reason | Cause | Action |
|-------------|-------|--------|
| 403 Forbidden | Insufficient permissions or system resource | Check namespace and resource type |
| "No resources in scope" | Empty namespace or wrong filter | Run `endorctl api list -r {Resource} -n {namespace} --traverse` to validate |
| Validation error on update | Immutable field in update_mask | Check `get_mutable_fields_cls()` on the model |

### Verifying with endorctl

```bash
# Check if namespace has data
endorctl api list -r Finding -n endor-solutions-tgowan --traverse --page-size 5

# Check a specific resource
endorctl api get -r Project -n endor-solutions-tgowan --uuid {uuid}
```

For test cleanup scripts, endorctl verification commands, and the full known-issues catalog, see [KNOWN_ISSUES.md](KNOWN_ISSUES.md).
