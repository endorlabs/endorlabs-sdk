# Endor Labs SDK: AI Agent Integration Guide

> This file is auto-loaded as workspace context for AI agents. It covers architecture, rules, skills, and reference links. For consumer usage see [README.md](README.md). For contributor setup see [CONTRIBUTORS.md](CONTRIBUTORS.md).

## Consuming the SDK

See [README.md](README.md) for installation, configuration, and quick start. Entry point: `endorlabs.Client(tenant="...")`. Key patterns: `client.<ResourceKind>.list()`, `.get()`, `.create()`, `.update()`, `.delete()` where `<ResourceKind>` is **PascalCase** and matches `endorctl api … --resource` (see [docs/contracts.md](docs/contracts.md) — Canonical naming).

```python
import endorlabs

# Example: resource-oriented client with default namespace
client = endorlabs.Client(tenant="tenant.namespace")
namespaces = client.Namespace.list(traverse=True)
projects = client.Project.list(max_pages=2)
```

### Agent notes: projects, findings, and workflows

These apply across tenants and skills; prefer them before assuming `lookup`, `main`, or full-tenant sweeps.

- **Ambiguous project URL:** The same `meta.name` (e.g. identical GitHub URL) may be registered as **multiple** `Project` resources under different child namespaces. `Project.lookup(name=...)` can raise **`AmbiguousError`**. Use `Project.list` with `traverse=True` (and pick `tenant_meta.namespace`), pass an explicit **namespace** to resolution CLIs, or use the **project UUID** from the UI/API.
- **Project-scoped list namespace:** With `Client(tenant=<estate_root>)` and default `traverse=False`, `.list()` hits **only that path segment** — not child namespaces where projects usually live. **Resolve `Project` first**, then pass **`namespace=project.namespace`** on every project-scoped list (`Finding`, `ScanResult`, `PackageVersion`, `DependencyMetadata`). Empty rows often mean **wrong namespace**, not missing data. Use `traverse=True` for **discovery** (`Project.list`); do not rely on implicit client namespace for project RCA. See [docs/contracts.md](docs/contracts.md) (Namespace scoping).
- **Finding branch field:** `spec.source_code_version.ref` is **not** always `refs/heads/main`; it may be a **short branch name** (e.g. default branch label only). Use `RepositoryVersion.list` for the project, or list findings **without** a branch filter first, then narrow once you know stored ref values.
- **Tenant-wide troubleshooting:** `python -m endorlabs.workflows.troubleshooting_scans.fetch_scan_results --all-projects` is **O(projects × scans)** and can run a long time. Prefer **project-scoped** `--project-name` / `--project-uuid` for interactive RCA; reserve all-projects for batch or narrow `--limit` / `--status-filter` windows.
- **Relationship map coverage:** `relationships.map` builds producer edges from a **bounded** `PackageVersion` list (`max_pages` × `page_size`). If `dependency_row_count` is zero, distinguish **unscanned consumers / wrong list namespace** from **pagination truncation** before raising caps (ask before “fetch everything”).
- **List deserialization vs API drift:** Rarely, `client.*.list()` may fail with Pydantic validation on a field the API populated differently than the shipped model (**ServerError** / validation details). That is a **model-sync** or payload-tolerance issue—see **troubleshoot-sdk** and `devtools/sync/`, not something to fix by changing query parameters alone.
- **List field masks (`list_parameters.mask` / facade `mask=`):** The API documents `list_parameters.mask` as a comma-separated **field subset** to return (see local OpenAPI: `list_parameters.mask` — *“List of fields to return (all fields are returned by default).”*). It does **not** define a separate sparse list-row schema. When **no** mask is set (or `mask` is empty / whitespace-only after strip), `client.*.list()` / `list_iter()` return full **Pydantic** resource models as today. When a **non-empty** mask is in effect after the same `ListParameters` merge as `list()`, each row is a shallow-copied **`dict[str, Any]`** (wire JSON shape)—no client-side model construction—so sparse payloads never hit nested required-field validation. **`lookup()`** always returns a typed model: it raises **`ValueError`** if an effective non-empty mask is present; use **`list()`** / **`list_iter()`** for masked dict rows. This is a **breaking change** for callers that passed `mask=` and assumed typed models; migrate with `isinstance(row, dict)` or omit `mask` when you need models. See [docs/guides/consumer-ux-list-update.md](docs/guides/consumer-ux-list-update.md) (filter vs mask) and [docs/changelog.md](docs/changelog.md). Sort + deep pagination constraints are separate; see [docs/rules-of-engagement/list-query-performance.md](docs/rules-of-engagement/list-query-performance.md).

