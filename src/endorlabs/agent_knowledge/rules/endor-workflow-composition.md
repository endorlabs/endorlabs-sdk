---
id: endor-workflow-composition
tags:
- workflows
- scripts
- composition
summary: Prefer workflow CLI, then library imports, then Client; extend artifacts
  instead of re-fetching discovery.
---

# Workflow composition

## Layer boundaries

| Layer | Location | Responsibility | Must not |
|-------|----------|----------------|----------|
| **Primitives** | `Client`, `APIClient` | CRUD/list/get per resource | Orchestration, file I/O, argparse |
| **Tools** | `endorlabs.tools.*` | Reusable list composition (e.g. `list_sharding` over accessors) | Tenant-wide workflow opinions, CLI mains |
| **Query** | `endorlabs.query.*` | Graph join recipes, topology/routing/validation; custom joins via `QuerySpec` | Unvalidated joins at estate scale |
| **Utils** | `endorlabs.utils.*` | Transport/concurrency/namespace helpers | Domain list composition |
| **Workflow libraries** | `endorlabs.workflows.*` (non-`cli`) | `Client` in → typed `WorkflowResult` out | `print()`, argparse, cwd-relative writes |
| **Workflow CLIs** | `*.cli`, `troubleshooting_scans/*` | Args, artifacts, filenames | Become copy-paste targets for agents |
| **Session scripts** | `workspace/runs/scratch/` | Thin glue on artifacts + library imports | Live in `src/`, reimplement discovery |

`endorlabs.workflows` ships **documented contracts** — prefer importing
`library_entrypoints` from `MANIFEST.json` over vendoring workflow source.

## Escalation ladder

Use one step at a time:

1. **Workflow CLI** — run the skill's documented command with defaults.
2. **Workflow library** — import composable functions (see `MANIFEST.json` `library_entrypoints`).
3. **`Client` facade** — when no workflow covers the query.
4. **Session script** — minimal glue under `runs/scratch/` (see `endor-workspace-layout`).

## Artifact-first

After a workflow run, treat outputs as source of truth:

- Read `context_manifest.json`, troubleshooting JSON, or step artifacts **before** re-listing the API.
- Thread `namespace` and UUIDs from artifacts into downstream calls.
- Do not repeat `Project.list(traverse=True)` when a prior step already wrote project JSON.
- Separate **evidence-backed** claims (API rows, artifacts, cited contracts) from **Inferred:** conclusions; use skill **endor-troubleshoot-sdk** for SDK/API failure playbooks (maintainers: `docs/contributing/troubleshooting.md`).

## Supported library imports

Generic entrypoints (no estate literals):

- `client.Project.search_by_name()` — bounded project discovery by repo URL substring or partial UUID
- `client.CallGraphData.decode()` — searchable callables/edges (`CallGraphDecoded`)
- `client.CallGraphData.fetch()` — raw envelope only (workflows use this internally; agents prefer `decode` + skills)
- `client.ScanResult.get_logs()` — scan log lines (ScanLogRequest wire API)
- `client.Finding.list_by_project()` / `list_for_context()` — generated relationship accessors
- `client.ScanResult.list_by_project()` — scan results for a project
- `client.<Resource>.count()` / `.list_groups()` / `.latest_created()` — list helpers (see [facade-helpers.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/guides/facade-helpers.md))
- `client.Query.execute()` / `.at_namespace()` — kind-agnostic graph joins (`QuerySpec` + `QueryScope`); see [query-recipes.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/guides/query-recipes.md)
- `client.Query.Project.count_pv()` / `.count_findings_by_category()` / `.count_dm()` — validated **estate** count joins (same guide)
- `endorlabs.query.discover_topology` / `TopologySnapshot.project_shards()` / `recommend` / `validate_sample` — estate routing plane
- `endorlabs.filters` — canonical main-context and finding MQL fragments
- `endorlabs.workflows.estate.fetch_online_dashboard_counts` — online Query tiles for estate dashboard
- `client.Project.is_app()` / `.is_cli()` / `.is_sbom()` — project registration inventory (see [facade-helpers.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/guides/facade-helpers.md))
- `endorlabs.filters` — canonical main-context and finding MQL fragments (replaces removed `workflows.findings.filters` submodule)
- `endorlabs.workflows.findings.finding_log_trends.build_finding_log_new_vs_resolved_analysis` — FindingLog CREATE/DELETE weekly chart data (online aggregated)
- `endorlabs.workflows.logs.group_by_time.group_by_time_counts` — generic log `list_groups` + `group_by_time` aggregation
- `endorlabs.workflows.auth.verify_auth` / `refresh_token_to_dotenv` — credential probe and browser refresh (`endor-auth`)
- `endorlabs.workflows.auth.probe_auth_logs` — tenant list-path auth-log RCA rows
- `endorlabs.workflows.auth.count_logins_from_groups` — server-side login counts (`list_groups`)
- `endorlabs.workflows.auth.list_auth_logs` / `count_logins_from_rows` — client-side fallback only
- `endorlabs.workflows.projects.inventory.fetch_installation_lookup` — Installation external_id lookup for CLI vs app classification
- `endorlabs.workflows.common.WorkflowResult`
- `endorlabs.workflows.policies.run_validate_policy`
- `endorlabs.workflows.estate.export_version_cardinality_for_package_match`
- `endorlabs.workflows.callgraph.run_callgraph_export`
- `endorlabs.workflows.callgraph.find_call_graph_path`
- `endorlabs.workflows.troubleshooting_scans` — workflow CLIs; prefer facade sugar for scan lists and project resolve
- `endorlabs.workflows.agent_context.hydration` — per-project BOM/CG hydration primitive; not a workflow orchestrator

See `MANIFEST.json` → `workflows[].library_entrypoints` for the catalog row tied to each skill.

## Anti-patterns

- Run **`endor-estate pull`** (namespace-wide bulk collect) unless the user explicitly requests it — see [docs/estate/README.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/estate/README.md).
- Copy-paste a workflow CLI `main()` into a session script.
- Unbounded re-fetch to "fix" empty rows (check namespace first).
- Add triage code under `src/endorlabs/` during an investigation.
- Fork filename/JSON contracts when extending troubleshooting pipelines.

## When to promote

Reusable, tested orchestration belongs in `endorlabs.workflows` (contributor PR), not a
permanent session script.
