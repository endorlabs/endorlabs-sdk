# Architecture Rules of Engagement

Two-layer, registry-driven design for the Endor Labs SDK. Use this when editing the client surface, facade, or registry, or when adding resources to the Client. See [AGENTS.md](../../AGENTS.md) (Architecture) and [.cursor/rules/architecture.mdc](../../.cursor/rules/architecture.mdc) for the short reference.

## Layers

1. **Transport (APIClient)** — `api_client.py`
   - HTTP, auth, retries only. No resource concepts; no Pydantic models.
   - Do not add tenant or resource accessors here.

2. **Resource surface (Client)** — `client_surface.py`
   - Holds default namespace and exposes resource facades (e.g. `client.namespace`, `client.project`).
   - Build facades from the **registry**; do not hand-wire each resource in `Client.__init__`.

3. **Facade (ResourceFacade[T])** — `facade.py`
   - Resolves namespace, builds `ListParameters` from convenience kwargs, delegates to module-level list/get/create/update/delete.
   - Single `ResourceFacade[T]` class handles all scopes via the `scope` parameter (`None` for tenant, `"system"`, `"oss"`).
   - Accept optional `update_fn`/`delete_fn` for resources that lack them; raise `NotImplementedError` when the operation is not supported.

4. **Registry** — single source of truth for which resources exist on `Client`
   - One entry per resource via `ResourceEntry.from_module(attr_name, module, model, api_path, ...)`.
   - Adding a resource = one registry entry.

## Rules

- **No coupling:** APIClient does not import or depend on resources, facade, or registry. Only the Client/facade layer depends on resource modules.
- **Registry-driven:** New resources are added by appending to the registry (e.g. `RESOURCE_REGISTRY` in `registry.py`), not by adding new lines in `Client.__init__`.
- **Module functions unchanged:** The facade delegates to existing module-level functions (e.g. `list_namespaces(client, tenant_namespace, list_params, max_pages)`). Do not duplicate logic in the facade.
- **Types:** Use `ResourceFacade[T]` with the Pydantic model as `T` so `client.namespace.list()` is typed as `list[Namespace]`; keep full type annotations for Pyright.

## When to Use

- Editing `client_surface.py`, `facade.py`, or `registry.py`.
- Adding or changing a resource exposed on `Client` (e.g. adding a new resource to the registry after implementing its module).
