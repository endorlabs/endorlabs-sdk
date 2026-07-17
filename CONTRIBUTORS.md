# Contributing to the Endor Labs SDK

Single source for contributor setup and development workflow. Consumer install is documented in [README.md](README.md); this file is for people working on the repo.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package and project manager)
- Python 3.12+ runtime support. Contributor/CI quality gates currently run on
  Python 3.13 for deterministic lint/type/test behavior (install via uv).

## Setup

From the repo root:

```bash
git clone https://github.com/endorlabs/endorlabs-sdk.git
cd endorlabs-sdk
uv sync
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

Alternatively: `uv venv` then `uv pip install -e .` and install dev dependencies from [pyproject.toml](pyproject.toml) (e.g. `uv sync --group dev` or equivalent for your uv version).

If `uv sync` fails on version metadata, see [docs/contributing/release-publishing.md](docs/contributing/release-publishing.md) and run `uv run python devtools/ship/check_project_version.py`.

## Before you commit / open a PR

Human checklist (automation: [.pre-commit-config.yaml](.pre-commit-config.yaml); PR body: [.github/pull_request_template.md](.github/pull_request_template.md)).

### Before commit

- [ ] **Hooks installed** — `uv run pre-commit install` and `uv run pre-commit install --hook-type pre-push` (see [Setup](#setup)).
- [ ] **Agent-knowledge** — after `agent-knowledge/` edits: `uv run python devtools/codegen/sync_agent_knowledge.py` and commit `src/endorlabs/agent_knowledge/`.
- [ ] **Docs freshness** — grep changed paths for stale layout or CLI strings (`workspace/sessions/`, removed `devtools/` scripts, wrong flags such as `endor-auth refresh --sso` vs `--method sso`). Align docstrings, argparse `help=`, and comments with current code (see shipped rule `endor-workspace-layout`, [docs-skillbase-consistency](.cursor/rules/docs-skillbase-consistency.mdc)).
- [ ] **No secrets or customer data** — never commit `.env`, tokens, API keys, or customer estate identifiers (tenants, production UUIDs, registered repo URLs, emails) in **any** tracked path: unit fixtures, docstrings, CLI examples, skills, docs. Use placeholders (`example-tenant`, `user@example.com` / `user@endor.ai`). Integration tests: real tenant via **env** only. Pre-commit **blocks** staged `.env` / `.endorlabs-context/`, runs **gitleaks**, and **fails** on emails / non-Endor URLs / estate `-n` flags / estate literals; see rule `endor-portable-examples`.
- [ ] **Changelog** — user-visible changes: one bullet under `docs/changelog.md` → **Unreleased** (policy: [agent-knowledge/rules/endor-changelog.md](agent-knowledge/rules/endor-changelog.md)). Pre-commit prints a **reminder** when user-facing paths are staged without `docs/changelog.md`.
- [ ] **Pre-commit passes** — `uv run pre-commit run --all-files` (or let the commit hook run: ruff, pyright, unit pytest, ship-artifacts verify when applicable). New guards: rule [`endor-maintainer-tooling`](agent-knowledge/rules/endor-maintainer-tooling.md). New/changed tests: rule [`endor-unit-tests`](agent-knowledge/rules/endor-unit-tests.md).

### Opening a pull request

- [ ] **Draft first** — open as a **draft** PR unless you are explicitly ready to merge (`gh pr create --draft`).
- [ ] **PR template** — fill Summary, changelog intake, and Test plan in [.github/pull_request_template.md](.github/pull_request_template.md).
- [ ] **Pre-push** — before `git push`: upstream ship-artifacts verify, model-sync contract validate, and bandit (pre-push hooks; needs network for `--fetch-spec`).

Maintainer invariants (stdout, typing, `endorctl scan`, portable examples): [docs/contributing/repository-layout.md](docs/contributing/repository-layout.md#maintainer-invariants).

## Environment

The SDK uses environment variables only (no config file loading). When extending the SDK, do not invent new `ENDOR_*` names — cite Endor Labs product docs and update [README.md](README.md) / [docs/contracts.md](docs/contracts.md); read with `os.getenv` and avoid mutating `os.environ` or `.env` unless the user explicitly requests it (rule `endor-environment-variables` in `agent-knowledge/rules/`).

Set these for local development:

- **Required:** `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`
- **Optional:** `ENDOR_API` (defaults to `https://api.endorlabs.com`), `ENDOR_NAMESPACE` (tenant namespace for operations), `ENDOR_LOG_LEVEL`, `ENDOR_MAX_RETRIES`

