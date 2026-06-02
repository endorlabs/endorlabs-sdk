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

If `uv sync` fails on version metadata (`0.1.1.dev19 can't be bumped`), see [docs/guides/pypi-publication-draft.md](docs/guides/pypi-publication-draft.md) and run `uv run python devtools/check_vcs_version.py`.

## Environment

The SDK uses environment variables only (no config file loading). Set these for local development:

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

Domain-driven test layout:

- `tests/unit/{client,workflows,platform,tooling}`
- `tests/integration/{client,resources,workflows}`

## Linting and type checking

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright --project pyproject.toml
uv run ruff check --select E,F,I,UP devtools/model_sync.py devtools/model_sync_pr_deltas.py devtools/generate_client_stub.py devtools/generate_reference_docs.py .github/scripts/check_endorctl_version.py
uv run pyright --project pyproject.toml devtools/model_sync.py devtools/model_sync_pr_deltas.py devtools/generate_client_stub.py devtools/generate_reference_docs.py .github/scripts/check_endorctl_version.py
uv run python devtools/generate_client_stub.py
git diff --exit-code -- src/endorlabs/client_surface.pyi
uv run pyright --verifytypes endorlabs --ignoreexternal --project pyproject.toml
```

Use `uv run ruff format .` (without `--check`) to apply formatting locally. CI runs the same ruff/pyright sequence (plus generated-artifact checks); see [.github/workflows/ci-pr-main.yml](.github/workflows/ci-pr-main.yml). **Pre-commit** mirrors that lint job via local `uv run` hooks (see [.pre-commit-config.yaml](.pre-commit-config.yaml)); install both local gates with `uv run pre-commit install` and `uv run pre-commit install --hook-type pre-push`. Pyright checks types; `--verifytypes endorlabs` checks that the package's public API does not expose `Unknown`. The stub check ensures `client_surface.pyi` stays synchronized with `RESOURCE_REGISTRY`.

**Repository variables (GitHub Settings → Actions):** If present, you may remove deprecated names that are no longer read by workflows: `ENDOR_ENABLE_GITHUB_CHECK_ANNOTATIONS`, `ENDOR_GITHUB_CHECK_MODE`, `ENDOR_GITHUB_CHECK_CONCLUSION` (removed Checks-annotations path). See [docs/guides/pr-comment-config-and-parallel-comments.md](docs/guides/pr-comment-config-and-parallel-comments.md) for the active PR-comment variables.

## Model-sync drift and regeneration

Upstream alignment uses **local pre-push hooks** and **CI**, not a bot workflow:

- **Pre-push** (after `uv run pre-commit install --hook-type pre-push`):
  - `model-sync-upstream-verify` — `devtools/model_sync.py --verify-upstream-only` (OpenAPI digest vs committed provenance)
  - `model-sync-contract-validate` — contract quality unit gate
- **CI** (`.github/workflows/ci-pr-main.yml`):
  - same upstream verify on the lint job
  - ephemeral `model_sync.py` generation for lint/tests (artifact shared across jobs)

When verify fails locally or in CI, regenerate and commit in your PR:

```bash
uv run python devtools/model_sync.py --fetch-spec --generate-stubs --generate-reference-docs
```

See [devtools/sync/README.md](devtools/sync/README.md) and [docs/rules-of-engagement/docs-drift-workflow.md](docs/rules-of-engagement/docs-drift-workflow.md).

Optional version check (local or cron): `.github/scripts/check_endorctl_version.py`

## Optional: direnv

If you use [direnv](https://direnv.net/), run `direnv allow` in the repo root. [.envrc](.envrc) loads the uv virtual environment and sources `.env` when you enter the directory.

## Consumer API style (SDK UX)

When using or documenting the registry-based client (`client.Namespace`, `client.Project`, etc.):

- **List:** Use flat kwargs on `.list()` — e.g. `client.Project.list(traverse=True)`, `client.Project.list(filter="...", mask="meta.name,spec.level", max_pages=1)`. Do **not** combine filter and mask into one parameter; filter = which rows, mask = which fields in the response. With a **non-empty** mask, each row is a **`dict`** (wire JSON), not a resource model—omit `mask` when you need typed instances. See [docs/contracts.md](docs/contracts.md) (List parameters, Update and update_mask) and [docs/guides/consumer-ux-list-update.md](docs/guides/consumer-ux-list-update.md).
- **Update:** Use `update_mask` only on `.update()`; it is separate from list mask.
- **Spec-driven UX:** Align with spec; centralize sources of truth in modules (see [docs/contracts.md](docs/contracts.md) and [docs/rules-of-engagement/](docs/rules-of-engagement/)).

## Optional: sync external docs

For full IDE context (OpenAPI spec + user docs from docs.endorlabs.com), create the gitignored `.endorlabs-context/` folder:

```bash
uv sync --extra context
# optional: DataFrame / Parquet tabular export tests
uv sync --extra tabular
```

```python
import endorlabs
endorlabs.init()  # downloads to .endorlabs-context/
```

Options: `include_openapi=True/False`, `include_user_docs=True/False`, `max_pages=N`, `force=True`, `sync_skills="none|cursor|claude|both"`.

The local pre-commit hook also refreshes these maintainer-only artifacts automatically:

- changes under `skills-src/` refresh any runtime skill mirrors already configured in the repo (for example `.cursor/` or `.claude/`)
- changes under `src/endorlabs/context/` refresh the existing `.endorlabs-context/` download (docs always; OpenAPI when auth is available)

See [AGENTS.md](AGENTS.md#context-bootstrap-for-ai-agents) for details.
