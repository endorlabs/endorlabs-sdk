# Endor Labs SDK: AI Agent Integration Guide

> Auto-loaded workspace context for AI agents. Consumer install/quick start: [README.md](README.md). Contributor setup: [CONTRIBUTORS.md](CONTRIBUTORS.md).

## Consuming the SDK

**Default:** `endorlabs.Client(...)` without `init()` — sufficient for API calls and `endorlabs.workflows` CLIs.

**Bootstrap when:** the agent reads skills/rules/contracts from disk, greps offline OpenAPI, or writes under `.endorlabs-context/workspace/`. See [SDK-only vs agent bootstrap](#sdk-only-vs-agent-bootstrap).

API patterns, env vars, and quick start: [README.md](README.md). Normative SDK behavior: [docs/contracts.md](docs/contracts.md).

### Agent notes: projects, findings, and workflows

Prefer these before assuming `lookup`, `main`, or full-tenant sweeps. Shipped bootstrap rules (`endor-namespace-scoping`, `endor-list-query-performance`, …) expand the same topics — load via `agent_knowledge_bootstrap_paths()` or `.endorlabs-context/sdk/rules/`.

- **Ambiguous project URL:** identical `meta.name` may exist under multiple child namespaces → `AmbiguousError` on `Project.lookup`. Use `Project.list(traverse=True)`, explicit namespace, or project UUID.
- **Project-scoped list namespace:** resolve `Project` first; pass `namespace=project.namespace` on `Finding`, `ScanResult`, `PackageVersion`, `DependencyMetadata`. Empty rows often mean wrong namespace, not missing data.
- **Finding branch field:** `spec.source_code_version.ref` may be a short branch name, not `refs/heads/main`. List findings without a branch filter first, or use `RepositoryVersion.list`.
- **Tenant-wide scan fetch:** `fetch_scan_results --all-projects` is O(projects × scans). Prefer `--project-name` / `--project-uuid` for interactive RCA.
- **Relationship map:** `relationships.map` uses a bounded `PackageVersion` list — distinguish wrong namespace / unscanned consumers from pagination truncation before raising caps.
- **List deserialization vs API drift:** Pydantic validation failures on `list()` → model-sync / payload tolerance (**endor-troubleshoot-sdk**, `devtools/sync/`), not query-parameter tweaks alone.
- **List field masks:** non-empty `mask=` → `dict` rows from `list()` / `list_iter()`; `lookup()` raises `ValueError` if masked. Details: [docs/guides/consumer-ux-list-update.md](docs/guides/consumer-ux-list-update.md), [docs/contracts.md](docs/contracts.md), shipped `contracts/list-parameters.md`.

## SDK-only vs agent bootstrap

| Need | Approach |
| ---- | -------- |
| API + workflow CLIs | **SDK-only** — no `.endorlabs-context/` |
| INDEX / MANIFEST / skills without cwd writes | `agent_knowledge_index_path()`, `agent_knowledge_manifest()` (wheel) |
| Cwd-relative skills + optional platform mirror | `endorlabs.init()` or `uv run endor-context` |
| IDE skill mirrors | `init(sync_skills="cursor")` / `"claude"` / `"both"` after materialization |

Consumer projects should **gitignore** `.endorlabs-context/`. Print the entry: `uv run endor-context --print-gitignore-line`. Agents must **ask the user** to add it — do not edit `.gitignore` automatically.

### Naming

| Layer | Path / module |
| ----- | ------------- |
| Authoring (repo) | `agent-knowledge/` |
| Shipped (wheel) | `src/endorlabs/agent_knowledge/` → `endorlabs.agent_knowledge` |
| Materialized (runtime) | `.endorlabs-context/sdk/` |

Edit `agent-knowledge/` → `uv run python devtools/sync_agent_knowledge.py` → commit `src/endorlabs/agent_knowledge/`.

## Context bootstrap (for AI agents)

Pick the shallowest depth:

1. **SDK-only** — `Client(...)` only.
2. **Wheel-only** — `agent_knowledge_index_path()` → `…/agent_knowledge/INDEX.md`; `agent_knowledge_manifest()` for skill paths. No auth, no cwd writes.
3. **Local materialization** — `init()` copies agent knowledge to `.endorlabs-context/sdk/` by default (`include_agent_knowledge=True`, no auth). Pass `include_openapi=True` / `include_user_docs=True` for platform downloads (`[docs]` extra required for user docs).

After materialization, read **INDEX.md** → **MANIFEST.json** → `skills/<id>/SKILL.md`. Non-Cursor harnesses: prepend `agent_knowledge_bootstrap_paths()`. Workflow outputs: `.endorlabs-context/workspace/` (see shipped `contracts/workspace-layout.md`).

**Auth:** OpenAPI/user-docs download only — `ENDOR_TOKEN` or API key/secret. Agent knowledge materialization requires no auth.

**`init()` / `endor-context` options:** `output_dir`, `include_openapi` (default False), `include_user_docs` (default False), `include_agent_knowledge` (default True), `max_pages`, `force`, `sync_skills` (`none` \| `cursor` \| `claude` \| `both`, default `none`). Bare `endor-context` materializes agent knowledge; add `--sync-openapi` / `--sync-user-docs` explicitly.

### Fresh-clone bootstrap (this repo)

1. `uv sync --extra docs --extra tabular` as needed
2. Credentials in `.env` — API keys or `uv run --env-file .env python devtools/refresh_token_to_dotenv.py` (`ENDOR_AUTH_METHOD`, `--admin`, `--sso`, `-n`)
3. Verify: `uv run --env-file .env python -c "import endorlabs; print(endorlabs.Client().whoami())"`
4. Optional full mirror: `endorlabs.init(include_openapi=True, include_user_docs=True)`
5. **Maintainers editing agent knowledge:** `uv run python devtools/sync_agent_knowledge.py` (CI/pre-push `--verify`)

## Critical project rules

- **Canonical naming:** `tenant.namespace.child`; no UUIDs in namespace paths.
- **Environment variables:** only names in [README.md](README.md), [CONTRIBUTORS.md](CONTRIBUTORS.md), product docs, or local OpenAPI. `refresh_token_to_dotenv.py` writes **`ENDOR_TOKEN`** only.
- **Env and security:** credentials via env; run `endorctl scan` before code changes.
- **Client facades:** `client.<Kind>` PascalCase = `endorctl api … --resource <Kind>`. Non-registry helper: **`ScanLogs`** (log lines); **`ScanLogRequest`** for log-request CRUD. Custom facades: [docs/contracts.md](docs/contracts.md).
- **Return types:** `.get()` / `.lookup()` → typed model or raise; `.list()` → models unless non-empty `mask=` → `dict` rows.
- **F():** `matches()` on strings; `contains()` on array fields only.
- **Stdout hygiene:** no `print()` in `src/endorlabs/**` except explicit CLI entrypoints.
- **Typing:** public surfaces strict-typed; internal roots ratcheted in [pyproject.toml](pyproject.toml).

Contributor CI, model-sync, and security scan gates: [CONTRIBUTORS.md](CONTRIBUTORS.md), [docs/contributing/docs-drift-workflow.md](docs/contributing/docs-drift-workflow.md), [devtools/sync/README.md](devtools/sync/README.md).

## Repository-scoped rules (`.cursor/rules/`)

| Rule | When |
| ---- | ---- |
| **Generated `endor-*.mdc`** | `endor-namespace-scoping` + `endor-list-query-performance` always-on; other bootstrap rules when globs match (`src/endorlabs/**`, `**/*.py`, `.endorlabs-context/**`, …) |
| **docs-skillbase-consistency.mdc** | Editing `**/*.{md,mdc}` |
| **agent-knowledge-authoring.mdc** | Editing `agent-knowledge/**` — [agent-knowledge/schema/README.md](agent-knowledge/schema/README.md) |

Regenerate: `uv run python devtools/sync_agent_knowledge.py`.

API workflow failures: **endor-troubleshoot-sdk** or [docs/contributing/troubleshooting.md](docs/contributing/troubleshooting.md). Surface extension: **endor-implement-sdk-resource**. Examples: canonical repo `endorlabs/endorlabs-sdk`; no customer tenants/UUIDs in git-tracked content.

## Repository layout

| Region | Role |
| ------ | ---- |
| [`agent-knowledge/`](agent-knowledge/) | Authoring — `rules/`, `contracts/`, `skills/`, `schema/` (not shipped) |
| [`src/endorlabs/agent_knowledge/`](src/endorlabs/agent_knowledge/) | Generated ship surface — `MANIFEST.json`, `workflows/entries.json` |
| [`src/endorlabs/`](src/endorlabs/) | Runtime SDK — transport, facades, workflows, `context/` |
| [`src/endorlabs/generated/`](src/endorlabs/generated/) | Model-sync — `registry_contract.py`, OpenAPI-aligned models |
| [`devtools/`](devtools/) | Maintainer automation |
| [`docs/`](docs/) | Contracts, guides, contributing playbooks |
| [`.endorlabs-context/`](.endorlabs-context/) | Gitignored runtime — `sdk/`, `platform/`, `workspace/` |
| [`.cursor/skills/`](.cursor/skills/) | Optional IDE mirror after `sync_skills` |

**Runtime rule:** read the **wheel** or **`.endorlabs-context/sdk/`** — not repo `agent-knowledge/` directly (authoring only).

## SDK runtime architecture

Two layers: **transport** (`api_client.py`) + **registry-driven facades** (`client_surface.py`, `facade.py`, `generated/registry_contract.py`). Deep dive: [docs/contributing/architecture.md](docs/contributing/architecture.md). Workflow inventory: shipped `MANIFEST.json` → `workflows`; console scripts in [pyproject.toml](pyproject.toml) `[project.scripts]`.

## Where to read next

| Topic | Location |
| ----- | -------- |
| Doc index | [docs/README.md](docs/README.md) |
| Contracts / errors / list params | [docs/contracts.md](docs/contracts.md) |
| Generated resource matrix | [docs/generated-reference/resources.md](docs/generated-reference/resources.md) |
| Local OpenAPI + user docs (after bootstrap) | `.endorlabs-context/platform/` |
| Platform docs (online fallback) | <https://docs.endorlabs.com/> |
| Contributing playbooks | [docs/contributing/README.md](docs/contributing/README.md) |

## Agent skills (on-demand workflows)

**Discovery:** materialized `.endorlabs-context/sdk/INDEX.md` → `MANIFEST.json` → `skills/`; or wheel via `agent_knowledge_index_path()`. Authoring index: [agent-knowledge/README.md](agent-knowledge/README.md) (maintainers only at runtime).

**Common entry skills:**

| Skill | When |
| ----- | ---- |
| [endor-retrieve-scan-results](agent-knowledge/skills/endor-retrieve-scan-results/) | Projects, ScanResults, Findings |
| [endor-troubleshooting-scans](agent-knowledge/skills/endor-troubleshooting-scans/) | Scan pipeline / logs / aggregate diffs |
| [endor-troubleshoot-sdk](agent-knowledge/skills/endor-troubleshoot-sdk/) | 404s, namespace mismatches, test failures |
| [endor-troubleshoot-authlog](agent-knowledge/skills/endor-troubleshoot-authlog/) | SSO / AuthenticationLog |
| [endor-implement-sdk-resource](agent-knowledge/skills/endor-implement-sdk-resource/) | Model-sync surface extension |

Full skill list and CLI/module mapping: `MANIFEST.json` → `skills[]` and `workflows[]` under `src/endorlabs/agent_knowledge/` (or materialized `sdk/`).

Skills compose with handoffs — see [agent-knowledge/schema/README.md — Skill composition](agent-knowledge/schema/README.md#skill-composition-and-handoffs) (e.g. troubleshooting-scans → retrieve-scan-results → lineage/policy skills).

---

Behavioral invariants also live in `.cursor/rules/*.mdc` (from `agent-knowledge/rules/`) and shipped `sdk/contracts/`.
