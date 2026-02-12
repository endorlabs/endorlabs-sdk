---
name: implement-sdk-resource
description: >-
  Implement a new Endor Labs resource in the SDK: API analysis, Pydantic
  models, CRUD operations, registry entry, and tests. Use when adding a new
  resource type, implementing list/get/create/update/delete for a resource,
  or extending the Client surface with a new facade.
---

# Implement a New SDK Resource

Phased workflow for adding a new Endor Labs resource to the SDK. Every resource
follows the same two-layer, registry-driven pattern.

## Phase 0: API Analysis (mandatory)

Before writing any code, understand the API contract.

1. **Find the resource in the OpenAPI spec**:
   - Local (preferred): `.endorlabs-context/openapiv2.swagger.json`
   - Online (fallback): <https://api.endorlabs.com/download/openapiv2.swagger.json>
   - Grep for `{Resource}Service` and endpoint paths

2. **Extract schema**: `v1{Resource}`, `v1{Resource}Spec`
   - Note required vs optional fields, readOnly fields, types
   - Map service name, URL endpoints, HTTP methods

3. **Validate with live data**:
   ```bash
   endorctl api list -r {Resource} -n {namespace} --traverse
   endorctl api get -r {Resource} -n {namespace} --uuid {uuid}
   ```
   Compare live response shape with OpenAPI definitions.

4. **Build implementation matrix**:
   - Universal fields (all resources have them)
   - Conditional fields (present in some resources)
   - Resource-specific fields
   - Which CRUD operations the API supports
   - Which list parameters work (filter, mask, traverse)

For the full pre-implementation checklist, see [API_VALIDATION.md](API_VALIDATION.md).

## Phase 1: Implementation

### Models

Create in `src/endorlabs/resources/{resource_name}.py`:

- `{Resource}Meta(BaseMeta)` -- resource metadata
- `{Resource}Spec(BaseSpec)` -- resource specification
- `{Resource}(BaseResource)` -- top-level resource, extending BaseResource

**Field aliasing rules**: See [docs/conventions.md (Field aliasing)](../../../docs/conventions.md#field-aliasing).

### Operations

CRUD operations are handled by `BaseResourceOperations` via the `Client` facade — no module-level CRUD wrapper functions needed. The resource module only needs to define Pydantic models and any resource-specific convenience functions (e.g. `associate_scan_profile_with_project`).

- `update` requires `update_mask: str` (comma-separated paths); sparse PATCH always
- Use `endorlabs.exceptions`; log full `response.text` on errors

### Create/Update fields

- Allowed create fields: defined in the resource's `build_create_payload`
- Allowed update fields: defined by model's `get_mutable_fields_cls()` and `get_immutable_fields_cls()`
- Override these classmethods if the resource differs from BaseResource defaults
- The facade may expose a subset as explicit optional kwargs

### Docstrings

All public functions require: Args, Returns, Raises. Pydantic/Pyright and IDE must be self-explanatory.

## Phase 2: Expose on Client

Add one entry to the registry in `src/endorlabs/registry.py`:

```python
ResourceEntry(
    attr_name="resource_name",
    resource_name="api-path",
    model_class=ResourceModel,
    supported_ops=frozenset({"list", "get", "create", "update", "delete"}),
    scope=None,  # "system", "oss", or None
)
```

Do NOT hand-wire in `Client.__init__`; the registry drives facade attachment.

For architecture rules, see [docs/rules-of-engagement/architecture.md](../../../docs/rules-of-engagement/architecture.md).

## Phase 2b: Tests

Each resource test file follows canonical order:

1. **LIST** -- from root namespace with `traverse=True`. Assert result is a list.
2. **GET** -- GET the first item from LIST (pass resource object for namespace). Skip if LIST empty.
3. **Create** -- for resources where `"create" in entry.supported_ops`. Capture UUID for teardown.
4. **Update** -- for resources where `"update" in entry.supported_ops`. Update resource from step 3.
5. **Delete** -- for resources where `"delete" in entry.supported_ops`. Delete resource from step 3.

**Fixtures**: Use conftest `api_client`, `namespace`, `root_namespace`.

**Cleanup**: Every CREATE test must use try/finally so cleanup runs on pass, failure, or exception.

**No-update resources**: For `api_keys`, `audit_logs`, `finding_logs`, `dependency_metadata`, `linter_results` -- add test asserting `.update()` raises `NotImplementedError`.

## Checklist

- [ ] Phase 0: API analysis complete (spec + live data)
- [ ] Models: Meta, Spec, Resource with correct field aliasing
- [ ] Operations: list/get/create/update/delete with BaseResourceOperations
- [ ] Registry entry added (one line in `registry.py`)
- [ ] Tests: LIST, GET, Create, Update, Delete in canonical order
- [ ] Docstrings: Args, Returns, Raises on all public functions
- [ ] `uv run ruff check .` and `uv run pyright` pass
- [ ] `uv run pytest tests/test_{resource}.py -v` passes
