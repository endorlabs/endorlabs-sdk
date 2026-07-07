---

id: query-vs-list-semantics

tags: [query, list, count, performance]

---



# Query vs list semantics



When to use **`Query.create`** graph joins vs facade **`count()`** / **`list()`** / **`list_groups`**.



## What Query is



The platform **Query service** (`client.Query.create`) retrieves a root **Resource Kind** and optional **nested references** in one HTTP call. Each node (root or reference) accepts the same **`list_parameters`** as facade list: `filter`, `mask`, `traverse`, `count`, `group`, `group_by_time`, pagination, etc.



Shipped SDK helpers in **`endorlabs.query`** are **validated recipes** (mostly **count joins** for dashboard/pre-flight). Custom joins use `QuerySpec` + `QueryExecutor` or `create(payload=...)`.



Related **Query\*** resources (not `Query.create`): `QueryVulnerability`, `QueryMalware` (oss), `VectorStoreQuery`, `QuerySimilarPackages`.



## Parity table



| Ask | Query path | Facade equivalent | Comparable? |

| --- | ---------- | ------------------- | ----------- |

| PV count per project | `client.Query.Project.count_pv` | `PackageVersion.count` per project | **Yes** — must match on sample |

| DM count per project | `client.Query.Project.count_dm` | `DependencyMetadata.count` per importer project | **Yes** — `recipe="dm"` |

| Finding counts by category | `client.Query.Project.count_findings_by_category` | `Finding.count` × categories | **Yes** — MALWARE may diverge |

| Vuln counts by severity | `client.Query.Project.count_findings_by_severity` | `Finding.count` × levels | **Yes** — validate on sample |

| Masked finding rows per project | `client.Query.Project.collect_*` | `Finding.list_by_project` | **Probe** — join + mask; paginate |

| PRF ecosystem totals | `client.Query.Project.count_prf_by_ecosystem` | `Finding.count` or list + aggregate | **Probe** — validate on sample |

| Nested masked lists (RV, Metric, …) | Custom nested `query_spec` | Multiple `list` calls | **Platform doc** — not a count |

| FindingLog weekly buckets | Root `FindingLog` + `group_by_time` (experimental) | `FindingLog.list_groups` + `group_by_time` | **Probe** — not a shipped recipe |

| DM version buckets | Root `DependencyMetadata` + `group` (experimental) | `DependencyMetadata.list_groups` | **Probe** — differs from per-project DM count |

| OSS coordinate lookup | `QueryVulnerability` / `QueryMalware` | — | **Query\*** only (oss scope) |



## Namespace invariant



`Query.create` POST URL must be each project's **wire namespace** (`tenant_meta.namespace`), not tenant root alone. Wrong namespace can return **count=0 with no error**. The SDK executor groups by wire namespace automatically.



## Validation before scale



Run `endorlabs.query.validate_sample(client, projects, recipe="pv"|"findings"|"dm")` on 5–10 projects before estate-wide **count** recipes. For custom joins, compare a small sample to the facade path you are replacing.



## Classify before estate-scale fetch



1. `discover_topology(client, namespace)` — project geometry

2. `recommend(OutputShape, topology=...)` — non-executing plan (recipes vs facade vs probe)

3. **Validated count joins** → `endorlabs.query` recipes

4. **Custom graph joins** → `QuerySpec` / `QueryExecutor` after probe parity

5. **Row materialization** → `list_by_project` / `list_for_shards` when export/checkpoint needs full pagination

6. **Shard key** — `TopologySnapshot.project_shards()` for list-plane parallel lists; `query_scopes()` for Query POST units



Canonical MQL: **`endorlabs.filters`**. Online estate dashboard: **`fetch_online_dashboard_counts`** → `ir/online_dashboard_counts.json`.



## Related



- [list-parameters.md](list-parameters.md) — filter/mask/pagination

- [resource-discovery.md](resource-discovery.md) — resolve `Project` first

- [docs/guides/query-recipes.md](../../docs/guides/query-recipes.md)

- Maintainer probes: `.tmp/query_workflow_map.md`
