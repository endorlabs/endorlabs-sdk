---
name: endor-analytics-estate-dependencies
description: 'Estate-scale DependencyMetadata aggregates: version cardinality by package
  name, optional single-package filtered export, and intra-minor CVE remediation comparisons.
  Use for estate-wide dependency diversity reporting, how many versions of a package
  are in use, or upgrade-path planning for a CVE on one coordinate.'
---

# Analytics — Estate Dependency Aggregates

Playbook for tenant-wide dependency usage reporting via grouped
`DependencyMetadata` queries.

## Prerequisites

- Auth via `ENDOR_*` env vars (see README / AGENTS.md bootstrap).
- Estate root namespace (for example `tenant`, `tenant.child`).
- `DependencyMetadata` is **tenant-scoped** for list/group API paths (customer
  namespace segment, not literal `oss`). Row fields such as
  `spec.dependency_data.namespace` may still read `oss` for catalog coordinates.

## Metric — version cardinality

For a qualified `spec.dependency_data.package_name`:

**version_cardinality** = count of distinct `spec.dependency_data.resolved_version`
values in use across the estate.

Rollup CSV columns: `package_name`, `version_cardinality`, `dependency_usage_rows`.
Detail CSV (optional): `project_uuid`, `package_name`, `package_version`,
`usage_count`.

## Query modes

| Goal | API / CLI | Notes |
|------|-----------|-------|
| All packages, full estate | `export_version_cardinality` / default CLI | Importer `PackageVersion` shards; slow on large estates |
| One package family | `--package-name-match` (+ optional `--exact-package-name`) | Per-namespace grouped list with name filter; minutes vs hours |
| CVE upgrade-path delta | `--remediation-cve CVE-…` + usage rows | Intra-minor flatten vs as-is; see [REMEDIATION.md](REMEDIATION.md) |

### Full estate (all packages)

```bash
uv run --env-file .env python -m endorlabs.workflows.analytics \
  -n <estate_root> \
  -o .endorlabs-context/workspace/sessions/agent/analytics/version-cardinality.csv \
  --usage-detail-output .endorlabs-context/workspace/sessions/agent/analytics/usage-by-project.csv \
  --max-project-workers 16
```

### Single package (example)

```bash
uv run --env-file .env python -m endorlabs.workflows.analytics \
  -n <estate_root> \
  -o .endorlabs-context/workspace/sessions/agent/analytics/jackson-cardinality.csv \
  --usage-detail-output .endorlabs-context/workspace/sessions/agent/analytics/jackson-usage.csv \
  --package-name-match jackson-databind \
  --exact-package-name "mvn://com.fasterxml.jackson.core:jackson-databind"
```

### CVE remediation comparison

```bash
uv run --env-file .env python -m endorlabs.workflows.analytics \
  -n <estate_root> \
  -o .endorlabs-context/workspace/sessions/agent/analytics/jackson-cardinality.csv \
  --package-name-match jackson-databind \
  --exact-package-name "mvn://com.fasterxml.jackson.core:jackson-databind" \
  --remediation-cve CVE-2018-19362 \
  --remediation-output .endorlabs-context/workspace/sessions/agent/analytics/jackson-remediation.json
```

Programmatic:

```python
from endorlabs.workflows.analytics import (
    analyze_intra_minor_remediation,
    export_version_cardinality_for_package_match,
)
```

## Namespace discovery

1. `Namespace.list(traverse=True)` under estate root → canonical paths
   (`spec.full_name`).
2. Omit estate root from counting when child namespaces exist (avoid double-count).
3. Never use estate-wide `DependencyMetadata` traverse for aggregates.

## Related skills

- **endor-dependency-finding-provenance** — project/commit finding and DM lineage for
  “is this CVE fixed here?” (tenant namespace for `DependencyMetadata` list/get).
- **endor-dependency-provenance** — manifest path and direct vs transitive introduction.
- **endor-retrieve-scan-results** — traverse patterns for discovery-only namespace walks.

## Pitfalls

- Unscoped grouped `DependencyMetadata` per namespace on large tenants (timeouts).
- Confusing importer `PackageVersion` inventory with transitive dependency
  version cardinality (different questions).
- Using literal `oss` wire namespace for `DependencyMetadata` list/group (wrong
  plane; use customer namespace).

## Reference

- [REMEDIATION.md](REMEDIATION.md) — flatten semantics and supported CVE policies
- CLI: `endor-analytics-export-deps` (`endorlabs.workflows.analytics.cli`)
