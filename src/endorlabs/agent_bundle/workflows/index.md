# Workflow CLI index

Thin index of SDK workflow entry points. See `MANIFEST.json` for machine-readable data.

| ID | CLI | Module | Skill | Default output |
|----|-----|--------|-------|----------------|
| agent-context | `endor-agent-context` | `endorlabs.workflows.agent_context.cli` | project-agent-context | .endorlabs-context/workspace/projects/<uuid>/ |
| analytics-export-deps | `endor-analytics-export-deps` | `endorlabs.workflows.analytics.cli` | analytics-estate-dependencies | .endorlabs-context/workspace/projects/<uuid>/ |
| callgraph-search | `endor-callgraph-search` | `endorlabs.workflows.callgraph.search` | fetch-and-search-call-graph | stdout or caller path |
| context-bootstrap | `endor-context` | `endorlabs.context.cli` | — | .endorlabs-context/ |
| policies-validate | `—` | `endorlabs.workflows.policies.validate` | validate-policy | stdout or --output-json |
| reachability-context | `endor-reachability-context` | `endorlabs.workflows.reachability.cli` | reachability-provenance | .endorlabs-context/workspace/projects/<uuid>/ |
| relationships-map | `—` | `endorlabs.workflows.relationships.map` | map-project-dependency-relationships | .endorlabs-context/workspace/projects/<uuid>/ |
| semgrep-inventory | `endor-semgrep-inventory` | `endorlabs.workflows.semgrep.inventory` | custom-sast-rules | .endorlabs-context/workspace/artifacts/semgrep_rule_metadata_inventory.json |
| troubleshooting-scans | `—` | `endorlabs.workflows.troubleshooting_scans` | troubleshooting-scans | .endorlabs-context/workspace/sessions/<user>/troubleshooting/ |
