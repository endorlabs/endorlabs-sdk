# Reference

**For SDK usage:** Start with [AGENTS.md](../../AGENTS.md) (install, APIClient, resource usage). This section is reference and boundaries.

SDK reference documentation. OpenAPI spec: <https://api.endorlabs.com/download/openapiv2.swagger.json> (schema drift workflow downloads to `.endorlabs-context/` in CI).

## Public API

Stable surface: `endorlabs.__all__` — APIClient, Client, exceptions (EndorAPIError, NotFoundError, etc.). **Client:** `endorlabs.Client(tenant="...")` exposes all resources via `client.namespace`, `client.project`, `client.finding`, etc.; the list is driven by the registry in `endorlabs.registry`. Resources without update or delete raise `NotImplementedError` for those operations. The **full** resource set is under `endorlabs.resources` (list in [resources.md](resources.md)); the top-level package re-exports a subset. Signatures and behavior: see module and function docstrings (Pydantic/Pyright).

## Other surfaces

- **operations:** `from endorlabs.operations import list_findings, ...` — single import surface for list/get/create/update/delete (finding, namespace, policy, project).
- **utils:** `endorlabs.utils` — SchemaDriftDetector, create_traverse_params, create_namespace_scoped_params (see [namespace-traversal.md](../rules-of-engagement/namespace-traversal.md)).
- **sast_analysis (experimental):** `endorlabs.experimental.sast_analysis` — FindingDataLoader, FindingDatabase; API may change. See [src/endorlabs/experimental/sast_analysis/README.md](../../src/endorlabs/experimental/sast_analysis/README.md).

**Model consistency and aliasing:** Model consistency compares SDK Pydantic field paths (Python names) to the OpenAPI spec. **Greenfield:** Use Python name = spec key for shared fields (`context`, `processing_status`, `index_data`); no prefixed names. If you add a Tier 3 alias (prefixed name + alias) for a shared concept, add an entry to [model_consistency.SDK_FIELD_ALIAS_TO_SHARED](../../src/endorlabs/utils/model_consistency.py). See [conventions.md](../conventions.md) (Models and API parity → Field aliasing, Style heuristic).

- [resources.md](resources.md) — Resource name, operations (list/get/create/update/delete), limitations.
- [namespace.md](namespace.md) — Namespace in the SDK (list/get/create/update/delete, parameters, pitfalls).

