# Workflow CLI index

Thin index of SDK workflow entry points. See `MANIFEST.json` for machine-readable data.

| ID | CLI | Module | Skill | Default output |
|----|-----|--------|-------|----------------|
| agent-context | `endor-agent-context` | `endorlabs.workflows.agent_context.cli` | endor-project-agent-context | .endorlabs-context/workspace/projects/<uuid>/ |
| analytics-export-deps | `endor-analytics-export-deps` | `endorlabs.workflows.analytics.cli` | endor-analytics-estate-dependencies | .endorlabs-context/workspace/projects/<uuid>/ |
| callgraph-search | `endor-callgraph-search` | `endorlabs.workflows.callgraph.search` | endor-fetch-and-search-call-graph | stdout or caller path |
| compile-dependency-graph | `endor-compile-dependency-graph` | `endorlabs.workflows.relationships.dependency_graph` | — | .endorlabs-context/session/<namespace>/ |
| context-bootstrap | `endor-context` | `endorlabs.context.cli` | — | .endorlabs-context/ |
| graph-summarize | `endor-graph-summarize` | `endorlabs.workflows.relationships.summarize_session` | — | stdout or --json |
| policies-validate | `—` | `endorlabs.workflows.policies.validate` | endor-validate-policy | stdout or --output-json |
| reachability-context | `endor-reachability-context` | `endorlabs.workflows.reachability.cli` | endor-reachability-provenance | .endorlabs-context/workspace/projects/<uuid>/ |
| relationships-map | `—` | `endorlabs.workflows.relationships.map` | endor-map-project-dependency-relationships | .endorlabs-context/workspace/projects/<uuid>/ |
| semgrep-inventory | `endor-semgrep-inventory` | `endorlabs.workflows.semgrep.inventory` | endor-custom-sast-rules | .endorlabs-context/workspace/artifacts/semgrep_rule_metadata_inventory.json |
| troubleshooting-scans | `—` | `endorlabs.workflows.troubleshooting_scans` | endor-troubleshooting-scans | .endorlabs-context/workspace/sessions/<user>/troubleshooting/ |
