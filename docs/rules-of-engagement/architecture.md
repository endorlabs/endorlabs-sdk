# Architecture Rules of Engagement

Two runtime layers plus registry-driven contract inputs define the Endor Labs SDK.
Use this when editing the client surface, facade, or registry, or when adding
resources to the Client. See [AGENTS.md](../../AGENTS.md) (Architecture) for the
short reference.

```mermaid
flowchart TD
    RC["generated registry contract<br/>src/endorlabs/generated/registry_contract.py"]
    RO["minimal overlay<br/>src/endorlabs/registry_overlay.py"]
    EXP["experimental append-only specs<br/>src/endorlabs/registry.py"]
    REG["registry adapter<br/>ResourceEntry values"]
    CLIENT["Layer 2: Client<br/>client_surface.py"]
    FACADE["Layer 2: ResourceRuntimeFacade[T]<br/>(ResourceFacade alias)"]
    OPS["BaseResourceOperations"]
    API["Layer 1: APIClient"]
    MODEL["Pydantic resource models"]
    NS["namespace resolution<br/>tenant / oss / system"]

    RC --> REG
    RO --> REG
    EXP --> REG
    REG --> CLIENT
    CLIENT --> FACADE
    FACADE --> OPS
    OPS --> API
    FACADE -. uses .-> MODEL
    FACADE -. resolves .-> NS
```

## Layers

1. **Transport (`APIClient`)** — `api_client.py`
   - HTTP, auth, retries only. No resource concepts; no Pydantic models.
   - Do not add tenant or resource accessors here.

2. **Resource surface (`Client`)** — `client_surface.py`
   - Holds default namespace and exposes resource facades (e.g. `client.Namespace`, `client.Project`).
   - Builds facades from the effective registry; do not hand-wire each resource in `Client.__init__`.

3. **Facade (`ResourceRuntimeFacade[T]`)** — `facade.py`
   - Resolves namespace, builds `ListParameters` from convenience kwargs, and delegates CRUD/list behavior to `BaseResourceOperations`.
   - `ResourceFacade` remains as a backward-compatible alias, but the runtime implementation is `ResourceRuntimeFacade`.
   - A single facade class handles all scopes via the `scope` property (`None` for tenant, `"oss"`, or `"system"`).
   - Enforces supported operations from registry metadata; unsupported methods raise `NotImplementedError`.

4. **Registry adapter** — generated-contract + overlay source of truth for `Client`
   - Runtime contract is generated at `src/endorlabs/generated/registry_contract.py` by `devtools/model_sync.py`.
   - `registry.py` adapts generated contract rows into `ResourceEntry(...)` objects, applies explicit overrides from `registry_overlay.py`, and appends narrowly scoped experimental facades when needed.
   - Prefer model-sync inputs plus the minimal overlay. Use experimental facades only as explicit, lightweight stopgaps instead of hand-authoring a large registry table.

## Rules

- **No coupling:** APIClient does not import or depend on resources, facade, or registry. Only the Client/facade layer depends on resource modules.
- **Contract-driven:** New resources normally come from model-sync generated contract data plus explicit overlay when needed. Experimental append-only facades live in `registry.py` and should stay minimal.
- **Facade delegates to BaseResourceOperations:** The facade instantiates `BaseResourceOperations` from registry metadata and delegates CRUD calls to it. Resource modules contain Pydantic models and convenience functions only; no module-level CRUD wrappers.
- **Types:** Use `ResourceRuntimeFacade[T]` with the Pydantic model as `T` so `client.Namespace.list()` is typed as `list[Namespace]`; the `ResourceFacade` alias remains for compatibility.

## When to Use

- Editing `client_surface.py`, `facade.py`, `registry.py`, or `registry_overlay.py`.
- Adding or changing a resource exposed on `Client` (through model-sync contract generation plus minimal overlay).
