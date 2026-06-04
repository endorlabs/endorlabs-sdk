# Model Sync Workflow

> **Canonical workflow for synchronizing OpenAPI schema and generated Pydantic models**

Local setup: see [CONTRIBUTORS.md](../../CONTRIBUTORS.md).

## Sync external docs (optional, for full IDE context)

Create the gitignored `.endorlabs-context/` folder with both the OpenAPI spec and local user documentation snapshots. **Optional, for full IDE context** — pull full platform-admin context into the IDE.

```bash
uv sync --extra context
```

```python
import endorlabs
endorlabs.init()  # downloads to .endorlabs-context/
```

This creates:

- `.endorlabs-context/openapiv2.swagger.json` — API spec
- `.endorlabs-context/docs/*.md` — User docs (sitemap-based, parallel download)

Options: `include_openapi=True/False`, `include_user_docs=True/False`, `max_pages=N`, `force=True`. See [AGENTS.md](../../AGENTS.md#context-bootstrap-for-ai-agents) for details.

## Model sync workflow (CI and local)

The model sync workflow:

1. **Download OpenAPI spec** — CI/local use `.endorlabs-context/openapiv2.swagger.json`.
2. **Run canonical generator** — Generate deterministic custom-mapped Pydantic model modules and mapping metadata.
3. **Run sync checks** — Validate eligibility (`x-internal` + exception allowlist), mapping determinism, and generated artifact freshness.
4. **Refresh runtime generated package** — Mirror generated model shards to `src/endorlabs/generated/models/` and refresh runtime registry contract.

## Release alignment guardrail

Release builds must validate generated SDK surfaces from the current OpenAPI snapshot before packaging artifacts:

- Canonical model-sync generator must produce no unexpected diffs
- `devtools/generate_client_stub.py` must produce no diff
- `devtools/generate_reference_docs.py` must produce no diff
- Runtime generated package (`src/endorlabs/generated/**`) must be refreshed by model sync

This keeps release artifacts aligned with the same spec-driven surfaces checked
in CI.

## CI and local gates

**CI** (`.github/workflows/ci-pr-main.yml`):

1. **Upstream verify** (lint job): `uv run python devtools/model_sync.py --verify-upstream-only` — fails when live OpenAPI SHA-256 differs from committed provenance in `src/endorlabs/generated/registry_contract.py`.
2. **Ephemeral generation** (`generate-model-sync` job): runs `devtools/model_sync.py` and shares artifacts with lint/unit tests (validates the generator; does not commit output).

**Pre-push** (`.pre-commit-config.yaml`): same upstream verify plus `model-sync-contract-validate` (pytest contract quality gate). Install with `uv run pre-commit install --hook-type pre-push`.

When verify fails, regenerate and commit in your PR:

```bash
uv run python devtools/model_sync.py --fetch-spec --generate-stubs --generate-reference-docs
```

### Triage

- **Upstream verify failed in CI or pre-push:** run the command above, review diffs under `src/endorlabs/generated/`, `workspace/model-sync/`, `client_surface.pyi`, and `docs/generated-reference/`, then push.
- **Optional version signal:** `.github/scripts/check_endorctl_version.py` (local or cron; not required for merge).

## Local Use

**Option A — Full context:** Sync spec + user docs into `.endorlabs-context/`, then run model sync (see [Sync external docs](#sync-external-docs-optional-for-full-ide-context) above).

**Option B — Spec only:** Download just the OpenAPI spec, then run model sync:

```python
from endorlabs.context import sync_openapi
sync_openapi()  # downloads to .endorlabs-context/openapiv2.swagger.json
```

Then run model sync:

**Linux / macOS (bash):**

```bash
export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-key"
export ENDOR_API_CREDENTIALS_SECRET="your-secret"
export ENDOR_NAMESPACE="your-namespace"

uv run python devtools/model_sync.py --generate-stubs --generate-reference-docs
```

**Windows (PowerShell):**

```powershell
$env:ENDOR_API = "https://api.endorlabs.com"
$env:ENDOR_API_CREDENTIALS_KEY = "your-key"
$env:ENDOR_API_CREDENTIALS_SECRET = "your-secret"
$env:ENDOR_NAMESPACE = "your-namespace"

uv run python devtools/model_sync.py --generate-stubs --generate-reference-docs
```

Check tooling availability without re-running generation:

```bash
uv run python devtools/model_sync.py --inventory-only
```

**Model consistency (static):** Use canonical model-sync artifacts as the static contract signal (no integration test run). Run: `uv run python devtools/model_sync.py` and inspect generated contract outputs under `workspace/model-sync/custom_mapping/` (`facade_contract.json`, `mapping/registry_parity_report.json`, `mapping/operation_path_metadata.json`, `mapping/payload_schemas.json`, `mapping/runtime_index.json`).

## Scripts

- **`.github/scripts/check_endorctl_version.py`** — Optional endorctl/OpenAPI drift check (local or cron).
- **`devtools/model_sync.py`** — Canonical model sync generator/check entrypoint.
- **`devtools/sync/README.md`** — Generation module responsibilities and triage map.
- **`src/endorlabs/generated/README.md`** — Runtime generated package maintenance policy.

## Related

- [API Validation](./api-validation.md) — Pre-implementation validation
- [Architecture](./architecture.md) — Generated client surface and overlay
- [Integration resource tests](./integration-resource-tests.md) — Facade validation tests
- [Troubleshooting](./troubleshooting.md) — Issue resolution
- [AGENTS.md](../../AGENTS.md) — AI agent index
