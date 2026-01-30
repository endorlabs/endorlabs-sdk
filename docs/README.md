# Endor Cockpit SDK Documentation

Index for SDK-only documentation. Non-SDK content (user docs, KB, internal wiki) has been moved to `.tmp/docs-revamp/` by classification; see `.tmp/docs-revamp/README.md`.

## Conventions

- [conventions.md](conventions.md) — Canonical naming, traverse, ListParameters, OpenAPI path, error handling (single source of truth).

## Reference

- [reference/README.md](reference/README.md) — List of reference docs and link to OpenAPI spec.
- [reference/resources.md](reference/resources.md) — Resource name, operations, limitations, links.
- [reference/namespace.md](reference/namespace.md) — Namespace in the SDK (list/get/create/update/delete).

## Guides

- [guides/README.md](guides/README.md) — List of guides.
- [guides/retrieving-scan-results.md](guides/retrieving-scan-results.md) — Project → ScanResult → Finding; traverse and field-mask.
- [guides/namespace-traversal.md](guides/namespace-traversal.md) — ListParameters(traverse=True) with list_*.
- [guides/rego-policies.md](guides/rego-policies.md) — How the SDK is used with policies; link to official Rego docs.

## Rules of Engagement

- [rules-of-engagement/README.md](rules-of-engagement/README.md) — Who uses RoE; list of RoE docs.
- [rules-of-engagement/resource-implementation.md](rules-of-engagement/resource-implementation.md)
- [rules-of-engagement/api-validation.md](rules-of-engagement/api-validation.md)
- [rules-of-engagement/troubleshooting.md](rules-of-engagement/troubleshooting.md)
- [rules-of-engagement/docs-drift-workflow.md](rules-of-engagement/docs-drift-workflow.md)

## Maintenance

- [maintenance.md](maintenance.md) — When to update docs; link to docs-drift-workflow and conventions. `.tmp/docs-revamp/` holds exported non-SDK content (not versioned in repo).
