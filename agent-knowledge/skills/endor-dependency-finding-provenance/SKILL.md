---
name: endor-dependency-finding-provenance
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

- For customer-facing output: separate **scope** (tenant/namespace/project), **evidence**
  (API rows and filters used), and **conclusion**; use placeholders such as
  `<tenant>` / `<namespace>` in portable examples (see
  [portable-examples](../../rules/endor-portable-examples.md)).
- Confirm auth mode before running queries:
  - If both API key/secret and `ENDOR_TOKEN` exist, pass `auth_method="browser-auth"` explicitly for token-first customer access.
- For package-lineage semantics (multi-manifest path separation, direct vs transitive normalization), apply `dependency-provenance` rules.

## Project-scoped namespace (required)

**Do this before Flow B/C.** `Client(tenant=<estate_root>)` with default
`traverse=False` lists **only the estate root path** — not child namespaces
where projects usually live. Filters like `spec.project_uuid` or
`spec.importer_data.project_uuid` do **not** substitute for the correct namespace;
you often get **zero rows with no error**.

1. **Discover** the project (when namespace unknown):
   `Project.search_by_name(query, traverse=True, max_pages=…)` and pick the intended row.
2. **Pin namespace** for all project-scoped lists:
   `namespace=project.namespace` on `Finding`, `ScanResult`, `PackageVersion`,
   and `DependencyMetadata`.
3. **Do not** rely on implicit client namespace for project RCA after step 1.

```python
# Safe pattern (estate-root client is fine once namespace is pinned)
project_ns = project.namespace
client.Finding.list(namespace=project_ns, filter=..., traverse=False)
client.DependencyMetadata.list(
    namespace=project_ns,
    filter=F("spec.importer_data.project_uuid") == project.uuid,
    traverse=False,
)
```

Use `traverse=True` on dependency lists only when **deliberately** searching
tenant-wide (costly). For single-project provenance, always pin
`project.namespace`.

## OSS namespace (OSS-scoped facades vs tenant-scoped DependencyMetadata)

Some resources use the literal top-level namespace **`oss`** on the wire (facade
`scope="oss"`), parallel to customer tenants — for example **`Vulnerability`**
catalog queries. **Do not** derive `<tenant>.oss` or child paths under the
customer root for those facades.

**`DependencyMetadata` list/get/group is tenant-scoped** (customer namespace
segment, same as `Project` / `PackageVersion`). Use the project's
`tenant_meta.namespace` (or an explicit child namespace) for Flow C — **not**
literal `oss`. Row payloads may still set `spec.dependency_data.namespace` to
`"oss"` for catalog coordinates; that is field semantics, not the API path.

Verified pattern (matches `endorlabs.workflows.estate.analyze.project_map.map` and estate analytics
workflows). Requires **`project` resolved first** — see
[Project-scoped namespace](#project-scoped-namespace-required):

```python
client.DependencyMetadata.list(
    namespace=project.namespace,
    traverse=False,
    filter=F("spec.importer_data.project_uuid") == project.uuid,
)
```

## Flow B — Finding Provenance

0. Resolve `Project` and set `project_ns = project.namespace` (see above).
1. Query findings scoped to **`namespace=project_ns`**.
2. Filter by CVE/GHSA and dependency package match terms.
3. Group by full `spec.target_dependency_package_name` string (exact coordinate), not substring family.
4. Record:
   - finding UUID
   - `spec.target_dependency_package_name`
   - `spec.target_uuid`
   - `spec.dependency_file_paths`
   - `spec.source_code_version.ref` and `.sha`

## Flow C — Dependency Provenance

0. Same `project` / `project.namespace` as Flow B.
1. Pull `PackageVersion` rows for project + branch/ref scope (**`namespace=project.namespace`**).
2. Inspect `spec.resolved_dependencies` when present:
   - dependency graph nodes
   - component names/versions
3. Pull `DependencyMetadata` on the **project's tenant namespace** (not literal
   `oss`); match `spec.importer_data.project_uuid` and optional
   `package_version_ref`/`sha`. See
   [OSS namespace vs DependencyMetadata](#oss-namespace-oss-scoped-facades-vs-tenant-scoped-dependencymetadata).
4. Validate referenced UUIDs from findings (`spec.target_uuid`) and flag non-resolving resources.
5. When function-level provenance/reachability is required, hand off to:
   - `uv run endor-reachability-context --tenant <tenant> --namespace <namespace> --finding-uuid <finding_uuid>` (default: `workspace/projects/<finding-uuid>/reachability_context.json`)
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

- **Implicit estate-root namespace** on project-scoped lists (`traverse=False`) —
  silent empty results; always use `namespace=project.namespace` after resolving
  the project (see [Project-scoped namespace](#project-scoped-namespace-required)).
- Wrong namespace for **`DependencyMetadata`** (using literal `oss` instead of
  customer namespace) or for true OSS-scoped facades (see
  [OSS namespace vs DependencyMetadata](#oss-namespace-oss-scoped-facades-vs-tenant-scoped-dependencymetadata)).
- Counting grouped findings by substring instead of exact coordinate.
- Treating findings labels and BOM coordinates as the same without lineage evidence.
- Relying on CSV export alone for commit-level conclusions.

## Related skills

| Need | Skill |
| ---- | ----- |
| List findings, filter by scan UUID | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) |
| Function-level reachability triage | [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md) |
| Scan never completed / aggregate stats collapsed | [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) |
| Exception policy on a finding | [endor-validate-policy](../endor-validate-policy/SKILL.md) |
| Manifest path introduction only | [endor-dependency-provenance](../endor-dependency-provenance/SKILL.md) |
