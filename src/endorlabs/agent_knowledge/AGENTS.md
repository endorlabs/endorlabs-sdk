# Endor Labs SDK — agent guide (consumer)

> Shipped in the `endorlabs` wheel. Repo-root `AGENTS.md` in the SDK GitHub repo is for **contributors** only.

## Step zero — before any API call

```python
import endorlabs

d = endorlabs.discover()
# Read every path in d.bootstrap_paths (INDEX, rules, contracts).
# Read d.stub for list() kwargs and relationship accessors (search_by_*, list_by_*).
```

Do not grep the SDK source tree or monorepo as primary discovery. Use wheel paths from `discover()`.

## Three discovery paths

| Path | Use when | Primary artifacts |
|------|----------|-------------------|
| **IDE** (Pyright/Pylance) | Human coding in VS Code/Cursor with type checking | `client_surface.pyi` + inherited facade types |
| **Cursor / runtime agent** | No LSP; Read files + shell `help()` / `inspect` | `discover().bootstrap_paths`, `discover().stub`, `python -m endorlabs.examples.day0` |
| **MCP-only** | Narrow reads/scans via platform MCP | Fix auth to **single mode** first; cannot replace SDK traverse/search |

## Auth (`.env`)

Use **one** credential mode (never commit secrets):

- `ENDOR_TOKEN` + `ENDOR_NAMESPACE`, **or**
- `ENDOR_API_CREDENTIALS_KEY` + `ENDOR_API_CREDENTIALS_SECRET` + `ENDOR_NAMESPACE`

If both token and API key env vars are set, the SDK prefers the token and logs INFO; **MCP and endorctl fail** with conflicting auth — unset one pair.

Verify: `endorlabs.Client().whoami()`

## Discovery order

1. `discover()` / `agent_knowledge_bootstrap_paths()` → read INDEX + contracts
2. Read `discover().stub` — flat method signatures on `_XFacade` classes
3. Shell: `help(client.Project.list)`, `inspect.signature(client.Finding.list_by_project)`
4. Bounded live probe: `python -m endorlabs.examples.day0`

## Common traps

- Filters: `filter=F(...)`, never positional as first arg to `list()`
- Pagination: `page_size` / `max_pages` on `.list()`; not `limit` (except `ScanResult.list_by_project(limit=)`)
- Findings text: `spec.summary`
- Project-scoped lists: resolve `Project`, then `namespace=project.namespace` or `list_by_project`
- `QueryVulnerability` / `QueryMalware`: create/query APIs — no `.list()`
- `endorlabs.query_vulnerability` is a **module**; use `client.QueryVulnerability`

## Optional: Pyright in dev deps

Batch typecheck substitutes for IDE hovers when agents run shell checks:

```bash
uv add --dev pyright
uv run pyright main.py
```

## Copy to your project

See `templates/consumer-AGENTS.md` for a minimal project-root template.
