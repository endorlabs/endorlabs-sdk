---
name: endor-compile-dependency-graph
description: 'Build an estate-wide compile-dependency graph over all project registrations
  (Git repos and binary/component nodes): direct import edges anchored on package_name,
  isolated nodes, publisher rankings, and optional Leiden partition. Multi-hop reachability
  is out of scope — query the built graph in post-processing.'
---

# Compile Dependency Graph

Build a **global compile-dependency graph** for an estate namespace:

- **Vertices:** All `Project` registrations — Git-backed repos (normalized Git URL
  union) and binary/component registrations (`registration_type`:
  `git_repository` | `binary_component`).
- **Edges:** **Direct** `DependencyMetadata` rows (`dependency_data.direct == true`)
  whose `package_name` resolves to another graph-node publisher via main-context
  `PackageVersion`.
- **Edge key:** `(consumer_node, publisher_node, anchor_package_name)`.
- **Isolated:** `in_degree == 0` and `out_degree == 0` on this graph.
- **Scope:** compile-time / build-time imports only (`dependency_scope: compile`).
  Runtime dependencies are out of scope.

## CLI

Primary entrypoint (console script):

```bash
uv run --env-file .env endor-compile-dependency-graph \
  --tenant "<auth_tenant>" \
  --namespace tenant \
  --max-workers 16
```

Module equivalent: `python -m endorlabs.workflows.relationships.dependency_graph`.

`--max-pages` and `--dep-metadata-max-pages` default to **0 (unlimited)**. Set a
positive cap only when you intentionally bound cost; phase validation flags
`project_list_not_truncated`, `package_version_list_not_truncated`, and
`no_dep_metadata_truncation` when a cap is hit.

Repeat `--namespace` for multiple estate roots (e.g. `tenant` and `tenant.other`).

### Session summary (no API)

After a build, read hubs, isolation %, communities, and phase validation:

```bash
uv run endor-graph-summarize --namespace tenant --json
```

### Collect strategy benchmark (optional)

Before changing DM collect defaults on a large namespace:

```bash
uv run --env-file .env endor-collect-strategy-spike \
  --tenant "<auth_tenant>" \
  --namespace tenant.child.grandchild \
  --max-pages 1
```

### Phases

| Phase | Artifact |
|-------|----------|
| `discover_projects` | `phase_discover_projects.json` |
| `filter_git_repositories` | `phase_filter_git_repositories.json` |
| `build_publisher_index` | `phase_build_publisher_index.json` |
| `collect_dependencies` | `phase_collect_dependencies.json`, `collected_direct_edges.json`, `dependency_corpus.jsonl` |
| `build_graph` | `compile_dependency_graph.json`, `publisher_rankings.json` |
| `enrich_graph` | `compile_dependency_graph_enriched.json`, `leiden_input.json` |
| `graph_analytics` | `graph_metrics.json`, optional `package_subgraph.json` |
| `partition_graph` | `graph_partition.json`, `community_summary.json` |

Requires `uv sync --extra graph` for `partition_graph` and `graph_analytics`.

Deep reference: [relationships/README.md](../../../src/endorlabs/workflows/relationships/README.md).

List phases log **preflight count / in_scope** progress before full fetches.

## Primary outputs

- **`compile_dependency_graph.json`** — nodes with `published_packages`,
  `direct_imports`, `imported_by`, `isolated`; edges with `anchor_package_name`.
- **`publisher_rankings.json`** — publishers ranked by inbound direct compile edges.
- **`dependency_corpus.jsonl`** — full DM row corpus for package-XYZ / license queries.
- **`compile_dependency_graph_enriched.json`** — v2 graph with corpus/tags/scopes joined.
- **`graph_metrics.json`** — centrality, SCC, k-core (local rerun, no API).
- **`graph_partition.json`** / **`community_summary.json`** — Leiden communities.

Optional: pass **`--cardinality-csv`** (from [endor-analytics-estate-dependencies](../endor-analytics-estate-dependencies/SKILL.md))
into `enrich_graph` for version-cardinality overlays.

Indirect multi-hop project chains (A→B→C) are **not** materialized at build time.
Traverse `compile_dependency_graph.json` edges on demand when needed.

## Cross-skill boundary

| Skill | When |
|-------|------|
| [endor-map-project-dependency-relationships](../endor-map-project-dependency-relationships/SKILL.md) | Single namespace; all DM rows; includes transitive edges |
| [endor-project-agent-context](../endor-project-agent-context/SKILL.md) | One repository bundle (manifest, PV index, hydration) |
| [endor-analytics-export-deps](../endor-analytics-export-deps/SKILL.md) | Estate DependencyMetadata cardinality aggregates |

Non-Git registrations (e.g. `PLATFORM_SOURCE_BINARY` component explosions like
`binary-dist_*`) are **included** as `binary_component` vertices with
`registration_type` on each node. Classification counts live in
`phase_filter_git_repositories.json` (`registration_counts`,
`binary_component_sample`).

## Node semantics

- **`registration_type`:** `git_repository` (Git URL `meta.name`) or
  `binary_component` (component/binary registration name).
