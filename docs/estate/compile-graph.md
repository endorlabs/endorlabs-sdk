# Compile dependency graph

Disk-first compile graph from pulled workspace resources.

## CLI

```bash
uv run --env-file .env endor-estate pull --namespace tenant.example.child

uv run endor-estate analyze --namespace tenant.example.child --only graph,viz
```

IR outputs under `intermediate-representation/`:

- `compile_dependency_graph.json`
- `compile_dependency_graph_enriched.json`
- `leiden_input.json`
- `graph_partition.json`
- `community_summary.json`
- `graph_metrics.json`

Visualization: `viz/estate_dashboard.html` (Graph overview + Bipartite tabs).

Module: `endorlabs.workflows.estate.analyze.compile_graph.disk_build`.

Main-context only.
