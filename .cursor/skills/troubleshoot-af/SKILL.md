---
name: troubleshoot-af
description: >-
  Debug Endor Labs AF errors, API failures, and test issues. Use when
  encountering 404 Not Found after traverse, 500 Server Error on list,
  "Spec is not full" errors, update_mask validation failures, namespace
  mismatches, or unexpected test skips. Covers platform-specific gotchas
  and resolution patterns.
---

# Troubleshoot AF Issues

Systematic workflow for diagnosing and resolving Endor Labs Agentic Framework and API
integration failures.

## Workflow

1. **Document** -- capture the task, context, approach, and full error (including stack trace and `response.text`).
2. **Research** -- search codebase, docs, and API spec. Spec URL: <https://api.endorlabs.com/download/openapiv2.swagger.json>.
3. **Investigate** -- read AF code and spec; test with `endorctl`; validate theories with live API calls.
4. **Resolve** -- implement fix; document signatures and learnings.

## Common Issues and Solutions

### 404 Not Found after `list(traverse=True)`

**Cause:** When you list with traverse and then call `get`/`update`/`delete` using just the UUID, the AF uses the client's default namespace. If the resource lives in a child namespace, the path won't match.

**Fix:** Pass the **resource object** instead of just a UUID:

```python
# Correct
client.project.delete(target)

# Wrong -- may 404
client.project.delete(target.uuid)
```

The AF extracts the namespace from `resource.tenant_meta.namespace`.

### 500 Server Error: "Spec is not full" / "not fully defined"

**Cause:** The backend may return 500 with messages like `FindingSpec is not full` when listing at certain namespaces (e.g., tenant root).

**Resolution:**
- If the API returns 5xx, the AF is correct to surface it as `ServerError`
- Try listing at a child namespace instead
- Use `mask` to request only the fields you need

### Path namespace vs body UUID mismatch

**Cause:** For endpoints that take a resource UUID in the body and a namespace in the path (e.g., scan-log-request with `scan_result_uuid`), the path namespace must be the **owning** namespace of that resource (`resource.tenant_meta.namespace`). Using a parent namespace can return 500 even with a valid UUID.

**Fix:** Always use the resource's own namespace:

```python
namespace = resource.tenant_meta.namespace  # or resource.namespace
```

### `update_mask` validation errors

**Cause:** `update_mask` is required for all update operations. Missing or empty mask raises `ValidationError`.

**Fix:** Always provide a comma-separated field path list:

```python
client.namespace.update(ns, update_mask="meta.description")
```

Or use field kwargs (mask is derived automatically):

```python
ns.update(client.namespace, meta_description="new description")
```

### Partial responses with list mask

**Cause:** List responses may omit spec-required fields when using `mask` or at certain scopes. The OpenAPI spec describes the full resource, but list is not guaranteed to return every field.

**Leniency:** The AF handles this for known cases:
- `Finding.context` -- optional when list response omits it
- `Project.spec.platform_source` -- optional when list mask omits it
- `BaseMeta.name` -- optional when list mask omits it

**Caller responsibility:** Handle `None` for these fields when using masks.

### System-owned resources (403 on GET/UPDATE/DELETE)

Resources `authentication_log`, `endor_license`, and `policy_template` are system-owned. LIST is allowed, but GET/UPDATE/DELETE return 403.

The AF Client exposes `list()` only for these. Calling `get`/`update`/`delete` raises `NotImplementedError`.

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
