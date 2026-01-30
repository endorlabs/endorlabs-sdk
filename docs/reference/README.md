# Reference

SDK reference documentation. OpenAPI spec: <https://api.endorlabs.com/download/openapiv2.swagger.json> (schema drift workflow downloads to `external_docs/` in CI).

## Public API

Stable surface: `endor_cockpit.__all__` — APIClient, exceptions (EndorAPIError, NotFoundError, etc.), resource submodules (finding, namespace, policy, project, etc.). See [resources.md](resources.md).

## Other surfaces

- **operations:** `from endor_cockpit.operations import list_findings, ...` — single import surface for list/get/create/update/delete (finding, namespace, policy, project).
- **utils:** `endor_cockpit.utils` — SchemaDriftDetector, create_traverse_params, create_namespace_scoped_params (see [namespace-traversal.md](../guides/namespace-traversal.md)).
- **analysis (experimental):** `endor_cockpit.analysis` — FindingDataLoader, FindingDatabase; API may change. See [src/endor_cockpit/analysis/README.md](../../src/endor_cockpit/analysis/README.md).

- [resources.md](resources.md) — Resource name, operations (list/get/create/update/delete), limitations.
- [namespace.md](namespace.md) — Namespace in the SDK (list/get/create/update/delete, parameters, pitfalls).
