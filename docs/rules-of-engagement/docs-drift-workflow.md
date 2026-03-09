# Schema Drift Detection Workflow

> **Automated workflow for detecting discrepancies between API responses and Pydantic models**

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

## Schema drift workflow (CI and local)

The schema drift workflow:

1. **Download OpenAPI spec** — CI downloads the spec to `.endorlabs-context/openapiv2.swagger.json` (gitignored) in the runner for reference.
2. **Run drift detection** — Runs integration tests and parses schema drift warnings via `.github/scripts/detect_schema_drift.py`.
3. **Create issues** — GitHub Action creates one issue per new drift (inline script; no separate script).

## GitHub Actions

**File**: `.github/workflows/schema-drift-detection.yml`

- **Schedule**: Hourly (endorctl version check); weekly Mondays 3 AM UTC.
- **Remote/manual triggers**: `workflow_dispatch`, `workflow_call`, and `repository_dispatch` (`schema-drift-check`).
- **Jobs**:
  1. **check-version**: Runs `.github/scripts/check_endorctl_version.py`; outputs whether version changed.
  2. **detect-schema-drift**: Runs when version changed or forced by dispatch input. Downloads OpenAPI spec (curl), runs `detect_schema_drift.py --run-tests --test-path tests/ --output schema_drift_report.json`, then creates issues from the report via `actions/github-script`.

### Failure semantics

- Version-check script errors are treated as workflow failures (fail-closed).
- Schema drift/test execution errors are no longer silently skipped.
- Concurrency is enabled to avoid overlapping scheduled runs.

### Triage and rollback

- If drift pipeline breaks due to upstream instability, trigger a manual run and inspect uploaded report artifacts first.
- For temporary mitigation, force a manual run with reduced scope via `workflow_dispatch` while preserving issue creation and run summary output.

## Local Use

**Option A — Full context:** Sync spec + user docs into `.endorlabs-context/`, then run drift detection (see [Sync external docs](#sync-external-docs-optional-for-full-ide-context) above).

**Option B — Spec only:** Download just the OpenAPI spec, then run drift detection:

```python
from endorlabs.context import sync_openapi
sync_openapi()  # downloads to .endorlabs-context/openapiv2.swagger.json
```

Then run drift detection:

**Linux / macOS (bash):**

```bash
export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-key"
export ENDOR_API_CREDENTIALS_SECRET="your-secret"
export ENDOR_NAMESPACE="your-namespace"

uv run python .github/scripts/detect_schema_drift.py --run-tests --test-path tests/ --output schema_drift_report.json
```

**Windows (PowerShell):**

```powershell
$env:ENDOR_API = "https://api.endorlabs.com"
$env:ENDOR_API_CREDENTIALS_KEY = "your-key"
$env:ENDOR_API_CREDENTIALS_SECRET = "your-secret"
$env:ENDOR_NAMESPACE = "your-namespace"

uv run python .github/scripts/detect_schema_drift.py --run-tests --test-path tests/ --output schema_drift_report.json
```

Check an existing report without re-running tests:

```bash
uv run python .github/scripts/detect_schema_drift.py --check-existing
```

**Model consistency (static):** Diff SDK Pydantic field paths vs OpenAPI definitions (no test run). Run: `uv run python .github/scripts/detect_schema_drift.py --model-consistency --output-format json`. Writes `model_consistency_report.json` (uses `.endorlabs-context/openapiv2.swagger.json` if present, else fetches spec).

## Scripts

- **`.github/scripts/check_endorctl_version.py`** — Version check (used by first job).
- **`.github/scripts/detect_schema_drift.py`** — Runs tests, parses drift warnings, writes `schema_drift_report.json`. No OpenAPI or user-docs download.

## Related

- [API Validation](../api-validation.md) — Pre-implementation validation
- [Resource Implementation](../resource-implementation.md) — Implementation patterns
- [Troubleshooting](../troubleshooting.md) — Issue resolution
- [AGENTS.md](../../AGENTS.md) — AI agent index
