# Endor Cockpit: AI Agent Integration Guide

> **Endor Cockpit**: Navigate the Endor Labs platform with tactical precision. This guide is the index for AI agents; detailed rules live in **repository-scoped** Cursor rules and docs.

## Quick Start

```python
from endor_cockpit.api_client import APIClient
client = APIClient()
from endor_cockpit.resources import namespace
namespaces = namespace.list_namespaces(client, "tenant.namespace")
```

**Workflow**: Initialize → Authenticate → Operate → Handle Errors

## Critical Requirements

- **Canonical naming**: `tenant.namespace.child` only; never UUIDs in paths.
- **Environment**: `ENDOR_API`, `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`.
- **Python**: 3.13+; dependencies pinned (no `latest`).
- **Linting**: Max 88 chars/line, sorted imports, no trailing whitespace. Run `uv run ruff check .` and `uv run ruff format .`.
- **Security**: Run `endorctl scan` before code changes.
- **Return types**: Functions return `Optional[Resource]` or `List[Resource]` for consistency.

## Typing Policy (Pyright)

- **Errors**: 0 Pyright errors required; CI must fail on new errors.
- **Public API** (`src/endor_cockpit/resources/*.py`, `api_client.py`, `types.py`): All exported functions and models must have explicit parameter and return types; no bare `list`/`dict` in public signatures; generics must have type args (e.g. `list[Finding]`).
- **Internal code** (`analysis/`, `utils/`, `models/base` helpers): May have remaining warnings; use `# pyright: ignore[...]` with a short comment when types are genuinely dynamic.
- **CI**: Optionally fail on new warnings in the curated public API file list to keep the public surface self-documented and consistent.

## Repository-Scoped Rules (`.cursor/rules/`)

Cursor rules in this repo apply when working here. Use **@rule** in chat or rely on glob/always-apply:

| Rule | When it applies |
|------|------------------|
| **endor-cockpit-core.mdc** | Always (project context and critical requirements) |
| **resource-patterns.mdc** | When editing `src/endor_cockpit/resources/**/*.py` |
| **api-workflow.mdc** | When editing models, resources, or OpenAPI spec |
| **test-driven-development.mdc** | When editing tests or `src/**/*.py` |

Details (patterns, LIST/UPDATE/error handling, API workflow) are in those `.mdc` files and in the docs below.

## Project Structure

```
endor_cockpit/
├── api_client.py
├── resources/
└── models/
```

- **Experimental:** `endor_cockpit.analysis` — may change without same stability guarantees.
- **Internal:** utils (model_validation, schema_drift, traversal), operations.

## Reference Guides

- **Documentation index**: [docs/README.md](docs/README.md) — what lives where; [docs/conventions.md](docs/conventions.md) — canonical naming, traverse, ListParameters, OpenAPI path, error handling.
- **Namespace**: [docs/reference/namespace.md](docs/reference/namespace.md) — list/get/create/update/delete; [docs/guides/namespace-traversal.md](docs/guides/namespace-traversal.md) — use `traverse=True` for tenant-wide queries.
- **API validation**: [docs/rules-of-engagement/api-validation.md](docs/rules-of-engagement/api-validation.md)
- **Resource implementation**: [docs/rules-of-engagement/resource-implementation.md](docs/rules-of-engagement/resource-implementation.md)
- **Docs drift workflow**: [docs/rules-of-engagement/docs-drift-workflow.md](docs/rules-of-engagement/docs-drift-workflow.md)
- **Troubleshooting**: [docs/rules-of-engagement/troubleshooting.md](docs/rules-of-engagement/troubleshooting.md)
- **Rego (SDK usage)**: [docs/guides/rego-policies.md](docs/guides/rego-policies.md)

## Essential Commands

```bash
uv run ruff check .
uv run ruff format .
uv run pytest
endorctl scan
```

## User-Scoped Rules (Optional)

For preferences that apply across all your projects (TDD, OS-agnostic scripts, consistency), see [.cursor/USER_RULES_SUGGESTION.md](.cursor/USER_RULES_SUGGESTION.md). Copy from there into **Cursor Settings → General → Rules for AI** if you want them globally.

---

*Index for AI agents. In-repo behavior is defined by `.cursor/rules/*.mdc` and the linked docs.*
