---
id: endor-output-shape-routing
tags: [query, list, estate, performance]
summary: >-
  Classify OutputShape and discover topology before estate-scale list or pull;
  prefer validated Query graph joins; use list sharding for full row export.
---

# Output shape routing

Before any **multi-project** or **tenant-wide** fetch:

1. **`discover_topology(client, namespace)`** — bounded project geometry
2. **`recommend(OutputShape, topology=...)`** — Query vs facade plan (non-executing)
3. **`validate_sample(..., recipe="pv"|"findings"|"dm")`** — parity gate for **count** recipes

## Validated count joins → Query recipes

| OutputShape | Recipe |
| ----------- | ------ |
| `COUNT_BY_PROJECT` | `client.Query.Project.count_pv` |
| `FINDING_CATEGORY_COUNTS` | `client.Query.Project.count_findings_by_category` |
| DM importer totals | `client.Query.Project.count_dm` |

Use **`fetch_online_dashboard_counts`** for estate HTML tiles without pulling finding rows.

## Custom graph joins (probe first)

| Pattern | Query shape | Workflow probe |
| ------- | ----------- | -------------- |
| PRF ecosystem totals | Project → Finding **count** refs × ecosystem | `.tmp/query_workflow_probes` `prf-counts` |
| Masked findings per project | Project → Finding **list** ref | `finding-list-join` |
| Nested RV + Metric | Project → RepositoryVersion → Metric **lists** | `nested-list` |

See `.tmp/query_workflow_map.md` for join fields and filters.

## Facade + sharding (default until probed)

| OutputShape | Path |
| ----------- | ---- |
| `FINDING_ROWS` | `Finding.list_by_project` / `list_for_shards` |
| `FINDING_LOG_TRENDS` | `FindingLog.list_groups` + `group_by_time` (Query `group_by_time` experimental) |
| `DM_VERSION_CARDINALITY` | `DependencyMetadata.list_groups` per leaf namespace |
| Bulk IR / graph | `endor-estate pull` (explicit opt-in) |

**`TopologySnapshot.project_shards()`** is the canonical list-plane shard source after `discover_topology` or `client.Query.Project.discover`.

## Related

- Contract [query-vs-list-semantics](../contracts/query-vs-list-semantics.md)
- Skill [endor-route-estate-queries](../skills/endor-route-estate-queries/SKILL.md)
- Rule [endor-list-query-performance](endor-list-query-performance.md)
