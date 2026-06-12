# Reference

**For SDK usage:** Start with [README.md](../../README.md) (install, quick start, configuration). This section is reference and boundaries.

SDK reference documentation. OpenAPI spec (local): `.endorlabs-context/platform/openapi/openapiv2.swagger.json`.
Generated reference surfaces are canonical in `docs/generated-reference/`. Per-resource create/list kwargs: [generated-reference/resources/README.md](../generated-reference/resources/README.md).
Runtime generated artifacts are documented in `src/endorlabs/generated/README.md`.

## Public API

Stable surface: `endorlabs.__all__` — APIClient, Client, exported exception classes (EndorAPIError, NotFoundError, etc.). **Client:** `endorlabs.Client(tenant="...")` exposes all resources via `client.Namespace`, `client.Project`, `client.Finding`, etc.; the list is driven by the registry in `endorlabs.registry`. Resources without update or delete raise `NotImplementedError` for those operations. The **full** resource set is under `endorlabs.resources` (list in [resources.md](resources.md)); the top-level package re-exports a subset. Signatures and behavior: see module and function docstrings (Pydantic/Pyright).

## Other surfaces

- **operations:** `from endorlabs.operations import BaseResourceOperations` — generic CRUD engine used internally by the `Client` facade. Not intended for direct consumer use; prefer `Client`.
- **utils:** `endorlabs.utils` — model validation helpers (see [namespace-traversal.md](../contributing/namespace-traversal.md)). API shape drift: [docs-drift-workflow.md](../contributing/docs-drift-workflow.md). Opt-in wire-key probes: `endorlabs.utils.schema_drift` (internal, not in `__all__`).

**Model consistency and aliasing:** Model consistency compares SDK Pydantic field paths (Python names) to the OpenAPI spec. **Greenfield:** Use Python name = spec key for shared fields (`context`, `processing_status`, `index_data`); no prefixed names. If you add a Tier 3 alias (prefixed name + alias) for a shared concept, add an entry to [`endorlabs.resources.field_aliases.SDK_FIELD_ALIAS_TO_SHARED`](../../src/endorlabs/resources/field_aliases.py). See [contracts.md](../contracts.md) (Models and API parity -> Field aliasing).

- [resources.md](resources.md) — Thin landing page to canonical generated resources matrix.
- [namespace.md](namespace.md) — Namespace in the SDK (list/get/create/update/delete, parameters, pitfalls).
- [api-surfaces.md](api-surfaces.md) — Thin landing page to canonical generated API surfaces.
- [create-update-payloads.md](create-update-payloads.md) — Thin landing page to canonical generated payload matrix.
- [../../devtools/sync/README.md](../../devtools/sync/README.md) — Model-sync generation module guide.
- [../../src/endorlabs/generated/README.md](../../src/endorlabs/generated/README.md) — Generated runtime artifact guide.
