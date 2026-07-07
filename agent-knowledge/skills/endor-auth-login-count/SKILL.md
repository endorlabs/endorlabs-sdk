---
name: endor-auth-login-count
description: >-
  Aggregate AuthenticationLog login activity by user identity over a configurable
  lookback window (default 90 days). Outputs a CSV with identity, user identifiers,
  last login, and login count. Shares workflow helpers with auth troubleshooting
  skills. Use for tenant login-activity audits—not for SSO policy mapping or
  per-user auth RCA.
endorlabs:
  catalog:
    workflow_id: auth-login-count
    module: endorlabs.workflows.auth.authentication_log
    agent_visible: true
    library_entrypoints:
      - endorlabs.workflows.auth.aggregate_login_activity_from_groups
      - endorlabs.workflows.auth.fetch_authentication_logs
      - endorlabs.workflows.auth.aggregate_login_activity
      - endorlabs.workflows.auth.authentication_log_row_to_dict
      - endorlabs.workflows.auth.extract_user_identifiers
      - endorlabs.workflows.auth.is_api_key_noise
      - endorlabs.workflows.auth.is_sso_login_uri
---

# Authentication login count report

Produce a **tenant-wide login activity CSV** from `AuthenticationLog` rows in the
last **N days** (default **90**), aggregated by **identity** derived from
`spec.claims`.

## Scope

**In scope**

- `AuthenticationLog.list` on the tenant list path (`namespace=<tenant>`, `traverse=False`).
- `AuthenticationLog.list_groups(paths=["spec.claims"])` for server-side counts.
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

## Workflow

### Step 1: Fetch login counts (default — server-side groups)

```python
import endorlabs
from endorlabs.workflows.auth import aggregate_login_activity_from_groups

client = endorlabs.Client(tenant="<tenant>")
activity = aggregate_login_activity_from_groups(
    client,
    days=7,
    namespace="<tenant>",
    traverse=False,
)
client.close()
```

**Server aggregation:** `AuthenticationLog.list_groups(paths=["spec.claims"])` with the
same list filter below. The API groups on the **full claims array** per row; for
interactive Google/SSO logins each user has a stable claim set, so buckets map
1:1 to identities. Counts come from `aggregation_count.count` on each bucket.

**`last login`:** supplemental sorted `list_iter` (`meta.create_time` desc) with
early stop once every grouped identity has a timestamp — not available from
`list_groups` alone.

**Fallback — client-side row aggregation:**

```python
from endorlabs.workflows.auth import (
    aggregate_login_activity,
    fetch_authentication_logs,
)

rows = fetch_authentication_logs(
    client,
    days=7,
    namespace="<tenant>",
    traverse=False,
)
activity = aggregate_login_activity(rows, days=7)
```

Use `--list-rows` on the bundled script to force the list path.

Library helpers live in `endorlabs.workflows.auth.authentication_log` — shared
normalization with [endor-troubleshoot-authlog](../endor-troubleshoot-authlog/SKILL.md).

**List filter (default — interactive human logins)**

```text
meta.create_time>=date(<iso>)
  and spec.success!=false
  and spec.uri matches '.*(/auth/google/callback|/auth/saml-callback|/auth/sso|/auth/oidc).*'
```

**Field mask:** `meta.create_time,spec.claims,spec.uri,spec.success,spec.remote_address`

**Tenant scoping (default):** list path only — equivalent to:

```bash
endorctl api list -r AuthenticationLog -n <tenant> \
  --filter="meta.create_time>now(-168h) and spec.uri matches '.*(/auth/google/callback|...).*'" \
  --group-aggregation-paths spec.claims
```

Use **`namespace=<tenant>`** and **`traverse=False`**. Do **not** add
`tenant_meta.namespace=="<tenant>"` to the filter — rows are stored under `system`
but are returned on the tenant list path (endorctl count ≈365 for tgowan 7d).

**`--platform-wide`:** sets `traverse=True` (child namespace fan-out).

Pass `--include-failed` to count unsuccessful attempts. Pass `--include-api-key`
to drop the interactive URI filter and include API-key automation events.

### Step 2: Write CSV

Default path: `.endorlabs-context/workspace/sessions/<user>/exports/login-count-<tenant>-<days>d.csv`

Bundled script:

```bash
uv run --env-file .env python agent-knowledge/skills/endor-auth-login-count/scripts/login_count_report.py \
  --tenant <tenant> \
  --days 90
```

After `init()` / sync, the same path under `.endorlabs-context/sdk/skills/endor-auth-login-count/scripts/`.

### Step 3: Summarize in chat

Report total identities, total login events, top identities by count, and the CSV path.

## Related skills

| Need | Skill |
| ---- | ----- |
| Login count / activity audit | **This skill** |
| Single-user SSO failure or policy correlation | [endor-troubleshoot-authlog](../endor-troubleshoot-authlog/SKILL.md) |
| SSO integration validation | [endor-sso-integration-validation-troubleshooting](../endor-sso-integration-validation-troubleshooting/SKILL.md) |
| SDK list / traverse errors | [endor-troubleshoot-sdk](../endor-troubleshoot-sdk/SKILL.md) |
