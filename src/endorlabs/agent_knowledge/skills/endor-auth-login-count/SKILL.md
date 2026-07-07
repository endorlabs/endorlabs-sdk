---
name: endor-auth-login-count
description: Aggregate AuthenticationLog login activity by user identity over a configurable
  lookback window (default 90 days). Outputs a CSV with identity, user identifiers,
  last login, and login count. Shares workflow helpers with auth troubleshooting skills.
  Use for tenant login-activity audits—not for SSO policy mapping or per-user auth
  RCA.
---

# Authentication login count report

Produce a **login activity CSV** for one tenant from `AuthenticationLog` rows in
the last **N days** (default **90**), aggregated by **identity** derived from
`spec.claims`.

## Prerequisites

- **SDK install:** `pip install endorlabs` (or `uv` in this repo). See [README.md](../../../README.md#installation).
- **Credentials:** API key pair or browser SSO token in `.env`, loaded with
  `uv run --env-file .env …`. Environment variables:
  `ENDOR_API_CREDENTIALS_KEY` / `ENDOR_API_CREDENTIALS_SECRET`, or `ENDOR_TOKEN`
  after browser refresh (`devtools/refresh_token_to_dotenv.py` with `--sso` and
  `-n <tenant>` when needed). The credential must be authorized to **list**
  `AuthenticationLog` on the target tenant; **403** usually means wrong tenant or
  insufficient scope for that namespace.
- **Bootstrap (agents):** workflow library code ships in the wheel (`endorlabs.workflows.auth`).
  To materialize this playbook on disk, run `endorlabs.init()` or
  `uv run endor-context --sync-skills cursor` — see [README.md](../../../README.md#agent-bootstrap-discover-vs-init)
  and [agent-knowledge/README.md](../../README.md). Runtime skill path:
  `.endorlabs-context/sdk/skills/endor-auth-login-count/`.
- **Outputs:** write under `.endorlabs-context/workspace/sessions/<user>/exports/`
  (see [workspace-layout](../../rules/endor-workspace-layout.md)).

## Scope

**In scope**

- `AuthenticationLog.list` on the tenant list path (`namespace=<tenant>`, `traverse=False`).
- `AuthenticationLog.list_groups(paths=["spec.claims"])` for server-side counts (default).
- Successful interactive logins by default (interactive `spec.uri` filter).
- CSV report: identity, user identifiers, last login, login count in N days.

**Out of scope**

- Per-user SSO failure RCA or policy clause matching → [endor-troubleshoot-authlog](../endor-troubleshoot-authlog/SKILL.md)
- SSO integration setup / claims-to-namespace mapping → [endor-sso-integration-validation-troubleshooting](../endor-sso-integration-validation-troubleshooting/SKILL.md)
- AuditLog or AuthorizationPolicy analysis → [endor-troubleshoot-authlog](../endor-troubleshoot-authlog/SKILL.md)

## CSV schema (required)

Write CSV with **exactly these four columns**, in this order:

| Column | Meaning |
|--------|---------|
| **`identity`** | Primary aggregation key (best email from claims, else first identifier) |
| **`user identifiers`** | Semicolon-separated `email=`, `user=`, `id=` claim strings for the identity |
| **`last login`** | ISO timestamp of the most recent counted login (`meta.create_time`) |
| **`login count in <N> days`** | Count of login events in the lookback window (column name includes N) |

Header example for the default window:

```text
identity,user identifiers,last login,login count in 90 days
```

## Bundled CLI (`login_count_report.py`)

Run from repo authoring path or from `.endorlabs-context/sdk/skills/endor-auth-login-count/scripts/`
after `init()`.

```bash
uv run --env-file .env python sdk/skills/endor-auth-login-count/scripts/login_count_report.py \
  --tenant <tenant> \
  --days 90
```

| Flag | Default | Meaning |
|------|---------|---------|
| **`--tenant`** | *(required)* | Tenant namespace for `Client(tenant=…)` and list `namespace=` |
| **`--days`** | `90` | Lookback window in days (`meta.create_time>=date(…)` filter) |
| **`--output`** | `workspace/sessions/<user>/exports/login-count-<tenant>-<days>d.csv` | CSV path |
| **`--json-summary`** | unset | Optional JSON summary path (adds `csv` key with output path) |
| **`--max-pages`** | unset | Cap `list` / `list_groups` pagination depth |
| **`--platform-wide`** | off | Set `traverse=True` (fan out child namespaces). Default: tenant list path only |
| **`--include-failed`** | off | Include rows with `spec.success==false` |
| **`--include-api-key`** | off | Drop interactive URI filter; include `/v1/auth/api-key` events |
| **`--list-rows`** | off | Client-side aggregation from full `list` rows instead of `list_groups` |

Default output: `.endorlabs-context/workspace/sessions/<user>/exports/login-count-<tenant>-<days>d.csv`

## endorctl parity

Equivalent count query (use **hours** in `now(-…h)` — `now(-7d)` is invalid):

```bash
endorctl api list -r AuthenticationLog -n <tenant> \
  --filter="meta.create_time>now(-2160h) and spec.success!=false and spec.uri matches '.*(/auth/google/callback|/auth/saml-callback|/auth/sso|/auth/oidc).*'" \
  --count \
  --timeout 60s
```

Equivalent grouped query (matches default script aggregation):

```bash
endorctl api list -r AuthenticationLog -n <tenant> \
  --filter="meta.create_time>now(-2160h) and spec.success!=false and spec.uri matches '.*(/auth/google/callback|/auth/saml-callback|/auth/sso|/auth/oidc).*'" \
  --group-aggregation-paths spec.claims \
  --timeout 60s
```

| endorctl flag | Role |
|---------------|------|
| **`-r AuthenticationLog`** | Resource kind |
| **`-n <tenant>`** | List path namespace (tenant scoping — do **not** use `tenant_meta.namespace` filter) |
| **`--filter`** | Same MQL as SDK `build_authentication_log_filter()` |
| **`--count`** | Row count only (fast probe) |
| **`--group-aggregation-paths spec.claims`** | Server-side identity buckets |
| **`--timeout`** | Raise for large windows (e.g. `90s` at 90 days) |
| **`--traverse`** | Only with `--platform-wide` / child-namespace fan-out |

Pass **`--api-key`** / **`--api-secret`** (or env) for API-key auth; **`--token`** for bearer token.

## Workflow (library)

### Step 1: Fetch login counts (default — server-side groups)

```python
import endorlabs
from endorlabs.workflows.auth import aggregate_login_activity_from_groups

client = endorlabs.Client(tenant="<tenant>")
activity = aggregate_login_activity_from_groups(
    client,
    days=90,
    namespace="<tenant>",
    traverse=False,
)
client.close()
```

**Server aggregation:** `AuthenticationLog.list_groups(paths=["spec.claims"])` with the
list filter below. The API groups on the **full claims array** per row; for
interactive Google/SSO logins each user has a stable claim set, so buckets map
1:1 to identities. Counts come from `aggregation_count.count` on each bucket.

**`last login`:** supplemental sorted `list` (`meta.create_time` desc, one page) with
unsorted fallback max scan — not available from `list_groups` alone.

**Fallback — client-side row aggregation:**

```python
from endorlabs.workflows.auth import (
    aggregate_login_activity,
    fetch_authentication_logs,
)

rows = fetch_authentication_logs(
    client,
    days=90,
    namespace="<tenant>",
    traverse=False,
)
activity = aggregate_login_activity(rows, days=90)
```

**List filter (default — interactive human logins)**

```text
meta.create_time>=date(<iso>)
  and spec.success!=false
  and spec.uri matches '.*(/auth/google/callback|/auth/saml-callback|/auth/sso|/auth/oidc).*'
```

**Field mask:** `meta.create_time,spec.claims,spec.uri,spec.success,spec.remote_address`

**Tenant scoping trap:** use **`namespace=<tenant>`** and **`traverse=False`**.
Do **not** add `tenant_meta.namespace=="<tenant>"` to the filter — wire rows often
show `system` but are returned on the tenant list path. A `tenant_meta.namespace`
filter typically returns **zero** rows.

### Step 2: Summarize

Report total identities, total login events, top identities by count, and the CSV path.

## Related skills

| Need | Skill |
| ---- | ----- |
| Login count / activity audit | **This skill** |
| Single-user SSO failure or policy correlation | [endor-troubleshoot-authlog](../endor-troubleshoot-authlog/SKILL.md) |
| SSO integration validation | [endor-sso-integration-validation-troubleshooting](../endor-sso-integration-validation-troubleshooting/SKILL.md) |
| SDK list / traverse errors | [endor-troubleshoot-sdk](../endor-troubleshoot-sdk/SKILL.md) |
