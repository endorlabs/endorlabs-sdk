---
id: errors-and-auth
tags: [auth, errors]
---

# Errors and authentication

## Environment variables

Use only documented variables:

- `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`
- `ENDOR_TOKEN`
- `ENDOR_NAMESPACE` (optional default)
- `ENDOR_API` (optional API base URL)

Do not invent credential or settings env var names.

## Exceptions

Use top-level `endorlabs` exception types (`NotFoundError`, `UnauthorizedError`,
`ValidationError`, `AmbiguousError`, …). Resources may return `None` on 404 where documented.

## Local OpenAPI spec

Preferred path after `init()`:

`.endorlabs-context/platform/openapi/openapiv2.swagger.json`

User docs mirror:

`.endorlabs-context/platform/user-docs/`
