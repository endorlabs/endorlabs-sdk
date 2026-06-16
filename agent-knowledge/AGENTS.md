# Endor Labs SDK — agent guide (consumer)

> Shipped in the `endorlabs` wheel. Repo-root `AGENTS.md` in the SDK GitHub repo is for **contributors** only.

**Canonical Tier 0:** [`INDEX.md`](INDEX.md) — first steps, trap tables, bootstrap rules, read order. It is included in `discover().bootstrap_paths`; read it before `Client()` and live API calls.

## Quick entry

```python
import endorlabs

d = endorlabs.discover()
# Read INDEX.md + every path in d.bootstrap_paths; read d.stub for list() / accessor kwargs.
# Same map: print(d)  or  python -m endorlabs.examples.agent_bootstrap --dry-run
```

Do not grep the SDK source tree as primary discovery. Use wheel paths from `discover()`.

## Where to go next

| Need | Location |
|------|----------|
| Traps, auth, client basics, validation | [`INDEX.md`](INDEX.md) |
| Skill playbooks | `MANIFEST.json` → `skills/<id>/SKILL.md` (materialize: `endorlabs.init()`) |
| Call graph workflow | `skills/endor-fetch-and-search-call-graph/SKILL.md` after `init()` |
| Copy minimal guide to your repo | [`templates/consumer-AGENTS.md`](templates/consumer-AGENTS.md) |

## Discovery paths

| Path | Use when |
|------|----------|
| **IDE** (Pyright) | Type checking — `discover().stub` |
| **Runtime agent** | `print(discover())` → read `bootstrap_paths` + stub |
| **MCP-only** | Narrow reads; fix single auth mode first — not a substitute for SDK traverse |
