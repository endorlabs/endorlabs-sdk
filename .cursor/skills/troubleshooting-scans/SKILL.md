---
name: troubleshooting-scans
description: >-
  Investigate scan regressions by resolving a project, retrieving anomalous
  ScanResults, pulling ScanLogs, and generating result/log diffs with
  repeatable parameterized scripts.
---

# Troubleshooting Scans

## What this skill does

This skill provides a repeatable workflow for customer scan RCA:

1. Resolve a project from name, URL, or UUID.
2. Pull a scan-result window.
3. Select suspicious adjacent scan pairs (drop/spike/failure patterns).
4. Pull logs for chosen scan UUIDs.
5. Diff scan-result fields and logs into machine + human reports.

All artifacts are written to local storage (default `.tmp/`) with a strict
filename contract:

`{rootTenant}__{objectKind}__{objectUuid}__{purpose}[__timestamp].ext`

## Prerequisites

- Valid authentication in environment variables (`ENDOR_TOKEN` or API creds).
- Read access to project, scan results, and scan logs in target namespace.

## Scripts

Located in `scripts/troubleshooting_scans/`.

- `resolve_projects.py`
  - Resolves target project candidates.
  - Inputs: tenant/namespace + project selector(s).
  - Output object kind: `project`.

- `fetch_scan_results.py`
  - Pulls raw scan results and normalized summary rows.
  - Inputs: project UUID (or project-name mode / all-projects mode), limit/status.
  - Use `--scan-window` (alias of `--limit`) to bound retrieved scan count.
  - Output object kind: `scan_results`.

- `select_anomalous_scans.py`
  - Scores adjacent pairs for likely regressions.
  - Inputs: summary JSON from previous step.
  - Output object kind: `scan_result_pairs`.

- `fetch_scan_logs.py`
  - Retrieves ScanLog entries for selected pair UUIDs (ScanLogs facade first, embedded fallback).
  - Inputs: selected pairs JSON.
  - Output object kinds: `scan_log`, `scan_logs`.

- `diff_scans.py`
  - Compares normalized scan metrics and writes JSON + markdown report.
  - Inputs: selected pairs JSON (+ optional logs index).
  - Output object kind: `scan_diff`.

- `search_scan_errors.py`
  - Independent mode to search scan logs for a regex pattern.
  - Inputs: project selector or tenant-wide, error regex.
  - Output object kind: `scan_error_hits`.

- `run_troubleshooting_workflow.py`
  - End-to-end orchestrator using only outputs from prior step.
  - Supports `--regression-only` to evaluate latest-vs-previous and skip expensive
    outputs when no regression is detected.
  - Supports `--emit-diff` when regression-only mode still needs a diff artifact.

## Fast path examples

Project-specific RCA from project name:

```bash
uv run --env-file .env python scripts/troubleshooting_scans/run_troubleshooting_workflow.py \
  --tenant datavant \
  --project-name "Apixio/codenavigator-monitoring" \
  --limit 30 \
  --output-dir .tmp \
  --timestamped
```

Fast regression check (latest pair only, logs only when regression exists):

```bash
uv run --env-file .env python scripts/troubleshooting_scans/run_troubleshooting_workflow.py \
  --tenant datavant \
  --project-name "Apixio/codenavigator-monitoring" \
  --scan-window 2 \
  --regression-only \
  --output-dir .tmp
```

Tenant-wide error signature search:

```bash
uv run --env-file .env python scripts/troubleshooting_scans/search_scan_errors.py \
  --tenant datavant \
  --all-projects \
  --error-pattern "maven-profiler|dependency-resolution-error|STATUS_FAILURE" \
  --limit 20 \
  --output-dir .tmp
```

Manual step-by-step mode:

```bash
uv run --env-file .env python scripts/troubleshooting_scans/resolve_projects.py --tenant datavant --project-name "Apixio/codenavigator-monitoring"
uv run --env-file .env python scripts/troubleshooting_scans/fetch_scan_results.py --tenant datavant --project-name "Apixio/codenavigator-monitoring" --limit 30
uv run --env-file .env python scripts/troubleshooting_scans/select_anomalous_scans.py --input-summary <summary-json> --root-tenant datavant --project-uuid <project-uuid>
uv run --env-file .env python scripts/troubleshooting_scans/fetch_scan_logs.py --tenant datavant --namespace <project-namespace> --project-uuid <project-uuid> --input-pairs <pairs-json>
uv run --env-file .env python scripts/troubleshooting_scans/diff_scans.py --tenant datavant --namespace <project-namespace> --input-pairs <pairs-json>
```

## Interpretation hints

- `scan_success` drop to zero + `dependency_count_total` collapse usually indicates dependency-resolution pipeline failure.
- Compare `endorctl_version`, scan status, and dependency metrics first.
- Use `search_scan_errors.py` with ecosystem-specific patterns to confirm signature recurrence.

## Recommended defaults

- Fast regression check:
  - `--scan-window 2 --regression-only`
- Full RCA:
  - `--scan-window 30` (or `50` for noisier repos)
- Emit diff in regression-only mode only when needed:
  - add `--emit-diff`
