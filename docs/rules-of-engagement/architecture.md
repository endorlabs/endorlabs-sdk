# Architecture Rules of Engagement

Two-layer, registry-driven design for the Endor Labs SDK. Use this when editing the client surface, facade, or registry, or when adding resources to the Client. See [AGENTS.md](../../AGENTS.md) (Architecture) and [.cursor/rules/architecture.mdc](../../.cursor/rules/architecture.mdc) for the short reference.

## Layers

1. **Transport (APIClient)** — `api_client.py`
   - HTTP, auth, retries only. No resource concepts; no Pydantic models.
   - Do not add tenant or resource accessors here.

2. **Resource surface (Client)** — `client_surface.py`
   - Holds default namespace and exposes resource facades (e.g. `client.Namespace`, `client.Project`).
   - Build facades from the **registry**; do not hand-wire each resource in `Client.__init__`.

3. **Facade (ResourceFacade[T])** — `facade.py`
   - Resolves namespace, builds `ListParameters` from convenience kwargs, and delegates CRUD/list behavior to `BaseResourceOperations`.
   - Single `ResourceFacade[T]` class handles all scopes via the `scope` parameter (`None` for tenant, `"oss"`).
   - Enforces supported operations from registry metadata; unsupported methods raise `NotImplementedError`.

4. **Registry adapter** — generated-contract + overlay source of truth for `Client`
   - Runtime contract is generated at `src/endorlabs/generated/registry_contract.py` by `devtools/model_sync.py`.
   - `registry.py` adapts generated contract rows into `ResourceEntry(...)` objects and applies explicit overrides from `registry_overlay.py`.
   - Adding/changing a resource should happen via model-sync inputs and the minimal overlay, not by hand-authoring a large registry table.

## Rules

- **No coupling:** APIClient does not import or depend on resources, facade, or registry. Only the Client/facade layer depends on resource modules.
- **Contract-driven:** New resources are added through model-sync generated contract data (and explicit overlay when needed), not by adding new lines in `Client.__init__`.
- **Facade delegates to BaseResourceOperations:** The facade instantiates `BaseResourceOperations` from registry metadata and delegates CRUD calls to it. Resource modules contain Pydantic models and convenience functions only — no module-level CRUD wrappers.
- **Types:** Use `ResourceFacade[T]` with the Pydantic model as `T` so `client.Namespace.list()` is typed as `list[Namespace]`; keep full type annotations for Pyright.

## When to Use

- Editing `client_surface.py`, `facade.py`, `registry.py`, or `registry_overlay.py`.
- Adding or changing a resource exposed on `Client` (through model-sync contract generation plus minimal overlay).
