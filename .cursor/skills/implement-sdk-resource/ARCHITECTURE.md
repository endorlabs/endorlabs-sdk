# Architecture Rules of Engagement

Two-layer, registry-driven design for the Endor Labs SDK. Use this when
editing the client surface, facade, or registry, or when adding resources
to the Client.

---

## Layers

### 1. Transport (APIClient)

**File:** `src/endorlabs/api_client.py`

- HTTP, auth, retries only. No resource concepts; no Pydantic models.
- Do not add tenant or resource accessors here.

### 2. Resource Surface (Client)

**File:** `src/endorlabs/client_surface.py`

- Holds default namespace and exposes resource facades (e.g., `client.namespace`, `client.project`).
- Build facades from the **registry**; do not hand-wire each resource in `Client.__init__`.

### 3. Facade (ResourceFacade[T])

**File:** `src/endorlabs/facade.py`

- Resolves namespace, builds `ListParameters` from convenience kwargs, delegates to module-level list/get/create/update/delete.
- Three facade types:
  - `ResourceFacade[T]` -- standard resources
  - `SystemResourceFacade[T]` -- system-owned resources (list only; get/update/delete raise NotImplementedError)
  - `OssResourceFacade[T]` -- OSS-scoped resources (namespace fixed to "oss")
- Accept optional `update_fn`/`delete_fn` for resources that lack them; raise `NotImplementedError` when the operation is not supported.

### 4. Registry

**File:** `src/endorlabs/registry.py`

- Single source of truth for which resources exist on `Client`.
- One entry per resource: `attr_name`, `model_class`, `list_fn`, `get_fn`, `create_fn`, `update_fn` (optional), `delete_fn` (optional), `scope`.
- Adding a resource = one registry entry. No other file changes needed for facade attachment.

---

## Rules

- **No coupling:** APIClient does not import or depend on resources, facade, or registry. Only the Client/facade layer depends on resource modules.
- **Registry-driven:** New resources are added by appending to the registry, not by adding new lines in `Client.__init__`.
- **Module functions unchanged:** The facade delegates to existing module-level functions (e.g., `list_namespaces(client, tenant_namespace, list_params, max_pages)`). Do not duplicate logic in the facade.
- **Types:** Use `ResourceFacade[T]` with the Pydantic model as `T` so `client.namespace.list()` is typed as `list[Namespace]`; keep full type annotations for Pyright.
- **Tags:** Tag/untag paths are derived from the model's mutable fields (no separate map needed).

---

## Adding a New Resource (Step by Step)

1. **Implement the resource module** in `src/endorlabs/resources/{name}.py`:
   - Models: `{Resource}(BaseResource)`, `{Resource}Spec(BaseSpec)`, `{Resource}Meta(BaseMeta)`
   - Operations: `_get_{name}_ops(client)` returning `BaseResourceOperations`
   - Functions: `list_*`, `get_*`, `create_*`, `update_*`, `delete_*`

2. **Add one registry entry** in `registry.py`:
   ```python
   ResourceEntry(
       attr_name="resource_name",
       model_class=Resource,
       list_fn=list_resources,
       get_fn=get_resource,
       create_fn=create_resource,
       update_fn=update_resource,    # None if not supported
       delete_fn=delete_resource,    # None if not supported
       scope=None,                   # "system" or "oss" if applicable
   )
   ```

3. **Write tests** following the canonical order (LIST, GET, Create, Update, Delete).

4. **Verify**: `uv run ruff check . && uv run pyright && uv run pytest tests/test_{name}.py -v`

---

## When to Use This Reference

- Editing `client_surface.py`, `facade.py`, or `registry.py`
- Adding or changing a resource exposed on `Client`
- Debugging facade behavior (namespace resolution, kwargs mapping)

## Related Files

- `src/endorlabs/api_client.py` -- Transport layer
- `src/endorlabs/client_surface.py` -- Client facade entry point
- `src/endorlabs/facade.py` -- ResourceFacade, SystemResourceFacade, OssResourceFacade
- `src/endorlabs/registry.py` -- Resource registry
- `docs/conventions.md` -- Naming, list parameters, update_mask, errors
- `docs/reference/create-update-payloads.md` -- Per-resource payload shapes
