# Endor Labs SDK Documentation

Index for SDK-specific documentation.

## Doc taxonomy

- [contracts.md](contracts.md) — Normative SDK behavior agreements (`MUST/SHALL` semantics).
- [design.md](design.md) — Design rationale and tradeoffs (non-normative).
- [reference/README.md](reference/README.md) — Curated reference index and stable landing pages.

## Reference

- [reference/README.md](reference/README.md) — List of reference docs.
- [reference/resources.md](reference/resources.md) — Landing page to canonical generated resources matrix.
- [reference/namespace.md](reference/namespace.md) — Namespace in the SDK (list/get/create/update/delete).
- [reference/api-surfaces.md](reference/api-surfaces.md) — Landing page to canonical generated API surfaces.
- [reference/create-update-payloads.md](reference/create-update-payloads.md) — Landing page to canonical generated payload matrix.
- [generated-reference/resources.md](generated-reference/resources.md) — Generated resource matrix from registry + spec.
- [generated-reference/resources/README.md](generated-reference/resources/README.md) — Per-resource pages (create convenience kwargs, ops, examples).
- [generated-reference/api-surfaces.md](generated-reference/api-surfaces.md) — Generated facade and client surface inventory.
- [generated-reference/create-update-payloads.md](generated-reference/create-update-payloads.md) — Generated create/update payload matrix.
- [generated-reference/coverage.json](generated-reference/coverage.json) — Structured generated coverage metadata.

## Analytics

- [estate/README.md](estate/README.md) — Unified estate workflows (`endor-estate`): session layers, risk cardinality, compile graph.

## Guides

- [guides/README.md](guides/README.md) — List of guides.
- [guides/examples.md](guides/examples.md) — Skill walkthrough and minimal API snippets for a first tenant session.
- [guides/consumer-ux-list-update.md](guides/consumer-ux-list-update.md) — Filter vs mask vs update_mask; flat kwargs; SDK consumer UX.
- [guides/retrieving-scan-results.md](guides/retrieving-scan-results.md) — Project → ScanResult → Finding; traverse and field-mask.

## Contributing

- [contributing/README.md](contributing/README.md) — Process and checklists for extending the generated SDK surface.
- [contributing/integration-resource-tests.md](contributing/integration-resource-tests.md)
- [contributing/api-validation.md](contributing/api-validation.md)
- [contributing/troubleshooting.md](contributing/troubleshooting.md)
- [contributing/docs-drift-workflow.md](contributing/docs-drift-workflow.md)
- [contributing/namespace-traversal.md](contributing/namespace-traversal.md) — Traverse and list parameters; patterns and examples.
- [contributing/list-query-performance.md](contributing/list-query-performance.md) — List scope, filters, pagination, debugging slow queries.

## Findings / Research

- [findings-pr-review-comment-matrix.md](findings-pr-review-comment-matrix.md) — Endor Finding fields vs GitHub pull request review comment payloads (CI script crosswalk).
- [findings/integration-test-pagination-research.md](findings/integration-test-pagination-research.md) — Research on test pagination configuration and conftest constants.

## When to update docs

API or endpoint behavior changes -> [contracts.md](contracts.md) and [generated-reference/resources.md](generated-reference/resources.md). New resources or operations -> reference index and [contributing/](contributing/) checklists. Drift and model consistency -> [contributing/docs-drift-workflow.md](contributing/docs-drift-workflow.md). **Internal:** utils (model_validation, schema_drift, traversal), operations — not in top-level `__all__`. **Skills:** authored in `agent-knowledge/skills/`, shipped via `src/endorlabs/agent_knowledge/`, materialized to `.endorlabs-context/sdk/skills/` — see [AGENTS.md](../AGENTS.md#repository-layout).

## Generated reference docs

The files in `docs/generated-reference/` are generated from SDK and spec sources of truth:

- `uv run python devtools/generate_client_stub.py`
- `uv run python devtools/generate_reference_docs.py`

CI validates both generated surfaces and fails if they are out of date.
