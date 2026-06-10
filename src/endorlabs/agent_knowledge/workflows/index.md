# Workflow CLI index

Thin index of SDK workflow entry points. See `MANIFEST.json` for machine-readable data.

| ID | CLI | Module | Skill | Default output |
|----|-----|--------|-------|----------------|
| agent-context | `endor-agent-context` | `endorlabs.workflows.agent_context.cli` | endor-project-retrieval-bundle | .endorlabs-context/workspace/projects/<slug>_<timestamp>/ |
| callgraph-search | `endor-callgraph-search` | `endorlabs.workflows.callgraph.search` | endor-fetch-and-search-call-graph | stdout or caller path |
| context-bootstrap | `endor-context` | `endorlabs.context.cli` | — | .endorlabs-context/ |
| estate-workspace | `endor-estate` | `endorlabs.workflows.estate.cli.main` | endor-estate-workspace | .endorlabs-context/workspace/<slug>-<YYYYMMDD>/ |
| policies-validate | `—` | `endorlabs.workflows.policies.validate` | endor-validate-policy | stdout or --output-json |
| reachability-context | `endor-reachability-context` | `endorlabs.workflows.reachability.cli` | endor-reachability-provenance | .endorlabs-context/workspace/projects/<uuid>/ |
| relationships-map | `—` | `endorlabs.workflows.estate.analyze.project_map.map` | endor-namespace-relationship-map | .endorlabs-context/workspace/ |
| semgrep-inventory | `endor-semgrep-inventory` | `endorlabs.workflows.semgrep.inventory` | endor-custom-sast-rules | `.endorlabs-context/workspace/artifacts/semgrep_rule_metadata_inventory.json` (`SemgrepRule.list`) |
| troubleshooting-scans | `—` | `endorlabs.workflows.troubleshooting_scans` | endor-troubleshooting-scans | .endorlabs-context/workspace/sessions/<user>/troubleshooting/ |

**Naming:** workflow id `semgrep-inventory` and module path `workflows/semgrep/` are shorthand; the API resource is **`SemgrepRule`** (`client.SemgrepRule`).
