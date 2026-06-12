---
id: endor-workflow-composition
tags: [workflows, scripts, composition]
summary: >-
  Prefer workflow CLI, then library imports, then Client; extend artifacts instead
  of re-fetching discovery.
---

# Workflow composition

## Layer boundaries

| Layer | Location | Responsibility | Must not |
|-------|----------|----------------|----------|
| **Primitives** | `Client`, `APIClient` | CRUD/list/get per resource | Orchestration, file I/O, argparse |
| **Tools** | `endorlabs.tools.*` | Reusable domain utilities (e.g. list sharding) | Tenant-wide workflow opinions, CLI mains |
| **Workflow libraries** | `endorlabs.workflows.*` (non-`cli`) | `Client` in → typed `WorkflowResult` out | `print()`, argparse, cwd-relative writes |
| **Workflow CLIs** | `*.cli`, `troubleshooting_scans/*` | Args, artifacts, filenames | Become copy-paste targets for agents |
| **Session scripts** | `workspace/sessions/<user>/scripts/` | Thin glue on artifacts + library imports | Live in `src/`, reimplement discovery |

`endorlabs.workflows` ships **documented contracts** — prefer importing
`library_entrypoints` from `MANIFEST.json` over vendoring workflow source.

## Escalation ladder

Use one step at a time:

1. **Workflow CLI** — run the skill's documented command with defaults.
2. **Workflow library** — import composable functions (see `MANIFEST.json` `library_entrypoints`).
3. **`Client` facade** — when no workflow covers the query.
4. **Session script** — minimal glue under `sessions/<user>/scripts/` (see `endor-workspace-layout`).

## Artifact-first

After a workflow run, treat outputs as source of truth:

- Read `context_manifest.json`, troubleshooting JSON, or step artifacts **before** re-listing the API.
- Thread `namespace` and UUIDs from artifacts into downstream calls.
- Do not repeat `Project.list(traverse=True)` when a prior step already wrote project JSON.

## Supported library imports

Generic entrypoints (no estate literals):

- `client.Project.resolve()` — resolve project by name or UUID
- `client.CallGraphData.decode()` / `.fetch()` — call graph fetch + decode
- `client.ScanResult.get_logs()` — scan log lines (ScanLogRequest wire API)
- `client.Finding.list_for_scan()` — scan-scoped finding lists
- `client.<Resource>.count()` / `.list_groups()` / `.latest_created()` — list helpers (see [facade-helpers.md](../../docs/guides/facade-helpers.md))
- `endorlabs.workflows.common.WorkflowResult`
- `endorlabs.workflows.policies.run_validate_policy`
- `endorlabs.workflows.estate.export_version_cardinality_for_package_match`
- `endorlabs.workflows.callgraph.run_callgraph_sweep`
- `endorlabs.workflows.troubleshooting_scans` — workflow CLIs; prefer facade sugar for scan lists and project resolve
- `endorlabs.workflows.agent_context.hydration` — per-project BOM/CG hydration primitive; not a workflow orchestrator

See `MANIFEST.json` → `workflows[].library_entrypoints` for the catalog row tied to each skill.

## Anti-patterns

- Run **`endor-estate pull`** (namespace-wide bulk collect) unless the user explicitly requests it — see [docs/estate/README.md](../../docs/estate/README.md).
- Copy-paste a workflow CLI `main()` into a session script.
- Unbounded re-fetch to "fix" empty rows (check namespace first).
- Add triage code under `src/endorlabs/` during an investigation.
- Fork filename/JSON contracts when extending troubleshooting pipelines.

## When to promote

Reusable, tested orchestration belongs in `endorlabs.workflows` (contributor PR), not a
permanent session script.
