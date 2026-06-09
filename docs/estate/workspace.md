# Estate workspace layout

Schema: `endor.workspace_collect.v1` in `data/collect_manifest.json`.

## Directory tree

```text
.endorlabs-context/workspace/<namespace_slug>-<YYYYMMDD>/
  data/
    collect_manifest.json
    project.jsonl
    dependency_metadata.jsonl
    finding.jsonl
    package_version.jsonl
  intermediate-representation/
    version_cardinality.json
    risk_cardinality.json
    compile_dependency_graph.json
    compile_dependency_graph_enriched.json
    clustering_graph.json
    community_detection.json
    community_profiles.json
    graph_metrics.json
    producer_rankings.json
  viz/
    estate_dashboard.html
  logs/
    pull.log
    analyze.log
```

## Collect manifest

Atomic writes to `collect_manifest.json.tmp` then `os.replace()`. Tracks per-resource status, line counts, and per-project shard progress for `dependency_metadata` and `finding`.

Validation (`validate_workspace_collect`) ensures manifest keys match JSONL line counts before `analyze`.

## CLI

```bash
# Pull all resources (project, dependency_metadata, finding, package_version)
uv run --env-file .env endor-estate pull -n tenant.example

# Resume partial pull
uv run endor-estate pull -n tenant.example --workspace .endorlabs-context/workspace/tenant_example-20260608 --resume

# Analyze (disk-only IR + dashboard)
uv run endor-estate analyze -n tenant.example --workspace .endorlabs-context/workspace/tenant_example-20260608

# Summarize IR
uv run endor-estate summarize -n tenant.example --workspace ...
```

## Resource alignment

| File | API resource |
|------|--------------|
| `project.jsonl` | `Project` |
| `dependency_metadata.jsonl` | `DependencyMetadata` (main context) |
| `finding.jsonl` | `Finding` (main context SCA+vuln) |
| `package_version.jsonl` | `PackageVersion` (main context) |
