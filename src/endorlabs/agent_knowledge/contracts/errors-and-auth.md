---
id: errors-and-auth
tags:
- auth
- errors
---

# Errors and authentication

## Environment variables (Tier A — ongoing sessions)

Monorepo-backed variables for SDK, `endor-auth`, and `endorctl` day-to-day use:

| Variable | When to set | endorctl flag | SDK / `endor-auth` |
|----------|-------------|---------------|---------------------|
| `ENDOR_TOKEN` | After browser refresh | `--token` | Yes |
| `ENDOR_API_CREDENTIALS_KEY` + `SECRET` | CI / automation | `--api-key` / `--api-secret` | Yes |
| `ENDOR_NAMESPACE` | Tenant-scoped work; SSO tenant root (`<tenant>.<child>` → `<tenant>`) | `-n` / `--namespace` | Yes |
| `ENDOR_API` | Non-default API host | `-a` / `--api` | Yes |
| `ENDOR_CONFIG_PATH` | Non-default endorctl config dir | `--config-path` | Yes (namespace fallback) |
| `ENDOR_LOG_LEVEL` | Optional logging | `--log-level` | Yes |

**SSO tenant precedence** (refresh + mid-session reauth): `endor-auth refresh -n` → `ENDOR_NAMESPACE` (shell, then `.env`) → `ENDOR_NAMESPACE` in endorctl `config.yaml` (via `ENDOR_CONFIG_PATH`).

**Single auth mode:** never set `ENDOR_TOKEN` and both API key env vars (same rule as endorctl). No `ENDOR_AUTH_MODE` env — unset one credential set or pass `auth_method=` to `Client(...)` in code.

**Do not use for ongoing SDK sessions:** `ENDOR_AUTH_TENANT`, `ENDOR_AUTH_MODE`, `ENDOR_AUTH_METHOD`, `ENDOR_BROWSER`, `ENDOR_AUTH_INTERACTIVE`, `ENDOR_AUTH_PERSIST_TOKEN`, `ENDOR_ADMIN_TOKEN`.

### `endorctl init` only (Tier B)

| Variable | Flag | Notes |
|----------|------|-------|
| `ENDOR_INIT_AUTH_MODE` | `--auth-mode` | Exact endorctl enum: `github`, `google`, `gitlab`, `azureadv2`, `sso`, `browser-auth` |
| `ENDOR_INIT_AUTH_TENANT` | `--auth-tenant` | Required when `auth-mode=sso` |
| `ENDOR_INIT_AUTH_EMAIL` | `--auth-email` | Email-link login |
| `ENDOR_INIT_HEADLESS_MODE` | `--headless-mode` | No browser during init |

These apply **only** while running `endorctl init`. They are **not** read by `endor-auth refresh` or `Client()` for day-to-day API work. After init, use Tier A vars (or config file).

## Read-only access (default)

- **Read** with `os.getenv` — treat missing or blank as unset.
- **Do not** assign to `os.environ` or call `os.putenv` from SDK code, agents, or session scripts unless a human explicitly requests a credential refresh or `.env` update.
- **Do not** write resolved defaults back into the process environment (e.g. setting `ENDOR_API` during `Client()` construction).
- Confirm variables exist without printing values (rule `endor-local-context`).
- `.env` upserts belong to documented auth workflows (`endor-auth refresh`) — not generic API helpers.

## Single auth mode (SDK, endorctl, MCP)

Use **one** credential mode in `.env` or the environment:

| Mode | Variables |
|------|-----------|
| Bearer token | `ENDOR_TOKEN` (load once at process start) + `ENDOR_NAMESPACE` (API scope; SSO tenant when method is `sso`) |
| API key | `ENDOR_API_CREDENTIALS_KEY` + `ENDOR_API_CREDENTIALS_SECRET` |

When **both** `ENDOR_TOKEN` and API key env vars are set:

- **SDK:** prefers bearer and logs INFO naming the conflict.
- **endorctl / platform MCP:** typically fail with conflicting authentication methods.

**Remediation:** unset either `ENDOR_TOKEN` or both API key variables before using MCP or endorctl alongside the SDK.

