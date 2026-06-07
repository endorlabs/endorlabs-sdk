---
name: endor-dependency-provenance
description: Resolve package-version lineage by manifest path and source ref/sha,
  and distinguish direct vs transitive introduction paths. Use when the same package
  appears at multiple versions or via multiple manifest files.
---

# Dependency Provenance

Use this playbook when a package appears in multiple versions and you need exact
introduction paths.

## Inputs

- Tenant namespace
- Project UUID or repo URL
- Package name or coordinate family (for example `azure-core`)
- Optional branch/ref and commit SHA scope

## Core Rule (required)

Do not collapse by package name alone.

Use this grouping key before any rollup:

`(target_dependency_package_name, dependency_file_path, source_code_version.ref|sha)`

This keeps separate introduction paths distinct across manifest files and refs.

## Workflow

1. Pull findings for the project/package scope.
2. Record exact coordinate (`spec.target_dependency_package_name`) and
   `spec.dependency_file_paths`.
3. Split rows by manifest path and ref/sha.
4. Identify parent introduction package when available (for example from
   finding summary text or dependency metadata).
5. Classify each path as direct or transitive and emit one row per path.
6. Report unresolved ambiguity explicitly (for example missing parent edge).

## Output Shape

Return a matrix with one row per introduction path:

- package coordinate
- dependency file path
- source ref/sha
- direct vs transitive
- parent package/version (if known)
- evidence resource IDs (finding UUID, target UUID)

## Common Pitfalls

- Grouping by package family (`azure-core`) instead of full coordinate.
- Merging paths from `requirements.txt`, `pyproject.toml`, and `uv.lock`.
- Treating same package across different refs as one lineage.
- Reporting one "introduced by" answer when multiple manifest paths exist.

## Related skills

| Need | Skill |
| ---- | ----- |
| Finding rows, scan UUIDs, project resolution | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) |
| Vuln fixed vs present at ref/sha | [endor-dependency-finding-provenance](../endor-dependency-finding-provenance/SKILL.md) |
| Scan pipeline failure (deps never resolved) | [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) |
