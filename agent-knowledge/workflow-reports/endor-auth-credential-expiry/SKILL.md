---
name: endor-auth-credential-expiry
description: |
  Use when auditing tenant APIKey resources for expired or soon-to-expire
  credentials—listing keys on a namespace path, classifying expiration, and writing
  a CSV report (default 30-day lookahead). Not for bearer ENDOR_TOKEN refresh, SSO
  policy mapping, or AuthenticationLog RCA.
endorlabs:
  catalog:
    workflow_id: auth-credential-expiry
    module: endorlabs.workflows.auth.credential_expiry
    agent_visible: true
    library_entrypoints:
      - endorlabs.workflows.auth.audit_api_key_expiry
      - endorlabs.workflows.auth.list_api_keys
      - endorlabs.workflows.auth.classify_expiration
      - endorlabs.workflows.auth.build_credential_expiry_row
      - endorlabs.workflows.auth.expiry_upper_bound_filter
---

# Credential expiry audit

Produce a **credential expiry CSV** for one tenant by listing `APIKey` rows and
flagging keys that are **expired** or **expiring within N days** (default **30**).

## Prerequisites

- **SDK install:** `pip install endorlabs` (or `uv` in this repo). See [README.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/README.md#installation).
- **Credentials:** Set up auth first — skill [endor-auth-setup](../endor-auth-setup/SKILL.md)
  or `uv run endor-auth check --tenant <tenant>`.
- **Bootstrap (agents):** workflow library code ships in the wheel (`endorlabs.workflows.auth`).
  To materialize this playbook on disk, run `endorlabs.init()` or
  `uv run endor-context --sync-skills cursor` — see [README.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/README.md#agent-bootstrap-discover-vs-init).
- **Outputs:** write under `.endorlabs-context/workspace/runs/auth-credential-expiry/`
  (see [workspace-layout](../../rules/endor-workspace-layout.md)).

## Scope

**In scope**

- `APIKey.list` on the tenant list path (`namespace=<tenant>`).
- Optional `traverse=True` (`--platform-wide`) to include child namespaces.
- Expiration classification from `spec.expiration_time`.
- CSV report: kind, name, namespace, uuid, key id, expiration, status, days until expiry.

**Out of scope**

- Bearer `ENDOR_TOKEN` session expiry for the current shell → [endor-auth-setup](../endor-auth-setup/SKILL.md) (`endor-auth check`)
- `SCMCredential` private Git PAT health — not on the SDK facade yet; use platform UI or `endorctl` when available
- Login activity or SSO failure RCA → [endor-auth-login-count](../endor-auth-login-count/SKILL.md), [endor-troubleshoot-authlog](../endor-troubleshoot-authlog/SKILL.md)
- AuthorizationPolicy `expiration_time` (policy disable dates, not API credentials)

## Library layers

Default: `audit_api_key_expiry` (list + classify + sort). Optional server filter:
`expiry_upper_bound_filter(within_days)` when narrowing large tenants before client
classification. Layer map: `endorlabs.workflows.auth.credential_expiry` module docstring.

## CSV schema (required)

Write CSV with **exactly these columns**, in this order:

| Column | Meaning |
|--------|---------|
| **`kind`** | Resource kind (`APIKey`) |
| **`name`** | `meta.name` |
| **`namespace`** | `tenant_meta.namespace` |
| **`uuid`** | API key UUID |
| **`key id`** | `spec.key` (identifier only — never the secret) |
| **`expiration time`** | `spec.expiration_time` (ISO) |
| **`status`** | `expired`, `expiring_soon`, `ok`, or `unknown` |
| **`days until expiry`** | Whole days until expiration (negative when expired) |
| **`propagate`** | `yes` / `no` from `propagate` |
| **`issuing user`** | Best-effort label from `spec.issuing_user` |

## Bundled CLI (`credential_expiry_report.py`)

Run from repo authoring path or from `agent-knowledge/workflow-reports/endor-auth-credential-expiry/scripts/`
after `init()`.

```bash
uv run --env-file .env python agent-knowledge/workflow-reports/endor-auth-credential-expiry/scripts/credential_expiry_report.py \
  --tenant <tenant> \
  --within-days 30 \
  --platform-wide
```

| Flag | Default | Meaning |
|------|---------|---------|
| **`--tenant`** | *(required)* | Tenant namespace for `Client(tenant=…)` and list `namespace=` |
| **`--within-days`** | `30` | Flag keys expiring within this many days |
| **`--output`** | `workspace/runs/auth-credential-expiry/credential-expiry-<tenant>-<days>d.csv` | CSV path |
| **`--json-summary`** | unset | Optional JSON summary path (adds `csv` key with output path) |
| **`--max-pages`** | unset | Cap `APIKey.list` pagination depth |
| **`--platform-wide`** | off | Set `traverse=True` (fan out child namespaces). Default: tenant list path only |
| **`--include-healthy`** | off | Include keys that are not expired or expiring soon |

Default output: `.endorlabs-context/workspace/runs/auth-credential-expiry/credential-expiry-<tenant>-<days>d.csv`

Exit code **1** when at least one key is **expired** (useful for scheduled checks).

## endorctl parity

List API keys in a namespace:

```bash
endorctl api list -r APIKey -n <tenant> \
  --mask="meta.name,tenant_meta.namespace,uuid,propagate,spec.expiration_time,spec.key" \
  --timeout 60s
```

Tenant-wide (child namespaces):

```bash
endorctl api list -r APIKey -n <tenant> --traverse \
  --mask="meta.name,tenant_meta.namespace,uuid,propagate,spec.expiration_time,spec.key" \
  --timeout 120s
```

Optional server-side pre-filter for keys expiring on or before a date:

```bash
endorctl api list -r APIKey -n <tenant> --traverse \
  --filter='spec.expiration_time<=date(2026-08-07)' \
  --mask="meta.name,tenant_meta.namespace,uuid,spec.expiration_time" \
  --timeout 120s
```

| endorctl flag | Role |
|---------------|------|
| **`-r APIKey`** | Resource kind |
| **`-n <tenant>`** | List path namespace |
| **`--traverse`** | Include child namespaces |
| **`--filter`** | MQL on `spec.expiration_time` (optional pre-filter) |
| **`--mask`** | Trim fields — never request `spec.secret` |

Pass **`--api-key`** / **`--api-secret`** (or env) for API-key auth; **`--token`** for bearer token.

## Workflow (library)

### Step 1: Audit API key expiration

```python
import endorlabs
from endorlabs.workflows.auth.credential_expiry import audit_api_key_expiry

client = endorlabs.Client(tenant="<tenant>")
rows = audit_api_key_expiry(
    client,
    namespace="<tenant>",
    within_days=30,
    traverse=True,
)
client.close()
```

**Classification**

| Status | Condition |
|--------|-----------|
| `expired` | `spec.expiration_time` is in the past |
| `expiring_soon` | Expires within `within_days` (default 30) |
| `ok` | Expires after the lookahead window |
| `unknown` | Missing or unparsable `spec.expiration_time` |

Rows sort with **expired** first, then **expiring_soon**, then by days until expiry.

**Optional server filter** before client classification:

```python
from endorlabs.workflows.auth.credential_expiry import expiry_upper_bound_filter

filt = expiry_upper_bound_filter(30)
keys = client.APIKey.list(
    namespace="<tenant>",
    traverse=True,
    filter=filt,
    mask="meta.name,tenant_meta.namespace,uuid,spec.expiration_time,spec.key",
)
```

### Step 2: Summarize

Report counts of expired vs expiring-soon keys, highlight namespaces with
`propagate=yes` keys nearing expiry, and the CSV path. Do **not** print
`spec.secret` or env credential values.

## Related skills

| Need | Skill |
| ---- | ----- |
| Credential expiry / API key rotation planning | **This skill** |
| Probe or refresh the current session token | [endor-auth-setup](../endor-auth-setup/SKILL.md) |
| Login activity audit | [endor-auth-login-count](../endor-auth-login-count/SKILL.md) |
| SSO login failure RCA | [endor-troubleshoot-authlog](../endor-troubleshoot-authlog/SKILL.md) |
| SDK list / traverse errors | [endor-troubleshoot-sdk](../endor-troubleshoot-sdk/SKILL.md) |