Create a `.env` file in the repo root (gitignored) or export in your shell. Example:

```bash
ENDOR_API="https://api.endorlabs.com"
ENDOR_API_CREDENTIALS_KEY="your-api-key"
ENDOR_API_CREDENTIALS_SECRET="your-api-secret"
ENDOR_NAMESPACE="your-tenant-namespace"
ENDOR_LOG_LEVEL="INFO"
```

Get API credentials from the Endor Labs platform or configure [endorctl](https://docs.endorlabs.com/endorctl/install-and-configure/). For token-based auth (e.g. browser flow), set `ENDOR_TOKEN` instead of key/secret; the SDK supports both.

## Validate

Check that env and authentication are correct with an SDK-authenticated call.

If your shell already has the variables exported:

```bash
uv run python -c "import endorlabs; print(endorlabs.Client().whoami())"
```

If you are using a repo-root `.env` file instead:

```bash
uv run --env-file .env python -c "import endorlabs; print(endorlabs.Client().whoami())"
```

On success this should print the authenticated identity (email, username, or display name).

## Tests

```bash
uv run pytest
```

If your env is not loaded in the shell (e.g. you use a `.env` file):

```bash
uv run --env-file .env pytest
```

With coverage:

```bash
uv run pytest --cov=endorlabs --cov-report=html
```

Integration tests (require valid credentials):

```bash
uv run pytest -m integration -v
```

**Pytest markers:** `integration`, `writes` (mutating API calls), `long` (heavy integration; CI runs `-m "not long"`), `interactive` (browser OAuth — excluded from CI; use `uv run endor-auth refresh`). The unused `slow` marker was removed; use `long` or `interactive` instead. Unit CI: `-m "not interactive and not long"`. Traverse coverage lives in `tests/integration/client/test_concurrent_list.py`; per-resource tests list in the integration `namespace` without `traverse`.

**Log-style integration bounds** (`tests/conftest.py`): `TEST_LOG_LIST_MAX_PAGES` (no forced `page_size` on logs), `TEST_LOG_LIST_MAX_ROWS`, `TEST_SCAN_LOG_MAX_ENTRIES`; helpers `log_list_kwargs()` / `bounded_log_list_params()` / `assert_bounded_log_rows()` in `tests/integration/conftest.py`.

Domain-driven test layout:

- `tests/unit/{client,workflows,platform,tooling}`
- `tests/integration/{client,resources,workflows}`

**Unit test writing:** prefer behavior/contracts over smoke and copy pins — rule
[`endor-unit-tests`](agent-knowledge/rules/endor-unit-tests.md)
([docs/contributing/unit-tests.md](docs/contributing/unit-tests.md)).
**Integration list/get:** shared harness
[`test_resource_list_get_roundtrip.py`](tests/integration/resources/test_resource_list_get_roundtrip.py);
per-resource extras only — [integration-resource-tests.md](docs/contributing/integration-resource-tests.md).

## Linting and type checking

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright --project pyproject.toml
uv run ruff check --select E,F,I,UP devtools/codegen/model_sync.py devtools/codegen/generate_client_stub.py devtools/codegen/generate_reference_docs.py .github/scripts/check_endorctl_version.py
uv run pyright --project pyproject.toml devtools/codegen/model_sync.py devtools/codegen/generate_client_stub.py devtools/codegen/generate_reference_docs.py .github/scripts/check_endorctl_version.py
uv run python devtools/codegen/generate_client_stub.py
git diff --exit-code -- src/endorlabs/client_surface.pyi
uv run pyright --verifytypes endorlabs --ignoreexternal --project pyproject.toml
```

Use `uv run ruff format .` (without `--check`) to apply formatting locally. CI runs the same ruff/pyright sequence (plus generated-artifact checks); see [.github/workflows/ci-pr-main.yml](.github/workflows/ci-pr-main.yml). **Pre-commit** mirrors the lint job via local `uv run` hooks, including **`pytest tests/unit/ -m "not interactive and not long"`** on staged Python changes (see [.pre-commit-config.yaml](.pre-commit-config.yaml)); install commit and push gates with `uv run pre-commit install` and `uv run pre-commit install --hook-type pre-push`. Pyright checks types; `--verifytypes endorlabs` checks that the package's public API does not expose `Unknown`. The stub check ensures `client_surface.pyi` stays synchronized with `RESOURCE_REGISTRY`.

## Model-sync drift and regeneration

Upstream alignment uses **pre-commit**, **pre-push**, and **CI**, not a bot workflow:

- **Pre-commit** (`.pre-commit-config.yaml`): `ship-artifacts-verify` runs
  `devtools/ship/verify_ship_artifacts.py --skip-upstream` **before** ruff/pyright when
  model-sync inputs or generated surfaces change — regen + `git diff` so linters see
  current stubs.
- **Pre-push** (after `uv run pre-commit install --hook-type pre-push`):
  - `ship-artifacts-verify-upstream` — `verify_ship_artifacts.py --fetch-spec` (upstream
    SHA, regen, ship `git diff`, agent-knowledge `--verify`; CI parity)
  - `model-sync-contract-validate` — contract quality unit gate
- **CI** (`.github/workflows/ci-pr-main.yml` lint job): `verify_ship_artifacts.py --fetch-spec`

When verify fails locally or in CI:

```bash
uv run python devtools/ship/verify_ship_artifacts.py --fetch-spec
# or: uv run python devtools/codegen/model_sync.py --fetch-spec --generate-stubs --generate-reference-docs
```

See [devtools/codegen/sync/README.md](devtools/codegen/sync/README.md) and [docs/contributing/docs-drift-workflow.md](docs/contributing/docs-drift-workflow.md).

Optional version check (local or cron): `.github/scripts/check_endorctl_version.py`

## Consumer API style (SDK UX)

When using or documenting the registry-based client (`client.Namespace`, `client.Project`, etc.):

- **List:** Use flat kwargs on `.list()` — e.g. `client.Project.list(traverse=True)`, `client.Project.list(filter="...", mask="meta.name,spec.level", max_pages=1)`. Do **not** combine filter and mask into one parameter; filter = which rows, mask = which fields in the response. With a **non-empty** mask, each row is a **`dict`** (wire JSON), not a resource model—omit `mask` when you need typed instances. See [docs/contracts.md](docs/contracts.md) (List parameters, Update and update_mask) and [docs/guides/consumer-ux-list-update.md](docs/guides/consumer-ux-list-update.md).
- **Update:** Use `update_mask` only on `.update()`; it is separate from list mask.
- **Spec-driven UX:** Align with spec; centralize sources of truth in modules (see [docs/contracts.md](docs/contracts.md) and [docs/contributing/](docs/contributing/)).

## Optional: SDK bootstrap and OpenAPI

For IDE use, bootstrap SDK agent knowledge and optionally download OpenAPI.
**Product docs** use the [Docs MCP server](https://docs.endorlabs.com/introduction/docs-mcp-server)
(`https://docs.endorlabs.com/mcp`). Unsupported harnesses can use
[https://docs.endorlabs.com/llms.txt](https://docs.endorlabs.com/llms.txt).

```bash
uv sync
# optional: DataFrame / Parquet export and estate graph analytics tests
uv sync --extra analytics
```

```python
import endorlabs
status = endorlabs.init(include_openapi=True)
# Writes:
#   .endorlabs-context/context.json
#   .endorlabs-context/sdk/              (shipped agent knowledge; no auth)
#   .endorlabs-context/platform/openapi/  (optional download)
#   .endorlabs-context/workspace/        (workflow outputs: projects/, runs/<run-bucket>/, inventory/)
# Product docs: Docs MCP
```

Options: `include_openapi=True/False`, `include_agent_knowledge=True/False`, `force=True`, `sync_skills="none|cursor|claude|both"`.

Consumer projects should add `.endorlabs-context/` to `.gitignore` (OpenAPI + local run artifacts).

The local pre-commit hook also refreshes these maintainer-only artifacts automatically:

- changes under `agent-knowledge/skills/` require `devtools/codegen/sync_agent_knowledge.py` (CI/pre-push `--verify` drift gate)
- `sync_skills` mirrors `.endorlabs-context/sdk/skills/`, not repo `agent-knowledge/skills/` (pip-safe)
- changes under `src/endorlabs/context/` refresh the existing SDK bootstrap tree (OpenAPI when auth is available)

See [AGENTS.md](AGENTS.md#bootstrap) for agent bootstrap. Full repo region map: [docs/contributing/repository-layout.md](docs/contributing/repository-layout.md).
