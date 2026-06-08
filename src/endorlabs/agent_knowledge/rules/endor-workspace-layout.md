---
id: endor-workspace-layout
tags:
- workspace
- artifacts
- sessions
summary: Write session/triage artifacts under workspace/sessions/<user>/; not repo-root
  .tmp/.
---

# Workspace layout

Run outputs and agent-written files belong under **`.endorlabs-context/workspace/`**
(gitignored). Do **not** write session/triage debugging artifacts or ad-hoc probe
scripts to repo-root `.tmp/` unless the user explicitly requests that path.

## Subdirectories

| Subdir | Use for |
|--------|---------|
| `session/<namespace_slug>/` | Compile-dependency-graph phased session artifacts (`dependency_graph` CLI; context root, not under `workspace/`) |
| `projects/<uuid>/` | Project-scoped workflow bundles (`endor-agent-context`, reachability exports, relationship maps) |
| `sessions/<user>/` | Interactive session, RCA/triage exports, one-off scripts, and other non-project scratch work |
| `artifacts/` | Namespace-scoped inventory outputs (e.g. Semgrep metadata) |

Common session subfolders (create as needed):

- `sessions/<user>/troubleshooting/` — scan RCA (`troubleshooting_scans` workflow default)
- `sessions/<user>/scripts/` — temporary probe/debug `.py` files for the current investigation
- `sessions/<user>/exports/` — structured JSON/CSV from auth/SSO/policy spot-checks

## Resolving `<user>`

Derive a short directory slug from `Client().whoami()` (email local-part, sanitized).
When identity is unknown, use `agent`.

## Agent rules

1. **Project workflows** — pass `--output-dir .endorlabs-context/workspace/projects/` (or omit when the CLI default is already `workspace/projects`).
2. **Triage / debugging** — write artifacts under `.endorlabs-context/workspace/sessions/<user>/` (add a task subdir when helpful).
3. **Temp scripts** — create under `sessions/<user>/scripts/`; never commit them to `src/` or repo root.
4. **Do not** assume `.endorlabs-context/` exists; `mkdir -p` parent dirs before writing.

Path helpers (SDK): `endorlabs.context.paths.workflow_projects_root`,
`workflow_sessions_root`, `workflow_artifacts_root`.
