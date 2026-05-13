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
  - If both API key/secret and `ENDOR_TOKEN` exist, pass `auth_method="browser-auth"` explicitly for token-first customer access.
- For package-lineage semantics (multi-manifest path separation, direct vs transitive normalization), apply `dependency-provenance` rules.

## OSS namespace (dependency plane and OSS-scoped facades)

OSS-scoped resources (for example `DependencyMetadata` when stored on the OSS plane, or `Vulnerability` queries against OSS) use the literal top-level namespace **`oss`**, parallel to customer tenants. **Do not** derive `<tenant>.oss`, `<customer>.oss`, or any child namespace under the customer root; the resource facade `scope` (for example `scope="oss"`) controls this plane separately from customer namespace paths.

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
3. Pull `DependencyMetadata` with the correct plane/scope (often OSS); match `spec.importer_data.project_uuid` and optional `package_version_ref`/`sha`. Follow [OSS namespace](#oss-namespace-dependency-plane-and-oss-scoped-facades) above for API paths.
4. Validate referenced UUIDs from findings (`spec.target_uuid`) and flag non-resolving resources.
5. When function-level provenance/reachability is required, hand off to:
   - `uv run endor-reachability-context --tenant <tenant> --namespace <namespace> --finding-uuid <finding_uuid> --output-dir .tmp/reachability`
   - Use generated `reachability_context.json` for cross-plane (`customer` + `oss`) stitching evidence.

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

- Wrong namespace or scope for `DependencyMetadata` / OSS-plane resources (see [OSS namespace](#oss-namespace-dependency-plane-and-oss-scoped-facades)).
- Counting grouped findings by substring instead of exact coordinate.
- Treating findings labels and BOM coordinates as the same without lineage evidence.
- Relying on CSV export alone for commit-level conclusions.
