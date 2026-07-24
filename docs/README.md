# Endor Labs SDK Documentation

Index for SDK-specific documentation.

## Doc taxonomy

- [contracts.md](contracts.md) — Normative SDK behavior agreements (`MUST/SHALL` semantics).
- [changelog.md](changelog.md) — User-facing release notes (**Added**, **Changed**, **Breaking**).
- [design.md](design.md) — Design rationale and tradeoffs (non-normative).
- [reference/README.md](reference/README.md) — Curated reference index and stable landing pages.

## Reference

- [reference/README.md](reference/README.md) — List of reference docs.
- [reference/resources.md](reference/resources.md) — Landing page to canonical generated resources matrix.
- [reference/namespace.md](reference/namespace.md) — Namespace in the SDK (list/get/create/update/delete).
- [reference/api-surfaces.md](reference/api-surfaces.md) — Landing page to canonical generated API surfaces.
- [reference/create-update-payloads.md](reference/create-update-payloads.md) — Landing page to canonical generated payload matrix.
- [generated-reference/resources.md](generated-reference/resources.md) — Generated resource matrix from registry + spec.
- [generated-reference/resources/README.md](generated-reference/resources/README.md) — Per-resource pages (CRUD, facade helpers, examples).
- [generated-reference/api-surfaces.md](generated-reference/api-surfaces.md) — Generated facade and client surface inventory.
- [generated-reference/resource-routes.md](generated-reference/resource-routes.md) — Generated relationship accessor edge table.
- [generated-reference/create-update-payloads.md](generated-reference/create-update-payloads.md) — Generated create/update payload matrix.
- [generated-reference/coverage.json](generated-reference/coverage.json) — Structured generated coverage metadata.

## Analytics

- [estate/README.md](estate/README.md) — Unified estate workflows (`endor-estate`): workspace pull/analyze, risk cardinality, compile graph.

## Guides

- [guides/README.md](guides/README.md) — List of guides.
- [guides/examples.md](guides/examples.md) — Skill walkthrough and minimal API snippets for a first tenant session.
- [guides/facade-helpers.md](guides/facade-helpers.md) — When to use `search_by_*`, relationship accessors, `RouteResult`, wire helpers.
- [guides/query-recipes.md](guides/query-recipes.md) — Query vs facade routing, supported `list_parameters`, and estate join recipes.
- [guides/consumer-ux-list-update.md](guides/consumer-ux-list-update.md) — Filter vs mask vs update_mask; flat kwargs; SDK consumer UX.
- [guides/retrieving-scan-results.md](guides/retrieving-scan-results.md) — Project → ScanResult → Finding; traverse and field-mask.

## Shipped agent contracts (wheel)

Normative shards for agents and skills (also under `agent-knowledge/contracts/` in this repo):

- [resource-discovery.md](../agent-knowledge/contracts/resource-discovery.md) — `search_by_*` identity lane and disambiguation.
- [list-parameters.md](../agent-knowledge/contracts/list-parameters.md) — Filter, mask, pagination, traverse.
- [dependency-metadata.md](../agent-knowledge/contracts/dependency-metadata.md) — Tenant wire path vs OSS catalog plane.
- [errors-and-auth.md](../agent-knowledge/contracts/errors-and-auth.md) — Exceptions and auth modes.
- [canonical-naming.md](../agent-knowledge/contracts/canonical-naming.md) — Namespace and facade naming.

## Contributing

- [contributing/README.md](contributing/README.md) — Process and checklists for extending the generated SDK surface.
- [contributing/release-publishing.md](contributing/release-publishing.md) — Version tags, hatch-vcs, OIDC PyPI/TestPyPI release CI.
- [changelog.md](changelog.md) — User-facing **Added**, **Changed**, and **Breaking** per release (including estate CLI/layout upgrades).
- [contributing/integration-resource-tests.md](contributing/integration-resource-tests.md)
- [contributing/api-validation.md](contributing/api-validation.md)
- [contributing/troubleshooting.md](contributing/troubleshooting.md)
- [contributing/docs-drift-workflow.md](contributing/docs-drift-workflow.md)
- [contributing/namespace-traversal.md](contributing/namespace-traversal.md) — Traverse and list parameters; patterns and examples.
- [contributing/architecture.md](contributing/architecture.md) — SDK layers, registry, facade; Query / estate composition.
- [contributing/list-query-performance.md](contributing/list-query-performance.md) — List scope, filters, pagination, debugging slow queries.

## When to update docs

API or endpoint behavior changes → [contracts.md](contracts.md) and [generated-reference/resources.md](generated-reference/resources.md). User-visible breaks or notable features → [changelog.md](changelog.md) (**Unreleased**). New resources or operations → reference index and [contributing/](contributing/) checklists. Drift and model consistency → [contributing/docs-drift-workflow.md](contributing/docs-drift-workflow.md). **Internal:** utils (model_validation, optional `utils.schema_drift` probes, traversal), operations — not in top-level `__all__`. **Skills:** authored in `agent-knowledge/skills/`, shipped via `src/endorlabs/agent_knowledge/`, materialized to `.endorlabs-context/sdk/skills/` — see [contributing/repository-layout.md](contributing/repository-layout.md). Ephemeral session notes belong under `.endorlabs-context/workspace/runs/scratch/` — not tracked in `docs/`.

## Generated reference docs

Regenerate from repo root:

```bash
uv run python devtools/model_sync.py --generate-stubs --generate-reference-docs
uv run python devtools/generate_route_contract.py
```

CI validates ship artifacts via `devtools/verify_ship_artifacts.py` (registry, route contract, reference docs, agent knowledge).
