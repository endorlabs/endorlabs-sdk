---
id: query-vs-list-semantics
tags: [query, list, count, performance]
---

# Query vs list semantics

When to use **`endorlabs.query`** graph joins vs facade **`count()`** / **`list()`** / **`list_groups`**.

## Parity table

| Ask | Query path | Facade equivalent | Comparable? |
| --- | ---------- | ------------------- | ----------- |
| PV count per project | `count_pv_by_project` / `client.Query.count_pv_by_project` | `PackageVersion.count` per project | **Yes** — must match on sample |
| Finding counts by category | `count_findings_by_category` | `Finding.count` × categories | **Yes** — validate; MALWARE may diverge on some layouts |
| Full finding rows | — | `Finding.list_by_project` / `list_for_context` | **No** |
| FindingLog trends | — | `FindingLog.list_groups` + `group_by_time` | **No Query mapping** |
| DM version buckets | — | `DependencyMetadata.list_groups` | **No** — Query gives per-project totals, not version groups |
| OSS coordinate lookup | `QueryVulnerability` / `QueryMalware` | — | **Query\*** only (oss scope) |

## Namespace invariant

`Query.create` POST URL must be each project's **wire namespace** (`tenant_meta.namespace`), not tenant root alone. Wrong namespace can return **count=0 with no error**. The SDK executor groups by wire namespace automatically.

## Validation before scale

Run `endorlabs.query.validate_sample(client, projects, recipe="pv"|"findings")` on 5–10 projects (mix namespace sizes) before estate-wide Query. Compare API call count and bytes, not wall time alone.

## Routing

Use `endorlabs.query.recommend(OutputShape, topology=discover_topology(...))` for a non-executing plan. Skill: [endor-route-estate-queries](../skills/endor-route-estate-queries/SKILL.md).

## Related

- [list-parameters.md](list-parameters.md) — filter/mask/pagination
- [resource-discovery.md](resource-discovery.md) — resolve `Project` first
- [docs/guides/query-recipes.md](../../docs/guides/query-recipes.md)
