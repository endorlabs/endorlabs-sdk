# Documentation Maintenance

When to update docs; link to docs-drift-workflow and [conventions.md](conventions.md). Non-SDK content (user docs, KB, internal wiki) has been moved to `.tmp/docs-revamp/` by classification; that directory is not versioned in the repo (`.tmp` is gitignored).

## SDK surface boundaries

- **Experimental:** `endor_cockpit.analysis` — may change without the same stability guarantees as the rest of the SDK.
- **Internal:** `utils` (model_validation, schema_drift, traversal), `operations` — used by or re-exported from the stable API; not in top-level `__all__`.

## When to Update

- API behavior or endpoints change: update [conventions.md](conventions.md) and [reference/resources.md](reference/resources.md) as needed.
- New resources or operations: update reference and RoE checklists.
- Drift workflow: see [rules-of-engagement/docs-drift-workflow.md](rules-of-engagement/docs-drift-workflow.md) for sync and schema drift.

## Automated Workflows

- **Schema drift**: `.github/workflows/schema-drift-detection.yml` — detects model/API mismatches.
- **Unified**: See [rules-of-engagement/docs-drift-workflow.md](rules-of-engagement/docs-drift-workflow.md) for manual commands and details.
