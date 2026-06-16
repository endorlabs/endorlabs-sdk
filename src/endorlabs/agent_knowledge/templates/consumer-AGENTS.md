# Endor Labs SDK — agent guide (consumer project)

Copy this file to your project root as `AGENTS.md` when using the Endor Labs Python SDK with AI agents.

## First steps

```python
import endorlabs

# 0. Map (no credentials)
print(endorlabs.discover())
# Or: python -m endorlabs.examples.agent_bootstrap --dry-run

d = endorlabs.discover()
# Read every path in d.bootstrap_paths; read d.stub (client_surface.pyi).

# 1. Auth
client = endorlabs.Client(tenant="your-tenant")  # or ENDOR_NAMESPACE
print(client.whoami())

# 2. Workflows (call graph, scan RCA) — skills not on dir(client)
endorlabs.init(include_openapi=False, include_user_docs=False)
# Read .endorlabs-context/sdk/skills/<id>/SKILL.md
```

## Auth (`.env`)

Use **one** mode:

- `ENDOR_TOKEN` + `ENDOR_NAMESPACE`, **or**
- `ENDOR_API_CREDENTIALS_KEY` + `ENDOR_API_CREDENTIALS_SECRET` + `ENDOR_NAMESPACE`

Do not set token and API key together — breaks MCP and endorctl.

Verify: `endorlabs.Client().whoami()` (not `Namespace.list()`).

## Discovery order

1. `print(discover())` or `agent_bootstrap --dry-run` → read every `bootstrap_paths` entry
2. `discover().stub` — list kwargs + relationship methods
3. Shell: `help(client.Project.list)`, `inspect.signature(client.Finding.list_by_project)`
4. Live smoke test: `python -m endorlabs.examples.agent_bootstrap` (includes auth + bounded list)

## Common traps

- Filters: `filter=F(...)`, never positional
- Pagination: `page_size`, `limit` (alias), or `max_pages` on `.list()`
- Call graph: read skill after `init()`; use `decode()` and `resolve_package_version_with_callgraph`
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
