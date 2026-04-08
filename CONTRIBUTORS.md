# Contributing to the Endor Labs SDK

Single source for contributor setup and development workflow. Consumer install is documented in [README.md](README.md); this file is for people working on the repo.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package and project manager)
- Python 3.12+ runtime support. Contributor/CI quality gates currently run on
  Python 3.13 for deterministic lint/type/test behavior (install via uv).

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

Domain-driven test layout:

- `tests/unit/{client,workflows,platform,tooling}`
- `tests/integration/{client,resources,workflows}`

## Linting and type checking

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright --project pyproject.toml
uv run ruff check --select E,F,I,UP scripts/model_sync.py scripts/model_sync_pr_deltas.py scripts/generate_client_stub.py scripts/generate_reference_docs.py .github/scripts/check_endorctl_version.py
uv run pyright --project pyproject.toml scripts/model_sync.py scripts/model_sync_pr_deltas.py scripts/generate_client_stub.py scripts/generate_reference_docs.py .github/scripts/check_endorctl_version.py
uv run python scripts/generate_client_stub.py
git diff --exit-code -- src/endorlabs/client_surface.pyi
uv run pyright --verifytypes endorlabs --ignoreexternal --project pyproject.toml
```

Use `uv run ruff format .` (without `--check`) to apply formatting locally. CI runs the same ruff/pyright sequence (plus generated-artifact checks); see [.github/workflows/ci-pr-main.yml](.github/workflows/ci-pr-main.yml). **Pre-commit** mirrors that lint job via local `uv run` hooks (see [.pre-commit-config.yaml](.pre-commit-config.yaml)); install with `uv run pre-commit install`. Pyright checks types; `--verifytypes endorlabs` checks that the package's public API does not expose `Unknown`. The stub check ensures `client_surface.pyi` stays synchronized with `RESOURCE_REGISTRY`.

**Repository variables (GitHub Settings → Actions):** If present, you may remove deprecated names that are no longer read by workflows: `ENDOR_ENABLE_GITHUB_CHECK_ANNOTATIONS`, `ENDOR_GITHUB_CHECK_MODE`, `ENDOR_GITHUB_CHECK_CONCLUSION` (removed Checks-annotations path). See [docs/guides/pr-comment-config-and-parallel-comments.md](docs/guides/pr-comment-config-and-parallel-comments.md) for the active PR-comment variables.

## Model-Sync automation topology

Model-sync automation is split by responsibility:

- **Detector:** `.github/workflows/model-sync-detector.yml`
  - checks latest `endorctl` version + OpenAPI SHA drift
  - dispatches `repository_dispatch` (`model-sync-check`) when a version/spec change is detected
- **Sync + PR:** `.github/workflows/model-sync-pr.yml`
  - runs canonical generation (`scripts/model_sync.py --generate-stubs --generate-reference-docs`)
  - scopes changed files to generated surfaces
  - creates/updates bot PR branch (`chore/model-sync-<utc-timestamp>`)
- **CI gate:** `.github/workflows/ci-pr-main.yml`
  - remains the required merge gate for all PRs, including bot PRs

## Optional: direnv

If you use [direnv](https://direnv.net/), run `direnv allow` in the repo root. [.envrc](.envrc) loads the uv virtual environment and sources `.env` when you enter the directory.

## Consumer API style (SDK UX)

When using or documenting the registry-based client (`client.Namespace`, `client.Project`, etc.):

- **List:** Use flat kwargs on `.list()` — e.g. `client.Project.list(traverse=True)`, `client.Project.list(filter="...", mask="meta.name,spec.level", max_pages=1)`. Do **not** combine filter and mask into one parameter; filter = which rows, mask = which fields in the response. See [docs/contracts.md](docs/contracts.md) (List parameters, Update and update_mask) and [docs/guides/consumer-ux-list-update.md](docs/guides/consumer-ux-list-update.md).
- **Update:** Use `update_mask` only on `.update()`; it is separate from list mask.
- **Spec-driven UX:** Align with spec; centralize sources of truth in modules (see [docs/contracts.md](docs/contracts.md) and [docs/rules-of-engagement/](docs/rules-of-engagement/)).

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

## Self-Validation and Nightly Operations

Use the SDK self-validation scorecard script to generate deterministic posture artifacts:

```bash
uv run python scripts/self_validation_scorecard.py \
  --repository-url "https://github.com/Endor-Solutions-Architecture/endorlabs-sdk.git" \
  --tenant "$ENDOR_NAMESPACE" \
  --output-dir ".endorlabs-context/self-validation" \
  --deterministic
```

Nightly automation is defined in `.github/workflows/nightly-self-validation.yml`.

Supported trigger paths:

- Scheduled nightly run (`schedule`)
- Manual run (`workflow_dispatch`) with typed inputs (`mode`, `repository_url`, `deterministic`, `strict_threat_claims`)
- Remote run (`repository_dispatch`) with event type `nightly-self-validation`

Example remote dispatch payload:

```json
{
  "event_type": "nightly-self-validation",
  "client_payload": {
    "mode": "full",
    "repository_url": "https://github.com/Endor-Solutions-Architecture/endorlabs-sdk.git",
    "deterministic": "true",
    "strict_threat_claims": "false"
  }
}
```

Operational rollback: switch dispatch `mode` to `smoke` and set `deterministic=true` to reduce run time and flake surface while preserving scorecard continuity.
