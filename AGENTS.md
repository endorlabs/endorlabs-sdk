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

**Options:**
- `output_dir`: Where to save files (default: `.endorlabs-context`)
- `include_openapi`: Download API spec (default: True)
- `include_user_docs`: Download user docs (default: True)
- `max_pages`: Limit user doc pages (default: all)
- `force`: Re-download even if files exist (default: False)

This is the recommended way for agents to bootstrap Endor Labs context before performing platform administration tasks.

## Architecture

Two-layer, registry-driven design. The same pattern applies to all resources.

- **Layer 1 — Transport:** `APIClient` in `api_client.py`. HTTP, auth, retries only.
- **Layer 2 — Resource surface:** `Client` in `client_surface.py` exposes resource facades built from the registry. At runtime these are `ResourceFacade[T]` instances; for static analysis the generated stub (`client_surface.pyi`) provides per-resource typed classes (e.g. `_ProjectFacade`) that expose only supported methods with concrete return types. The `scope` property (`None`, `"system"`, `"oss"`) is set per-resource from the registry and controls namespace resolution.
- **Registry adapter:** `endorlabs.registry` builds `ResourceEntry(...)` values from generated runtime contract data in `src/endorlabs/generated/registry_contract.py` plus explicit overrides in `src/endorlabs/registry_overlay.py`.
- **Pydantic models:** Request/response types in resource modules and `models/`. No HTTP or registry logic in models. CRUD/list execution lives in `BaseResourceOperations` (via facades), not module-level CRUD wrappers.

For the full rules, see [docs/rules-of-engagement/architecture.md](docs/rules-of-engagement/architecture.md).

## Critical Project Rules

- **Canonical naming:** `tenant.namespace.child` only; no UUIDs in paths.
- **Env and security:** Credentials via env; run `endorctl scan` before code changes.
- **Client resource attributes (endorctl parity):** `client.<Kind>` uses **PascalCase** matching `endorctl api … --resource <Kind>` (same as endorctl’s resource syntax). The only non-registry helper on `Client` is **`ScanLogs`** — for fetching log lines; **`ScanLogRequest`** remains the endorctl-aligned resource for scan log *requests*. SDK-only facades use `CustomFacadeEntry` in `registry.py` (including `pyi_*` fields for stub generation); see [docs/contracts.md](docs/contracts.md) (Canonical naming — Custom facades).
- **Return types:** Functions return typed models: `Resource | None` or `list[Resource]`.
- **Field aliasing:** Follows a three-tier rule set (syntax collisions, spec case, semantic renames); see [docs/contracts.md](docs/contracts.md) (Models and API parity -> Field aliasing).
- **Create/update:** Common create/update args may be exposed as explicit optional facade kwargs; validation remains in the resource’s builder and model; the model is the single source of truth for mutable and immutable fields.
- **F() operator semantics:** Import: `from endorlabs import F`. `F().matches(pattern)` is for **string** substring/regex matching on scalar fields (e.g. `F("meta.name").matches("endor-sdk")`). `F().contains(value)` is for **array** membership checks on list fields (e.g. `F("spec.finding_tags").contains("FINDING_TAGS_REACHABLE_FUNCTION")`). Using `contains` on a scalar string field will silently return zero results. The `filter=` parameter on `.list()` accepts `str | FilterExpression | None`.
- **Stdout hygiene:** Production SDK modules under `src/endorlabs/**` must not use `print()`. Use structured logging; keep any `print()` allowances limited to explicit demo entrypoints.
- **Typing policy boundary:** Public SDK surfaces are strict-typed; internal modules follow a staged strictness ratchet (unknown-type diagnostics move from `none` -> `warning` -> `error` by root).

## Automation

Ruff (style, imports, docstrings) and Pyright (typing) are configured in [pyproject.toml](pyproject.toml). CI runs `ruff check .`, `ruff format --check`, `pyright`, `pytest`. Run the same commands locally before pushing. Public API modules are strict-typed; internal roots are tightened incrementally via the pyright execution-environment ratchet. For the exact command list, see [.github/workflows/ci-pr-main.yml](.github/workflows/ci-pr-main.yml).

Model-sync automation is intentionally split:

- **Detector workflow:** [.github/workflows/model-sync-detector.yml](.github/workflows/model-sync-detector.yml) detects upstream version/spec drift and dispatches sync events.
- **Sync + PR workflow:** [.github/workflows/model-sync-pr.yml](.github/workflows/model-sync-pr.yml) regenerates canonical artifacts and opens/updates the bot PR branch.
- **Required CI gate:** [.github/workflows/ci-pr-main.yml](.github/workflows/ci-pr-main.yml) validates all PRs (including bot-generated PRs).

## Repository-Scoped Rules (`.cursor/rules/`)

Cursor rules apply when working here. Use **@rule** in chat or rely on glob/always-apply:

| Rule | When it applies |
|------|------------------|
| **tdd.mdc** | Always (TDD protocol, quality gate, zero-regression requirement) |
| **code-review.mdc** | Always (agent self-review checklist before committing) |
| **local-context.mdc** | Always (local-first research: check `.endorlabs-context/` docs and API spec before going online) |
| **security.mdc** | When editing `src/endorlabs/**` (credential handling, network safety, dangerous ops) |
| **architecture.mdc** | When editing `client_surface.py`, `facade.py`, `registry.py`, or adding resources to the Client |
| **resource-patterns.mdc** | When editing `src/endorlabs/resources/**/*.py` |

Details (patterns, LIST/UPDATE, errors) live in those rules and in the docs below. For API workflow guidance, use the **implement-sdk-resource** skill. For troubleshooting, use the **troubleshoot-sdk** skill or see [docs/rules-of-engagement/troubleshooting.md](docs/rules-of-engagement/troubleshooting.md).

## Project Structure

```
endorlabs/
├── api_client.py        # Transport only (Layer 1)
├── client_surface.py    # Client facade (Layer 2 entry point)
├── client_surface.pyi   # Generated stub: per-resource typed facades for IDE DX
├── facade.py            # ResourceFacade, _ListableFacade, ScanLogsFacade
├── registry.py          # Registry of resources exposed on Client
├── resources/           # Pydantic models, convenience functions, and resource-specific logic
└── models/
```

> **Stub regeneration:** `uv run python scripts/generate_client_stub.py` rebuilds `client_surface.pyi` from the registry. Run after adding resources or changing facade method signatures.

- **Tools:** `endorlabs.tools` — standalone utilities (e.g. `dependency_explorer`).
- **Internal:** utils (model_validation, schema_drift), operations.

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
| [custom-sast-rules](.cursor/skills/custom-sast-rules/) | Threat modeling, authoring, or importing OpenGrep/Semgrep rules |
| [implement-sdk-resource](.cursor/skills/implement-sdk-resource/) | Adding a new resource to the SDK (models, operations, registry, tests) |
| [retrieve-scan-results](.cursor/skills/retrieve-scan-results/) | Querying projects, scan results, and findings |
| [troubleshoot-sdk](.cursor/skills/troubleshoot-sdk/) | Debugging 404s, 500s, namespace mismatches, test failures |

Setup and usage: [.cursor/skills/README.md](.cursor/skills/README.md).

## Essential Commands

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest tests/unit/ -m "not slow and not long"
uv run pytest tests/integration/ -m "not long"
endorctl scan
```

CI runs these (except optional endorctl); include pyright. Unit tests run without credentials; integration tests require `ENDOR_*` env vars.

---

Index for AI agents; in-repo behavior and patterns are defined by `.cursor/rules/*.mdc` and the linked docs.

