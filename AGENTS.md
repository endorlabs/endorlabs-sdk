# Endor Cockpit: AI Agent Integration Guide

> **Endor Cockpit**: Navigate the Endor Labs platform with tactical precision. This guide is the index for AI agents; behavior is defined by `.cursor/rules` and the linked docs.

## Consuming the AF

- **Python:** 3.11+ required; CI and releases are tested on 3.13 only.
- **Install:** `uv add endor-cockpit` or, in this repo, `uv sync`.
- **Entry point:** `endorlabs.Client(tenant="...")`; then `client.namespace.list(traverse=True)`, `client.project.get(uuid)`, etc. **Create:** use `client.<resource>.create(name="...", namespace="...", ...)` (kwargs) or `create(payload=CreateXPayload(...))` (payload-based create). See [Architecture](#architecture) below.
- **Client options:** You can pass `timeout`, `content_type`, `accept_encoding`, `max_retries`, `base_url` to `Client(...)` to control transport; other APIClient options go via `**client_kwargs`. Use `content_type="application/json"` if compact responses cause validation issues.
- **Advanced / transport-only:** `APIClient()` from `endorlabs.api_client` is available for custom HTTP usage, but all resource operations should go through `Client`.
- **Errors:** `endorlabs.exceptions`; see [docs/conventions.md](docs/conventions.md) (Errors section).

```python
import endorlabs

# Example: resource-oriented client with default namespace
client = endorlabs.Client(tenant="tenant.namespace")
namespaces = client.namespace.list(traverse=True)
projects = client.project.list(max_pages=2)
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
- Dependencies: `pip install endor-cockpit[context]`

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
- **Layer 2 — Resource surface:** `Client` in `client_surface.py` exposes `ResourceFacade[T]` instances built from the registry. The `scope` parameter (`None`, `"system"`, `"oss"`) controls namespace resolution.
- **Registry:** `endorlabs.registry` — one `ResourceEntry(attr_name=..., resource_name=..., model_class=..., supported_ops=..., ...)` per resource. Adding a resource = one registry entry.
- **Pydantic models:** Request/response types in resource modules and `models/`. No HTTP or registry logic in models.

For the full rules, see [docs/rules-of-engagement/architecture.md](docs/rules-of-engagement/architecture.md).

## Critical Project Rules

- **Canonical naming:** `tenant.namespace.child` only; no UUIDs in paths.
- **Env and security:** Credentials via env; run `endorctl scan` before code changes.
- **Return types:** Functions return typed models: `Resource | None` or `list[Resource]`.
- **Field aliasing:** Follows a three-tier rule set (syntax collisions, spec case, semantic renames); see [docs/conventions.md](docs/conventions.md) (Models and API parity → Field aliasing).
- **Create/update:** Common create/update args may be exposed as explicit optional facade kwargs; validation remains in the resource’s builder and model; the model is the single source of truth for mutable and immutable fields.

## Automation

Ruff (style, imports, docstrings) and Pyright (typing) are configured in [pyproject.toml](pyproject.toml). CI runs `ruff check .`, `ruff format --check`, `pyright`, `pytest`. Run the same commands locally before pushing. Pyright enforces types in CI; public API must be fully typed (see pyproject.toml). For the exact command list, see [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Repository-Scoped Rules (`.cursor/rules/`)

Cursor rules apply when working here. Use **@rule** in chat or rely on glob/always-apply:

| Rule | When it applies |
|------|------------------|
| **endor-cockpit-core.mdc** | Always (project context and critical requirements) |
| **tdd.mdc** | Always (TDD protocol, quality gate, zero-regression requirement) |
| **code-review.mdc** | Always (agent self-review checklist before committing) |
| **security.mdc** | When editing `src/endorlabs/**` (credential handling, network safety, dangerous ops) |
| **architecture.mdc** | When editing `client_surface.py`, `facade.py`, `registry.py`, or adding resources to the Client |
| **resource-patterns.mdc** | When editing `src/endorlabs/resources/**/*.py` |
| **api-workflow.mdc** | When editing models, resources, or OpenAPI spec |
| **troubleshooting.mdc** | When debugging AF/integration failures or editing troubleshooting docs |

Details (patterns, LIST/UPDATE, errors, API workflow) live in those rules and in the docs below. Troubleshooting workflow: troubleshooting.mdc and [docs/rules-of-engagement/troubleshooting.md](docs/rules-of-engagement/troubleshooting.md).

## Project Structure

```
endorlabs/
├── api_client.py      # Transport only (Layer 1)
├── client_surface.py  # Client facade (Layer 2 entry point)
├── facade.py          # SystemResourceFacade, OssResourceFacade, ResourceFacade; delegates to BaseResourceOperations
├── registry.py        # Registry of resources exposed on Client
├── resources/         # Pydantic models, convenience functions, and resource-specific logic
└── models/
```

- **SAST analysis:** `endorlabs.sast_analysis` — finding correlation and SQL-backed analysis tools.
- **Agent:** `endorlabs.agent` — LangGraph-based agent and demo CLI (requires `[agent]` extras).
- **Tools:** `endorlabs.tools` — standalone utilities (e.g. `dependency_explorer`).
- **Internal:** utils (model_validation, schema_drift), operations.

## Reference — External

- **User docs:** <https://docs.endorlabs.com/>
- **API spec:** <https://api.endorlabs.com/download/openapiv2.swagger.json> — use for required/optional fields, types, read-only; schema drift workflow downloads to `.endorlabs-context/` in CI.
- **Advanced users (IDE context):** Create the gitignored `.endorlabs-context/` folder with spec + user docs: `uv sync --extra context` then `import endorlabs; endorlabs.init()`. See [Context Bootstrap](#context-bootstrap-for-ai-agents) above for options.

## Reference — In-Repo

- **Index:** [docs/README.md](docs/README.md) — what lives where.
- **Conventions:** [docs/conventions.md](docs/conventions.md) — naming, traverse, ListParameters, OpenAPI path, models and API parity, update_mask, errors.
- **Consumer UX (list/update):** filter vs mask, flat kwargs, spec-driven — [docs/conventions.md](docs/conventions.md), [docs/guides/consumer-ux-list-update.md](docs/guides/consumer-ux-list-update.md).
- **Reference:** [docs/reference/README.md](docs/reference/README.md) (public API, resources, namespace); [docs/reference/resources.md](docs/reference/resources.md) (operations per resource); [docs/reference/namespace.md](docs/reference/namespace.md) (list/get/create/update/delete).
- **Guides:** [docs/guides/README.md](docs/guides/README.md); consumer-ux-list-update, retrieving-scan-results.
- **Rules of engagement:** [docs/rules-of-engagement/README.md](docs/rules-of-engagement/README.md); api-validation, resource-implementation, troubleshooting, docs-drift-workflow.

## Agent Skills (On-Demand Workflows)

Skills are modular, on-demand workflow packages that agents activate when a task matches. Unlike `.cursor/rules/` (always-on context), skills are read only when triggered. They follow the cross-compatible format supported by both Cursor and Anthropic Agent Skills.

| Skill | When to use |
|-------|-------------|
| [custom-sast-rules](.cursor/skills/custom-sast-rules/) | Threat modeling, authoring, or importing OpenGrep/Semgrep rules |
| [implement-af-resource](.cursor/skills/implement-af-resource/) | Adding a new resource to the AF (models, operations, registry, tests) |
| [retrieve-scan-results](.cursor/skills/retrieve-scan-results/) | Querying projects, scan results, and findings |
| [troubleshoot-af](.cursor/skills/troubleshoot-af/) | Debugging 404s, 500s, namespace mismatches, test failures |

Setup and usage: [.cursor/skills/README.md](.cursor/skills/README.md).

## Essential Commands

```bash
uv run ruff check .
uv run ruff format .
uv run pyright
uv run pytest tests/unit/ -m "not slow"
uv run pytest tests/integration/ -m "not long"
endorctl scan
```

CI runs these (except optional endorctl); include pyright. Unit tests run without credentials; integration tests require `ENDOR_*` env vars.

## User-Scoped Rules (Optional)

For preferences that apply across all your projects (TDD, OS-agnostic scripts, consistency), see [.cursor/USER_RULES_SUGGESTION.md](.cursor/USER_RULES_SUGGESTION.md). Copy from there into **Cursor Settings → General → Rules for AI** if you want them globally.

---

Index for AI agents; in-repo behavior and patterns are defined by `.cursor/rules/*.mdc` and the linked docs.

