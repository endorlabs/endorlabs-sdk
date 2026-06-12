# Repository layout

Map of tracked repo regions, gitignored runtime paths, and how agent knowledge flows from authoring to the wheel. **SDK runtime layers** (transport, facade, registry): [architecture.md](architecture.md).

## Audiences

| Reader | Start here |
| ------ | ---------- |
| SDK consumer (pip install) | [README.md](../../README.md) — no repo checkout required |
| Agent with shipped knowledge only | Wheel `agent_knowledge_index_path()` → `INDEX.md` / `MANIFEST.json` |
| Agent in a consumer project | `endorlabs.init()` or `endor-context` → `.endorlabs-context/sdk/` |
| Agent or human in **this repo** | [AGENTS.md](../../AGENTS.md) (bootstrap + API gotchas) · this page (full map) · [CONTRIBUTORS.md](../../CONTRIBUTORS.md) (setup) |

`AGENTS.md` is **repo-root only** — not shipped in the `endorlabs` wheel. Cursor and similar tools may auto-load it when the workspace is this repository.

## Tracked vs gitignored

```text
GIT TRACKED                          GITIGNORED (per project)
───────────                          ────────────────────────
agent-knowledge/  ──sync──►         .endorlabs-context/
  rules contracts skills               ├── sdk/          ← materialized agent bundle
src/endorlabs/agent_knowledge/         ├── platform/     ← OpenAPI + user-docs (optional)
  (shipped in wheel)                     └── workspace/    ← workflow + session outputs
src/endorlabs/  (SDK + workflows)
docs/  (public docs)
devtools/  (maintainer automation)
.cursor/rules/  (optional IDE rule mirror)
.cursor/skills/  (optional IDE skill mirror)
```

**Runtime read rule:** at execution time, read the **wheel** or **`.endorlabs-context/sdk/`** — not repo `agent-knowledge/` (authoring only).

## Top-level regions

| Region | Role |
| ------ | ---- |
| [`agent-knowledge/`](../../agent-knowledge/) | Authoring — `rules/`, `contracts/`, `skills/`, `schema/` (not pip-installed as source tree) |
| [`src/endorlabs/agent_knowledge/`](../../src/endorlabs/agent_knowledge/) | Shipped bundle — `INDEX.md`, `MANIFEST.json`, mirrored rules/skills/contracts |
| [`src/endorlabs/`](../../src/endorlabs/) | Runtime SDK — `api_client`, facades, `workflows/`, `context/`, hand `resources/` (includes `base.py`, `*_config.py`, `field_aliases.py`) |
| [`src/endorlabs/generated/`](../../src/endorlabs/generated/) | Model-sync output — `registry_contract.py`, `models/**` (never hand-edit; wire mirror, distinct from `resources/`) |
| [`src/endorlabs/registry.py`](../../src/endorlabs/registry.py) + [`registry_overlay.py`](../../src/endorlabs/registry_overlay.py) | Registry adapter + explicit overrides |
| [`devtools/`](../../devtools/) | Model sync, agent-knowledge sync, reference generation |
| [`docs/`](../../docs/) | Tracked public docs — contracts, guides, contributing, generated reference |
| [`tests/`](../../tests/) | `unit/` (client, workflows, platform, tooling) · `integration/` (client, resources, workflows) |
| [`.github/workflows/`](../../.github/workflows/) | CI, model-sync verify, PyPI release |
| [`.endorlabs-context/`](../../.endorlabs-context/) | Local runtime root (see below) |
| [`.cursor/skills/`](../../.cursor/skills/) | Optional IDE skill mirror after `sync_skills` — not authoring source |

Edit `agent-knowledge/` → `uv run python devtools/sync_agent_knowledge.py` → commit `src/endorlabs/agent_knowledge/`.

## `.endorlabs-context/` layout

