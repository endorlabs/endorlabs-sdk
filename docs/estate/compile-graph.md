# Compile dependency graph

Disk-first compile graph from pulled workspace resources.

## CLI

```bash
uv run --env-file .env endor-estate pull --namespace tenant.example.child

uv run endor-estate analyze --namespace tenant.example.child --only graph,viz
```

IR outputs under `intermediate-representation/`:

- `compile_dependency_graph.json` — importer/producer vertices and compile-import edges
- `compile_dependency_graph_enriched.json` — corpus tags, risk metadata, evidence counts
- `clustering_graph.json` — bipartite clustering input (importer/producer edges)
- `community_detection.json` — community membership and detection parameters
- `community_profiles.json` — per-community summaries (namespaces, linking packages)
- `graph_metrics.json` — WCC/SCC, k-core, centrality
- `producer_rankings.json` — most-reused internal libraries by inbound import count

Visualization: `viz/estate_dashboard.html` (Internal dependencies tab).

Module: `endorlabs.workflows.estate.analyze.compile_graph.disk_build`.

Main-context only.

## Edge and vertex vocabulary

Compile-import edges use **importer** (consumer project) → **producer** (library project) direction:

| Field | Meaning |
|-------|---------|
| `importer_vertex_id` / `producer_vertex_id` | Graph node ids on the flat import graph |
| `linking_package_name` | Package coordinate that links importer to producer |
| `import_evidence_count` | DependencyMetadata rows supporting the edge |

Clustering graph edges (`clustering_graph.json`) use `importer`, `producer`, `linking_package_name`, and `import_evidence_count`.

Community detection reads `community_detection.json` fields `edge_weight_source` and `vertex_weight_source` (defaults: `import_evidence_count` and `inbound_import_count`).

Canonical filenames and schema IDs live in `endorlabs.workflows.estate.contracts.ir_artifacts`.
