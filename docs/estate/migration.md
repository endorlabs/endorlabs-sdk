# Estate workflow migration (breaking)

## Removed console scripts / subcommands

| Removed | Replacement |
|---------|-------------|
| `endor-analytics-export-deps` | `endor-estate pull` + `endor-estate analyze` |
| `endor-analytics-risk-cardinality` | `endor-estate analyze` (risk step) |
| `endor-analytics-risk-family-chart` | `viz/estate_dashboard.html` (risk tab) |
| `endor-compile-dependency-graph` | `endor-estate analyze` (graph step) |
| `endor-graph-summarize` | `endor-estate summarize` |
| `endor-estate plan` | `data/collect_manifest.json` |
| `endor-estate export` | `endor-estate analyze` (viz step) |

## Layout change

| Old | New |
|-----|-----|
| `.endorlabs-context/session/<slug>/` | `.endorlabs-context/workspace/<slug>-<YYYYMMDD>/` |
| `layers/dependency_corpus.jsonl` | `data/dependency_metadata.jsonl` |
| `layers/findings_sca_vulnerability_main.jsonl` | `data/finding.jsonl` |
| `layers/publisher_index.jsonl` | `data/package_version.jsonl` |
| `layers/projects.jsonl` | `data/project.jsonl` |
| `estate_manifest.json` | `data/collect_manifest.json` |
| `analyses/*` | `intermediate-representation/*` + `viz/estate_dashboard.html` |

## Python package moves

- `pull_layers` → `collect_workspace`
- `session_dir_for` → removed (use `workspace_dir_for`)
- `load_corpus_records` → `load_dependency_metadata_records`
- `endorlabs.workflows.estate.session.*` → `endorlabs.workflows.estate.workspace.*`

## Example

Before:

```bash
uv run endor-estate pull --namespace tenant.example.child --layers dependency_corpus,findings_sca_vulnerability_main
uv run endor-estate analyze risk-cardinality --namespace tenant.example.child
uv run endor-estate export family-risk-chart --namespace tenant.example.child
```

After:

```bash
uv run endor-estate pull --namespace tenant.example.child
uv run endor-estate analyze --namespace tenant.example.child --workspace .endorlabs-context/workspace/tenant_example_child-20260608
```

Open `.endorlabs-context/workspace/tenant_example_child-20260608/viz/estate_dashboard.html`.

## IR artifact renames (breaking)

Re-run `endor-estate analyze --only graph,viz` after upgrading; old filenames and JSON keys are not read.

| Old IR file | New IR file |
|-------------|-------------|
| `leiden_input.json` | `clustering_graph.json` |
| `graph_partition.json` | `community_detection.json` |
| `community_summary.json` | `community_profiles.json` |
| `publisher_rankings.json` | `producer_rankings.json` |

| Old schema ID | New schema ID |
|---------------|---------------|
| `endor.leiden_input.v1` | `endor.clustering_graph.v1` |
| `endor.graph_partition.v1` | `endor.community_detection.v1` |
| `endor.community_summary.v1` | `endor.community_profiles.v1` |
| `endor.publisher_rankings.v1` | `endor.producer_rankings.v1` |

Selected JSON field renames on compile graph artifacts:

| Old | New |
|-----|-----|
| `source_id` / `target_id` | `importer_vertex_id` / `producer_vertex_id` |
| `anchor_package_name` | `linking_package_name` |
| `consumer_row_count` | `import_evidence_count` |
| `publishers_with_consumers` | `producers_with_importers` |
| `inbound_edge_count` | `inbound_import_count` |

Phased CLI: `partition_graph` → `detect_communities`; flags `--partition-*` → `--community-*`.
