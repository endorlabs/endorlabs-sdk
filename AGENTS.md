# Endor Labs SDK: AI Agent Integration Guide

> **Audience:** Agents and humans using the SDK with optional shipped skills/rules.
> - **Any project:** [README.md](README.md) (install, quick start) · normative behavior in [docs/contracts.md](docs/contracts.md).
> - **Shipped agent knowledge (wheel or after `init()`):** `agent_knowledge_index_path()` → `INDEX.md` / `MANIFEST.json` — not this file unless you are in the SDK repo.
> - **This repository only:** [CONTRIBUTORS.md](CONTRIBUTORS.md) · full region map [docs/contributing/repository-layout.md](docs/contributing/repository-layout.md).

`AGENTS.md` is repo-root documentation (also linked from README). It is **not** bundled in the `endorlabs` PyPI package.

## Start here

| You need | Go to |
| -------- | ----- |
| Install and first API calls | [README.md](README.md) |
| Skill playbooks | Wheel or `.endorlabs/_cache/sdk/INDEX.md` → `skills/<id>/SKILL.md` |
| Bootstrap depth (SDK-only vs `init()`) | [Bootstrap](#bootstrap) below · [CONTRIBUTORS.md — Optional: SDK bootstrap and OpenAPI](CONTRIBUTORS.md#optional-sdk-bootstrap-and-openapi) |
| Repo regions and gitignored paths | [docs/contributing/repository-layout.md](docs/contributing/repository-layout.md) |
| Extend the SDK surface | [docs/contributing/architecture.md](docs/contributing/architecture.md) · skill **endor-implement-sdk-resource** |
| Commit / open a PR (maintainers) | [CONTRIBUTORS.md](CONTRIBUTORS.md#before-you-commit--open-a-pr) · [pull_request_template.md](.github/pull_request_template.md) |
| Author or update agent skills | [agent-knowledge/schema/README.md](agent-knowledge/schema/README.md) · skill **endor-author-agent-skill** |

## Consuming the SDK

**Default:** `endorlabs.Client(...)` without `init()` — sufficient for API calls and `endorlabs.workflows` CLIs.

**Bootstrap when:** the agent reads skills/rules/contracts from disk, greps offline OpenAPI, or writes under `.endorlabs/` (`reports/`, `tasks/`). See [Bootstrap](#bootstrap).

Shipped bootstrap rules (`endor-namespace-scoping`, `endor-list-query-performance`, `endor-workspace-layout`, …) expand namespace, list, and workspace topics — load via `agent_knowledge_bootstrap_paths()` or `.endorlabs/_cache/sdk/rules/`.

## Agent notes

Prefer these before assuming full-tenant sweeps or hand-built relationship filters.
Canonical trap text: shipped
[critical-validation-traps.md](agent-knowledge/reference/critical-validation-traps.md)
(also via Tier-0 [INDEX.md](agent-knowledge/INDEX.md) → `references[]`).

<!-- trap-ids: ambiguous-project-url, project-scoped-list-namespace, finding-branch-refs, tenant-wide-scan-cost, list-masks-return-dict, portable-examples -->

- **ambiguous-project-url** — identical `meta.name` may exist under multiple child namespaces; use `Project.search_by_name(..., traverse=True, max_pages=…)` or UUID `get()`.
- **project-scoped-list-namespace** — resolve `Project` first; pass `namespace=project.namespace` or `list_by_project`.
- **finding-branch-refs** — `spec.source_code_version.ref` may be a short branch name; list without branch filter first.
- **tenant-wide-scan-cost** — prefer `--project-name` / `--project-uuid` over `--all-projects` for interactive RCA.
- **list-masks-return-dict** — non-empty `mask=` → `dict` rows from `list()` / `search_by_*`.
- **portable-examples** — placeholders only in tracked content; integration tenants via env.

### Contributor extras (not trap-table rows)

- **Generated accessor helpers:** `Finding.list_by_project`, `Finding.list_for_context`, `ScanResult.list_by_project`, `Finding.to_dependency_metadata` — [resource-routes.md](docs/generated-reference/resource-routes.md).
- **Relationship map:** `estate.analyze.project_map.map` uses a bounded `PackageVersion` list — distinguish wrong namespace / unscanned consumers from pagination truncation before raising caps.
- **List deserialization vs API drift:** Pydantic validation failures on `list()` → model-sync / payload tolerance (**endor-troubleshoot-sdk**, `devtools/codegen/sync/`).
- **Sharded parallel lists:** [list-query-performance.md](docs/contributing/list-query-performance.md#sharded-parallel-lists).
- **Graph joins / estate counts:** `client.Query.execute` / `Query.Project.count_*` — [query-recipes.md](docs/guides/query-recipes.md); run `validate_sample` before scale.
- **Evidence vs inference:** Mark guesses as **Inferred:**; skill **endor-troubleshoot-sdk**.
- **Endor Patches grain:** family/version keys are `spec.target_dependency_package_name` + `target_dependency_version`, not UIA `upgrade_list`. Quote the filter before comparing counts.
- **`list_groups` counts:** use `aggregation_count.count` / `GroupBucket.count`.
- **Client concurrency:** One `Client` per credential set — [docs/contracts.md](docs/contracts.md#concurrency-and-transport-retries).

## Bootstrap

| Need | Approach |
| ---- | -------- |
| API + workflow CLIs | **SDK-only** — no `.endorlabs/` |
| INDEX / MANIFEST / skills without cwd writes | `agent_knowledge_index_path()`, `agent_knowledge_manifest()` (wheel) |
| Cwd-relative skills + optional OpenAPI | `endorlabs.init()` or `uv run endor-context` |
| IDE skill mirrors | `init(sync_skills="both")` after SDK bootstrap (`.agents/skills/` + `.claude/skills/`) |

Pick the shallowest depth:

1. **SDK-only** — `Client(...)` only.
2. **Wheel-only** — `agent_knowledge_index_path()` → `INDEX.md`; `agent_knowledge_manifest()` for skill paths. No auth, no cwd writes.
3. **SDK bootstrap** — `init()` copies agent knowledge to `.endorlabs/_cache/sdk/` by default. Optional OpenAPI goes under `.endorlabs/_cache/openapi.json`. Product docs: Docs MCP (`https://docs.endorlabs.com/mcp`); unsupported harnesses: [llms.txt](https://docs.endorlabs.com/llms.txt). Full option list: [CONTRIBUTORS.md — Optional: SDK bootstrap and OpenAPI](CONTRIBUTORS.md#optional-sdk-bootstrap-and-openapi).

After SDK bootstrap, read **INDEX.md** → **MANIFEST.json** → `skills/<id>/SKILL.md`. Non-Cursor harnesses: prepend `agent_knowledge_bootstrap_paths()`. Workflow outputs: `.endorlabs/reports/` and `.endorlabs/tasks/` (shipped rule `rules/endor-workspace-layout.md`).

Consumer projects should **gitignore** `.endorlabs/`. Print the entry: `uv run endor-context --print-gitignore-line`. Agents must **ask the user** to add it — do not edit `.gitignore` automatically.

### Agent knowledge naming

| Layer | Path / module |
| ----- | ------------- |
| Authoring (repo) | `agent-knowledge/` |
| Shipped (wheel) | `src/endorlabs/agent_knowledge/` → `endorlabs.agent_knowledge` |
| Materialized (runtime) | `.endorlabs/_cache/sdk/` |

Maintainers editing authoring: `uv run python devtools/codegen/sync_agent_knowledge.py` — see [repository-layout.md](docs/contributing/repository-layout.md).

## SDK behavior (quick reference)

- **Canonical naming:** `tenant.namespace.child`; no UUIDs in namespace paths.
- **Environment variables:** only names in [README.md](README.md), [CONTRIBUTORS.md](CONTRIBUTORS.md), product docs, or local OpenAPI; read with `os.getenv` — do not mutate `os.environ` or `.env` unless a human explicitly requests it (maintainers: rule `endor-environment-variables`).
- **Client facades:** `client.<Kind>` PascalCase = `endorctl api … --resource <Kind>`. Custom: **`CallGraphData`** (decode/fetch); log lines via **`ScanResult.get_logs`** — [docs/contracts.md](docs/contracts.md), [docs/guides/facade-helpers.md](docs/guides/facade-helpers.md).
- **Return types:** `.get()` → typed model or raise; `.list()` / `search_by_*` / `list_by_*` / `list_for_context` → models unless non-empty `mask=` → `dict` rows; `to_*` stitch accessors → `RouteResult`.
- **F():** `matches()` on strings; `contains()` on array fields only.

## Repository layout (summary)

| Region | Role |
| ------ | ---- |
| [`agent-knowledge/`](agent-knowledge/) | Authoring — rules, contracts, skills (not runtime read path) |
| [`src/endorlabs/agent_knowledge/`](src/endorlabs/agent_knowledge/) | Shipped bundle — `MANIFEST.json`, mirrored skills/rules |
| [`src/endorlabs/workflows/`](src/endorlabs/workflows/) | Executable workflows + console scripts |
| [`src/endorlabs/generated/`](src/endorlabs/generated/) | Model-sync models and registry contract |
| [`docs/`](docs/) | Tracked public docs |
| [`.endorlabs/`](.endorlabs/) | Gitignored — `_cache/`, `reports/`, `tasks/` |

**Workflows** = code in `src/endorlabs/workflows/`. **Skills** = playbooks in the shipped bundle. Catalog: `MANIFEST.json` → `workflows[]`. Full map: [docs/contributing/repository-layout.md](docs/contributing/repository-layout.md).

## Skills and handoffs

**Discovery:** `.endorlabs/_cache/sdk/INDEX.md` → `MANIFEST.json` → `skills/`; or wheel via `agent_knowledge_index_path()`. Authoring index (maintainers): [agent-knowledge/README.md](agent-knowledge/README.md).

Common entry skills: **endor-auth-setup**, **endor-retrieve-scan-results**, **endor-troubleshooting-scans**, **endor-troubleshoot-sdk**, **endor-troubleshoot-authlog**. Full list: `MANIFEST.json` → `skills[]`.

Tenant / namespace **executive HTML reports** (QBR read-out, onboarding growth, sprawl, FindingLog burndown): skill **endor-workflow-reports** → `uv run endor-reports -n <tenant>` — see [docs/guides/executive-report-packet.md](docs/guides/executive-report-packet.md).

Skills compose with handoffs — [agent-knowledge/schema/README.md — Skill composition](agent-knowledge/schema/README.md#skill-composition-and-handoffs).

## Further reading

| Topic | Location |
| ----- | -------- |
| Doc index | [docs/README.md](docs/README.md) |
| Examples + browser auth | [docs/guides/examples.md](docs/guides/examples.md) |
| Generated resource matrix | [docs/generated-reference/resources.md](docs/generated-reference/resources.md) |
| SDK layers (contributors) | [docs/contributing/architecture.md](docs/contributing/architecture.md) |
| Local OpenAPI | `.endorlabs/_cache/openapi.json` after bootstrap |
| Platform docs (online) | <https://docs.endorlabs.com/> |
| Troubleshooting / surface extension | skills **endor-troubleshoot-sdk**, **endor-implement-sdk-resource** |

---

Behavioral invariants also live in shipped `rules/` and `contracts/` (wheel or `.endorlabs/_cache/sdk/`). Maintainer setup: [CONTRIBUTORS.md](CONTRIBUTORS.md).
