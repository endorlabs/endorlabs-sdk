---
id: endor-environment-variables
tags: [maintainer, sdk, configuration, security]
summary: >-
  Do not invent ENDOR_* env vars; cite Endor Labs docs before encoding; read with
  os.getenv; never mutate os.environ or .env unless a human explicitly requests it.
---

# Environment variables (maintainer)

Repo-only guidance when extending `src/endorlabs/**`, workflows, or contributor docs.
Not shipped in the wheel bootstrap bundle.

## Allowed sources (do not invent)

Support only variable names that appear in **at least one** of:

| Source | Use for |
| ------ | ------- |
| [README.md](../../README.md) — Configuration table | Public SDK contract |
| [docs/contracts.md](../../docs/contracts.md) | Transport, auth, and behavioral contracts |
| [CONTRIBUTORS.md](../../CONTRIBUTORS.md) — Environment | Maintainer dev setup |
| Shipped [contracts/errors-and-auth.md](../contracts/errors-and-auth.md) | Agent/auth quick reference |
| Endor Labs product docs | endorctl parity — prefer synced copy under `.endorlabs-context/platform/user-docs/` (e.g. `developers-api/cli/environment-variables.md`) |
| Local OpenAPI / user-docs after `init()` | API-specific flags only when product docs reference them |

**Do not** add parallel spellings, SDK-only aliases, or new `ENDOR_*` names without a
doc citation and README/contract update in the same change.

## Read safely (default)

- **Read** with `os.getenv(key)` or `os.environ.get(key)` — treat missing/blank as unset.
- **Constructor args and parameters override env** — resolve locally; do not write resolved
  values back into the process environment.
- **Never log secret values** — confirm presence only (rule `endor-local-context`).
- **Prefer explicit parameters** on public APIs over new env knobs when both would work.

### Precedent

`APIClient` must not set `os.environ["ENDOR_API"]` (or any other var) during construction.
Read defaults locally; let the caller's shell or `.env` loader own the process environment.

## Forbidden by default

| Pattern | Why |
| ------- | --- |
| `os.environ[key] = …` / `os.putenv` in SDK core, facades, or utils | Surprises other libraries, tests, and MCP/endorctl in the same process |
| Writing env vars to pass defaults to child code | Use function args, instance fields, or explicit config objects |
| New `ENDOR_*` without doc citation + README/contract row | Drift from endorctl and customer `.env` templates |
| Agents or session scripts upserting `.env` without user consent | Credential and namespace changes need explicit human approval |
| Inventing non-`ENDOR_*` names for Endor settings | Use documented names or constructor kwargs |

## Allowed mutation (explicit human intent only)

| Case | Module / entrypoint |
| ---- | ------------------- |
| Interactive browser token refresh | `endor-auth refresh`, `refresh_token_to_dotenv`, `upsert_dotenv_key` |
| User-directed `.env` merge after OAuth | `endorlabs.workflows.auth.dotenv` (owner-only file permissions) |
| Tests | `monkeypatch.setenv` / `delenv` in pytest only |

Workflows that mutate `.env` must document the keys they touch and must not run silently
from `Client()` construction or generic library helpers.

## Adding or extending support

1. **Cite** the product-doc or endorctl flag/env row (link or synced path).
2. **Document** user-facing vars in [README.md](../../README.md); transport/auth behavior in [docs/contracts.md](../../docs/contracts.md) and/or [contracts/errors-and-auth.md](../contracts/errors-and-auth.md).
3. **Implement** read-only resolution (`os.getenv`); constructor/param overrides env.
4. **Avoid** `os.environ` mutation outside the allowed table above.
5. **Test** with `monkeypatch` — not by assuming a clean global environment.

Skill **endor-implement-sdk-resource** checklist should include env-var doc parity when
touching `api_client.py`, auth, or transport helpers.

## Related

- [docs/contributing/repository-layout.md](../../docs/contributing/repository-layout.md#maintainer-invariants) — maintainer invariants
- [docs/contributing/architecture.md](../../docs/contributing/architecture.md) — `APIClient` transport layer
- Contract **errors-and-auth** — consumer/agent auth env list
- Rule **endor-local-context** — confirm `.env` keys without printing values
- Rule **endor-portable-examples** — never commit secrets