## Context Bootstrap (for AI Agents)

If you need full Endor Labs platform context (API spec, user docs) for agentic workflows:

```python
import endorlabs

# Bootstrap context - downloads to .endorlabs-context/
status = endorlabs.init()

# Access downloaded files
print(status.openapi_path)     # .endorlabs-context/openapiv2.swagger.json
print(status.user_docs_path)   # .endorlabs-context/docs/
print(status.user_docs_count)  # number of docs downloaded
```

**Requirements:**
- Authentication: `ENDOR_API_CREDENTIALS_KEY` + `ENDOR_API_CREDENTIALS_SECRET` env vars (or `ENDOR_TOKEN`)
- Dependencies: `pip install endorlabs-sdk[context]`

### Fresh-clone bootstrap

For a repo-local agent session after `git clone`, the SDK consumes **process env / `.env` only**; `endorctl init` does not automatically populate SDK auth.

1. Install the repo with optional extras as needed:
   - `uv sync --extra context` — local OpenAPI/docs bootstrap (`endorlabs.init()`)
   - `uv sync --extra tabular` — DataFrame/Parquet export (`endorlabs.utils.tabular`)
   - `uv sync --extra context --extra tabular` — typical agent + reporting setup
2. Establish credentials in `.env` using one of:
   - API key auth: write `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`, and optional `ENDOR_NAMESPACE`
   - Browser token refresh: `uv run python devtools/refresh_token_to_dotenv.py --env-file .env` (writes `ENDOR_TOKEN` to `.env`)
3. Verify auth before any heavier workflow:
   - `uv run --env-file .env python -c "import endorlabs; print(endorlabs.Client().whoami())"`
4. Bootstrap local context:
   - `uv run --env-file .env python -c "import endorlabs; endorlabs.init()"`

**Options:**
- `output_dir`: Where to save files (default: `.endorlabs-context`)
- `include_openapi`: Download API spec (default: True)
- `include_user_docs`: Download user docs (default: True)
- `max_pages`: Limit user doc pages (default: all)
- `force`: Re-download even if files exist (default: False)
- `sync_skills`: Mirror `skills-src/` into `.cursor/skills/`, `.claude/skills/`, or both (`none`, `cursor`, `claude`, `both`; default: `none`)

This is the recommended way for agents to bootstrap Endor Labs context before performing platform administration tasks.

## Architecture

Two-layer, registry-driven design. The same pattern applies to all resources.

- **Layer 1 — Transport:** `APIClient` in `src/endorlabs/api_client.py`. HTTP, auth, retries only.
- **Layer 2 — Resource surface:** `Client` in `src/endorlabs/client_surface.py` exposes resource facades built from the registry. At runtime these are `ResourceRuntimeFacade[T]` instances (with `ResourceFacade` kept as a backward-compatible alias); for static analysis the generated stub (`client_surface.pyi`) provides per-resource typed classes (e.g. `_ProjectFacade`) that expose only supported methods with concrete return types. The `scope` property (`None`, `"oss"`, `"system"`) is set per-resource from the registry and controls namespace resolution.
- **Registry adapter:** `endorlabs.registry` builds `ResourceEntry(...)` values from generated runtime contract data in `src/endorlabs/generated/registry_contract.py`, applies explicit overrides in `src/endorlabs/registry_overlay.py`, and can append narrowly scoped experimental facades when the generated contract has not caught up yet.
- **Pydantic models:** OpenAPI-aligned types in `src/endorlabs/generated/models/` (model-sync); hand-written resource modules under `src/endorlabs/resources/`; occasional shared types in `src/endorlabs/models/`. No HTTP or registry logic in models. CRUD/list execution lives in `BaseResourceOperations` (via facades), not module-level CRUD wrappers.

For the full rules, see [docs/rules-of-engagement/architecture.md](docs/rules-of-engagement/architecture.md).

