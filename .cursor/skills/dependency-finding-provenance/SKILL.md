---
name: dependency-finding-provenance
description: >-
  Trace vulnerability and dependency lineage across Findings, PackageVersions,
  and SBOM artifacts to verify resolved vs present state at branch/commit
  scope. Use for customer asks about "is this fixed", orphaned related-resource
  errors, patched-vs-upstream coordinate confusion, or mismatches between UI
  exports and API data.
---

# Dependency and Finding Provenance

Playbook for customer-facing dependency/finding investigations.

## Inputs

- Tenant namespace (for example `endorlabs`)
- Project identifier (UUID or repo URL)
- Vulnerability identifier(s) (CVE, GHSA)
- Branch/ref and commit SHA of interest
- Optional artifacts: CSV export, SBOM export

## Prerequisites

- Use customer-request framing and output style from `.cursor/rules/customer-requests.mdc`.
- Confirm auth mode before running queries:
  - Prefer `ENDOR_TOKEN` (or `token=...` constructor arg) for token-first customer access; avoid relying on custom auth-mode environment variables.

## Flow B — Finding Provenance

1. Query findings scoped to the project namespace.
2. Filter by CVE/GHSA and dependency package match terms.
3. Group by full `spec.target_dependency_package_name` string (exact coordinate), not substring family.
4. Record:
   - finding UUID
   - `spec.target_dependency_package_name`
   - `spec.target_uuid`
   - `spec.dependency_file_paths`
   - `spec.source_code_version.ref` and `.sha`

## Flow C — Dependency Provenance

1. Pull `PackageVersion` rows for project + branch/ref scope.
2. Inspect `spec.resolved_dependencies` when present:
   - dependency graph nodes
   - component names/versions
3. Pull `DependencyMetadata` with correct scope (commonly `oss`), keyed by:
   - `spec.importer_data.project_uuid`
   - optional `package_version_ref`/`sha`
4. Validate referenced UUIDs from findings (`spec.target_uuid`) and flag non-resolving resources.

## Flow D — Artifact Reconciliation

Compare API truth vs exported artifacts:

- Findings CSV
  - missing commit SHA
  - missing package/dependency UUIDs
  - coordinate coverage gaps
- SBOM export
  - determine format (CycloneDX vs SPDX)
  - reconcile component purl/version with finding coordinate
  - inspect pedigree/ancestor/patch metadata where available

Always separate:

- upstream coordinate (for example `...@9.4.18.v20190429`)
- Endor-patched coordinate (for example `...@9.4.18.v20190429-endor-YYYY-MM-DD`)

## Flow E — Commit-Level Disposition

For the exact commit SHA:

1. Confirm findings exist at SHA in general (sanity check).
2. Re-run with vulnerability/dependency filters at same SHA.
3. Conclude one of:
   - present at SHA
   - not present at SHA
   - inconclusive (data gaps)
4. Include confidence and why.

## Output Template

Use this structure in investigation notes:

```markdown
# Dependency/Finding Provenance Summary

- Tenant/project:
- Branch/commit scope:
- Vulnerability scope:

## High-confidence facts
- ...

## Data quality caveats
- ...

## Resolved vs present at commit
- Status:
- Evidence:
- Confidence:

## Open hypotheses
- ...

## Next verification steps
- ...
```

## Common Pitfalls

- Mixing namespace scope (tenant namespace vs `oss`) for dependency metadata.
- Counting grouped findings by substring instead of exact coordinate.
- Treating findings labels and BOM coordinates as the same without lineage evidence.
- Relying on CSV export alone for commit-level conclusions.
