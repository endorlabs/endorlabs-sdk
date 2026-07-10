---
name: endor-troubleshoot-authlog
description: |
  Use when investigating tenant SSO/login issues with AuthenticationLog,
  AuthorizationPolicy, and optional AuditLog—correlating IdP claims with Endor
  policy mapping, "no authorized tenant" symptoms, or exporting structured
  flow-agnostic auth investigation JSON.
---

# Troubleshoot authentication logs and authorization policies

Systematic workflow for **Endor-side** evidence: what the platform recorded at login
(`AuthenticationLog`) versus how access is configured (`AuthorizationPolicy`).

  `uv run --env-file .env python ...` (browser refresh: `uv run endor-auth refresh --method sso -n <tenant>`).
- **Auth setup:** [endor-auth-setup](../endor-auth-setup/SKILL.md) — `uv run endor-auth check --tenant <tenant>`.
- **Local context (optional):** API spec at `.endorlabs-context/platform/openapi/openapiv2.swagger.json`;
  resource models in `src/endorlabs/resources/authentication_log.py`,
  `authorization_policy.py`
- **Permissions:** token must be able to list `AuthenticationLog` and
  `AuthorizationPolicy` on the target tenant list path.

## What this skill does

1. Fetches **`AuthenticationLog`** via `endorlabs.workflows.auth` on the **tenant list path**
   (`namespace=<tenant>`, `traverse=False`) with a **time-bounded server filter** — not unfiltered
   `traverse=True` sweeps.
2. Lists **`AuthorizationPolicy`** under the same tenant (use `traverse=True` only when policy
   rows live in child namespaces).
3. Applies **narrow filters** on auth logs (SSO URI slices, target email/group,
   failed or no-tenant rows) before drawing conclusions — see interpretation notes.
4. Optionally writes **investigation export** JSON under
   `.endorlabs-context/workspace/runs/troubleshoot-authlog/`.

## Library layers

Preset RCA stack: `probe_auth_logs` → `filter_auth_logs_by_email` → `auth_log_snapshot`.
Use `probe_auth_logs` (not `list_auth_logs`) — broader rows including failures and
`authorized_tenants`. For custom filters, compose `auth_log_filter` +
`client.AuthenticationLog.list` → `normalize_auth_log`. Full layer map:
`endorlabs.workflows.auth.authentication_log` module docstring.

**Tenant trap:** `namespace=<tenant>` on list; never `tenant_meta.namespace` in MQL.

## How to run

### AuthenticationLog (fast path — shared with login-count)

```python
import endorlabs
from endorlabs.workflows.auth import (
    auth_log_snapshot,
    probe_auth_logs,
    filter_auth_logs_by_email,
)

client = endorlabs.Client(tenant="<tenant-hint>")
rows = probe_auth_logs(
    client,
    namespace="<tenant-hint>",
    days=30,
    max_pages=10,
)
# Optional: narrow to one user
rows = filter_auth_logs_by_email(rows, "user@example.com")
snapshots = [auth_log_snapshot(row) for row in rows]
client.close()
```

Defaults include **failed** logins and **non-interactive** URIs (broader than login-count).
For login **counts** only, see
[endor-workflow-reports](../endor-workflow-reports/SKILL.md)
(`list_groups` on `spec.claims` — server-side aggregation).

### AuthorizationPolicy

```python
import endorlabs

client = endorlabs.Client(tenant="<tenant-hint>")
policies = client.AuthorizationPolicy.list(traverse=True, max_pages=2)
client.close()
```

For structured exports, write JSON under `.endorlabs-context/workspace/runs/troubleshoot-authlog/`
(see [workspace-layout](../../rules/endor-workspace-layout.md)).

SSO claim-to-namespace mapping: [endor-sso-integration-validation-troubleshooting](../endor-sso-integration-validation-troubleshooting/SKILL.md)
(`sso_access_spotcheck.py` uses the same `probe_auth_logs` helper).

## Interpretation notes (for agents)

- **`spec.claims`** uses list **membership** filters (`contains`); regex on claims is
  easy to misuse — the utility prefers exact `contains` strings.
- **SSO vs API-key noise:** broad auth lists include `/v1/auth/api-key` and
  `issuing_user=...`; narrow with `filter=` on `spec.uri` for SAML/OIDC callbacks
  (`auth/saml-callback`, `auth/sso`, `tenant=<name>`) before correlating tenants.
- **`authorized_tenants`** in a row vs **`spec.uri`** with `tenant=...` — compare
  both when reasoning about tenant mapping.
- **Policy clauses** are **AND**ed within a policy; strings are case-sensitive.
- **Tenant scoping:** use `namespace=<tenant>` on AuthenticationLog — do **not** filter
  `tenant_meta.namespace` (rows may show `system` but return on the tenant list path).

## Related skills

| Need | Skill |
| ---- | ----- |
| Credential setup / refresh | [endor-auth-setup](../endor-auth-setup/SKILL.md) |
| SSO setup / claim-to-namespace spot-check | [endor-sso-integration-validation-troubleshooting](../endor-sso-integration-validation-troubleshooting/SKILL.md) |
| Broader SDK debugging | [endor-troubleshoot-sdk](../endor-troubleshoot-sdk/SKILL.md) |
| Contributing | `docs/contributing/troubleshooting.md` |
