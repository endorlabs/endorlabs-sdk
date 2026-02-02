# Schema Drift Detection Workflow

> **Automated workflow for detecting discrepancies between API responses and Pydantic models**

Local setup: see [CONTRIBUTORS.md](../../CONTRIBUTORS.md).

## Sync external docs (recommended for advanced users)

A single workflow creates the gitignored `external_docs/` folder with both the OpenAPI spec and user documentation from [docs.endorlabs.com](https://docs.endorlabs.com/). **Recommended for advanced users** to pull full platform-admin context into the IDE.

```bash
uv sync --extra docs
uv run python scripts/sync_external_docs.py --all
```

This creates:

- `external_docs/openapi-swagger.json` — API spec
- `external_docs/user-docs/*.md` — User docs (sitemap-based, parallel download)

See [scripts/README.md](../../scripts/README.md#sync_external_docspy) for options (e.g. spec-only, `--max-pages`, `--force`).

## Schema drift workflow (CI and local)

The schema drift workflow:

1. **Download OpenAPI spec** — CI downloads the spec to `external_docs/openapi-swagger.json` (gitignored) in the runner for reference.
2. **Run drift detection** — Runs integration tests and parses schema drift warnings via `.github/scripts/detect_schema_drift.py`.
3. **Create issues** — GitHub Action creates one issue per new drift (inline script; no separate script).

## GitHub Actions

**File**: `.github/workflows/schema-drift-detection.yml`

- **Schedule**: Hourly (endorctl version check); weekly Mondays 3 AM UTC; also `workflow_dispatch`.
- **Jobs**:
  1. **check-version**: Runs `.github/scripts/check_endorctl_version.py`; outputs whether version changed.
  2. **detect-schema-drift**: Runs when version changed or manually triggered. Downloads OpenAPI spec (curl), runs `detect_schema_drift.py --run-tests --test-path tests/ --output schema_drift_report.json`, then creates issues from the report via `actions/github-script`.

## Local Use

**Option A — Full context:** Sync spec + user docs into `external_docs/`, then run drift detection (see [Sync external docs](#sync-external-docs-recommended-for-advanced-users) above).

**Option B — Spec only:** Create `external_docs/` and download the spec with the sync script, then run drift detection:

```bash
uv run python scripts/sync_external_docs.py --download-openapi

export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-key"
export ENDOR_API_CREDENTIALS_SECRET="your-secret"
export ENDOR_NAMESPACE="your-namespace"

python .github/scripts/detect_schema_drift.py --run-tests --test-path tests/ --output schema_drift_report.json
```

Check an existing report without re-running tests:

```bash
python .github/scripts/detect_schema_drift.py --check-existing
```

**Model consistency (static):** Diff SDK Pydantic field paths vs OpenAPI definitions (no test run). Run: `uv run python .github/scripts/detect_schema_drift.py --model-consistency --output-format json`. Writes `model_consistency_report.json` (uses `external_docs/openapi-swagger.json` if present, else fetches spec).

## Scripts

- **`.github/scripts/check_endorctl_version.py`** — Version check (used by first job).
- **`.github/scripts/detect_schema_drift.py`** — Runs tests, parses drift warnings, writes `schema_drift_report.json`. No OpenAPI or user-docs download.
- **`scripts/sync_external_docs.py`** — Single script that creates `external_docs/` with OpenAPI spec and/or user docs (sitemap). Use `--all` for full IDE context. See [scripts/README.md](../../scripts/README.md#sync_external_docspy).

## Related

- [API Validation](../api-validation.md) — Pre-implementation validation
- [Resource Implementation](../resource-implementation.md) — Implementation patterns
- [Troubleshooting](../troubleshooting.md) — Issue resolution
- [AGENTS.md](../../AGENTS.md) — AI agent index
