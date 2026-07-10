# PRF & PV resolution report — reference

Metric and cohort definitions for `endor-potentially-reachable-analysis` scripts.

## Finding filters

### PRF base

```
context.type==CONTEXT_TYPE_MAIN
and spec.finding_categories contains FINDING_CATEGORY_VULNERABILITY
and spec.finding_tags contains FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION
```

### PRD column (subset of PRF)

PRF base **plus**:

```
and spec.finding_tags contains FINDING_TAGS_POTENTIALLY_REACHABLE_DEPENDENCY
```

Counts PRF vulnerabilities that are also tagged as potentially reachable via dependency (PRD).

### Approximation split

On PRF base per ecosystem:

- **Approximated vulns:** `spec.approximation==true`
- **Not approximated vulns:** `spec.approximation==false`

## Summary table columns

| Column | Definition |
|--------|------------|
| PRF vulnerabilities | Count of PRF findings for ecosystem (traverse) |
| PRD vulnerabilities | PRF findings also tagged PRD (summary table); breakdown **PRD vulns** counts all PRD-tagged findings on cohort PVs |
| Approximated / Not approximated | PRF split by `spec.approximation` |
| % approximated vulns | `approximated / PRF × 100` |
| Unique PVs | Distinct PRF-parent PackageVersions resolved in main context for ecosystem |
| PVs with Dep Resolution errors | PRF-parent PVs where `spec.resolution_errors.unresolved` **or** `.resolved` is non-empty |
| % PVs with Dep Resolution errors | Dep error PVs / unique PVs |
| PVs with Call Graph Errors | PRF-parent PVs where `spec.resolution_errors.call_graph` exists (dict) |
| % PVs with Call Graph Errors | Call graph error PVs / unique PVs |

**Total row:** PRF/PRD/approx counts sum across ecosystems. **Unique PVs** in the total row is the **set union** across ecosystems (not a sum).

## Error analysis breakdowns

Per ecosystem, two sections:

### Dependency resolution errors

- **Cohort:** PRF-parent main-context PVs with dep resolution errors (same count as summary **PVs with Dep Resolution errors**).
- **Grouped by:** `error_analysis_best_match.matching_rule` from `resolution_errors.unresolved` or `.resolved` (whichever is present).
- **Row metrics:**
  - **PRF vulns:** sum of PRF finding counts (`meta.parent_uuid`) for PVs in bucket
  - **PRD vulns:** same for PRD-tagged findings
  - **Precomputed reachability PVs:** PVs in bucket with `spec.precomputed_call_graph_state == PRECOMPUTED_STATE_SUCCESS`

### Call graph errors

- **Cohort:** PRF-parent PVs with `spec.resolution_errors.call_graph` present (same count as summary **PVs with Call Graph Errors**).
- **Grouped by:** `error_analysis_best_match.matching_rule` on the call_graph error object.
- **Excludes:** PVs without call graph errors (no “no call graph error” row).
- Same row metrics as dep resolution breakdown.

## Missing parent PVs

PRF findings may reference `meta.parent_uuid` values with no matching main-context PackageVersion (deleted, wrong context, or pagination edge). Count reported as **missing parent PVs**; those UUIDs are excluded from error breakdown denominators.

## PackageVersion fetch

Direct GET by UUID may 404; scripts batch-list:

```
context.type==CONTEXT_TYPE_MAIN and uuid in ["...", "..."]
```

on `v1/namespaces/{tenant}/package-versions` with `traverse=true`.

## API list parameters

Always use prefixed list parameters (not bare `filter`):

- `list_parameters.filter`
- `list_parameters.traverse=true`
- `list_parameters.count=true` (for count-only queries)
- `list_parameters.page_size`
