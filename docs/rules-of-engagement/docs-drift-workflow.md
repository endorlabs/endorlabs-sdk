# Unified Documentation & Schema Drift Workflow

> **Automated workflow for keeping documentation and schema models in sync**

**Note:** Documentation Sync (OpenAPI + user docs from sitemap) is not run in main CI; use for personal branch or local refresh.

## Overview

The unified documentation and schema drift workflow orchestrates two critical maintenance tasks:

1. **Documentation Sync**: Downloads and updates external documentation (OpenAPI spec and user docs)
2. **Schema Drift Detection**: Detects discrepancies between API responses and Pydantic models

This workflow ensures that:
- Documentation is always fresh before drift detection
- Schema drift is automatically detected and tracked
- GitHub issues are created for new drifts
- All operations are coordinated and logged

## Architecture

The workflow consists of three phases:

```
Phase 1: Documentation Sync
  ├── Download OpenAPI specification
  └── Download user documentation (optional)

Phase 2: Schema Drift Detection
  ├── Run integration tests
  ├── Parse drift warnings
  └── Generate drift report

Phase 3: Issue Creation & Reporting
  ├── Create GitHub issues for new drifts
  └── Generate summary report
```

## Usage

### Command-Line Interface

The unified workflow script (`.github/scripts/unified_docs_workflow.py`) provides flexible options:

#### Full Workflow

Run both documentation update and drift detection:

```bash
python .github/scripts/unified_docs_workflow.py --all
```

#### Documentation Only

Update documentation without checking for drift:

```bash
python .github/scripts/unified_docs_workflow.py --update-docs-only
```

#### Drift Detection Only

Check for schema drift without updating docs:

```bash
python .github/scripts/unified_docs_workflow.py --check-drift-only
```

**Note**: Drift detection will be skipped if docs weren't updated (unless `--force` is used).

#### Force Operations

Force operations even if not needed:

```bash
python .github/scripts/unified_docs_workflow.py --all --force
```

#### Include User Documentation

Download user docs along with OpenAPI spec:

```bash
python .github/scripts/unified_docs_workflow.py --update-docs-only \
  --download-user-docs \
  --max-pages 100
```

### GitHub Actions Integration

The workflow is integrated into two GitHub Actions workflows:

#### 1. Documentation Sync Workflow

**File**: `.github/workflows/sync-external-docs.yml`

- **Schedule**: Weekly on Mondays at 2 AM UTC
- **Action**: Updates documentation only
- **Command**: `--update-docs-only --download-openapi --download-user-docs`

#### 2. Schema Drift Detection Workflow

**File**: `.github/workflows/schema-drift-detection.yml`

- **Schedule**: 
  - Hourly (version checks)
  - Weekly on Mondays at 3 AM UTC (after docs sync)
- **Action**: Detects schema drift and creates issues
- **Command**: `--check-drift-only`

## Workflow Phases

### Phase 1: Documentation Sync

**Purpose**: Ensure external documentation is up to date

**Operations**:
1. Download OpenAPI specification from Endor Labs API
2. Optionally download user documentation from sitemap
3. Track whether files were actually updated

**Outputs**:
- `external_docs/openapi-swagger.json` - OpenAPI specification
- `external_docs/user-docs/` - User documentation (if enabled)

**Smart Behavior**:
- Skips download if file exists and `--force` is not used
- Tracks file modification times to detect actual updates
- Only triggers drift detection if docs were updated

### Phase 2: Schema Drift Detection

**Purpose**: Detect discrepancies between API responses and Pydantic models

**Operations**:
1. Run integration tests with drift detection enabled
2. Parse schema drift warnings from test output
3. Generate comprehensive drift report
4. Track new vs. known drifts

**Outputs**:
- `schema_drift_report.json` - Detailed drift report

**Smart Behavior**:
- Only runs if docs were updated in Phase 1 (unless `--force`)
- Avoids duplicate drift detection when docs haven't changed
- Captures both drift warnings and validation errors

### Phase 3: Issue Creation & Reporting

**Purpose**: Create actionable GitHub issues for new drifts

**Operations**:
1. Read drift report
2. Check for existing issues to avoid duplicates
3. Create GitHub issues for new drifts
4. Generate summary report

**Outputs**:
- GitHub issues with label `schema-drift`
- Summary report with drift statistics

**Smart Behavior**:
- Checks existing issues to avoid duplicates
- Only creates issues for drifts with status "new"
- Provides detailed issue descriptions with code locations

## Exit Codes

The workflow uses exit codes to indicate status:

- `0` - Success, no drift detected
- `1` - Success, but drift detected (action needed)
- `2` - Error occurred during execution

## Configuration

### Environment Variables

