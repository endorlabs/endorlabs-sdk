# Workflow CLI index

Thin index of SDK workflow entry points. See `MANIFEST.json` for machine-readable data.

| ID | CLI | Module | Skill | Default output |
|----|-----|--------|-------|----------------|
| agent-context | `endor-agent-context` | `endorlabs.workflows.agent_context.cli` | endor-project-retrieval-bundle | .endorlabs/tasks/<slug>-<YYYY-MM-DD>/projects/<slug>_<timestamp>/ |
| auth-setup | `endor-auth` | `endorlabs.workflows.auth.cli` | endor-auth-setup | — |
| callgraph-path | `endor-callgraph-path` | `endorlabs.workflows.callgraph.path_cli` | — | stdout or caller path |
| callgraph-search | `endor-callgraph-search` | `endorlabs.workflows.callgraph.search` | endor-fetch-and-search-call-graph | stdout or caller path |
| context-bootstrap | `endor-context` | `endorlabs.context.cli` | — | .endorlabs/ |
| log-export | `endor-log-export` | `endorlabs.workflows.log_export.cli` | — | .endorlabs/tasks/<slug>-<YYYY-MM-DD>/logs/ |
| policies-validate | `—` | `endorlabs.workflows.policies.validate` | endor-validate-policy | stdout or --output-json |
| query-estate-routing | `—` | `endorlabs.query` | endor-route-estate-queries | — |
| reachability-context | `endor-reachability-context` | `endorlabs.workflows.reachability.cli` | endor-reachability-provenance | .endorlabs/tasks/<slug>-<YYYY-MM-DD>/projects/<uuid>/reachability_context.json |
| relationships-map | `—` | `endorlabs.workflows.estate.analyze.project_map.map` | endor-namespace-relationship-map | .endorlabs/tasks/<slug>-<YYYY-MM-DD>/relationships/<namespace>/ |
| semgrep-inventory | `endor-semgrep-inventory` | `endorlabs.workflows.semgrep.inventory` | endor-custom-sast-rules | `.endorlabs/tasks/inventory/semgrep_rule_metadata_inventory.json` (`SemgrepRule.list`) |
| troubleshooting-scans | `—` | `endorlabs.workflows.troubleshooting_scans` | endor-troubleshooting-scans | .endorlabs/tasks/<slug>-<YYYY-MM-DD>/troubleshooting/ |
| vector-query | `endor-vector-query` | `endorlabs.workflows.vector_search.cli` | — | stdout or caller path |

**Naming:** workflow id `semgrep-inventory` and module path `workflows/semgrep/` are shorthand; the API resource is **`SemgrepRule`** (`client.SemgrepRule`).