## Missing credentials

`ValidationError` from `APIClient` / `Client` construction lists these options:

1. `ENDOR_TOKEN` (bearer; validated at `Client()` startup)
2. `ENDOR_API_CREDENTIALS_KEY` + `ENDOR_API_CREDENTIALS_SECRET`
3. `Client(auth_method=…)` when browser login must be explicit (see below)

### Interactive browser methods (opt-in)

Documented as supported for SDK / `endor-auth refresh` only when live-verified:

| `auth_method` / `--method` | Behavior |
|----------------------------|----------|
| `sso` | SSO URL; **requires** `auth_tenant=` / `-n` / `ENDOR_NAMESPACE` (tenant root) — no silent `endor-admin`. `/v1/auth` often reports `authentication_source` as the IdP object id (mapped to `sso`). |
| `google` | Direct `/v1/auth/google?redirect=cli` |
| `github` | Direct `/v1/auth/github?redirect=cli` |
| `gitlab` | Direct `/v1/auth/gitlab?redirect=cli` |
| `email` | Email magic-link; **requires** `--email` / `auth_email=`. `/v1/auth` reports `authentication_source=endor` |

Other endorctl-style modes (`azureadv2`, `browser-auth`) may exist in code for parity experiments; **do not treat them as supported** until listed here after a live check.

Bare `Client()` / `APIClient()` **does not** open a browser when credentials are missing.

Use `endor-auth refresh --method sso -n <tenant>`, `--method google`, `--method github`, `--method gitlab`, or `--method email --email <addr>` to persist `ENDOR_TOKEN` to `.env`.

## Bearer session (in-memory only)

`Client()` **never** writes `ENDOR_TOKEN`, mutates `os.environ`, or upserts `.env`. Cross-session persistence is **only** via `endor-auth refresh` (human/agent opt-in).

| Phase | Behavior |
|-------|----------|
| Startup | Read `ENDOR_TOKEN` or `token=`; validate via `GET /v1/auth`; learn refresh hint routing in-memory (`google`, `sso`, …) from response metadata |
| Proactive (&lt;30m) | One **stderr** warning with `endor-auth refresh` hint (no token values) |
| Expired / 401 | Fail closed with `UnauthorizedError` and `endor-auth refresh` guidance |
| Next shell / process | Run `endor-auth refresh` or pass a fresh `token=` — child processes do not inherit in-memory tokens |

Thread-safety: one `Client` instance uses `RLock` on session state. API-key auth may retry once after re-authentication; bearer auth does not.

## Setup workflow (shipped)

Before task skills or live API calls:

1. **Probe:** `uv run endor-auth check [--tenant <namespace>] [--json]` — env-key scan (no
   values), optional endorctl probe, `Client().whoami()` when creds exist. JSON includes
   `auth_mode_resolved`, `sso_tenant_resolved`, `browser_auth_method_resolved`, `expires_in_seconds`.
2. **Refresh (interactive):** `uv run endor-auth refresh --method sso -n <tenant>` —
   browser OAuth; upserts `ENDOR_TOKEN` in `.env`; prints whoami + TTL (not for CI).
   No separate post-refresh `check` is required — failures surface on stderr / error logs.
3. **endorctl-native:** `endorctl init --auth-mode=sso --auth-tenant=<tenant>` persists
   to `~/.endorctl/config.yaml` (SDK reads `ENDOR_NAMESPACE` from that file when env unset).

Skill: `skills/endor-auth-setup/SKILL.md`. Library:
`endorlabs.workflows.auth.verify_auth`,
`refresh_token_to_dotenv`.

## Exceptions

Use top-level `endorlabs` exception types (`NotFoundError`, `UnauthorizedError`,
`ValidationError`, `AmbiguousError`, …). Resources may return `None` on 404 where documented.

**Note:** `AmbiguousError` is no longer raised by facade discovery — use `search_by_*` and explicit disambiguation instead of exact-match `lookup()`.

## Local OpenAPI spec

Preferred path after `init()`:

`.endorlabs-context/platform/openapi/openapiv2.swagger.json`

User docs mirror:

`.endorlabs-context/platform/user-docs/`
