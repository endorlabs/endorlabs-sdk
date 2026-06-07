---
id: endor-local-context
tags:
- context
- openapi
- bootstrap
summary: Check gitignored .endorlabs-context paths explicitly; prefer local platform
  docs before the web; never print secrets.
---

# Local context discovery

When guidance references local context under gitignored paths, do not assume those
files are absent because a broad search did not show them.

## Check explicitly

- `.endorlabs-context/`
- `.endorlabs-context/context.json`
- `.endorlabs-context/sdk/INDEX.md`
- `.endorlabs-context/sdk/MANIFEST.json`
- `.endorlabs-context/platform/openapi/openapiv2.swagger.json`
- `.endorlabs-context/platform/user-docs/`
- `.env` (confirm variables exist only — **never print secrets**)

Gitignored paths may be missing from workspace search; try targeted reads before
concluding context is unavailable.

## Research order

1. Wheel: `agent_knowledge_index_path()` / `agent_knowledge_manifest()` (site-packages), or materialized `.endorlabs-context/sdk/` after `init()`.
2. Local OpenAPI and user docs under `.endorlabs-context/platform/` (when bootstrapped).
3. Online API spec and docs only as fallback.

Materialize with `endorlabs.init()` when a cwd-relative tree is needed.
