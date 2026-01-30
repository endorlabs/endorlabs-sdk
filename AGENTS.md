# Endor Cockpit: AI Agent Integration Guide

> **Endor Cockpit**: Navigate the Endor Labs platform with tactical precision. This guide is the index for AI agents; behavior is defined by `.cursor/rules` and the linked docs.

## Consuming the SDK

- **Install:** `uv add endor-cockpit` or, in this repo, `uv sync`.
- **Entry:** `from endor_cockpit.api_client import APIClient`; then resource modules under `endor_cockpit.resources` (e.g. `namespace`, `finding`, `project`).
- **Pattern:** `APIClient()` reads env (`ENDOR_API`, `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`); resource functions take `client` and namespace/path; they return typed models or `None` (e.g. 404).
- **Errors:** `endor_cockpit.exceptions`; see [docs/conventions.md](docs/conventions.md) (Errors section).

```python
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import namespace

client = APIClient()
namespaces = namespace.list_namespaces(client, "tenant.namespace")
```

## Critical Project Rules

- **Canonical naming:** `tenant.namespace.child` only; no UUIDs in paths.
- **Env and security:** Credentials via env; run `endorctl scan` before code changes.
- **Return types:** Functions return typed models: `Resource | None` or `list[Resource]`.

## Automation

Ruff (style, imports, docstrings) and Pyright (typing) are configured in [pyproject.toml](pyproject.toml). CI runs `ruff check .`, `ruff format --check`, `pyright`, `pytest`. Pyright enforces types in CI; public API must be fully typed (see pyproject.toml). For the exact command list, see [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Repository-Scoped Rules (`.cursor/rules/`)

Cursor rules apply when working here. Use **@rule** in chat or rely on glob/always-apply:

| Rule | When it applies |
|------|------------------|
| **endor-cockpit-core.mdc** | Always (project context and critical requirements) |
| **resource-patterns.mdc** | When editing `src/endor_cockpit/resources/**/*.py` |
| **api-workflow.mdc** | When editing models, resources, or OpenAPI spec |
| **test-driven-development.mdc** | When editing tests or `src/**/*.py` |

Details (patterns, LIST/UPDATE, errors, API workflow) live in those rules and in the docs below.

## Project Structure

```
endor_cockpit/
├── api_client.py
├── resources/
└── models/
```

- **Experimental:** `endor_cockpit.analysis` — may change without same stability guarantees.
- **Internal:** utils (model_validation, schema_drift, traversal), operations.

## Reference — External

- **User docs:** <https://docs.endorlabs.com/>
- **API spec:** <https://api.endorlabs.com/download/openapiv2.swagger.json> — use for required/optional fields, types, read-only; schema drift workflow downloads to `external_docs/` in CI.

## Reference — In-Repo

- **Index:** [docs/README.md](docs/README.md) — what lives where.
- **Conventions:** [docs/conventions.md](docs/conventions.md) — naming, traverse, ListParameters, OpenAPI path, update_mask, errors.
- **Reference:** [docs/reference/README.md](docs/reference/README.md) (public API, resources, namespace); [docs/reference/resources.md](docs/reference/resources.md) (operations per resource); [docs/reference/namespace.md](docs/reference/namespace.md) (list/get/create/update/delete).
- **Guides:** [docs/guides/README.md](docs/guides/README.md); namespace-traversal, retrieving-scan-results, rego-policies.
- **Rules of engagement:** [docs/rules-of-engagement/README.md](docs/rules-of-engagement/README.md); api-validation, resource-implementation, troubleshooting, docs-drift-workflow.

## Essential Commands

```bash
uv run ruff check .
uv run ruff format .
uv run pytest
endorctl scan
```

CI runs these (except optional endorctl).

## User-Scoped Rules (Optional)

For preferences that apply across all your projects (TDD, OS-agnostic scripts, consistency), see [.cursor/USER_RULES_SUGGESTION.md](.cursor/USER_RULES_SUGGESTION.md). Copy from there into **Cursor Settings → General → Rules for AI** if you want them globally.

---

Index for AI agents; in-repo behavior and patterns are defined by `.cursor/rules/*.mdc` and the linked docs.