| Path | Purpose |
| ---- | ------- |
| `context.json` | Materialization manifest |
| `sdk/` | Copy of shipped agent knowledge (`rules/`, `skills/`, `contracts/`, `INDEX.md`, `MANIFEST.json`) |
| `platform/openapi/` | Downloaded OpenAPI (`openapiv2.swagger.json`) when synced |
| `platform/user-docs/` | Downloaded platform docs when synced (`[docs]` extra) |
| `workspace/projects/<uuid>/` | Project-scoped workflow bundles (agent context, call graph, relationship maps) |
| `workspace/sessions/<user>/` | Interactive RCA, exports, temp scripts, notes |
| `workspace/artifacts/` | Namespace-scoped inventories (e.g. **`SemgrepRule`** metadata from `endor-semgrep-inventory`) |
| `workspace/<slug>-<YYYYMMDD>/` | Estate pull/analyze workspaces — [estate/workspace.md](../estate/workspace.md) |

Path helpers: `endorlabs.context.paths`. Session layout rule: shipped `rules/endor-workspace-layout.md`.

Consumer projects should **gitignore** `.endorlabs-context/`. Print the line: `uv run endor-context --print-gitignore-line`.

## Workflows vs skills vs rules

| Layer | Location | Role |
| ----- | -------- | ---- |
| **Workflows** | `src/endorlabs/workflows/` + `[project.scripts]` in [pyproject.toml](../../pyproject.toml) | Executable Python and console CLIs |
| **Skills** | `agent-knowledge/skills/*/SKILL.md` → shipped bundle | Agent playbooks that invoke SDK/workflows |
| **Workflow catalog** | Skill frontmatter `endorlabs.catalog` + [workflows.yaml](../../agent-knowledge/workflows.yaml) + `MANIFEST.json` | Links CLI/module ↔ skill (or `skill: null` for bootstrap-only tools) |
| **Rules** | `agent-knowledge/rules/` | Bootstrap constraints (namespace, list perf, workspace, changelog, …) |
| **Contracts** | `agent-knowledge/contracts/` | On-demand SDK semantics (list params, errors, naming) |

Skills **condense and route**; workflows **run**. Full skill index: [agent-knowledge/README.md](../../agent-knowledge/README.md).

## Documentation placement

Tracked [`docs/`](../README.md) is durable and public-safe. Ephemeral markdown → `.endorlabs-context/workspace/sessions/<user>/notes/` (gitignored). Do not commit `docs/findings/`, `*-draft.md`, or parallel `*-migration.md` — use [changelog.md](../changelog.md). Details: [design.md](../design.md).

## Cursor / IDE mirrors (this repo)

| Path | Role |
| ---- | ---- |
| [`.cursor/rules/endor-*.mdc`](../../.cursor/rules/) | Generated from `agent-knowledge/rules/` — `endor-namespace-scoping` and `endor-list-query-performance` are always-on in Cursor |
| [`.cursor/skills/`](../../.cursor/skills/) | Optional mirror after `init(sync_skills=...)` or `endor-context --sync-skills` |
| [`agent-knowledge-authoring.mdc`](../../.cursor/rules/agent-knowledge-authoring.mdc) | Editing `agent-knowledge/**` — [schema/README.md](../../agent-knowledge/schema/README.md) |

Regenerate rules/skills: `uv run python devtools/sync_agent_knowledge.py`.

## Maintainer invariants

When editing `src/endorlabs/**`:

- **Stdout:** no `print()` except explicit CLI entrypoints.
- **Typing:** public surfaces strict-typed; internal roots ratcheted in [pyproject.toml](../../pyproject.toml).
- **Security:** credentials via env; run `endorctl scan` before code changes.
- **Examples in git:** canonical repo `endorlabs/endorlabs-sdk`; no customer tenants/UUIDs in tracked content.

CI, model-sync, and drift gates: [CONTRIBUTORS.md](../../CONTRIBUTORS.md), [docs-drift-workflow.md](docs-drift-workflow.md), [devtools/sync/README.md](../../devtools/sync/README.md).

## Related

- [architecture.md](architecture.md) — transport, facade, registry, model-sync policy
- [AGENTS.md](../../AGENTS.md) — agent bootstrap depth and API gotchas (repo root)
- [list-query-performance.md](list-query-performance.md) — sharded parallel list patterns
- [release-publishing.md](release-publishing.md) · [changelog.md](../changelog.md) · rule `endor-changelog` — release and changelog policy