## Critical Project Rules

- **Canonical naming:** `tenant.namespace.child` only; no UUIDs in paths.
- **Environment variables:** Do not invent names for credentials or SDK settings. Use only variables documented in [README.md](README.md), [CONTRIBUTORS.md](CONTRIBUTORS.md), this guide (including bootstrap above), or in official Endor Labs product/API documentation—and in the local OpenAPI download (`.endorlabs-context/openapiv2.swagger.json`) when it defines the same purpose. Bearer refresh via `devtools/refresh_token_to_dotenv.py` updates **`ENDOR_TOKEN`** only.
- **Env and security:** Credentials via env; run `endorctl scan` before code changes.
- **Client resource attributes (endorctl parity):** `client.<Kind>` uses **PascalCase** matching `endorctl api … --resource <Kind>` (same as endorctl’s resource syntax). The only non-registry helper on `Client` is **`ScanLogs`** — for fetching log lines; **`ScanLogRequest`** remains the endorctl-aligned resource for scan log *requests*. SDK-only facades use `CustomFacadeEntry` in `registry.py` (including `pyi_*` fields for stub generation); see [docs/contracts.md](docs/contracts.md) (Canonical naming — Custom facades).
- **Return types:** `.get()` and `.lookup()` return `Resource | None`. `.list()` and `.list_iter()` return `list[Resource]` unless a non-empty `mask=` is in effect, then `list[dict[str, Any]]` (see list field masks above). `.create()` and `.update()` return typed models.
- **Field aliasing:** Follows a three-tier rule set (syntax collisions, spec case, semantic renames); see [docs/contracts.md](docs/contracts.md) (Models and API parity -> Field aliasing).
- **Create/update:** Common create/update args may be exposed as explicit optional facade kwargs; validation remains in the resource’s builder and model; the model is the single source of truth for mutable and immutable fields.
- **F() operator semantics:** Import: `from endorlabs import F`. `F().matches(pattern)` is for **string** substring/regex matching on scalar fields (e.g. `F("meta.name").matches("endor-sdk")`). `F().contains(value)` is for **array** membership checks on list fields (e.g. `F("spec.finding_tags").contains("FINDING_TAGS_REACHABLE_FUNCTION")`). Using `contains` on a scalar string field will silently return zero results. The `filter=` parameter on `.list()` accepts `str | FilterExpression | None`.
- **Stdout hygiene:** Production SDK modules under `src/endorlabs/**` must not use `print()`. Use structured logging; keep any `print()` allowances limited to explicit demo entrypoints.
- **Typing policy boundary:** Public SDK surfaces are strict-typed; internal modules follow a staged strictness ratchet (unknown-type diagnostics move from `none` -> `warning` -> `error` by root).

## Automation

Ruff (style, imports, docstrings) and Pyright (typing) are configured in [pyproject.toml](pyproject.toml). CI runs `ruff check .`, `ruff format --check`, `pyright`, `pytest`. Run the same commands locally before pushing. Public API modules are strict-typed; internal roots are tightened incrementally via the pyright execution-environment ratchet. For the exact command list, see [.github/workflows/ci-pr-main.yml](.github/workflows/ci-pr-main.yml).

Commits targeting `main` and `dev` must keep a clean bill-of-health in security scanning: `.github/workflows/ci-pr-main.yml` includes a dedicated Endor Labs CI security scan job (OIDC auth + PR review comments from API findings + SCA/Secrets/SAST/AI SAST), and changes should not merge with unresolved policy-breaking findings under current enforcement settings.

Model-sync drift is enforced by **pre-push hooks** and **CI PR Main** (`--verify-upstream-only` on lint; ephemeral generation for tests). Regenerate committed artifacts in the PR that needs them: `uv run python devtools/model_sync.py --fetch-spec --generate-stubs --generate-reference-docs`. See [docs/rules-of-engagement/docs-drift-workflow.md](docs/rules-of-engagement/docs-drift-workflow.md).

**Maintainer commands** (fetch spec, regenerate, compact deltas): [devtools/sync/README.md](devtools/sync/README.md).

## Repository-Scoped Rules (`.cursor/rules/`)

Git-tracked Cursor rules (use **@rule** in chat or rely on glob/always-apply):

