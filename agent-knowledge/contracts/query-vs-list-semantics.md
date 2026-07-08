---
id: query-vs-list-semantics
tags: [query, list, count, performance]
---

# Query vs list semantics

When to use **`Query.create`** graph joins vs facade **`count()`** / **`list()`** / **`list_groups`**.

## What Query is

The platform **Query service** (`client.Query.create`) is **kind-agnostic**: any root **Resource Kind** string plus optional **nested references** in one HTTP call. Each node accepts the same **`list_parameters`** as facade list: `filter`, `mask`, `traverse`, `count`, `group`, `group_by_time`, pagination, etc.

**`client.Query.Project.*`** is one **validated recipe family** for estate dashboard patterns (per-project counts and masked finding joins). It is not the full Query API.

- **Generic joins:** `QuerySpec` + `client.Query.execute` / `at_namespace` / `create(payload=...)`
- **Estate recipes:** `client.Query.Project.count_*`, `collect_*`, `discover`, `validate_sample`

Related **Query\*** resources (not `Query.create`): `QueryVulnerability`, `QueryMalware` (oss), `VectorStoreQuery`, `QuerySimilarPackages`.

## Namespace-scoped roots (non-Project)

When the ask has **no per-project grain**, POST at the target wire namespace with an arbitrary root kind:

| Ask | Query path | Facade equivalent | Comparable? |
| --- | ---------- | ----------------- | ----------- |
| Count/filter at one namespace (e.g. `AgentHookEvent`) | `Query.at_namespace(QuerySpec.root("AgentHookEvent").list_parameters(count=True, filter=…), namespace=…)` | `AgentHookEvent.count(filter=…)` at same namespace | **Probe** — same `list_parameters` |
| Tenant-wide finding total (no per-project breakdown) | `Query.at_namespace(QuerySpec.root("Finding").list_parameters(count=True, filter=…), namespace=leaf)` | `Finding.count(traverse=True)` | **Probe** — namespace + traverse semantics |
| FindingLog time buckets | Root `FindingLog` + `group_by_time` | `FindingLog.list_groups` + `group_by_time` | **Probe** |

Use `QueryScope(namespace=ns, keys=())` — empty `keys` skips UUID batching. `QuerySpec.root_has_uuid_keys()` is **Project only** today.

## Project-root estate joins (parity table)

Validated dashboard patterns; compare to facade on a sample before estate scale.

| Ask | Query path | Facade equivalent | Comparable? |
| --- | ---------- | ----------------- | ----------- |
| PV count per project | `client.Query.Project.count_pv` | `PackageVersion.count` per project | **Yes** — must match on sample |
| DM count per project | `client.Query.Project.count_dm` | `DependencyMetadata.count` per importer project | **Yes** — `recipe="dm"` |
| Finding counts by category | `client.Query.Project.count_findings_by_category` | `Finding.count` × categories | **Yes** — MALWARE may diverge |
| Vuln counts by severity | `client.Query.Project.count_findings_by_severity` | `Finding.count` × levels | **Yes** — validate on sample |
| Masked finding rows per project | `client.Query.Project.collect_*` | `Finding.list_by_project` | **Probe** — join + mask; paginate |
| PRF ecosystem totals | `client.Query.Project.count_prf_by_ecosystem` | `Finding.count` or list + aggregate | **Probe** — validate on sample |
| Latest scan metadata per project | Project → `ScanResult` list ref (probe) | `ScanResult.list_by_project(limit=1)` × N | **Probe** — `scan-latest-join` |
| Nested masked lists (RV, Metric, …) | Custom nested `query_spec` | Multiple `list` calls | **Platform doc** — not a count |
| DM version buckets | Root `DependencyMetadata` + `group` (experimental) | `DependencyMetadata.list_groups` | **Probe** — differs from per-project DM count |
| OSS coordinate lookup | `QueryVulnerability` / `QueryMalware` | — | **Query\*** only (oss scope) |

## Namespace invariant

`Query.create` POST URL must be the resource's **wire namespace** (`tenant_meta.namespace`), not tenant root alone when data lives in children. Wrong namespace can return **count=0 with no error**. The SDK executor groups by wire namespace automatically.

## Validation before scale

Run `endorlabs.query.validate_sample(client, projects, recipe="pv"|"findings"|"dm")` on 5–10 projects before estate-wide **Project-root count** recipes. For custom joins, compare a small sample to the facade path you are replacing.

## Classify before estate-scale fetch

1. `discover_topology(client, namespace)` — project geometry (when per-project grain needed)
2. `recommend(OutputShape, topology=...)` — non-executing plan (recipes vs facade vs probe)
3. **Validated Project-root count joins** → `client.Query.Project.*`
4. **Namespace-scoped analytics** → `Query.at_namespace` + `QuerySpec.root(any_kind)`
5. **Custom graph joins** → `QuerySpec` / `QueryExecutor` after probe parity
6. **Row materialization** → `list_by_project` / `list_for_shards` when export/checkpoint needs full pagination
7. **Shard key** — `TopologySnapshot.project_shards()` for list-plane parallel lists; `query_scopes()` for Query POST units

Canonical MQL: **`endorlabs.filters`**. Online estate dashboard: **`fetch_online_dashboard_counts`** → `ir/online_dashboard_counts.json`.

## Related

- [list-parameters.md](list-parameters.md) — filter/mask/pagination
- [resource-discovery.md](resource-discovery.md) — resolve `Project` first
- [docs/guides/query-recipes.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/guides/query-recipes.md) — counterexamples by resource
- Maintainer probes: `.tmp/query_workflow_map.md`
