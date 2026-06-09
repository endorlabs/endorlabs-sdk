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
- `session_dir_for` → `workspace_dir_for`
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
