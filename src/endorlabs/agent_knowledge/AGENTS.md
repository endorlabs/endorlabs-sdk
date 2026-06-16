# Endor Labs SDK — agent guide (consumer)

> Shipped in the `endorlabs` wheel. Repo-root `AGENTS.md` in the SDK GitHub repo is for **contributors** only.

## First steps

```python
import endorlabs

# Map (no credentials)
print(endorlabs.discover())  # human-readable paths — not the dataclass repr
# Same output: python -m endorlabs.examples.agent_bootstrap --dry-run

d = endorlabs.discover()
# Read every path in d.bootstrap_paths; read d.stub for list() / accessor kwargs.

# Auth
client = endorlabs.Client(tenant="your-tenant")
print(client.whoami())

# Workflows (skills not on dir(client))
endorlabs.init(include_openapi=False, include_user_docs=False)
# → .endorlabs-context/sdk/skills/<id>/SKILL.md
```

Do not grep the SDK source tree or monorepo as primary discovery. Use wheel paths from `discover()`.

## Three discovery paths

| Path | Use when | Primary artifacts |
|------|----------|-------------------|
| **IDE** (Pyright/Pylance) | Human coding in VS Code/Cursor with type checking | `client_surface.pyi` + inherited facade types |
| **Cursor / runtime agent** | No LSP; Read files + shell `help()` / `inspect` | `print(discover())` or `agent_bootstrap --dry-run`, then read `bootstrap_paths` + `stub` |
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
4. Bounded live smoke test: `python -m endorlabs.examples.agent_bootstrap`
5. **Workflows:** `endorlabs.init()` → `.endorlabs-context/sdk/skills/<id>/SKILL.md`

## Workflows (call graph example)

Skills are not on `dir(client)`. After `init()`, read **`skills/endor-fetch-and-search-call-graph/SKILL.md`**.

```python
from endorlabs.workflows.callgraph import (
    resolve_package_version_with_callgraph,
    find_call_graph_path,
)

pv, decoded = resolve_package_version_with_callgraph(
    client, project, namespace=project.tenant_meta.namespace
)
# decoded.callables / decoded.edges — not CallGraphData.fetch() alone

result = find_call_graph_path(
    decoded.callables,
    decoded.edges,
    from_patterns=["_is_verbose"],
    to_patterns=["bool"],
    max_depth=4,
)
```

`spec.call_graph_available` indicates capability; the helper above verifies decode succeeds.

## Common traps

- Filters: `filter=F(...)`, never positional as first arg to `list()`
- Pagination: `page_size`, `limit` (alias), or `max_pages` on `.list()`; `list_by_project(limit=)` unchanged
- Findings text: `spec.summary`
- Project-scoped lists: resolve `Project`, then `namespace=project.namespace` or `list_by_project`
- `QueryVulnerability` / `QueryMalware`: create/query APIs — no `.list()`
- `endorlabs.query_vulnerability` is a **module**; use `client.QueryVulnerability`
- Call graph: `decode()` not `fetch()` for search; use `resolve_package_version_with_callgraph`

## Optional: Pyright in dev deps

Batch typecheck substitutes for IDE hovers when agents run shell checks:

```bash
uv add --dev pyright
uv run pyright main.py
```

## Copy to your project

See `templates/consumer-AGENTS.md` for a minimal project-root template.
