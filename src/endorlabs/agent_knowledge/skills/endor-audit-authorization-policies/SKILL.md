---
name: endor-audit-authorization-policies
description: Audit AuthorizationPolicy wire shape and claim/namespace form for common
  misconfigurations (comma-separated namespace blobs, wrong IdP claim keys, double
  provider suffixes). Use when reviewing Auth Policy setup, "no authorized tenant"
  after successful IdP login, or customer policy imports— not for credential refresh
  (endor-auth-setup), Enterprise SSO planning (endor-sso-integration-validation-troubleshooting),
  or AuthenticationLog RCA (endor-troubleshoot-authlog).
---

# Audit AuthorizationPolicy form

LLM-oriented checklist for **whether policies are shaped correctly**, not whether
SSO IdP metadata is configured. Normative product docs:
[Authorization policies](https://docs.endorlabs.com/platform-administration/rbac/authorization-policies).

## Scope

**In scope**

- `AuthorizationPolicy.spec.clause` and `spec.target_namespaces` list shape
- Per-IdP claim key/value conventions (GitHub/GitLab handle, Google email/domain, …)
- Heuristic flags for known customer footguns (comma-blobs, double `@provider`)
- Optional scripted estate scan → JSON findings

**Out of scope**

- SDK / `endor-auth` credential env vars → [endor-auth-setup](../endor-auth-setup/SKILL.md)
  and contract [errors-and-auth](../../contracts/errors-and-auth.md)
- Enterprise SSO intake / claim→namespace access planning →
  [endor-sso-integration-validation-troubleshooting](../endor-sso-integration-validation-troubleshooting/SKILL.md)
- Login failure RCA via AuthenticationLog →
  [endor-troubleshoot-authlog](../endor-troubleshoot-authlog/SKILL.md)

## When to use this skill vs others

| Goal | Start here | Then |
|------|------------|------|
| “Are these Auth Policies well-formed?” | **This skill** | SSO skill if IdP/group mapping is wrong |
| “User authenticated but no tenant” | **This skill** (claim form) | authlog skill for login evidence |
| “Set up Okta/Entra SSO” | SSO skill | This skill to audit resulting policies |
| “Refresh ENDOR_TOKEN / API keys” | auth-setup | — |

## Wire shape (SDK / API)

`V1AuthorizationPolicySpec`:

| Field | Type | Meaning |
|-------|------|---------|
| `clause` | `list[str]` | **AND** of claim predicates; each entry is typically `key=value` or a provider tag (`google`, `gitlab`, …) |
| `target_namespaces` | `list[str]` | **One namespace path per list element** |
| `propagate` | `bool` | Also authorize children of each target |
| `permissions` | object | Roles / rules |

Exact matching is **case-sensitive**. Clause strings have a restricted character set
(see generated model docstring on `clause`).

## Correct claim forms (by IdP)

Full tables: [claim-and-namespace-forms.md](claim-and-namespace-forms.md).

| IdP | Key | Value (UI) | Typical stored clause pair |
|-----|-----|------------|----------------------------|
| GitHub / GitLab | `user` | Platform **handle only** (e.g. `jsmith`) | `user=jsmith@github` + `github` |
| Google | `user` or `domain` | Email or domain | `user=a@b.com@google` + `google` |
| Email (magic link) | `email` | Inbox address | `email=a@b.com` + `email` (or provider tag as stored) |
| Custom OIDC/SAML | IdP claim name | Exact token claim value | As asserted by IdP |

**GitLab/GitHub:** do **not** put email in `user`, and do **not** type `handle@gitlab`
into the Value field (the UI/IdP tag already appends `@gitlab` → `handle@gitlab@gitlab`).

## Anti-patterns (audit these)

### 1. Comma-separated namespace blob (critical)

**Wrong** — one `target_namespaces` element containing many paths:

```text
"doordash.doordash-github-creditornot, doordash.doordash-github-doordash, doordash.doordash-github-roo"
```

**Right** — three list elements:

```text
[
  "doordash.doordash-github-creditornot",
  "doordash.doordash-github-doordash",
  "doordash.doordash-github-roo"
]
```

Same footgun appears when a CSV is pasted into a **single** clause string.

### 2. Double provider suffix

```text
user=timmy166@gitlab@gitlab   # bad — Value was "timmy166@gitlab"
user=timmy166@gitlab          # good — Value was "timmy166"
```

### 3. Wrong key for the IdP

- `email=…` on a **GitLab/GitHub** policy (docs reserve `email` for Email IdP / some cloud principals)
- Google-style `user=person@company.com` on a **GitLab** policy

### 4. Missing provider tag / empty clause

Policies should usually include both claim predicate(s) and the IdP tag element
as stored by the platform (inspect a known-good peer policy in the same tenant).

### 5. Propagate vs target confusion

`target_namespaces=["tenant"]` + `propagate=false` does **not** authorize
`tenant.child`. That is scope intent, not form — still flag when the customer
expected child access.

## Workflow

1. Resolve tenant root (`ENDOR_NAMESPACE` / `-n` / endorctl config). Prefer
   **API key** or an admin bearer that can `AuthorizationPolicy.list`.
2. List policies: `client.AuthorizationPolicy.list(namespace=<tenant>, traverse=…)`
   (use `traverse=True` only when policies live under children).
3. Run form heuristics (manual checklist or script below).
4. For each finding: cite `uuid`, `meta.name`, field, observed value, suggested fix.
5. If form is clean but login still fails → hand off to
   [endor-troubleshoot-authlog](../endor-troubleshoot-authlog/SKILL.md) /
   [endor-sso-integration-validation-troubleshooting](../endor-sso-integration-validation-troubleshooting/SKILL.md).

### Scripted scan

Prefer library imports, then the thin skill CLI:

```python
from endorlabs import Client
from endorlabs.workflows.auth import (
    audit_authorization_policy_forms,
    list_authorization_policies,
)

client = Client(tenant="<tenant>")
records = list_authorization_policies(client, namespace="<tenant>", traverse=False)
findings = audit_authorization_policy_forms(list(records))
client.close()
```

```bash
uv run --env-file .env python \
  .endorlabs-context/sdk/skills/endor-audit-authorization-policies/scripts/audit_authorization_policies.py \
  --tenant-hint <tenant> \
  --output-dir .endorlabs-context/workspace/runs/audit-authorization-policies
```

Authoring path (this repo): `sdk/skills/endor-audit-authorization-policies/scripts/…`.
Library: `endorlabs.workflows.auth.list_authorization_policies`,
`audit_authorization_policy_forms`.

## Outputs

| Artifact | Default |
|----------|---------|
| Findings JSON | `.endorlabs-context/workspace/runs/audit-authorization-policies/auth_policy_form_audit.json` |

Override with `--output-dir`. Never write secrets or full bearer tokens.

## Related skills

| Need | Skill |
| ---- | ----- |
| Credentials / `endor-auth` | [endor-auth-setup](../endor-auth-setup/SKILL.md) |
| SSO setup + claim→namespace spot-check | [endor-sso-integration-validation-troubleshooting](../endor-sso-integration-validation-troubleshooting/SKILL.md) |
| AuthenticationLog RCA | [endor-troubleshoot-authlog](../endor-troubleshoot-authlog/SKILL.md) |
| Login activity CSV | [endor-auth-login-count](../endor-auth-login-count/SKILL.md) |