| Rule | When it applies |
|------|------------------|
| **local-context.mdc** | Always — local-first research: `.endorlabs-context/` docs and OpenAPI before the web |
| **docs-skillbase-consistency.mdc** | When editing `**/*.{md,mdc}` — keep docs aligned with `skills-src/`, generated reference, and workflow/CLI inventory |

Patterns for LIST/UPDATE, architecture, security, TDD, and code review live in [docs/rules-of-engagement/](docs/rules-of-engagement/README.md) (not separate `.mdc` files). For API workflow guidance, use **implement-sdk-resource**; for failures, **troubleshoot-sdk** or [docs/rules-of-engagement/troubleshooting.md](docs/rules-of-engagement/troubleshooting.md). Python examples: canonical repo `endorlabs/endorlabs-sdk`; no customer names, UUIDs, or tenant-specific literals.

## Project Structure

```
src/endorlabs/
├── api_client.py              # Layer 1: transport
├── client_surface.py          # Layer 2: Client entry
├── client_surface.pyi         # Generated per-resource facade stub (IDE)
├── facade.py                  # ResourceRuntimeFacade, ScanLogsFacade, …
├── registry.py                # Registry adapter (+ registry_overlay.py)
├── generated/
│   ├── registry_contract.py   # model-sync runtime contract
│   └── models/                # OpenAPI-aligned Pydantic shards
├── resources/                 # Hand-written resource modules + builders
├── models/                    # Small shared hand-written models
├── core/                      # exceptions, F/filter, ListParameters
├── operations/                # BaseResourceOperations
├── utils/                     # model_validation, schema_drift, parallel, …
├── context/                   # endorlabs.init / bootstrap
├── workflows/                 # Composable orchestration (no LLM in core)
└── tools/                     # Standalone utilities (e.g. dependency_explorer)
```

> **Stub regeneration:** `uv run python devtools/generate_client_stub.py` rebuilds `client_surface.pyi` from the registry. Run after adding resources or changing facade method signatures.

- **Tools:** `endorlabs.tools` — standalone utilities (e.g. `dependency_explorer`).
- **Workflows:** `endorlabs.workflows` — tenant-facing orchestration (no LLM calls): `agent_context` (context bundles), `callgraph`, `troubleshooting_scans`, `relationships`, `analytics`, `semgrep`, `findings`, `platform`, `notifications`, `dependencies`, `projects`, `reachability`. Optional CLIs: `endor-agent-context`, `endor-callgraph-search`, `endor-semgrep-inventory`, `endor-reachability-context`, `endor-analytics-export-deps` (see `[project.scripts]` in [pyproject.toml](pyproject.toml)).
- **Internal:** `core`, `operations`, `utils`, `context` (see tree above).

## Reference — External

