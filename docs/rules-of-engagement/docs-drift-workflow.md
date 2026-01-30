# Schema Drift Detection Workflow

> **Automated workflow for detecting discrepancies between API responses and Pydantic models**

## Overview

The schema drift workflow:

1. **Download OpenAPI spec** — Workflow downloads the spec to `external_docs/openapi-swagger.json` (gitignored) in the runner for reference.
2. **Run drift detection** — Runs integration tests and parses schema drift warnings via `.github/scripts/detect_schema_drift.py`.
3. **Create issues** — GitHub Action creates one issue per new drift (inline script; no separate script).

User-docs sync and sitemap downloads are deprecated in this repo; context is handled via Cursor rules and DeepWiki.

## GitHub Actions

**File**: `.github/workflows/schema-drift-detection.yml`

- **Schedule**: Hourly (endorctl version check); weekly Mondays 3 AM UTC; also `workflow_dispatch`.
- **Jobs**:
  1. **check-version**: Runs `.github/scripts/check_endorctl_version.py`; outputs whether version changed.
  2. **detect-schema-drift**: Runs when version changed or manually triggered. Downloads OpenAPI spec (curl), runs `detect_schema_drift.py --run-tests --test-path tests/ --output schema_drift_report.json`, then creates issues from the report via `actions/github-script`.

## Local Use

Download the OpenAPI spec and run drift detection:

```bash
mkdir -p external_docs
curl -sSfL -o external_docs/openapi-swagger.json https://api.endorlabs.com/download/openapiv2.swagger.json

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

## Scripts

- **`.github/scripts/check_endorctl_version.py`** — Version check (used by first job).
- **`.github/scripts/detect_schema_drift.py`** — Runs tests, parses drift warnings, writes `schema_drift_report.json`. No OpenAPI or user-docs download.

## Related

- [API Validation](../api-validation.md) — Pre-implementation validation
- [Resource Implementation](../resource-implementation.md) — Implementation patterns
- [Troubleshooting](../troubleshooting.md) — Issue resolution
- [AGENTS.md](../../AGENTS.md) — AI agent index
