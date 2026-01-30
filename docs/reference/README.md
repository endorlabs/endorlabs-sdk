# Reference

**For SDK usage:** Start with [AGENTS.md](../../AGENTS.md) (install, APIClient, resource usage). This section is reference and boundaries.

SDK reference documentation. OpenAPI spec: <https://api.endorlabs.com/download/openapiv2.swagger.json> (schema drift workflow downloads to `external_docs/` in CI).

## Public API

Stable surface: `endorlabs.__all__` — APIClient, Client, exceptions (EndorAPIError, NotFoundError, etc.). **Client:** `endorlabs.Client(tenant="...")` exposes all resources via `client.namespaces`, `client.projects`, `client.findings`, etc.; the list is driven by the registry in `endorlabs.registry`. Resources without update or delete raise `NotImplementedError` for those operations. The **full** resource set is under `endorlabs.resources` (list in [resources.md](resources.md)); the top-level package re-exports a subset. Signatures and behavior: see module and function docstrings (Pydantic/Pyright).

## Other surfaces

- **operations:** `from endorlabs.operations import list_findings, ...` — single import surface for list/get/create/update/delete (finding, namespace, policy, project).
- **utils:** `endorlabs.utils` — SchemaDriftDetector, create_traverse_params, create_namespace_scoped_params (see [namespace-traversal.md](../guides/namespace-traversal.md)).
- **analysis (experimental):** `endorlabs.analysis` — FindingDataLoader, FindingDatabase; API may change. See [src/endorlabs/analysis/README.md](../../src/endorlabs/analysis/README.md).

- [resources.md](resources.md) — Resource name, operations (list/get/create/update/delete), limitations.
- [namespace.md](namespace.md) — Namespace in the SDK (list/get/create/update/delete, parameters, pitfalls).

