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
- **Local context (optional):** API spec at `.endorlabs-context/openapiv2.swagger.json`;
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

Implementation file: [troubleshoot_authlog.py](troubleshoot_authlog.py)

Run from repo root:

```bash
uv run --env-file .env python .cursor/skills/troubleshoot-authlog/troubleshoot_authlog.py \
  --target-email user@example.com \
  --tenant-hint ice \
  --target-group-claim your-ad-group-slug \
  --max-pages-auth 200 \
  --max-pages-policy 20 \
  --investigation-export \
  --output-dir .tmp
```

**Useful flags**

| Flag | Purpose |
|------|---------|
| `--target-user-claim` | Exact `user=...` value (e.g. `email@domain@idp-marker`) |
| `--target-group-claim` | Exact group name without `groups=` prefix |
| `--max-pages-auth` / `--max-pages-policy` / `--max-pages-audit` | Pagination depth |
| `--include-audit` | Parallel `AuditLog` sweep per discovered namespace |
| `--control-email` | Known-positive control for SSO filter validation |
| `--investigation-export` | Also write structured investigation JSON (evidence + scalars) |
| `--investigation-max-auth-rows-per-probe N` | Cap rows **only** in investigation evidence file (`0` = no cap) |

## Outputs (same timestamp per run)

| File | Contents |
|------|----------|
| `authlog_probe_report.<stamp>.json` | Full report: `sampling`, `filters`, validation/auth rows, policies, `sso_uri_slice_user_claim_policy_correlation`, `diagnostics` |
| `authlog_probe_summary.<stamp>.json` | Scalar counts for triage |
| `authlog_investigation_evidence.<stamp>.json` | If `--investigation-export`: structured evidence (same stamp as other outputs) |
| `authlog_investigation_scalars.<stamp>.json` | If `--investigation-export`: scalars only (no interpretive "suspected" flags) |

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
