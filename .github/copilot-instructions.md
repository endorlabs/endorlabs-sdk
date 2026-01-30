# Endor Cockpit – Repository instructions for GitHub Copilot

**Project**: Production Python SDK for Endor Labs. API-first platform for security governance.

---

## What to seek when suggesting or reviewing code

**Security**: Actively look for security issues. Examples: credential or secret handling (use env only; no hardcoding); injection or unsafe use of user-controlled input in paths or request bodies; missing or weak validation of API responses; dependency or supply-chain concerns. Prefer safe defaults and fail closed where appropriate.

**SDK consumer UX**: View changes from the perspective of someone using this SDK in their application. Prefer clear, consistent naming; predictable error handling (use `endorlabs.exceptions`; no silent swallowing); helpful docstrings and type hints; ergonomic defaults (e.g. `traverse=True` for tenant-wide queries where documented). Avoid breaking or surprising behavior for existing callers; preserve backward compatibility unless explicitly changing the contract.

**Consistency and parity with API spec and docs**: Keep SDK models and resource behavior aligned with the authoritative API definition and user documentation. When adding or changing resources or models, check the OpenAPI spec and user docs for path names, request/response shapes, required vs optional fields, and documented semantics. Flag drift (e.g. SDK fields or behavior that no longer match the spec or docs) and suggest corrections. Use the references below.

---

## Reference – API spec and user docs

- **API spec (OpenAPI)**: <https://api.endorlabs.com/download/openapiv2.swagger.json> (schema drift workflow downloads to `external_docs/` in CI; folder is gitignored)
- **User documentation**: <https://docs.endorlabs.com/> — sitemap <https://docs.endorlabs.com/sitemap.xml>
- **In-repo docs**: `docs/README.md` (index), `docs/conventions.md` (naming, traverse, ListParameters), `docs/reference/namespace.md`, `docs/rules-of-engagement/api-validation.md`, `docs/rules-of-engagement/resource-implementation.md`, `docs/rules-of-engagement/docs-drift-workflow.md`

