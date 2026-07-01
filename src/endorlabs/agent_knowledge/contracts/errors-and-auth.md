---
id: errors-and-auth
tags:
- auth
- errors
---

# Errors and authentication

## Environment variables

Use only documented variables:

- `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`
- `ENDOR_TOKEN`
- `ENDOR_NAMESPACE` (optional default)
- `ENDOR_API` (optional API base URL)

Do not invent credential or settings env var names.

## Single auth mode (SDK, endorctl, MCP)

Use **one** credential mode in `.env` or the environment:

| Mode | Variables |
|------|-----------|
| Bearer token | `ENDOR_TOKEN` |
| API key | `ENDOR_API_CREDENTIALS_KEY` + `ENDOR_API_CREDENTIALS_SECRET` |

When **both** `ENDOR_TOKEN` and API key env vars are set:

- **SDK:** prefers `ENDOR_TOKEN` (browser-auth validation path) and logs INFO naming the conflict.
- **endorctl / platform MCP:** typically fail with conflicting authentication methods.

**Remediation:** unset either `ENDOR_TOKEN` or both API key variables before using MCP or endorctl alongside the SDK.

## Missing credentials

`ValidationError` from `APIClient` / `Client` construction lists these options:

1. `ENDOR_TOKEN` (bearer; validated when set)
2. `ENDOR_API_CREDENTIALS_KEY` + `ENDOR_API_CREDENTIALS_SECRET`
3. `APIClient(auth_method='browser-auth')` for interactive OAuth

## Exceptions

Use top-level `endorlabs` exception types (`NotFoundError`, `UnauthorizedError`,
`ValidationError`, `AmbiguousError`, …). Resources may return `None` on 404 where documented.

**Note:** `AmbiguousError` is no longer raised by facade discovery — use `search_by_*` and explicit disambiguation instead of exact-match `lookup()`.

## Local OpenAPI spec

Preferred path after `init()`:

`.endorlabs-context/platform/openapi/openapiv2.swagger.json`

User docs mirror:

`.endorlabs-context/platform/user-docs/`