- **`published_packages`:** main-context `PackageVersion` rows aggregated on the node.
- **`direct_imports`:** outgoing compile edges (this node imports another publisher).
- **`imported_by`:** incoming compile edges (other nodes import this publisher).
- **`isolated`:** no direct compile import relationship to any other graph node.

## Ordering

1. Credentials in `.env`; `uv sync --extra graph` if partitioning.
2. Run full pipeline (`--phase all`) or resume from a failed phase.
3. Read `isolated_count` and `publisher_rankings.json` before community analysis.

## Graph analysis (pipeline)

Phases after `build_graph` are **local** — they read session artifacts and do not call the API.
Requires `uv sync --extra graph` (`igraph`, `leidenalg`).

### `enrich_graph`

Joins `compile_dependency_graph.json` with `phase_discover_projects.json` and
`dependency_corpus.jsonl`:

| Addition | Where | Purpose |
| -------- | ----- | ------- |
| v2 schema | `compile_dependency_graph_enriched.json` | `endor.compile_dependency_graph.v2` with corpus/tags/scopes |
| Node tags / namespaces | enriched nodes | Rolled up from discover rows |
| Corpus stats | `corpus_dependency_count`, `corpus_direct_count`, `corpus_oss_dependency_count` | Per-node DM row totals |
| Edge scopes / licenses | enriched edges | `scopes`, `license_spdx_ids`, `resolved_versions`, `consumer_row_count`, `mutual_edge` |
| Version cardinality | nodes (optional) | `version_cardinality_max` when `--cardinality-csv` is passed |
| Leiden input | `leiden_input.json` | Normalized node/edge list for partition phase |

Optional **`--cardinality-csv`**: path to `version_cardinality.csv` from
[endor-analytics-estate-dependencies](../endor-analytics-estate-dependencies/SKILL.md);
joins max version cardinality per published package onto nodes.

### `graph_analytics`

Builds an igraph view from the enriched graph (falls back to v1 flat graph) and writes
**`graph_metrics.json`**:

| Metric | Field | Notes |
| ------ | ----- | ----- |
| In/out degree tops | `centrality.in_degree_top`, `out_degree_top` | Top 50 publishers/consumers |
| PageRank / betweenness | `centrality.pagerank_top`, `betweenness_top` | Skipped when `node_count > --analytics-max-nodes` (default 5000) |
| Weak / strong components | `components.weakly_connected_*`, `strongly_connected_*` | WCC/SCC counts and size histograms |
| Cycles | `scc.has_cycles`, `scc.cyclic_components` | Mutual internal deps surface here |
| k-core | `k_core.max_k`, `k_core.nodes_at_max_k` | Undirected core decomposition |

Optional **`--package-name-match`**: substring match on corpus `package_name`; emits
**`package_subgraph.json`** with consumer project UUIDs, version counts, and induced graph nodes.

### `partition_graph`

Runs **Leiden** community detection on the directed graph (prefers `leiden_input.json` /
enriched graph):

| Flag | Default | Effect |
| ---- | ------- | ------ |
| `--partition-resolution` | `1.0` | Leiden `resolution_parameter` (higher → more communities) |
| `--partition-iterations` | `10` | Leiden `n_iterations` |
| `--partition-weight-field` | `none` | `none` \| `consumer_row_count` (edge) \| `inbound_rank` (vertex) |
| `--partition-component-min-size` | `1` | Skip partition when largest WCC is smaller than N |

Outputs:

- **`graph_partition.json`** — membership map, community node lists, algorithm metadata.
- **`community_summary.json`** — per-community rollups: `node_count`, `edge_count`,
  `dominant_namespaces`, `top_tags`, `top_anchor_packages`, `hub_node_ids`.

### Analysis-only rerun (no API)

When `compile_dependency_graph.json` (and ideally corpus + discover artifacts) already
exist under `.endorlabs-context/session/<slug>/`:

```bash
uv run endor-compile-dependency-graph \
  --tenant "<auth_tenant>" \
  --namespace tenant \
  --phase enrich_graph

uv run endor-compile-dependency-graph \
  --tenant "<auth_tenant>" \
  --namespace tenant \
  --phase graph_analytics \
  --package-name-match "pypi://requests"

uv run endor-compile-dependency-graph \
  --tenant "<auth_tenant>" \
  --namespace tenant \
  --phase partition_graph \
  --partition-resolution 1.2 \
  --partition-weight-field consumer_row_count
```

`--tenant` is still required for CLI wiring but analysis phases do not list from the API.

### Artifact interpretation

| Artifact | Answers |
| -------- | ------- |
| `compile_dependency_graph.json` | How many repos/components, edges, isolated nodes? Who publishes/consumes whom? |
| `publisher_rankings.json` | Which internal publishers have the most inbound compile imports? |
| `compile_dependency_graph_enriched.json` | Tags, namespaces, corpus stats, edge scopes/licenses for filtering |
| `graph_metrics.json` | Hubs (degree), bottlenecks (betweenness), fragmentation (WCC), cycles (SCC), dense core (k-core) |
| `community_summary.json` | Which namespace/tag clusters form natural estate groupings? |
| `graph_partition.json` | Raw Leiden membership for custom downstream joins |
| `package_subgraph.json` | Who depends on package X and at which resolved versions? |
| `phase_*_validation.json` | Did truncation or prior-phase checks pass? (`ok: true` expected) |
