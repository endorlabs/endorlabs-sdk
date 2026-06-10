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
- [generated-reference/resources/README.md](generated-reference/resources/README.md) — Per-resource pages (create convenience kwargs, ops, examples).
- [generated-reference/api-surfaces.md](generated-reference/api-surfaces.md) — Generated facade and client surface inventory.
- [generated-reference/create-update-payloads.md](generated-reference/create-update-payloads.md) — Generated create/update payload matrix.
- [generated-reference/coverage.json](generated-reference/coverage.json) — Structured generated coverage metadata.

## Analytics

- [estate/README.md](estate/README.md) — Unified estate workflows (`endor-estate`): workspace pull/analyze, risk cardinality, compile graph.

## Guides

- [guides/README.md](guides/README.md) — List of guides.
- [guides/examples.md](guides/examples.md) — Skill walkthrough and minimal API snippets for a first tenant session.
- [guides/consumer-ux-list-update.md](guides/consumer-ux-list-update.md) — Filter vs mask vs update_mask; flat kwargs; SDK consumer UX.
- [guides/retrieving-scan-results.md](guides/retrieving-scan-results.md) — Project → ScanResult → Finding; traverse and field-mask.

## Contributing

- [contributing/README.md](contributing/README.md) — Process and checklists for extending the generated SDK surface.
- [contributing/release-publishing.md](contributing/release-publishing.md) — Version tags, hatch-vcs, OIDC PyPI/TestPyPI release CI.
- [changelog.md](changelog.md) — User-facing **Added**, **Changed**, and **Breaking** per release (including estate CLI/layout upgrades).
- [contributing/pr-review-comments.md](contributing/pr-review-comments.md) — Endor findings → GitHub PR review comments in CI.
- [contributing/pr-review-comment-matrix.md](contributing/pr-review-comment-matrix.md) — Finding fields vs GitHub review comment payloads.
- [contributing/integration-resource-tests.md](contributing/integration-resource-tests.md)
- [contributing/api-validation.md](contributing/api-validation.md)
- [contributing/troubleshooting.md](contributing/troubleshooting.md)
- [contributing/docs-drift-workflow.md](contributing/docs-drift-workflow.md)
- [contributing/namespace-traversal.md](contributing/namespace-traversal.md) — Traverse and list parameters; patterns and examples.
- [contributing/list-query-performance.md](contributing/list-query-performance.md) — List scope, filters, pagination, debugging slow queries.

## When to update docs

API or endpoint behavior changes -> [contracts.md](contracts.md) and [generated-reference/resources.md](generated-reference/resources.md). User-visible breaks or notable features -> [changelog.md](changelog.md) (**Unreleased**). New resources or operations -> reference index and [contributing/](contributing/) checklists. Drift and model consistency -> [contributing/docs-drift-workflow.md](contributing/docs-drift-workflow.md). **Internal:** utils (model_validation, schema_drift, traversal), operations — not in top-level `__all__`. **Skills:** authored in `agent-knowledge/skills/`, shipped via `src/endorlabs/agent_knowledge/`, materialized to `.endorlabs-context/sdk/skills/` — see [contributing/repository-layout.md](contributing/repository-layout.md). Ephemeral session notes belong under `.endorlabs-context/workspace/sessions/<user>/notes/` — not tracked in `docs/`.

## Generated reference docs

The files in `docs/generated-reference/` are generated from SDK and spec sources of truth:

- `uv run python devtools/generate_client_stub.py`
- `uv run python devtools/generate_reference_docs.py`

CI validates both generated surfaces and fails if they are out of date.
