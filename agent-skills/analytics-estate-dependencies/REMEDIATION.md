# Remediation comparison (intra-minor flatten)

Optional second phase after exporting **usage-by-version** rows
(`package_name`, `package_version`, `usage_count`).

## Intra-minor flatten

Within each **minor line** (for example all `2.15.x`), collapse consumers to the
**latest in-use patch** among versions present in the export. Dependency instance
counts are preserved (summed); version cardinality drops.

Models the operational step: “standardize patch levels within a minor before
cross-minor upgrades.”

## CVE comparison outputs

`analyze_intra_minor_remediation(usage_rows, cve_id=…)` returns two phases:

| Phase | Meaning |
|-------|---------|
| **as_is** | Metrics from raw `resolved_version` rows |
| **flattened** | Metrics after intra-minor collapse |

Each phase reports:

- `version_cardinality`
- `dependency_instances`
- `vulnerable_distinct_versions` / `vulnerable_instances` (for the CVE policy)
- `upgrade_paths_to_fix` — distinct `(from_version → fix_target)` pairs
- `already_patched_*` — rows not requiring action for this CVE

## Supported CVE policies

Built-in fix-floor maps (extend in `remediation.py`):

| CVE | Notes |
|-----|-------|
| `CVE-2018-19362` | Jackson databind micro-patches: 2.6.7.3, 2.7.9.5, 2.8.11.3, 2.9.8+ |

Arbitrary CVE ids require adding a policy adapter (OSV ranges or Endor vuln metadata).

## Interpreting deltas

- **version_cardinality** delta — operational diversity reduction from flattening.
- **upgrade_paths_to_fix** delta — remediation program size for the specific CVE.
- **vulnerable_instances** may drop after flatten when the latest in-use patch on
  a minor line is already CVE-fixed.

Flattening does **not** change total dependency instance counts.
