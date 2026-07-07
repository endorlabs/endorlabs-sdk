---
name: endor-troubleshoot-authlog
description: Investigate tenant SSO/login issues using AuthenticationLog, AuthorizationPolicy,
  and optional AuditLog. Use when correlating IdP claims with Endor policy mapping,
  "no authorized tenant" symptoms, or exporting structured, flow-agnostic auth investigation
  JSON.
---

# Troubleshoot authentication logs and authorization policies

Systematic workflow for **Endor-side** evidence: what the platform recorded at login
(`AuthenticationLog`) versus how access is configured (`AuthorizationPolicy`).

## Prerequisites

- **Credentials:** `ENDOR_TOKEN` (or API creds) available to the SDK, e.g.
  `uv run --env-file .env python ...` (browser refresh: `devtools/refresh_token_to_dotenv.py`; `--sso` / `-n` or env tenant; `--admin` for endor-admin).
- **Local context (optional):** API spec at `.endorlabs-context/platform/openapi/openapiv2.swagger.json`;
  resource models in `src/endorlabs/resources/authentication_log.py`,
  `authorization_policy.py`
- **Permissions:** token must be able to list `AuthenticationLog` and
  `AuthorizationPolicy` in the target tenant context (typically with
  `traverse=True`).

## What this skill does

1. Lists **`AuthenticationLog`** with `Client(tenant=<tenant-hint>)` and
   `traverse=True` to collect auth evidence from the customer context.
2. Lists **`AuthorizationPolicy`** under the same tenant with `traverse=True`
   and inspects `meta`/`spec` (clauses, `target_namespaces`, `propagate`,
   `permissions`, expiration).
3. Applies **narrow filters** on auth logs (SSO URI slices, target email/group,
   failed or no-tenant rows) before drawing conclusions — see interpretation notes.
4. Optionally writes **investigation export** JSON under
   `.endorlabs-context/workspace/sessions/<user>/` (flow-agnostic evidence bundle;
   add a human-written `interpretation.md` beside outputs when needed).

## How to run

Use the SDK directly (no bundled script). Example probe pattern:

```python
import endorlabs

client = endorlabs.Client(tenant="<tenant-hint>")
logs = client.AuthenticationLog.list(traverse=True, max_pages=2)
policies = client.AuthorizationPolicy.list(traverse=True, max_pages=2)
```

For structured exports, write JSON under `.endorlabs-context/workspace/sessions/<user>/`
(see [workspace-layout](../../rules/endor-workspace-layout.md)).

For **tenant-wide login activity counts** (identity, last login, count in N days),
use [endor-auth-login-count](../endor-auth-login-count/SKILL.md) and
`endorlabs.workflows.auth` helpers (`fetch_authentication_logs`,
`aggregate_login_activity`).

## Interpretation notes (for agents)

- **`spec.claims`** uses list **membership** filters (`contains`); regex on claims is
  easy to misuse — the utility prefers exact `contains` strings.
- **SSO vs API-key noise:** broad auth lists include `/v1/auth/api-key` and
  `issuing_user=...`; narrow with `filter=` on `spec.uri` for SAML/OIDC callbacks
  (`auth/saml-callback`, `auth/sso`, `tenant=<name>`) before correlating tenants.
- **`authorized_tenants`** in a row vs **`spec.uri`** with `tenant=...` — compare
  both when reasoning about tenant mapping.
- **Policy clauses** are **AND**ed within a policy; strings are case-sensitive.

## Related skills

| Need | Skill |
| ---- | ----- |
| Tenant-wide login count / activity CSV | [endor-auth-login-count](../endor-auth-login-count/SKILL.md) |
| Broader SDK debugging | [endor-troubleshoot-sdk](../endor-troubleshoot-sdk/SKILL.md) |
| Contributing | `docs/contributing/troubleshooting.md` |
