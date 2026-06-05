---
name: troubleshooting-scans
description: >-
  Investigate scan regressions by resolving a project, retrieving anomalous
  ScanResults, pulling ScanLogs, and generating result/log diffs with
  repeatable parameterized scripts.
endorlabs:
  catalog:
    workflow_id: troubleshooting-scans
    module: endorlabs.workflows.troubleshooting_scans
    default_output: .endorlabs-context/workspace/sessions/<user>/troubleshooting/
    agent_visible: true
    composition: artifact_chain
    library_entrypoints:
      - endorlabs.workflows.troubleshooting_scans.list_scan_results_for_project
      - endorlabs.workflows.troubleshooting_scans.resolve_project
---

# Troubleshooting Scans

Chain CLI steps on JSON artifacts; extend with library imports per [workflow-composition](../../rules/workflow-composition.md).

## What this skill does

This skill provides a repeatable workflow for customer scan RCA:

1. Resolve a project from name, URL, or UUID.
2. Pull a scan-result window.
3. Select suspicious adjacent scan pairs (drop/spike/failure patterns).
4. Pull logs for chosen scan UUIDs.
5. Diff scan-result fields and logs into machine + human reports.

All artifacts are written under `.endorlabs-context/workspace/sessions/` (default
`.../sessions/troubleshooting/`; prefer `.../sessions/<user>/troubleshooting/` for
interactive RCA). See [workspace-layout](../../rules/workspace-layout.md). Filename
contract:

`{rootTenant}__{objectKind}__{objectUuid}__{purpose}[__timestamp].ext`

## Prerequisites

- Valid authentication in environment variables (`ENDOR_TOKEN` or API creds).
- Read access to project, scan results, and scan logs in target namespace.
- If package lineage questions arise (same package, multiple manifest paths/versions), hand off to `dependency-provenance`.

## Modules (`endorlabs.workflows.troubleshooting_scans`)

Installed package modules (run with `uv run python -m endorlabs.workflows.troubleshooting_scans.<name>`).

- `resolve_projects.py`
  - Resolves target project candidates.
  - Inputs: tenant/namespace + project selector(s).
  - Output object kind: `project`.

- `fetch_scan_results.py`
  - Pulls raw scan results and normalized summary rows.
  - Inputs: project UUID (or project-name mode / all-projects mode), limit/status.
  - Use `--scan-window` (alias of `--limit`) to bound retrieved scan count.
  - Optional **`--status-filter`** (e.g. `STATUS_FAILURE`, `STATUS_PARTIAL_SUCCESS`) filters results client-side after listing.
  - Output object kind: `scan_results`.
  - **Cost:** `--all-projects` walks **every** project under `--tenant`; expect **long runtimes** on large tenants. Prefer project-scoped `--project-name` / `--project-uuid` for interactive RCA (see [AGENTS.md](../../AGENTS.md) — Agent notes, tenant-wide troubleshooting).

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
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.run_troubleshooting_workflow \
  --tenant <tenant> \
  --project-name "https://github.com/endorlabs/endorlabs-sdk" \
  --limit 30 \
  --timestamped
```

Fast regression check (latest pair only, logs only when regression exists):

```bash
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.run_troubleshooting_workflow \
  --tenant <tenant> \
  --project-name "https://github.com/endorlabs/endorlabs-sdk" \
  --scan-window 2 \
  --regression-only
```

Tenant-wide error signature search:

```bash
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.search_scan_errors \
  --tenant <tenant> \
  --all-projects \
  --error-pattern "maven-profiler|dependency-resolution-error|STATUS_FAILURE" \
  --limit 20
```

Manual step-by-step mode:

```bash
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.resolve_projects --tenant <tenant> --project-name "https://github.com/endorlabs/endorlabs-sdk"
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.fetch_scan_results --tenant <tenant> --project-name "https://github.com/endorlabs/endorlabs-sdk" --limit 30
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.select_anomalous_scans --input-summary <summary-json> --root-tenant <tenant> --project-uuid <project-uuid>
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.fetch_scan_logs --tenant <tenant> --namespace <project-namespace> --project-uuid <project-uuid> --input-pairs <pairs-json>
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.diff_scans --tenant <tenant> --namespace <project-namespace> --input-pairs <pairs-json>
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
