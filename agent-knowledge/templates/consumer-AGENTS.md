# Endor Labs SDK — agent guide (consumer project)

Copy this file to your project root as `AGENTS.md` when using the Endor Labs Python SDK with AI agents.

**Full Tier 0 reference** (trap tables, rules, read order): read `discover().index` — shipped as `INDEX.md` in the wheel (`endorlabs.agent_knowledge_index_path()`).

## First steps

```python
import endorlabs

# 0. Map (no credentials)
print(endorlabs.discover())
# Or: python -m endorlabs.examples.agent_bootstrap --dry-run

d = endorlabs.discover()
# Read d.index (INDEX.md) and every path in d.bootstrap_paths.
client = endorlabs.Client(tenant="your-tenant")
print(client.Finding.describe())  # no credentials required

# 1. Auth
# uv run endor-auth check --tenant your-tenant
print(client.whoami())  # not Namespace.list()

# 2. Workflows — skills not on dir(client)
endorlabs.init(include_openapi=False)
# Read .endorlabs/_cache/sdk/skills/<id>/SKILL.md
```

## Auth (`.env`)

One mode only: `ENDOR_TOKEN` + `ENDOR_NAMESPACE`, **or** key + secret + namespace. Not both token and API key (breaks MCP/endorctl).

Probe: `uv run endor-auth check`. Refresh: `uv run endor-auth refresh --method sso -n <tenant>`. Skill: **endor-auth-setup**.

## High-signal traps

See INDEX.md for the full table. Most common:

- `list(filter=F(...), …)` — never positional `F()`
- Project-scoped lists: resolve `Project`, use `namespace=project.namespace` or `list_by_*`
- Call graph: `init()` → skill **endor-fetch-and-search-call-graph**; `decode()` not `fetch()` alone

## Outputs

Write artifacts under `.endorlabs/` (gitignore this tree):

- `tasks/<slug>-<YYYY-MM-DD>/projects/` — project bundles and per-uuid reachability JSON
- `tasks/<slug>-<YYYY-MM-DD>/<activity>/` — CSV, JSON, RCA (activity segment per skill; see INDEX)
- `reports/<subcommand>/` — report CSV/HTML outputs
- `tasks/inventory/` — namespace inventories (no tenant-day bucket)

## MCP (optional)

Narrow reads/scans only. Estate traversal and RCA use SDK `Client`, not MCP.
