---
name: endor-auth-setup
description: Probe, verify, and refresh Endor Labs SDK credentials before API workflows.
  Covers env-key scan, Client whoami check, endorctl detection, and interactive browser
  token refresh into .env. Use as step zero for any tenant session—not for SSO policy
  mapping or AuthenticationLog RCA.
---

# Authentication setup

Step-zero playbook for **SDK**, **endorctl**, and **MCP** consumers. Normative env
rules live in [errors-and-auth](../../contracts/errors-and-auth.md).

## Prerequisites

- **SDK install:** `pip install endorlabs` (or `uv` in this repo). See [README.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/README.md#installation).
- **Bootstrap (agents):** `endorlabs.init()` or `uv run endor-context --sync-skills cursor` —
  see [README.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/README.md#agent-bootstrap-discover-vs-init).
- **Not for CI:** browser refresh opens localhost:30000 and requires a human present.

## Environment variables (Tier A — ongoing sessions)

| Variable | When to set | endorctl flag | SDK / `endor-auth` |
|----------|-------------|---------------|---------------------|
| `ENDOR_TOKEN` | After browser refresh | `--token` | Yes |
| `ENDOR_API_CREDENTIALS_KEY` + `SECRET` | CI / automation | `--api-key` / `--api-secret` | Yes |
| `ENDOR_NAMESPACE` | Tenant-scoped work; SSO tenant root (`<tenant>.<child>` → `<tenant>`) | `-n` / `--namespace` | Yes |
| `ENDOR_API` | Non-default API host | `-a` / `--api` | Yes |
| `ENDOR_CONFIG_PATH` | Non-default endorctl config dir | `--config-path` | Yes (namespace fallback) |

**SSO tenant precedence** (refresh + reauth): `endor-auth refresh -n` → `ENDOR_NAMESPACE` (shell, then `.env`) → `ENDOR_NAMESPACE` in endorctl `config.yaml` (via `ENDOR_CONFIG_PATH`).

**Single auth mode:** never set `ENDOR_TOKEN` and both API key vars (same rule as endorctl). No `ENDOR_AUTH_MODE` env — unset one credential set or pass `auth_method=` to `Client(...)` in code.

**Do not document or invent:** `ENDOR_AUTH_TENANT`, `ENDOR_AUTH_MODE`, `ENDOR_AUTH_METHOD`, `ENDOR_BROWSER`, `ENDOR_AUTH_INTERACTIVE`, `ENDOR_AUTH_PERSIST_TOKEN`, `ENDOR_TOKEN_REFRESH_METHOD`.

### `endorctl init` env vars (Tier B — init-time only)

| Variable | Flag | Use |
|----------|------|-----|
| `ENDOR_INIT_AUTH_MODE` | `--auth-mode` | `sso`, `google`, `github`, `gitlab`, `azureadv2` |
| `ENDOR_INIT_AUTH_TENANT` | `--auth-tenant` | Required for `sso` |
| `ENDOR_INIT_AUTH_EMAIL` | `--auth-email` | Email-link login |
| `ENDOR_INIT_HEADLESS_MODE` | `--headless-mode` | Headless init |

*These apply only while running `endorctl init`. They are not read by `endor-auth refresh` or `Client()` for day-to-day API work. After init, use Tier A vars (or config file).*

## Quick start

```bash
# 1. Probe env + whoami (no secret output)
uv run endor-auth check --tenant <namespace>

# 2. If missing or expired — interactive browser SSO into .env
uv run endor-auth refresh --method sso -n <tenant>

# 3. Re-check, then run workflows with --env-file
uv run --env-file .env endor-auth check --tenant <namespace>
```

JSON for agents:

```bash
uv run endor-auth check --tenant <namespace> --json
```

Fields include `auth_mode_resolved`, `sso_tenant_resolved`, `browser_auth_method_resolved`, and `whoami.expires_in_seconds`.

## CLI (`endor-auth`)

| Subcommand | Purpose |
|------------|---------|
| **`check`** | Scan env keys (booleans only), probe endorctl, run `Client().whoami()` when creds exist |
| **`refresh`** | Browser OAuth → upsert `ENDOR_TOKEN` in a dotenv file |

### `endor-auth check`

| Flag | Default | Meaning |
|------|---------|---------|
| **`--tenant`** | unset | Pass to `Client(tenant=…)`; falls back to `ENDOR_NAMESPACE` / endorctl config |
| **`--json`** | off | Structured summary (`status`, `environment`, `endorctl`, `whoami`, `next_steps`, `auth_mode_resolved`, `sso_tenant_resolved`) |

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

## endorctl entrypoint

```bash
endorctl init --auth-mode=sso --auth-tenant=<tenant>
```

Persists credentials and namespace under `~/.endorctl/` (or `ENDOR_CONFIG_PATH`).

## Library

`verify_auth` bundles `scan_auth_env`, `probe_endorctl`, and `Client().whoami()`.
Call pieces separately when you only need env or endorctl probes.

```python
from endorlabs.workflows.auth import (
    scan_auth_env,
    verify_auth,
    refresh_token_to_dotenv,
    probe_endorctl,
)

scan = scan_auth_env()
result = verify_auth(tenant="<namespace>")
endorctl = probe_endorctl()
```

## Decision tree

| Situation | Action |
|-----------|--------|
| `dual_mode_conflict` | Unset `ENDOR_TOKEN` **or** both API key env vars — [errors-and-auth](../../contracts/errors-and-auth.md) |
| No creds, `endorctl` on PATH | `endorctl init --auth-mode=sso --auth-tenant=<tenant>` (persists to `~/.endorctl/config.yaml`) |
| No creds, SDK-only | API key in `.env` **or** `endor-auth refresh --method sso -n <tenant>` |
| Bearer without `ENDOR_NAMESPACE` | Set `ENDOR_NAMESPACE` or pass `-n` / `--tenant` |
| `whoami` fails / 401 | `endor-auth refresh` (token expired) |
| `whoami` fails / 403 | Wrong tenant or insufficient scope — fix `ENDOR_NAMESPACE` / credential access |
| Creds OK | Proceed to task skills (`endor-retrieve-scan-results`, …) with `uv run --env-file .env` |

**Single auth mode:** SDK, endorctl, and MCP must not mix bearer token and API key in the same environment.

## `.env` primer

```bash
ENDOR_TOKEN=...
ENDOR_NAMESPACE=<tenant.namespace>
```

Use **one** credential mode per file (bearer **or** API key pair).

## API key alternative (CI / automation)

```bash
ENDOR_API_CREDENTIALS_KEY=...
ENDOR_API_CREDENTIALS_SECRET=...
ENDOR_NAMESPACE=<tenant.namespace>
```

Verify: `uv run --env-file .env endor-auth check`.

## Harness matrix

| Harness | Auth behavior |
|---------|----------------|
| Human local | `endor-auth refresh` then `uv run --env-file .env` workflows |
| Agent / sandbox (no browser) | Run `endor-auth check`; output `endor-auth refresh` for human — do not open browser |
| Long scripted session | One `Client` instance; bearer sessions warn before expiry, then raise `UnauthorizedError` when expired |
| Persist token | **Only** `endor-auth refresh` — `Client` never writes refreshed bearer state to disk |

## Expired token mid-session

- **In-memory only:** one `Client` instance holds the bearer until it expires; no `.env` or `os.environ` writes.
- **Proactive:** when expiry is within 30 minutes, `Client` prints a **one-time stderr warning** (no token values) with the matching `endor-auth refresh --method …` command; `endor-auth check --json` also exposes `expires_in_seconds`.
- **Expired / 401:** bearer auth fails closed with `UnauthorizedError`; rerun `endor-auth refresh` before continuing.
- **Next process:** run `endor-auth refresh` (or pass `token=` again) — child shells do not inherit in-memory tokens.

## Related skills

| Need | Skill |
| ---- | ----- |
| Auth setup / refresh | **This skill** |
| Login activity CSV | [endor-auth-login-count](../endor-auth-login-count/SKILL.md) |
| API key expiration audit | [endor-auth-credential-expiry](../endor-auth-credential-expiry/SKILL.md) |
| SSO / login RCA | [endor-troubleshoot-authlog](../endor-troubleshoot-authlog/SKILL.md) |
| SDK list / traverse errors | [endor-troubleshoot-sdk](../endor-troubleshoot-sdk/SKILL.md) |