**Required for Documentation Sync**:
- `ENDOR_API` - Endor Labs API base URL
- `ENDOR_API_CREDENTIALS_KEY` - API credentials key
- `ENDOR_API_CREDENTIALS_SECRET` - API credentials secret

**Required for Issue Creation**:
- `GITHUB_REPOSITORY` - GitHub repository (e.g., `owner/repo`)
- `GITHUB_TOKEN` - GitHub personal access token

**Optional**:
- `ENDOR_NAMESPACE` - Endor Labs namespace for API calls

### Command-Line Options

**Action Flags** (mutually exclusive, one required):
- `--all` - Run both documentation update and drift detection
- `--update-docs-only` - Only update documentation
- `--check-drift-only` - Only check for schema drift

**Documentation Options**:
- `--download-openapi` - Download OpenAPI spec (default: True)
- `--no-download-openapi` - Skip OpenAPI spec download
- `--download-user-docs` - Download user documentation
- `--openapi-output PATH` - OpenAPI spec output path
- `--user-docs-output PATH` - User docs output directory
- `--max-pages N` - Maximum user doc pages to download

**Drift Detection Options**:
- `--test-path PATH` - Test directory path (default: `tests/`)
- `--drift-report-output PATH` - Drift report output file
- `--no-create-issues` - Don't create GitHub issues

**Common Options**:
- `--force` - Force operations even if not needed
- `--verbose` - Enable verbose logging

## Relationship to Individual Scripts

The unified workflow script orchestrates existing scripts:

- **`.github/scripts/sync_external_docs.py`**: Provides documentation download functions
- **`.github/scripts/detect_schema_drift.py`**: Provides drift detection logic
- **`.github/scripts/create_drift_issues.py`**: Provides GitHub issue creation

**Backward Compatibility**: All individual scripts remain functional for manual use.

## Troubleshooting

### Documentation Not Updating

**Problem**: OpenAPI spec shows as "already exists" even when it should update.

**Solution**: Use `--force` flag to force re-download:
```bash
python .github/scripts/unified_docs_workflow.py --update-docs-only --force
```

### Drift Detection Skipped

**Problem**: Drift detection is skipped even when you want it to run.

**Solution**: Use `--force` flag to force drift detection:
```bash
python .github/scripts/unified_docs_workflow.py --check-drift-only --force
```

### GitHub Issues Not Created

**Problem**: Drifts detected but no issues created.

**Check**:
1. `GITHUB_REPOSITORY` environment variable is set
2. `GITHUB_TOKEN` environment variable is set and valid
3. Token has permissions to create issues
4. Use `--verbose` to see detailed error messages

### Test Failures

**Problem**: Tests fail during drift detection.

**Note**: Test failures don't prevent drift detection. The workflow uses `continue-on-error: true` in GitHub Actions to ensure drift detection completes even if some tests fail.

**Solution**: Review test output and fix failing tests separately.

## Best Practices

### For Automated Workflows

1. **Schedule Coordination**: Documentation sync should run before drift detection
2. **Force Flag**: Use `--force` sparingly, only when needed
3. **Issue Management**: Review and close drift issues after fixing models
4. **Monitoring**: Check workflow runs regularly for failures

### For Manual Use

1. **Update Docs First**: Always update docs before checking drift
2. **Use Force Sparingly**: Only use `--force` when you know docs need updating
3. **Review Reports**: Check drift reports before creating issues
4. **Test Locally**: Test workflow changes locally before committing

## Integration with API Understanding Workflow

This workflow supports the [API Understanding Workflow](../api-validation.md) by:

1. **Keeping Spec Fresh**: Ensures OpenAPI spec is always up to date
2. **Detecting Changes**: Automatically detects when API changes
3. **Creating Issues**: Provides actionable issues for model updates
4. **Tracking Drift**: Maintains history of schema drift over time

## Related Documentation

- [API Validation Guide](../api-validation.md) - Pre-implementation validation
- [Resource Implementation Guide](../resource-implementation.md) - Implementation patterns
- [Troubleshooting Guide](../troubleshooting.md) - Issue resolution patterns
- [AGENTS.md](../../AGENTS.md) - AI agent integration guide

## Examples

### Local Development

Update docs and check for drift:

```bash
export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-key"
export ENDOR_API_CREDENTIALS_SECRET="your-secret"

python .github/scripts/unified_docs_workflow.py --all
```

### CI/CD Integration

In a CI pipeline, you might want to check drift without updating docs:

```bash
python .github/scripts/unified_docs_workflow.py --check-drift-only --force
```

### Manual Issue Creation

If you have a drift report but want to create issues separately:

```bash
export GITHUB_REPOSITORY="owner/repo"
export GITHUB_TOKEN="your-token"

python .github/scripts/create_drift_issues.py --report schema_drift_report.json
```

