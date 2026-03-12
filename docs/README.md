# Endor Labs SDK Documentation

Index for SDK-specific documentation.

## Doc taxonomy

- [contracts.md](contracts.md) — Normative SDK behavior agreements (`MUST/SHALL` semantics).
- [design.md](design.md) — Design rationale and tradeoffs (non-normative).
- [reference/README.md](reference/README.md) — Resource inventories and API-facing reference pages.

## Reference

- [reference/README.md](reference/README.md) — List of reference docs.
- [reference/resources.md](reference/resources.md) — Resource name, operations, limitations, links.
- [reference/namespace.md](reference/namespace.md) — Namespace in the SDK (list/get/create/update/delete).
- [reference/api-surfaces.md](reference/api-surfaces.md) — API surface contracts (Developer, Module-level, Raw client).
- [reference/create-update-payloads.md](reference/create-update-payloads.md) — Per-resource create/update payload shapes.

## Guides

- [guides/README.md](guides/README.md) — List of guides.
- [guides/consumer-ux-list-update.md](guides/consumer-ux-list-update.md) — Filter vs mask vs update_mask; flat kwargs; SDK consumer UX.
- [guides/retrieving-scan-results.md](guides/retrieving-scan-results.md) — Project → ScanResult → Finding; traverse and field-mask.

## Rules of Engagement

- [rules-of-engagement/README.md](rules-of-engagement/README.md) — Who uses RoE; list of RoE docs.
- [rules-of-engagement/resource-implementation.md](rules-of-engagement/resource-implementation.md)
- [rules-of-engagement/api-validation.md](rules-of-engagement/api-validation.md)
- [rules-of-engagement/troubleshooting.md](rules-of-engagement/troubleshooting.md)
- [rules-of-engagement/docs-drift-workflow.md](rules-of-engagement/docs-drift-workflow.md)
- [rules-of-engagement/namespace-traversal.md](rules-of-engagement/namespace-traversal.md) — Traverse and list parameters; patterns and examples.
- [rules-of-engagement/spec-first-prototype-branch.md](rules-of-engagement/spec-first-prototype-branch.md)
- [rules-of-engagement/spec-first-stainless-feasibility.md](rules-of-engagement/spec-first-stainless-feasibility.md)
- [rules-of-engagement/spec-first-rd-approval-bundle.md](rules-of-engagement/spec-first-rd-approval-bundle.md)

## Findings / Research

- [findings/integration-test-pagination-research.md](findings/integration-test-pagination-research.md) — Research on test pagination configuration and conftest constants.

## When to update docs

API or endpoint behavior changes -> [contracts.md](contracts.md) and [reference/resources.md](reference/resources.md). New resources or operations -> reference and RoE checklists. Drift and model consistency -> [rules-of-engagement/docs-drift-workflow.md](rules-of-engagement/docs-drift-workflow.md). **Internal:** utils (model_validation, schema_drift, traversal), operations — not in top-level `__all__`. **Skills:** Cursor/Anthropic agent skills under `.cursor/skills/`.

## Generated reference docs

The files in `docs/reference/` are generated from SDK and spec sources of truth:

- `uv run python scripts/generate_client_stub.py`
- `uv run python scripts/generate_reference_docs.py`

CI validates both generated surfaces and fails if they are out of date.
