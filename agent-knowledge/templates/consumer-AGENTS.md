# Endor Labs SDK — agent guide (consumer project)

Copy this file to your project root as `AGENTS.md` when using the Endor Labs Python SDK with AI agents.

## Step zero — before any API call

```python
import endorlabs

d = endorlabs.discover()
# Read every path in d.bootstrap_paths; then read d.stub (client_surface.pyi).
```

## Auth (`.env`)

Use **one** mode:

- `ENDOR_TOKEN` + `ENDOR_NAMESPACE`, **or**
- `ENDOR_API_CREDENTIALS_KEY` + `ENDOR_API_CREDENTIALS_SECRET` + `ENDOR_NAMESPACE`

Do not set token and API key together — breaks MCP and endorctl.

Verify: `endorlabs.Client().whoami()`

## Discovery order

1. Shipped knowledge (`discover()` / `agent_knowledge_bootstrap_paths()`)
2. `discover().stub` — list kwargs + relationship methods
3. Shell: `help(client.Project.list)`, `inspect.signature(client.Finding.list_by_project)`
4. Bounded live probe: `python -m endorlabs.examples.day0`

## Common traps

- Filters: `filter=F(...)`, never positional
- Pagination: `page_size` / `max_pages`, not `limit` on `.list()`
- Findings text: `spec.summary`
- Project-scoped lists: resolve `Project`, use `namespace=project.namespace` or `list_by_project`
- Query* resources: create/query APIs, not `.list()`

## MCP (optional)

Narrow reads/scans only. Fix auth to single mode first. For estate traversal use SDK `Client`, not MCP.

## Optional: Pyright

```toml
[dependency-groups]
dev = ["pyright>=1.1"]
```

```bash
uv run pyright main.py
```
