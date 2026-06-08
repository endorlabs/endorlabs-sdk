# Compile dependency graph

Build a **global compile-dependency graph** for an estate namespace: direct import
edges between project registrations, publisher rankings, optional graph analytics, and
a full `DependencyMetadata` corpus for ad hoc queries.

**Workflow catalog:** `compile-dependency-graph` in shipped `workflows/entries.json`
(`skill: null`, `agent_visible: true`). This is **not** an agent skill — do not start
a full estate collect without explicit operator approval. Prefer reading an existing
session with `endor-graph-summarize` when artifacts are already on disk.

## When to use

| Use this | Not this |
|----------|----------|
| Estate compile topology, internal publisher hubs, isolated nodes | Single-repo remediation bundle → `endor-agent-context` |
| Leiden communities, centrality, k-core on compile graph | Namespace transitive paths → `relationships.map` |
| Package-XYZ consumers/versions via `dependency_corpus.jsonl` | Version cardinality CSV only → `endor-analytics-export-deps` |

**Vertices:** all `Project` registrations — Git URLs (union-normalized) and binary/component
nodes (`registration_type`: `git_repository` | `binary_component`).

**Edges:** direct `DependencyMetadata` rows (`dependency_data.direct == true`) whose
`package_name` resolves to another graph-node publisher via main-context `PackageVersion`.

**Scope:** compile-time imports only. Multi-hop chains (A→B→C) are not materialized;
traverse `compile_dependency_graph.json` on demand.

## Prerequisites

- Credentials in `.env` (see [README.md](../../README.md)).
- `uv sync --extra graph` for `graph_analytics` and `partition_graph` (`igraph`, `leidenalg`).
- Session output: `.endorlabs-context/session/<namespace_slug>/` (gitignored). See shipped
  `endor-workspace-layout` rule.

## CLIs

| Script | Role |
|--------|------|
| `endor-compile-dependency-graph` | Phased API fetch + local enrich/analytics/partition |
| `endor-graph-summarize` | Read session artifacts (no API) |
| `endor-collect-strategy-spike` | Benchmark per-project vs namespace DM collect |

```bash
uv run --env-file .env endor-compile-dependency-graph \
  --tenant "<auth_tenant>" \
  --namespace tenant \
  --max-workers 16
```

Module: `python -m endorlabs.workflows.relationships.dependency_graph`.

`--max-pages` and `--dep-metadata-max-pages` default to **0 (unlimited)**. Positive caps
risk truncation; phase validation flags `*_not_truncated` and `count_matches_list`.

Repeat `--namespace` for multiple estate roots.

### Session summary (no API)

```bash
uv run endor-graph-summarize --namespace tenant --json
```

### Collect strategy benchmark (optional)

```bash
uv run --env-file .env endor-collect-strategy-spike \
  --tenant "<auth_tenant>" \
  --namespace tenant.child.grandchild \
  --max-pages 1
```

## Phase chain

```
discover_projects → filter_git_repositories → build_publisher_index → collect_dependencies
→ build_graph → enrich_graph → graph_analytics → partition_graph
```

Re-run downstream phases from disk (`--phase enrich_graph`, etc.) without re-fetching API data.

| Phase | Artifacts |
|-------|-----------|
| `discover_projects` | `phase_discover_projects.json` |
| `filter_git_repositories` | `phase_filter_git_repositories.json` |
| `build_publisher_index` | `phase_build_publisher_index.json` |
| `collect_dependencies` | `phase_collect_dependencies.json`, `collected_direct_edges.json`, `dependency_corpus.jsonl` |
| `build_graph` | `compile_dependency_graph.json`, `publisher_rankings.json` |
| `enrich_graph` | `compile_dependency_graph_enriched.json`, `leiden_input.json` |
| `graph_analytics` | `graph_metrics.json`, optional `package_subgraph.json` |
| `partition_graph` | `graph_partition.json`, `community_summary.json` |

Phases log **preflight count / in_scope** progress before expensive lists.

## Performance

| Tier | Operation | Typical cost |
|------|-----------|--------------|
| Slowest | `collect_dependencies` + corpus | Hours on large estates (10k+ projects) |
| Medium | `discover_projects` + `build_publisher_index` | Minutes–tens of minutes |
| Fastest | `enrich_graph`, `graph_analytics`, `partition_graph` | Seconds–minutes (local only) |

**Warning:** estate-wide collect is a batch operator job, not an interactive agent task.

## Useful flags

```bash
# Analysis-only rerun (no API lists)
uv run --env-file .env endor-compile-dependency-graph \
  --tenant "<auth_tenant>" --namespace tenant --phase enrich_graph

uv run --env-file .env endor-compile-dependency-graph \
  --tenant "<auth_tenant>" --namespace tenant \
  --partition-resolution 1.0 --partition-iterations 10 \
  --partition-weight-field consumer_row_count \
  --cardinality-csv path/to/version_cardinality.csv

uv run --env-file .env endor-compile-dependency-graph \
  --tenant "<auth_tenant>" --namespace tenant \
  --phase graph_analytics --package-name-match "pypi://requests"
```

| Flag | Purpose |
|------|---------|
| `--phase` | Run one phase or `all` |
| `--max-workers` | Parallel per-project DM collect (default 8) |
| `--retry-fetch-errors` | Re-fetch projects in `collect_fetch_errors.json`; append corpus |
| `--cardinality-csv` | Join version cardinality onto enriched nodes (`enrich_graph`) |
| `--package-name-match` | Emit `package_subgraph.json` (`graph_analytics`) |
| `--partition-*` | Leiden resolution, iterations, weights |

## Primary outputs

| Artifact | Answers |
|----------|---------|
| `compile_dependency_graph.json` | Who directly compile-imports whom? Isolated count? |
| `publisher_rankings.json` | Top internal publishers by inbound compile edges |
| `dependency_corpus.jsonl` | Consumers/versions/paths for package XYZ without re-fetch |
| `compile_dependency_graph_enriched.json` | Tags, namespaces, corpus stats, edge scopes/licenses |
| `graph_metrics.json` | Hubs, WCC/SCC, k-core |
| `community_summary.json` | Namespace/tag cluster rollups |
| `phase_*_validation.json` | Phase checks (`ok` expected for strict completion) |

Optional: `--cardinality-csv` from
[endor-analytics-estate-dependencies](../../agent-knowledge/skills/endor-analytics-estate-dependencies/SKILL.md)
feeds `enrich_graph`.

## Related workflows

- **relationships.map** — namespace project graph with transitive edges; see
  [endor-map-project-dependency-relationships](../../agent-knowledge/skills/endor-map-project-dependency-relationships/SKILL.md).
- **endor-analytics-export-deps** — estate version cardinality CSV.
- **Maintainer runner:** `devtools/run_phased_compile_graph.py` (phased collect with auth preflight).

Deep implementation reference:
[`src/endorlabs/workflows/relationships/README.md`](../../src/endorlabs/workflows/relationships/README.md).

## Agent note

The workflow appears in `workflows/entries.json` so agents can discover CLIs and output
paths, but there is **no** `endor-compile-dependency-graph` skill. Agents should:

1. **Not** launch full `--phase all` on large tenants without explicit user request.
2. Prefer `endor-graph-summarize` and on-disk JSON when a session already exists.
3. Hand off single-repo work to `endor-project-agent-context` and namespace transitive
   graphs to `endor-map-project-dependency-relationships`.
