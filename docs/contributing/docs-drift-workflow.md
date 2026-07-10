# Model Sync Workflow

> **Canonical workflow for synchronizing OpenAPI schema and generated Pydantic models**

Local setup: see [CONTRIBUTORS.md](../../CONTRIBUTORS.md).

## Sync external docs (optional, for full IDE context)

Create the gitignored `.endorlabs-context/` folder with both the OpenAPI spec and local user documentation snapshots. **Optional, for full IDE context** — pull full platform-admin context into the IDE.

```bash
uv sync --extra docs
```

```python
import endorlabs
status = endorlabs.init()  # materializes sdk/; optional platform downloads
```

This creates:

- `.endorlabs-context/sdk/` — shipped agent knowledge (INDEX, rules, skills, contracts)
- `.endorlabs-context/platform/openapi/openapiv2.swagger.json` — API spec
- `.endorlabs-context/platform/user-docs/*.md` — User docs (sitemap-based, parallel download)
- `.endorlabs-context/context.json` — init manifest

Options: `include_openapi=True/False`, `include_user_docs=True/False`, `include_agent_knowledge=True/False`, `max_pages=N`, `force=True`. See [AGENTS.md](../../AGENTS.md#bootstrap) and [CONTRIBUTORS.md](../../CONTRIBUTORS.md#optional-sync-external-docs).

## Model sync workflow (CI and local)

The model sync workflow:

1. **Download OpenAPI spec** — CI/local use `.endorlabs-context/platform/openapi/openapiv2.swagger.json`.
2. **Run canonical generator** — Generate deterministic custom-mapped Pydantic model modules and mapping metadata.
3. **Run sync checks** — Validate eligibility (`x-internal` + exception allowlist), mapping determinism, and generated artifact freshness.
4. **Refresh runtime generated package** — Mirror generated model shards to `src/endorlabs/generated/models/` and refresh runtime registry contract.

## Release alignment guardrail

Release, TestPyPI, and CI lint jobs run the same ship-artifact verifier:

```bash
uv run python devtools/ship/verify_ship_artifacts.py --fetch-spec
```

The verifier (in order): upstream OpenAPI SHA check (`--verify-upstream-only`), full model-sync
regeneration, route contract regeneration (`generate_route_contract.py`), `git diff` on committed
generated surfaces (`src/endorlabs/generated/**`, `client_surface.pyi`,
`docs/generated-reference/**`), and `sync_agent_knowledge.py --verify`.

Release workflows also pass `--verify-changelog VERSION` so `docs/changelog.md` contains a
matching `## VERSION` section before publish.

## CI and local gates

**CI** (`.github/workflows/ci-pr-main.yml` lint job): `uv run python devtools/ship/verify_ship_artifacts.py --fetch-spec`

**Release** (`.github/workflows/release-tag-publish.yml`, `release-testpypi.yml`): composite
`.github/actions/release-build-gate` (quality gate + `verify_ship_artifacts` + wheel build).
Production PyPI publish is **`release-tag-publish.yml`** `workflow_dispatch` from `main` — see
[release-publishing.md](./release-publishing.md). `release-pypi.yml` is dry-run only unless infra
registers a second PyPI trusted publisher.

**Pre-commit** (`.pre-commit-config.yaml`): `ship-artifacts-verify` runs
`verify_ship_artifacts.py --skip-upstream` before ruff/pyright when model-sync or
generated paths change.

**Pre-push**: `ship-artifacts-verify-upstream` (`--fetch-spec`) plus
`model-sync-contract-validate`. Install with `uv run pre-commit install --hook-type pre-push`.

When verify fails, regenerate and commit in your PR:

```bash
uv run python devtools/codegen/model_sync.py --fetch-spec --generate-stubs --generate-reference-docs
uv run python devtools/codegen/generate_route_contract.py
uv run python devtools/codegen/sync_agent_knowledge.py
```

### Triage

- **Ship-artifact verify failed in CI or release:** run the commands above, review diffs under
  `src/endorlabs/generated/`, `client_surface.pyi`, and `docs/generated-reference/`, then push.
- **Optional version signal:** `.github/scripts/check_endorctl_version.py` (local or cron; not required for merge).

## Local Use

**Option A — Full context:** Sync spec + user docs into `.endorlabs-context/`, then run model sync (see [Sync external docs](#sync-external-docs-optional-for-full-ide-context) above).

**Option B — Spec only:** Download just the OpenAPI spec, then run model sync:

```python
from endorlabs.context import sync_openapi
sync_openapi()  # downloads to .endorlabs-context/platform/openapi/openapiv2.swagger.json
```

Then run model sync (credentials in `.env`; see [README.md](../../README.md#configuration)):

```bash
uv run --env-file .env python devtools/codegen/model_sync.py --generate-stubs --generate-reference-docs
```

Check tooling availability without re-running generation:

```bash
uv run python devtools/codegen/model_sync.py --inventory-only
```

**Model consistency (static):** Use the committed runtime registry contract as the static contract signal (no integration test run). Run: `uv run python devtools/codegen/model_sync.py` and inspect `src/endorlabs/generated/registry_contract.py` plus `validate_contract_artifacts` output at sync time.

## Scripts

- **`.github/scripts/check_endorctl_version.py`** — Optional endorctl/OpenAPI drift check (local or cron).
- **`devtools/codegen/model_sync.py`** — Canonical model sync generator/check entrypoint.
- **`devtools/codegen/sync/README.md`** — Generation module responsibilities and triage map.
- **`src/endorlabs/generated/README.md`** — Runtime generated package maintenance policy.

## Related

- [API validation](./api-validation.md) — OpenAPI and optional wire checks before overlay or hand modules
- [Architecture](./architecture.md) — Generated client surface and overlay
- [Integration resource tests](./integration-resource-tests.md) — Facade validation tests
- [Troubleshooting](./troubleshooting.md) — Issue resolution
- [AGENTS.md](../../AGENTS.md) — Agent bootstrap and API gotchas
- [repository-layout.md](./repository-layout.md) — Full repo region map
