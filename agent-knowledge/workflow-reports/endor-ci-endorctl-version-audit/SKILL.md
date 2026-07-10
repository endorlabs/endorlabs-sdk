---
name: endor-ci-endorctl-version-audit
description: |
  Use when auditing projects whose latest scan in a recent window ran via CLI
  endorctl (not agentless Cloud)—aggregating project counts by
  ScanResult.spec.environment.endorctl_version for CI adoption, stale CLI versions,
  or version-specific rollout status. Not for scan pipeline RCA or Cloud vs CLI
  registration classification alone.
---

# CI endorctl version audit

Summarize **how many projects** recently ran their **latest** scan through **CLI
`endorctl`** (`RunBySystem=false`), grouped by **`endorctl_version`**.

## Scope

**In scope**

- Tenant-wide or single-project audit via the bundled script.
- Default **7-day** lookback on **latest** `ScanResult.meta.create_time`.
- CLI execution only — exclude agentless Cloud scans (`RunBySystem=true`).
- Optional `--version` filter to list projects on a specific endorctl release (e.g. `1.7.980`).
- Emit CSV + chat summary with version histogram.

**Out of scope**

- Project **registration** source (SCM app vs CLI) → [endor-cli-vs-cloud-projects](../endor-cli-vs-cloud-projects/SKILL.md)
- Scan failures, metric spikes, log diffs → [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md)
- Per-project findings or scan rows → [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md)

## Inclusion rules

For each non-SBOM `Project` (`spec.sbom` unset):

1. Fetch newest `ScanResult` (`ScanResult.list_by_project`, `limit=1`).
2. **Recent:** `meta.create_time` within `--days` (default 7).
3. **CLI latest:** `spec.environment.config.RunBySystem` is **false** → CLI execution.
4. **Version:** read `spec.environment.endorctl_version` (normalize `endorctl version vX.Y.Z` → `X.Y.Z`).

Projects whose latest scan is Cloud/agentless or older than the window are excluded from the version histogram (counts reported separately in summary).

## Workflow

### Step 1: Run the bundled script

Default output: `.endorlabs-context/workspace/runs/ci-endorctl-version-audit/<tenant>-ci-endorctl-versions.csv`

```bash
uv run python agent-knowledge/workflow-reports/endor-ci-endorctl-version-audit/scripts/audit_ci_endorctl_versions.py \
  --tenant <tenant> \
  --output .endorlabs-context/workspace/runs/ci-endorctl-version-audit/<tenant>-ci-endorctl-versions.csv
```

Optional flags:

- `--days <n>` — lookback window (default 7).
- `--version <semver>` — list projects on that endorctl version (e.g. `1.7.980`).
- `--project-uuid <uuid>` — restrict to one or more projects (repeatable).
- `--max-pages <n>` — bound project list pagination when requested.
- `--max-workers <n>` — parallel latest-scan lookup (default 12).
- `--summary-json <path>` — machine-readable summary alongside chat output.

After `endorlabs.init()`, the script path is also under `sdk/skills/endor-ci-endorctl-version-audit/scripts/`.

### Step 2: Summarize in chat (required)

Always report:

- Tenant and lookback days.
- Projects considered (SBOM excluded count).
- Exclusion breakdown: no scan, not recent, non-CLI latest.
- **CLI projects in window** total.
- **Version histogram** (`endorctl version` → project count), descending.
- When `--version` is set: matching project list with namespace and latest scan time.
- Path to CSV written.

Use script stdout as source of truth; do not re-list the API for summary numbers.

## CSV schema

| Column | Source |
|--------|--------|
| **`project name`** | `Project.meta.name` |
| **`namespace`** | `Project.tenant_meta.namespace` |
| **`uuid`** | `Project.uuid` |
| **`latest scan execution`** | Always `CLI` for included rows |
| **`endorctl version`** | Normalized `ScanResult.spec.environment.endorctl_version` |
| **`latest scan time`** | `ScanResult.meta.create_time` (ISO) |

Header row:

```text
project name,namespace,uuid,latest scan execution,endorctl version,latest scan time
```

## Output checklist

Before finishing, confirm:

- [ ] CSV exists with the header above
- [ ] Every row has `latest scan execution` = `CLI`
- [ ] Version histogram covers all included projects
- [ ] Exclusion counts printed when projects were dropped
- [ ] Artifacts under `.endorlabs-context/workspace/runs/ci-endorctl-version-audit/` (gitignored)

## When to use this skill vs others

| Question | Start here | Then |
|----------|------------|------|
| Which endorctl versions are CI projects running? | **This skill** | — |
| Is the project Cloud-integrated or CLI-registered? | [endor-cli-vs-cloud-projects](../endor-cli-vs-cloud-projects/SKILL.md) | This skill for latest scan execution version |
| Scan failed after a version bump | [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) | This skill to confirm fleet version mix |
| Findings for one project | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) | — |

## Related skills

| Need | Skill |
| ---- | ----- |
| CLI vs Cloud registration and mixed mode | [endor-cli-vs-cloud-projects](../endor-cli-vs-cloud-projects/SKILL.md) |
| Scan pipeline RCA | [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) |
| Single-project scan + findings | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) |
