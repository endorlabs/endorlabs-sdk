---
name: troubleshoot-authlog
description: >-
  Investigate tenant SSO/login issues using AuthenticationLog,
  AuthorizationPolicy, and optional AuditLog.
  Use when correlating IdP claims with Endor policy mapping, "no authorized
  tenant" symptoms, or exporting structured, flow-agnostic auth investigation JSON.
---

# Troubleshoot authentication logs and authorization policies

Systematic workflow for **Endor-side** evidence: what the platform recorded at login
(`AuthenticationLog`) versus how access is configured (`AuthorizationPolicy`).

## Prerequisites

- **Credentials:** `ENDOR_TOKEN` (or API creds) available to the SDK, e.g.
  `uv run --env-file .env python ...` (browser refresh: `devtools/refresh_token_to_dotenv.py` writes `ENDOR_TOKEN` to `.env`).
- **Local context (optional):** API spec at `.endorlabs-context/platform/openapi/openapiv2.swagger.json`;
  resource models in `src/endorlabs/resources/authentication_log.py`,
  `authorization_policy.py`
- **Permissions:** token must be able to list `AuthenticationLog` and
  `AuthorizationPolicy` in the target tenant context (typically with
  `traverse=True`).

## What this skill does

1. Lists **`AuthenticationLog` with `Client(tenant=<tenant-hint>)`** using
   traversal so auth evidence is collected from the customer context.
2. Traverses **namespaces** under `--tenant-hint` and pulls full
   **`AuthorizationPolicy`** `meta`/`spec` (clauses, `target_namespaces`,
   `propagate`, `permissions`, expiration).
3. Runs **validated probes**: control email + SSO URI filter, tenant-attributed SSO
   slice, target identity/group filters, failed / no-tenant slices.
4. Optionally emits **investigation export** artifacts (`--investigation-export`):
   separate evidence and scalar JSON (flow-agnostic; SSO-slice correlation is labeled
   as such—not “successful auth”). Operators may add a human-written
   `interpretation.md` beside outputs; the script does not generate it.

## How to run

Use the SDK directly (no bundled script). Example probe pattern:

```python
import endorlabs

client = endorlabs.Client(tenant="<tenant-hint>")
logs = client.AuthenticationLog.list(traverse=True, max_pages=2)
policies = client.AuthorizationPolicy.list(traverse=True, max_pages=2)
```

For structured exports, write JSON under `.endorlabs-context/workspace/sessions/<user>/`
(see [workspace-layout](../contracts/workspace-layout.md)).

## Interpretation notes (for agents)

- **`spec.claims`** uses list **membership** filters (`contains`); regex on claims is
  easy to misuse — the utility prefers exact `contains` strings.
- **SSO vs API-key noise:** broad auth lists include `/v1/auth/api-key` and
  `issuing_user=...`; use `tenant_sso` / `target_with_sso` filters for SAML/OIDC
  callbacks (`auth/saml-callback`, `auth/sso`, `tenant=<name>`).
- **`authorized_tenants`** in a row vs **`spec.uri`** with `tenant=...` — compare
  both when reasoning about tenant mapping.
- **Policy clauses** are **AND**ed within a policy; strings are case-sensitive.

## Relationship to other docs

- Broader SDK debugging: [troubleshoot-sdk](../troubleshoot-sdk/SKILL.md)
- Contributing: `docs/contributing/troubleshooting.md`
