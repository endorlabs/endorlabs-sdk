---
id: endor-output-shape-routing
tags:
- query
- list
- estate
- performance
summary: Classify OutputShape and discover topology before estate-scale list or pull;
  prefer validated Query graph joins; use list sharding for full row export.
---

# Output shape routing

Before any **multi-project** or **tenant-wide** fetch:

1. **Classify grain** — per-project (estate dashboard) vs namespace-scoped (no Project root)
2. **`discover_topology(client, namespace)`** — when per-project grain is needed
3. **`recommend(OutputShape, topology=...)`** — Query vs facade plan (non-executing)
4. **`validate_sample(..., recipe="pv"|"findings"|"dm")`** — parity gate for **Project-root count** recipes

## Generic graph joins (any root kind)

Query is **kind-agnostic**. Use when the ask does not need per-project breakdown:

- `client.Query.at_namespace(QuerySpec.root("<Kind>").count(...), namespace=…)`
- `client.Query.execute(spec, [QueryScope(namespace=…)], parse=…)`

See [query-recipes.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/guides/query-recipes.md) counterexamples for Finding, ScanResult, PackageVersion, DependencyMetadata.

## Validated Project-root count joins

| OutputShape | Recipe |
| ----------- | ------ |
| `COUNT_BY_PROJECT` | `client.Query.Project.count_pv` |
| `FINDING_CATEGORY_COUNTS` | `client.Query.Project.count_findings_by_category` |
| DM importer totals | `client.Query.Project.count_dm` |

Use **`fetch_online_dashboard_counts`** for estate HTML tiles without pulling finding rows.

## Custom graph joins (validate on sample first)

| Pattern | Query shape |
| ------- | ----------- |
| PRF ecosystem totals | Project → Finding **count** refs × ecosystem |
| Masked findings per project | Project → Finding **list** ref |
| Latest scan metadata per project | Project → ScanResult **list** ref; mask `spec.environment` |
| Nested RV + Metric | Project → RepositoryVersion → Metric **lists** |

## Facade + sharding

| OutputShape | Path |
| ----------- | ---- |
| `FINDING_ROWS` | `Finding.list_by_project` / `list_for_shards` |
| `TENANT_FINDING_TOTALS` | `Query.at_namespace` with `Finding` root count, or facade `count` with bounds — validate on sample |
| `FINDING_LOG_TRENDS` | `FindingLog.list_groups` + `group_by_time` — **not Query** |
| `DM_VERSION_CARDINALITY` | `DependencyMetadata.list_groups` or root Query `group` — **not** `count_dm` |
| Bulk IR / graph | `endor-estate pull` (explicit opt-in) |

**`TopologySnapshot.project_shards()`** is the canonical list-plane shard source after `discover_topology` or `client.Query.Project.discover`.

## Related

- Contract [query-vs-list-semantics](../contracts/query-vs-list-semantics.md)
- Skill [endor-route-estate-queries](../skills/endor-route-estate-queries/SKILL.md)
- Rule [endor-list-query-performance](endor-list-query-performance.md)
