# Endor Cockpit: AI Agent Integration Guide

> **Endor Cockpit**: Navigate the Endor Labs platform with tactical precision. This guide is the index for AI agents; behavior is defined by `.cursor/rules` and the linked docs.

## Consuming the SDK

- **Python:** 3.11+ required; CI and releases are tested on 3.13 only.
- **Install:** `uv add endor-cockpit` or, in this repo, `uv sync`.
- **Recommended entry:** `endorlabs.Client(tenant="...")`; then `client.namespace.list(traverse=True)`, `client.project.get(uuid)`, etc. **Create:** use `client.<resource>.create(name="...", namespace="...", ...)` (kwargs) or `create(payload=CreateXPayload(...))` (power users). See [Architecture](#architecture) below.
- **Client options:** You can pass `timeout`, `content_type`, `accept_encoding`, `max_retries`, `base_url` to `Client(...)` to control transport; other APIClient options go via `**client_kwargs`. Use `content_type="application/json"` if compact responses cause validation issues.
- **Alternative:** `APIClient()` and resource modules under `endorlabs.resources` (e.g. `namespace.list_namespaces(client, "tenant.namespace")`). Same behavior; use when you need the transport only or module-level calls.
- **Errors:** `endorlabs.exceptions`; see [docs/conventions.md](docs/conventions.md) (Errors section).

```python
import endorlabs

# Recommended: resource-oriented client with default namespace
client = endorlabs.Client(tenant="tenant.namespace")
namespaces = client.namespace.list(traverse=True)
projects = client.project.list(max_pages=2)
```

```python
# Alternative: transport + module-level functions
from endorlabs.api_client import APIClient
from endorlabs.resources import namespace

client = APIClient()
namespaces = namespace.list_namespaces(client, "tenant.namespace")
```

## Architecture

The SDK uses a two-layer, registry-driven design so the same pattern applies to all resources.

- **Layer 1 — Transport:** `APIClient` in `api_client.py`. HTTP, auth, retries only. No resource concepts; no Pydantic models.
- **Layer 2 — Resource surface:** `Client` in `client_surface.py` holds default namespace and exposes resource facades (e.g. `client.namespace`, `client.project`). Each facade is a `SystemResourceFacade[T]`, `OssResourceFacade[T]`, or `ResourceFacade[T]` in `facade.py` (chosen by registry `scope`); facades resolve namespace, build `ListParameters` from kwargs, and delegate to existing module-level list/get/create/update/delete functions.
- **Registry:** Which resources exist on `Client` is defined in a single registry in `endorlabs.registry`. `Client` exposes all resources via `client.<resource>.list(...)`, `client.<resource>.get(...)`, etc. Adding a resource = one registry entry (with optional `scope`: "system", "oss", or None); no hand-wiring in `Client`. Resources without update or delete (e.g. api_keys, audit_logs, finding_logs) raise `NotImplementedError` for those operations.
- **Pydantic models:** Request/response types live in resource modules and `models/`; used by module functions and by facade types only as the type parameter. No HTTP or registry logic in models.

When editing the client surface, facade, or registry, follow [docs/rules-of-engagement/architecture.md](docs/rules-of-engagement/architecture.md) and `.cursor/rules/architecture.mdc`.

## Critical Project Rules

- **Canonical naming:** `tenant.namespace.child` only; no UUIDs in paths.
- **Env and security:** Credentials via env; run `endorctl scan` before code changes.
- **Return types:** Functions return typed models: `Resource | None` or `list[Resource]`.
- **Field aliasing:** Follows a three-tier rule set (syntax collisions, spec case, semantic renames); see [docs/conventions.md](docs/conventions.md) (Models and API parity → Field aliasing).

## Automation

Ruff (style, imports, docstrings) and Pyright (typing) are configured in [pyproject.toml](pyproject.toml). CI runs `ruff check .`, `ruff format --check`, `pyright`, `pytest`. The same lint/format/typecheck run locally via the repo's pre-commit hook when installed (see [CONTRIBUTORS.md](CONTRIBUTORS.md)). Pyright enforces types in CI; public API must be fully typed (see pyproject.toml). For the exact command list, see [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Repository-Scoped Rules (`.cursor/rules/`)

Cursor rules apply when working here. Use **@rule** in chat or rely on glob/always-apply:

| Rule | When it applies |
|------|------------------|
| **endor-cockpit-core.mdc** | Always (project context and critical requirements) |
| **architecture.mdc** | When editing `client_surface.py`, `facade.py`, `registry.py`, or adding resources to the Client |
| **resource-patterns.mdc** | When editing `src/endorlabs/resources/**/*.py` |
| **api-workflow.mdc** | When editing models, resources, or OpenAPI spec |
| **test-driven-development.mdc** | When editing tests or `src/**/*.py` |
| **troubleshooting.mdc** | When debugging SDK/integration failures or editing troubleshooting docs |

Details (patterns, LIST/UPDATE, errors, API workflow) live in those rules and in the docs below. Troubleshooting workflow: troubleshooting.mdc and [docs/rules-of-engagement/troubleshooting.md](docs/rules-of-engagement/troubleshooting.md).

## Project Structure

```
endorlabs/
├── api_client.py      # Transport only (Layer 1)
├── client_surface.py  # Client facade (Layer 2 entry point)
├── facade.py          # SystemResourceFacade, OssResourceFacade, ResourceFacade; delegates to module functions
├── registry.py        # Registry of resources exposed on Client
├── resources/         # Module-level list/get/create/update/delete
└── models/
```

- **Experimental:** `endorlabs.experimental.sast_analysis` — may change without same stability guarantees. `endorlabs.analysis` is deprecated; use the new path.
- **Internal:** utils (model_validation, schema_drift, traversal), operations.

## Reference — External

- **User docs:** <https://docs.endorlabs.com/>
- **API spec:** <https://api.endorlabs.com/download/openapiv2.swagger.json> — use for required/optional fields, types, read-only; schema drift workflow downloads to `external_docs/` in CI.
- **Advanced users (IDE context):** One workflow creates the gitignored `external_docs/` folder with spec + user docs: `uv sync --extra docs` then `uv run python scripts/sync_external_docs.py --all`. See [CONTRIBUTORS.md](CONTRIBUTORS.md) (optional: sync external docs) and [scripts/README.md](scripts/README.md) for sync options; [docs/rules-of-engagement/docs-drift-workflow.md](docs/rules-of-engagement/docs-drift-workflow.md).

## Reference — In-Repo

- **Index:** [docs/README.md](docs/README.md) — what lives where.
- **Conventions:** [docs/conventions.md](docs/conventions.md) — naming, traverse, ListParameters, OpenAPI path, models and API parity, update_mask, errors.
- **Consumer UX (list/update):** filter vs mask, flat kwargs, spec-driven — [docs/conventions.md](docs/conventions.md), [docs/guides/consumer-ux-list-update.md](docs/guides/consumer-ux-list-update.md).
- **Reference:** [docs/reference/README.md](docs/reference/README.md) (public API, resources, namespace); [docs/reference/resources.md](docs/reference/resources.md) (operations per resource); [docs/reference/namespace.md](docs/reference/namespace.md) (list/get/create/update/delete).
- **Guides:** [docs/guides/README.md](docs/guides/README.md); consumer-ux-list-update, retrieving-scan-results.
- **Rules of engagement:** [docs/rules-of-engagement/README.md](docs/rules-of-engagement/README.md); api-validation, resource-implementation, troubleshooting, docs-drift-workflow.

## Essential Commands

```bash
uv run ruff check .
uv run ruff format .
uv run pyright
uv run pytest
endorctl scan
```

CI runs these (except optional endorctl); include pyright.

## User-Scoped Rules (Optional)

For preferences that apply across all your projects (TDD, OS-agnostic scripts, consistency), see [.cursor/USER_RULES_SUGGESTION.md](.cursor/USER_RULES_SUGGESTION.md). Copy from there into **Cursor Settings → General → Rules for AI** if you want them globally.

---

Index for AI agents; in-repo behavior and patterns are defined by `.cursor/rules/*.mdc` and the linked docs.

