# Relationships workflows

First-party **estate compile-dependency graph** pipeline, optional **collect-strategy benchmark**, **session summary**, and a separate **transitive relationship map**.

## First-party analysis workflow

| Step | Console script | Role |
|------|----------------|------|
| 1. Build graph | `endor-compile-dependency-graph` | Phased API fetch + local enrich/analytics/partition |
| 2. Summarize session | `endor-graph-summarize` | Read session artifacts; hubs, isolation, communities, validation |
| 3. (Optional) Benchmark collect | `endor-collect-strategy-spike` | Compare per-project vs namespace DM strategies before changing defaults |
| 4. (Optional) Transitive map | `python -m endorlabs.workflows.relationships.map` | Single-namespace project paths (different semantics) |

Equivalent module invocations:

```bash
uv run --env-file .env endor-compile-dependency-graph \
  --tenant "<auth_tenant>" --namespace tenant --max-workers 16

uv run endor-graph-summarize --namespace tenant --namespace tenant.other

uv run --env-file .env endor-collect-strategy-spike \
  --tenant "<auth_tenant>" --namespace tenant.child.grandchild --max-pages 1
```

Requires `uv sync --extra graph` for `graph_analytics` and `partition_graph`.

### Artifact paths

| Workflow | Output root |
|----------|-------------|
| `endor-compile-dependency-graph` | `.endorlabs-context/session/<namespace_slug>/` |
| `endor-graph-summarize` | stdout / `--json` (reads session dir) |
| `endor-collect-strategy-spike` | `.endorlabs-context/workspace/sessions/<user>/exports/collect-strategy-spike/` |
| `map.py` | `.endorlabs-context/workspace/projects/` |

Do not write session artifacts to repo-root `.tmp/`. See shipped rule `endor-workspace-layout`.

## `endor-compile-dependency-graph` — compile graph pipeline

**Vertices:** all `Project` registrations (Git URL and binary/component).
**Edges:** direct `DependencyMetadata` rows whose `package_name` resolves to another graph-node publisher (main context).

### Phase chain

```
discover_projects → filter_git_repositories → build_publisher_index → collect_dependencies
→ build_graph → enrich_graph → graph_analytics → partition_graph
```

Re-run downstream phases from disk (`--phase enrich_graph`, etc.) without re-fetching API data.

### Key artifacts

| File | Purpose |
|------|---------|
| `dependency_corpus.jsonl` | Full DM inventory (direct + transitive rows) for package-XYZ / license queries |
| `compile_dependency_graph.json` | v1 direct compile graph |
| `compile_dependency_graph_enriched.json` | v2 graph + tags, scopes, versions, corpus stats |
| `leiden_input.json` | Partition/analytics input derived from enriched graph |
| `graph_metrics.json` | Centrality, WCC/SCC, k-core |
| `graph_partition.json` / `community_summary.json` | Leiden communities + rollups |
| `package_subgraph.json` | Optional single-coordinate subgraph (`--package-name-match`) |

### Progress / preflight counts

Before each expensive list, the pipeline issues a **count** with the same namespace/filter as the full fetch. Logs use `processed/in_scope` denominators (e.g. `DependencyMetadata rows: 12000/118432`).

### Performance tiers

| Tier | Operation | Typical cost |
|------|-----------|--------------|
| Slowest | `collect_dependencies` + `dependency_corpus.jsonl` | Hours (estate-wide) |
| Medium | `discover_projects` + `build_publisher_index` | Minutes–tens of minutes |
| Fastest | `enrich_graph`, `graph_analytics`, `partition_graph` from session | Seconds–minutes (no API) |

Set `--max-pages` and `--dep-metadata-max-pages` to **0** (default) for unlimited lists. Positive caps risk truncation; phase validation flags `*_not_truncated` and `count_matches_list` checks.

### Useful flags

```bash
uv run --env-file .env endor-compile-dependency-graph \
  --tenant "<auth_tenant>" --namespace tenant --phase enrich_graph

uv run --env-file .env endor-compile-dependency-graph \
  --tenant "<auth_tenant>" --namespace tenant \
  --partition-resolution 1.0 --partition-iterations 10 \
  --partition-weight-field consumer_row_count \
  --cardinality-csv path/to/version_cardinality.csv
```

### Collect strategy (reference benchmark)

On one large child namespace (5k+ projects, ~1.1M DM rows, unlimited pages):

| Strategy | Wall time | Parity |
|----------|-----------|--------|
| **S0** per-project + 16 workers | **~6.8× faster** than S1 | Full row + UUID parity |
| **S1** single namespace list | Baseline | Full |

**Default:** keep per-project parallel collect (S0). See [AGENTS.md](../../../AGENTS.md) (sharded parallel lists).

Use `endor-collect-strategy-spike` to reproduce on your namespace before changing collect defaults.

## `endor-graph-summarize` — session readout

Reads `compile_dependency_graph.json`, optional `graph_partition.json`, `graph_metrics.json`, and `publisher_rankings.json`; reports isolation %, top publishers, Leiden community stats, k-core/WCC highlights, and `phase_*_validation` status.

```bash
uv run endor-graph-summarize --namespace tenant --json
```

## `map.py` — single-namespace relationship map

Includes **transitive** project paths (BFS); different semantics from the compile graph. Defaults to `workflow_projects_root()`.

## Cross-skill workflows

| Skill | Use when |
|-------|----------|
| `endor-compile-dependency-graph` | CLI entry + skill summary |
| `endor-map-project-dependency-relationships` | Transitive map in one namespace |
| `endor-analytics-estate-dependencies` | Grouped cardinality CSV → `--cardinality-csv` join |

## Analysis value (quick reference)

| Artifact | Question |
|----------|----------|
| `compile_dependency_graph.json` | Who directly compile-imports whom? |
| `publisher_rankings.json` | Top internal publishers by inbound edges |
| `dependency_corpus.jsonl` | Consumers/versions/paths for package XYZ without re-fetch |
| `graph_metrics.json` | Hubs, cycles (SCC), k-core nucleus |
| `community_summary.json` | Cluster namespaces/tags/anchors for migration scope |
