---
id: endor-workspace-layout
tags:
- workspace
- artifacts
- sessions
summary: Write workflow artifacts under workspace/projects, workspace/runs/<run-bucket>,
  or workspace/inventory; not repo-root .tmp/.
---

# Workspace layout

Run outputs and agent-written files belong under **`.endorlabs-context/workspace/`**
(gitignored). Do **not** write session/triage debugging artifacts or ad-hoc probe
scripts to repo-root `.tmp/` unless the user explicitly requests that path.

## Three buckets (+ estate)

| Bucket | Use for | Default pattern |
|--------|---------|-----------------|
| **`projects/`** | One project: bundles, per-finding reachability | `projects/<slug>_<timestamp>/` · `projects/<uuid>/reachability_context.json` |
| **`runs/`** | Ephemeral workflow CSV/JSON/RCA/HTML | `runs/<run-bucket>/` + tenant in **filename** |
| **`inventory/`** | Namespace-scoped inventories | `inventory/<artifact-name>.json` |
| **`<estate-slug>-<YYYYMMDD>/`** | Explicit `endor-estate` bulk only | unchanged |

SDK helpers: `default_runs_dir(run_bucket)`, `workflow_projects_root()`,
`workflow_inventory_root()`, `project_workspace_dir()`.

## Run bucket (not a timestamp)

**Run bucket** is a fixed folder name under `runs/` — authored per skill, not
generated at runtime.

1. Skill has `endorlabs.catalog.workflow_id` → use that string (see `MANIFEST.json` → `workflows[].id`).
2. Script-only skill → skill id minus `endor-` prefix (e.g. `endor-duplicate-projects` → `duplicate-projects`).
3. Never use timestamps as run bucket names.

**Filename convention** in `runs/`: `<tenant-sanitized>-<purpose>.{ext}` unless a
workflow documents a richer pattern (e.g. troubleshooting `--timestamped`).

## Timestamps

| Location | Pattern | When |
|----------|---------|------|
| `projects/` bundle | `<slug>_YYYYMMDDTHHMMSSZ/` | `endor-agent-context` |
| `runs/troubleshooting-scans/` files | `…__purpose[__YYYYMMDDTHHMMSSZ].ext` | optional `--timestamped` |
| Estate | `<slug>-<YYYYMMDD>/` | `endor-estate` collect |

## Agent scratch (optional)

Ad-hoc probes and ephemeral notes may use `runs/scratch/` (scripts, markdown).
Do not commit under `docs/`.

## Agent rules

1. **Project workflows** — `--output-dir` under `workspace/projects/` (or CLI default).
2. **Report / RCA workflows** — default `workspace/runs/<run-bucket>/`; override with `--output` / `--output-dir`.
3. **Temp scripts** — `runs/scratch/`; never commit to `src/` or repo root.
4. **Do not** assume `.endorlabs-context/` exists; create parent dirs before writing.
5. **Gitignore** — consumer projects should ignore `.endorlabs-context/` (`uv run endor-context --print-gitignore-line`).

## Legacy paths

Older docs used `workspace/sessions/<user>/exports/…` and `workspace/artifacts/`.
Prefer the three-bucket layout above. `workflow_artifacts_root()` aliases
`workflow_inventory_root()` (`inventory/`).
