# Contributing to Endor Cockpit

Single source for contributor setup and development workflow. Consumer install is documented in [README.md](README.md); this file is for people working on the repo.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package and project manager)
- Python 3.13+ (e.g. installed via uv)

## Setup

From the repo root:

```bash
git clone https://github.com/endor-solutions-architecture/endor-cockpit.git
cd endor-cockpit
uv sync
```

Alternatively: `uv venv` then `uv pip install -e .` and install dev dependencies from [pyproject.toml](pyproject.toml) (e.g. `uv sync --group dev` or equivalent for your uv version).

### Pre-commit hook (recommended)

Run the same lint/format/typecheck as CI before each commit. Pre-commit is a dev dependency; use it so hooks run automatically for all maintainers.

From the repo root after `uv sync`:

```bash
uv run pre-commit install
```

That installs the git hook so every `git commit` runs ruff check, ruff format (check), and pyright. Skipping with `--no-verify` should be rare (e.g. WIP commits) and not for normal upstream contributions.

Alternative (no pre-commit framework): copy the native hook so it runs the same commands:

```bash
cp githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

The repo uses [.pre-commit-config.yaml](.pre-commit-config.yaml) with `minimum_pre_commit_version` and `default_install_hook_types` so a single `pre-commit install` is enough.

## Environment

The SDK uses environment variables only (no config file loading). Set these for local development:

- **Required:** `ENDOR_API`, `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`
- **Optional:** `ENDOR_NAMESPACE` (tenant namespace for operations), `ENDOR_LOG_LEVEL`, `ENDOR_MAX_RETRIES`

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

Check that env and connectivity are correct:

```bash
curl -s "$ENDOR_API/health"
```

Or with Python (requires `requests`): `uv run python -c "import os, requests; r = requests.get(os.environ['ENDOR_API'] + '/health', timeout=5); print(r.status_code)"`

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

## Linting and type checking

```bash
uv run ruff check .
uv run ruff format .
uv run pyright
```

CI runs these; see [.github/workflows/ci.yml](.github/workflows/ci.yml). They also run automatically before commit when the pre-commit hook is installed (see [Pre-commit hook](#pre-commit-hook-recommended) above).

## Optional: direnv

If you use [direnv](https://direnv.net/), run `direnv allow` in the repo root. [.envrc](.envrc) loads the uv virtual environment and sources `.env` when you enter the directory.

## Optional: sync external docs

For full IDE context (OpenAPI spec + user docs from docs.endorlabs.com), create the gitignored `external_docs/` folder:

```bash
uv sync --extra docs
uv run python scripts/sync_external_docs.py --all
```

See [scripts/README.md](scripts/README.md) for options (spec-only, `--max-pages`, `--force`). For CI and schema drift workflow, see [docs/rules-of-engagement/docs-drift-workflow.md](docs/rules-of-engagement/docs-drift-workflow.md).