- **User docs (local):** `.endorlabs-context/docs/` — pre-downloaded mirror of docs.endorlabs.com, refreshed by `endorlabs.init()`. **Search here first** using Glob + Read. See `local-context.mdc` for the research protocol.
- **User docs (online):** <https://docs.endorlabs.com/> — fallback only when local docs do not cover the topic.
- **API spec (local):** `.endorlabs-context/openapiv2.swagger.json` — use for required/optional fields, types, enums, read-only markers. **Grep this file** to confirm field formats before implementing.
- **API spec (online):** <https://api.endorlabs.com/download/openapiv2.swagger.json> — fallback for freshness checks.
- **Bootstrap:** Create the gitignored `.endorlabs-context/` folder: `uv sync --extra context` then `import endorlabs; endorlabs.init()`. See [Context Bootstrap](#context-bootstrap-for-ai-agents) for options.

## Reference — In-Repo

- **Index:** [docs/README.md](docs/README.md) — what lives where.
- **Contracts:** [docs/contracts.md](docs/contracts.md) — naming, traverse, ListParameters, OpenAPI path, models and API parity, update_mask, errors.
- **Design notes:** [docs/design.md](docs/design.md) — rationale and tradeoffs for SDK behavior.
- **Consumer UX (list/update):** filter vs mask, flat kwargs — [docs/contracts.md](docs/contracts.md), [docs/guides/consumer-ux-list-update.md](docs/guides/consumer-ux-list-update.md).
- **Reference:** [docs/reference/README.md](docs/reference/README.md) (curated index and stable landing pages), [docs/generated-reference/resources.md](docs/generated-reference/resources.md) (canonical generated operations matrix), [docs/generated-reference/api-surfaces.md](docs/generated-reference/api-surfaces.md), [docs/generated-reference/create-update-payloads.md](docs/generated-reference/create-update-payloads.md), [docs/reference/namespace.md](docs/reference/namespace.md) (list/get/create/update/delete).
- **Guides:** [docs/guides/README.md](docs/guides/README.md); consumer-ux-list-update, retrieving-scan-results.
- **Rules of engagement:** [docs/rules-of-engagement/README.md](docs/rules-of-engagement/README.md); api-validation, resource-implementation, troubleshooting, docs-drift-workflow.

## Agent Skills (On-Demand Workflows)

Skills are modular, on-demand workflow packages that agents activate when a task matches. Unlike `.cursor/rules/` (always-on context), skills are read only when triggered. They follow the cross-compatible format supported by both Cursor and Anthropic Agent Skills.

| Skill | When to use |
|-------|-------------|
| [analytics-estate-dependencies](skills-src/analytics-estate-dependencies/) | Estate DependencyMetadata aggregates, version cardinality, single-package export, CVE remediation comparison | `endorlabs.workflows.analytics`; `endor-analytics-export-deps` |
| [custom-sast-rules](skills-src/custom-sast-rules/) | Threat modeling, authoring, or importing OpenGrep/Semgrep rules |
| [dependency-finding-provenance](skills-src/dependency-finding-provenance/) | Trace vulnerability/dependency lineage across Findings, PackageVersions, and SBOM artifacts; fixed vs present at branch/commit scope |
| [dependency-provenance](skills-src/dependency-provenance/) | Resolve package-version lineage by manifest path and ref/sha; direct vs transitive introduction |
| [project-agent-context](skills-src/project-agent-context/) | Multi-pass project context: PV index, targeted hydration, optional call-graph sweep; read `MULTIPASS_LLM_CONTRACT.md` for manifest/escalation semantics (`endorlabs.workflows.agent_context`) |
| [map-project-dependency-relationships](skills-src/map-project-dependency-relationships/) | Namespace-wide project-to-project dependency graph (JSON) via `python -m endorlabs.workflows.relationships.map` |
| [fetch-and-search-call-graph](skills-src/fetch-and-search-call-graph/) | Fetch, decode, and search project call graph artifacts (`endorlabs.workflows.callgraph`; `endor-callgraph-search` for local JSON search) |
| [implement-sdk-resource](skills-src/implement-sdk-resource/) | Adding a new resource to the SDK (models, operations, registry, tests) |
| [retrieve-scan-results](skills-src/retrieve-scan-results/) | Querying projects, scan results, and findings |
| [reachability-provenance](skills-src/reachability-provenance/) | Triaging conflicting reachability signals on findings (dependency vs function reachability, callpath attribution) |
| [sso-integration-validation-troubleshooting](skills-src/sso-integration-validation-troubleshooting/) | Customer SSO setup, validation, and claims-to-namespace troubleshooting |
| [troubleshooting-scans](skills-src/troubleshooting-scans/) | Scan regressions: anomalous ScanResults, ScanLogs, result/log diffs via `python -m endorlabs.workflows.troubleshooting_scans.*` |
| [troubleshoot-sdk](skills-src/troubleshoot-sdk/) | Debugging 404s, 500s, namespace mismatches, test failures |
| [troubleshoot-authlog](skills-src/troubleshoot-authlog/) | AuthenticationLog, AuthorizationPolicy, and SSO/login troubleshooting |
| [validate-policy](skills-src/validate-policy/) | Validate policies against project findings via PolicyValidation API (`endorlabs.workflows.policies.validate`) |

Setup and usage: [skills-src/README.md](skills-src/README.md) (`.cursor/skills` is the mirrored runtime path used by Cursor).

CI runs these (except optional endorctl); include pyright. Unit tests run without credentials; integration tests require `ENDOR_*` env vars.

---

Index for AI agents; in-repo behavior and patterns are defined by `.cursor/rules/*.mdc`, [docs/rules-of-engagement/](docs/rules-of-engagement/README.md), skills above, and the linked docs.
