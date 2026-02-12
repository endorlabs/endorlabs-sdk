# Endor Labs SDK Documentation

Index for SDK-specific documentation. Platform concepts and user docs: [docs.endorlabs.com](https://docs.endorlabs.com/).

## Conventions

- [conventions.md](conventions.md) — Canonical naming, traverse, ListParameters, OpenAPI path, error handling (single source of truth). Consumer UX (list/update): filter vs mask vs update_mask, flat kwargs — List parameters and Update and update_mask sections; full guide: [guides/consumer-ux-list-update.md](guides/consumer-ux-list-update.md).

## Reference

- [reference/README.md](reference/README.md) — List of reference docs and link to OpenAPI spec.
- [reference/resources.md](reference/resources.md) — Resource name, operations, limitations, links.
- [reference/namespace.md](reference/namespace.md) — Namespace in the SDK (list/get/create/update/delete).

## Guides

- [guides/README.md](guides/README.md) — List of guides.
- [guides/consumer-ux-list-update.md](guides/consumer-ux-list-update.md) — Filter vs mask vs update_mask; flat kwargs; spec-driven UX.
- [guides/retrieving-scan-results.md](guides/retrieving-scan-results.md) — Project → ScanResult → Finding; traverse and field-mask.

## Rules of Engagement

- [rules-of-engagement/README.md](rules-of-engagement/README.md) — Who uses RoE; list of RoE docs.
- [rules-of-engagement/resource-implementation.md](rules-of-engagement/resource-implementation.md)
- [rules-of-engagement/api-validation.md](rules-of-engagement/api-validation.md)
- [rules-of-engagement/troubleshooting.md](rules-of-engagement/troubleshooting.md)
- [rules-of-engagement/docs-drift-workflow.md](rules-of-engagement/docs-drift-workflow.md)
- [rules-of-engagement/namespace-traversal.md](rules-of-engagement/namespace-traversal.md) — Traverse and list parameters; patterns and examples.

## When to update docs

API or endpoint changes → [conventions.md](conventions.md) and [reference/resources.md](reference/resources.md). New resources or operations → reference and RoE checklists. Drift and model consistency → [rules-of-engagement/docs-drift-workflow.md](rules-of-engagement/docs-drift-workflow.md). **Internal:** utils (model_validation, schema_drift, traversal), operations — not in top-level `__all__`. **Skills:** Cursor/Anthropic agent skills under `.cursor/skills/`.
