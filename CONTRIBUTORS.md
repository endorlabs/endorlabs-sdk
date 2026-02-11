# Contributing to the Endor Labs SDK

Single source for contributor setup and development workflow. Consumer install is documented in [README.md](README.md); this file is for people working on the repo.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package and project manager)
- Python 3.11+ (CI and releases are tested on 3.13 only; e.g. install via uv)

## Setup

From the repo root:

```bash
git clone https://github.com/Endor-Solutions-Architecture/endorlabs-sdk.git
cd endorlabs-sdk
uv sync
```

Alternatively: `uv venv` then `uv pip install -e .` and install dev dependencies from [pyproject.toml](pyproject.toml) (e.g. `uv sync --group dev` or equivalent for your uv version).

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
uv run pyright --project pyproject.toml
uv run pyright --verifytypes endorlabs --ignoreexternal --project pyproject.toml
```

CI runs these; see [.github/workflows/ci.yml](.github/workflows/ci.yml). Pyright checks types; `--verifytypes endorlabs` checks that the package's public API does not expose `Unknown`.

## Optional: direnv

If you use [direnv](https://direnv.net/), run `direnv allow` in the repo root. [.envrc](.envrc) loads the uv virtual environment and sources `.env` when you enter the directory.

## Consumer API style (SDK UX)

When using or documenting the registry-based client (`client.namespace`, `client.project`, etc.):

- **List:** Use flat kwargs on `.list()` — e.g. `client.project.list(traverse=True)`, `client.project.list(filter="...", mask="meta.name,spec.level", max_pages=1)`. Do **not** combine filter and mask into one parameter; filter = which rows, mask = which fields in the response. See [docs/conventions.md](docs/conventions.md) (List parameters, Update and update_mask) and [docs/guides/consumer-ux-list-update.md](docs/guides/consumer-ux-list-update.md).
- **Update:** Use `update_mask` only on `.update()`; it is separate from list mask.
- **Spec-driven UX:** Align with spec; centralize sources of truth in modules (see [docs/conventions.md](docs/conventions.md) and [docs/rules-of-engagement/](docs/rules-of-engagement/)).

## Optional: sync external docs

For full IDE context (OpenAPI spec + user docs from docs.endorlabs.com), create the gitignored `.endorlabs-context/` folder:

```bash
uv sync --extra context
```

```python
import endorlabs
endorlabs.init()  # downloads to .endorlabs-context/
```

Options: `include_openapi=True/False`, `include_user_docs=True/False`, `max_pages=N`, `force=True`. See [AGENTS.md](AGENTS.md#context-bootstrap-for-ai-agents) for details.

