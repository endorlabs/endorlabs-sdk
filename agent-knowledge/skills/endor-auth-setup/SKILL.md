---
name: endor-auth-setup
description: >-
  Probe, verify, and refresh Endor Labs SDK credentials before API workflows.
  Covers env-key scan, Client whoami check, endorctl detection, and interactive
  browser token refresh into .env. Use as step zero for any tenant session—not
  for SSO policy mapping or AuthenticationLog RCA.
endorlabs:
  catalog:
    workflow_id: auth-setup
    module: endorlabs.workflows.auth.cli
    cli: endor-auth
    agent_visible: true
    library_entrypoints:
      - endorlabs.workflows.auth.scan_auth_env
      - endorlabs.workflows.auth.verify_auth
      - endorlabs.workflows.auth.refresh_token_to_dotenv
      - endorlabs.workflows.auth.probe_endorctl
---

# Authentication setup

Step-zero playbook for **SDK**, **endorctl**, and **MCP** consumers. Normative env
rules live in [errors-and-auth](../../contracts/errors-and-auth.md).

## Prerequisites

- **SDK install:** `pip install endorlabs` (or `uv` in this repo). See [README.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/README.md#installation).
- **Bootstrap (agents):** `endorlabs.init()` or `uv run endor-context --sync-skills cursor` —
  see [README.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/README.md#agent-bootstrap-discover-vs-init).
- **Not for CI:** browser refresh opens localhost:30000 and requires a human present.

## Quick start

```bash
# 1. Probe env + whoami (no secret output)
uv run endor-auth check --tenant <tenant>

# 2. If missing or expired — interactive browser SSO into .env
uv run endor-auth refresh --method sso -n <tenant>

# 3. Re-check, then run workflows with --env-file
uv run --env-file .env endor-auth check --tenant <tenant>
```

JSON for agents:

```bash
uv run endor-auth check --tenant <tenant> --json
```

## CLI (`endor-auth`)

| Subcommand | Purpose |
|------------|---------|
| **`check`** | Scan env keys (booleans only), probe endorctl, run `Client().whoami()` when creds exist |
| **`refresh`** | Browser OAuth → upsert `ENDOR_TOKEN` in a dotenv file |

### `endor-auth check`

| Flag | Default | Meaning |
|------|---------|---------|
| **`--tenant`** | unset | Pass to `Client(tenant=…)`; falls back to `ENDOR_NAMESPACE` / endorctl config |
| **`--json`** | off | Structured summary (`status`, `environment`, `endorctl`, `whoami`, `next_steps`) |

Exit **0** when `status=ready`; **1** otherwise.

### `endor-auth refresh`

| Flag | Default | Meaning |
|------|---------|---------|
| **`--env-file`** | `.env` | Dotenv path to create or update |
| **`--method`** | `sso` | `sso`, `google`, `github`, `gitlab`, or `email` |
| **`-n` / `--namespace`** | unset | SSO tenant (root segment). Fallback: `ENDOR_NAMESPACE`, dotenv, `~/.endorctl/config.yaml` |
| **`--email`** | unset | Required when `--method=email` |
| **`--environment`** | from `ENDOR_API` | API host segment for auth URLs |
| **`--timeout`** | `120` | OAuth callback wait (seconds) |

Does **not** print the token — only confirms the file was updated.

## Library

`verify_auth` bundles `scan_auth_env`, `probe_endorctl`, and `Client().whoami()`.
Call pieces separately when you only need env or endorctl probes. Session layer map:
`endorlabs.workflows.auth.session` module docstring.

```python
from endorlabs.workflows.auth import (
    scan_auth_env,
    verify_auth,
    refresh_token_to_dotenv,
    probe_endorctl,
)

scan = scan_auth_env()
result = verify_auth(tenant="<tenant>")
endorctl = probe_endorctl()
```

## Decision tree

| Situation | Action |
|-----------|--------|
| `dual_mode_conflict` | Unset `ENDOR_TOKEN` **or** both API key env vars — [errors-and-auth](../../contracts/errors-and-auth.md) |
| No creds, `endorctl` on PATH | `endorctl init --auth-mode=sso --auth-tenant=<tenant>` (persists to `~/.endorctl/config.yaml`) |
| No creds, SDK-only | API key in `.env` **or** `endor-auth refresh --method sso -n <tenant>` |
| `whoami` fails / 401 | `endor-auth refresh` (token expired) |
| `whoami` fails / 403 | Wrong tenant or insufficient scope — fix `ENDOR_NAMESPACE` / credential access |
| Creds OK | Proceed to task skills (`endor-retrieve-scan-results`, …) with `uv run --env-file .env` |

**Single auth mode:** SDK, endorctl, and MCP must not mix bearer token and API key in the same environment.

## API key alternative (CI / automation)

Set in `.env` (never commit secrets):

```bash
ENDOR_API_CREDENTIALS_KEY=...
ENDOR_API_CREDENTIALS_SECRET=...
ENDOR_NAMESPACE=<tenant.namespace>
```

Verify: `uv run --env-file .env endor-auth check`.

Platform reference (after `init(include_user_docs=True)`):
`.endorlabs-context/platform/user-docs/developers-api/cli/install-and-configure.md`

## Related skills

| Need | Skill |
| ---- | ----- |
| Auth setup / refresh | **This skill** |
| Login activity CSV | [endor-auth-login-count](../endor-auth-login-count/SKILL.md) |
| SSO / login RCA | [endor-troubleshoot-authlog](../endor-troubleshoot-authlog/SKILL.md) |
| SDK list / traverse errors | [endor-troubleshoot-sdk](../endor-troubleshoot-sdk/SKILL.md) |
