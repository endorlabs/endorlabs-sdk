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
| Skill playbooks | Wheel or `.endorlabs-context/sdk/INDEX.md` → `skills/<id>/SKILL.md` |
| Bootstrap depth (SDK-only vs `init()`) | [Bootstrap](#bootstrap) below · [CONTRIBUTORS.md — Optional: sync external docs](CONTRIBUTORS.md#optional-sync-external-docs) |
| Repo regions and gitignored paths | [docs/contributing/repository-layout.md](docs/contributing/repository-layout.md) |
| Extend the SDK surface | [docs/contributing/architecture.md](docs/contributing/architecture.md) · skill **endor-implement-sdk-resource** |
| Commit / open a PR (maintainers) | [CONTRIBUTORS.md](CONTRIBUTORS.md#before-you-commit--open-a-pr) · [pull_request_template.md](.github/pull_request_template.md) |
| Author or update agent skills | [agent-knowledge/schema/README.md](agent-knowledge/schema/README.md) · skill **endor-author-agent-skill** |

## Consuming the SDK

**Default:** `endorlabs.Client(...)` without `init()` — sufficient for API calls and `endorlabs.workflows` CLIs.

**Bootstrap when:** the agent reads skills/rules/contracts from disk, greps offline OpenAPI, or writes under `.endorlabs-context/workspace/`. See [Bootstrap](#bootstrap).

Shipped bootstrap rules (`endor-namespace-scoping`, `endor-list-query-performance`, `endor-workspace-layout`, …) expand namespace, list, and workspace topics — load via `agent_knowledge_bootstrap_paths()` or `.endorlabs-context/sdk/rules/`.

## Agent notes

Prefer these before assuming full-tenant sweeps or hand-built relationship filters:

- **Ambiguous project URL:** identical `meta.name` may exist under multiple child namespaces. Use `Project.search_by_name(..., traverse=True, max_pages=…)` and pick the row for the intended namespace, or use project UUID with `get()`.
- **Project-scoped list namespace:** resolve `Project` first; pass `namespace=project.namespace` on downstream lists or use **`list_by_project`** accessors. Empty rows often mean wrong namespace, not missing data.
- **Generated accessor helpers:** use `Finding.list_by_project`, `Finding.list_for_context`, `ScanResult.list_by_project`, `Finding.to_dependency_metadata` — relationship map in [docs/generated-reference/resource-routes.md](docs/generated-reference/resource-routes.md).
- **Finding branch field:** `spec.source_code_version.ref` may be a short branch name, not `refs/heads/main`. List findings without a branch filter first, or use `RepositoryVersion.list`.
- **Tenant-wide scan fetch:** `fetch_scan_results --all-projects` is O(projects × scans). Prefer `--project-name` / `--project-uuid` for interactive RCA.
- **Relationship map:** `estate.analyze.project_map.map` uses a bounded `PackageVersion` list — distinguish wrong namespace / unscanned consumers from pagination truncation before raising caps.
- **List deserialization vs API drift:** Pydantic validation failures on `list()` → model-sync / payload tolerance (**endor-troubleshoot-sdk**, `devtools/sync/`), not query-parameter tweaks alone.
- **List field masks:** non-empty `mask=` → `dict` rows from `list()` / `list_iter()` and from `search_by_*`. See [docs/guides/consumer-ux-list-update.md](docs/guides/consumer-ux-list-update.md), [docs/contracts.md](docs/contracts.md), shipped `contracts/list-parameters.md`.
- **Sharded parallel lists:** for large project-scoped resources, prefer per-project parallel `list()` with selective filters — [docs/contributing/list-query-performance.md](docs/contributing/list-query-performance.md#sharded-parallel-lists).
- **Graph joins across projects:** `client.Query.Project.count_*` / `collect_*` and custom `client.Query.execute` joins — POST namespace is grouped per wire path automatically; validate with `validate_sample` before scale; see [docs/guides/query-recipes.md](docs/guides/query-recipes.md).
- **Evidence vs inference:** Separate API rows, workflow artifacts, and cited spec paths from heuristic or partial conclusions. Mark guesses as **Inferred:**; for SDK/API failure playbooks use skill **endor-troubleshoot-sdk** (maintainers: [docs/contributing/troubleshooting.md](docs/contributing/troubleshooting.md)).
- **Client concurrency:** One `Client` per credential set; thread-safe session with blocking I/O — see [docs/contracts.md](docs/contracts.md#concurrency-and-transport-retries).

## Bootstrap

| Need | Approach |
| ---- | -------- |
| API + workflow CLIs | **SDK-only** — no `.endorlabs-context/` |
| INDEX / MANIFEST / skills without cwd writes | `agent_knowledge_index_path()`, `agent_knowledge_manifest()` (wheel) |
| Cwd-relative skills + optional platform mirror | `endorlabs.init()` or `uv run endor-context` |
| IDE skill mirrors | `init(sync_skills="cursor")` / `"claude"` / `"both"` after materialization |

Pick the shallowest depth:

1. **SDK-only** — `Client(...)` only.
2. **Wheel-only** — `agent_knowledge_index_path()` → `INDEX.md`; `agent_knowledge_manifest()` for skill paths. No auth, no cwd writes.
3. **Local materialization** — `init()` copies agent knowledge to `.endorlabs-context/sdk/` by default. Optional OpenAPI/user-docs under `.endorlabs-context/platform/` (`[docs]` extra for user docs). Full option list: [CONTRIBUTORS.md — Optional: sync external docs](CONTRIBUTORS.md#optional-sync-external-docs).

After materialization, read **INDEX.md** → **MANIFEST.json** → `skills/<id>/SKILL.md`. Non-Cursor harnesses: prepend `agent_knowledge_bootstrap_paths()`. Workflow outputs: `.endorlabs-context/workspace/` (shipped rule `rules/endor-workspace-layout.md`).

Consumer projects should **gitignore** `.endorlabs-context/`. Print the entry: `uv run endor-context --print-gitignore-line`. Agents must **ask the user** to add it — do not edit `.gitignore` automatically.

### Agent knowledge naming

| Layer | Path / module |
| ----- | ------------- |
| Authoring (repo) | `agent-knowledge/` |
| Shipped (wheel) | `src/endorlabs/agent_knowledge/` → `endorlabs.agent_knowledge` |
| Materialized (runtime) | `.endorlabs-context/sdk/` |

Maintainers editing authoring: `uv run python devtools/sync_agent_knowledge.py` — see [repository-layout.md](docs/contributing/repository-layout.md).

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
| [`.endorlabs-context/`](.endorlabs-context/) | Gitignored — `sdk/`, `platform/`, `workspace/` |

**Workflows** = code in `src/endorlabs/workflows/`. **Skills** = playbooks in the shipped bundle. Catalog: `MANIFEST.json` → `workflows[]`. Full map: [docs/contributing/repository-layout.md](docs/contributing/repository-layout.md).

## Skills and handoffs

**Discovery:** `.endorlabs-context/sdk/INDEX.md` → `MANIFEST.json` → `skills/`; or wheel via `agent_knowledge_index_path()`. Authoring index (maintainers): [agent-knowledge/README.md](agent-knowledge/README.md).

Common entry skills: **endor-auth-setup**, **endor-retrieve-scan-results**, **endor-troubleshooting-scans**, **endor-troubleshoot-sdk**, **endor-troubleshoot-authlog**. Full list: `MANIFEST.json` → `skills[]`.

Skills compose with handoffs — [agent-knowledge/schema/README.md — Skill composition](agent-knowledge/schema/README.md#skill-composition-and-handoffs).

## Further reading

| Topic | Location |
| ----- | -------- |
| Doc index | [docs/README.md](docs/README.md) |
| Examples + browser auth | [docs/guides/examples.md](docs/guides/examples.md) |
| Generated resource matrix | [docs/generated-reference/resources.md](docs/generated-reference/resources.md) |
| SDK layers (contributors) | [docs/contributing/architecture.md](docs/contributing/architecture.md) |
| Local OpenAPI + user docs | `.endorlabs-context/platform/` after bootstrap |
| Platform docs (online) | <https://docs.endorlabs.com/> |
| Troubleshooting / surface extension | skills **endor-troubleshoot-sdk**, **endor-implement-sdk-resource** |

---

Behavioral invariants also live in shipped `rules/` and `contracts/` (wheel or `.endorlabs-context/sdk/`). Maintainer setup: [CONTRIBUTORS.md](CONTRIBUTORS.md).
