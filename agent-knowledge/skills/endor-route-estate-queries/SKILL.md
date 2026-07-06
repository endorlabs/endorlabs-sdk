---
name: endor-route-estate-queries
description: >-
  Routes estate-scale data pulls between Query graph joins and facade
  list/count/shard patterns after bounded topology discovery. Use when choosing
  how to fetch counts, aggregates, or validated joins across many projects.
  Not for single-project RCA — hand off when full row export is needed without
  a validated Query join.
---

# Route estate queries (Query vs facade)

**Default path:** classify the ask → discover topology → pick shard grain → validate on a sample → scale.

Normative parity: [query-vs-list-semantics contract](../../contracts/query-vs-list-semantics.md). Guide: [docs/guides/query-recipes.md](../../../docs/guides/query-recipes.md).

## Scope

| In scope | Out of scope |
| -------- | ------------ |
| Dashboard **counts** across many projects | Single-project finding RCA |
| Query graph joins vs `count()` / `list_groups` | Unvalidated custom joins at full tenant |
| Topology discovery (bounded `Project.list`) | `endor-estate pull` unless user asks |
| Sample validation before estate-wide Query | Policy validation |

**Handoffs:** [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) (one repo rows) · [endor-project-retrieval-bundle](../endor-project-retrieval-bundle/SKILL.md) (single-project bundle) · [endor-namespace-relationship-map](../endor-namespace-relationship-map/SKILL.md) (consumer graph).

## Step 0 — Classify output

| User wants | `OutputShape` | Primary path |
| ---------- | ------------- | ------------ |
| PV / finding category counts per project | `COUNT_BY_PROJECT` / `FINDING_CATEGORY_COUNTS` | Query recipes after validation |
| DM count per importer project | (dashboard) | `client.Query.Project.count_dm` after `recipe="dm"` validation |
| Online estate dashboard tiles (no pull) | — | `fetch_online_dashboard_counts` → `ir/online_dashboard_counts.json` |
| Finding rows for one scan | `FINDING_ROWS` | `Finding.list_by_project` |
| New vs resolved over time | `FINDING_LOG_TRENDS` | `FindingLog.list_groups` (probe Query `group_by_time`) |
| Package usage by version | `DM_VERSION_CARDINALITY` | `DependencyMetadata.list_groups` |
| OSS CVE/coordinate lookup | `OSS_COORDINATE_LOOKUP` | `QueryVulnerability` / `QueryMalware` |

```python
from endorlabs.query import OutputShape, discover_topology, recommend

topo = discover_topology(client, "<tenant>", traverse=True, max_pages=...)
plan = recommend(OutputShape.COUNT_BY_PROJECT, topology=topo)
shards = topo.project_shards()
# plan.primary, plan.shard_key, plan.validate_recommended, plan.notes
```

## Step 1 — Discover topology

```python
from endorlabs.query import discover_topology

topo = discover_topology(
    client,
    "<tenant>",
    traverse=True,
    max_pages=...,  # bound cost during discovery
)
# topo.archetype: single_repo | monorepo_hub | managed_platform | estate_sprawl | mixed
# topo.namespace_geometry — project counts per leaf namespace
# topo.duplicate_name_groups — disambiguate meta.name
```

Resolve **`Project`** rows first; pass **resource objects** or discovery list into Query recipes.

## Step 2 — Correctness gate (before scale)

```python
from endorlabs.query import validate_sample

sample = topo.projects[:10]  # mix namespace sizes when possible
result = validate_sample(client, sample, recipe="pv", sample_size=5)
assert result.matched, result.to_dict()
dm_result = validate_sample(client, sample, recipe="dm", sample_size=5)
counts = client.Query.Project.count_pv(topo.projects)
dm_counts = client.Query.Project.count_dm(topo.projects)
```

Canonical MQL: **`endorlabs.filters`** (not `workflows/findings/filters`).

Or via facade sugar:

```python
counts = client.Query.Project.count_pv(topo.projects)
```

## Step 3 — Execute

| Archetype | Shard key | Query? |
| --------- | --------- | ------ |
| `single_repo` | project | Optional; `recommend()` may prefer `facade_count` — use `list_by_project` for rows |
| `monorepo_hub` | leaf namespace + pagination | Yes for validated count joins |
| `managed_platform` / `estate_sprawl` | leaf namespace batches | Yes if sample validated |

**Row materialization** (findings/DM JSONL): `topo.project_shards()` → `tools/list_sharding`. **Online-only dashboard:** `endorlabs.workflows.estate.fetch_online_dashboard_counts` (no `endor-estate pull`).

Parallel row materialization: [`tools/list_sharding`](../../../src/endorlabs/tools/list_sharding.py). Query executor supports `max_workers` for namespace fan-out (default sequential).

## Anti-patterns

- POST `Query` at **tenant root** when projects live in child namespaces
- Assume **count** is the only Query output shape without probing list/group joins
- Skip sample validation because Query was faster on another customer
- `traverse=True` on findings after `Project` is already resolved

## Related skills

| Skill | When |
| ----- | ---- |
| [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) | One project findings |
| [endor-list-query-performance](../../rules/endor-list-query-performance.md) | List/count performance |
| [endor-namespace-scoping](../../rules/endor-namespace-scoping.md) | Namespace invariants |
