---
name: endor-troubleshooting-scans
description: >-
  Scan pipeline RCA: resolve a project, fetch a bounded scan window, heuristically
  rank suspicious scan pairs, pull scan logs via ScanResult.get_logs for selected
  metrics/logs. Not for individual Finding rows or policy validation — hand off to
  other skills when deeper analysis is needed.
endorlabs:
  catalog:
    workflow_id: troubleshooting-scans
    module: endorlabs.workflows.troubleshooting_scans
    default_output: .endorlabs-context/workspace/sessions/<user>/troubleshooting/
    agent_visible: true
    composition: artifact_chain
    library_entrypoints:
      - endorlabs.Client.ScanResult.list_by_project
      - endorlabs.Client.Project.search_by_name
---

# Troubleshooting Scans

Chain CLI steps on JSON artifacts; extend with library imports per [workflow-composition](../../rules/endor-workflow-composition.md). Each step is optional — use the orchestrator for convenience or run modules individually and stop when you have enough signal.

## Scope

**In scope (this skill):**

- Resolve project candidates (name, URL, UUID).
- Fetch a **bounded** scan-result window and normalized summary metrics.
- **Heuristically** rank adjacent scan pairs (status, aggregate finding counts, dependency totals).
- Pull **scan logs** for the selected pair via `client.ScanResult.get_logs` (at most two scan UUIDs by default).
- Diff scan-level metrics and log excerpts into JSON + markdown artifacts.

**Out of scope (use another skill):**

- Listing or triaging individual **Finding** resources → [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md)
- Policy / exception matching → [endor-validate-policy](../endor-validate-policy/SKILL.md)
- Reachability signal conflicts on a finding → [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md)
- Fixed vs present at branch/commit, SBOM reconciliation → [endor-dependency-finding-provenance](../endor-dependency-finding-provenance/SKILL.md)
- Package introduction paths across manifests/versions → [endor-dependency-provenance](../endor-dependency-provenance/SKILL.md)

Finding counts here come from **`ScanResult.spec.stats` aggregates only** — not `Finding.list`.

## When to use this skill vs others

| Symptom / goal | Start here | Then |
| ---------------- | ---------- | ---- |
| Scan failed, metrics spiked, or logs look wrong between runs | **This skill** | — |
| Need CVE/finding rows, filters, branch dedup | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) | This skill if scan *pipeline* regressed |
| Diff flagged `findings_*` counts; need which findings changed | This skill (pair UUIDs from diff) | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) filtered by `context.scan_uuid` |
| Exception policy matches a finding? | [endor-validate-policy](../endor-validate-policy/SKILL.md) | — |
| Reachable dep vs unreachable function | [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md) | — |
| Same package, multiple versions/paths | [endor-dependency-provenance](../endor-dependency-provenance/SKILL.md) | — |

## Optional stops (artifact chain)

You do not need every step:

| Stop after | When |
| ---------- | ---- |
| `resolve_projects` | You only needed project UUID + namespace |
| `fetch_scan_results` | You want the scan window/summary without pair scoring |
| `select_anomalous_scans` | You have candidate pair UUIDs; skip logs until user confirms |
| `fetch_scan_logs` | Logs are enough; skip markdown diff |
| `run_troubleshooting_workflow --regression-only` | Fast check; skips logs/diff when heuristic score is zero |

Thread UUIDs and namespace from each artifact into the next step; do not re-list projects when JSON already has them.

## What this skill does

1. Resolve a project from name, URL, or UUID.
2. Pull a scan-result window.
3. **Heuristically** score adjacent scan pairs (drop/spike/failure patterns).
4. Pull logs for the chosen pair UUIDs.
5. Diff scan-result aggregate fields and log index into reports.

Artifacts live under `.endorlabs-context/workspace/sessions/` (default
`.../sessions/troubleshooting/`; prefer `.../sessions/<user>/troubleshooting/` for
interactive RCA). See [workspace-layout](../../rules/endor-workspace-layout.md). Filename
contract:

`{rootTenant}__{objectKind}__{objectUuid}__{purpose}[__timestamp].ext`

## Prerequisites

- Valid authentication in environment variables (`ENDOR_TOKEN` or API creds).
- Read access to project, scan results, and scan logs in target namespace.

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
  - **Cost:** lists scan results for the namespace then filters by project client-side; keep `--limit` small for interactive RCA. **`--all-projects`** walks every project under `--tenant` — expect long runtimes (see [AGENTS.md](../../../AGENTS.md#agent-notes) — tenant-wide scan fetch).

- `select_anomalous_scans.py`
  - **Heuristic** scoring on adjacent pairs using summary metrics (status, total finding counts, dependency totals, `scan_success` / `scan_failures` deltas). Default thresholds: `--min-delta-findings 10`, `--min-delta-deps 50`.
  - **`regression_detected`** means the selected pair's **score > 0** — not a platform-defined regression.
  - **`--pair-mode`:** `best-anomaly` (default, one pair), `latest` (most recent pair), `adjacent` (all pairs ranked).
  - Inputs: summary JSON from previous step.
  - Output object kind: `scan_result_pairs`.

- `fetch_scan_logs.py`
  - Retrieves ScanLog entries for the **first selected pair** (up to two scan UUIDs; `--max-entries` default 500). `ScanResult.get_logs` first, embedded `spec.logs` fallback.
  - Inputs: selected pairs JSON.
  - Output object kinds: `scan_log`, `scan_logs`.

- `diff_scans.py`
  - Compares normalized scan metrics (including aggregate `findings_*` counts, deps, status, ref/sha) and writes JSON + markdown report.
  - Does **not** diff individual Finding rows.
  - Inputs: selected pairs JSON (+ optional logs index).
  - Output object kind: `scan_diff`.

- `search_scan_errors.py`
  - Standalone: regex search over **embedded** `spec.logs` lines in a bounded scan window (no ScanLogRequest API).
  - Inputs: project selector or tenant-wide, error regex.
  - Output object kind: `scan_error_hits`.

- `run_troubleshooting_workflow.py`
  - End-to-end orchestrator chaining the steps above.
  - **`--regression-only`:** `--scan-window 2`, latest pair, skip logs and diff when heuristic score is zero.
  - **`--emit-diff`:** with `--regression-only`, still write diff when regression detected.

## Fast path examples

Project-specific RCA from project name:

```bash
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.run_troubleshooting_workflow \
  --tenant <tenant> \
  --project-name "https://github.com/endorlabs/endorlabs-sdk" \
  --limit 30 \
  --timestamped
```

Fast regression check (latest pair only, logs only when heuristic score > 0):

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

Manual step-by-step mode (stop at any step):

```bash
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.resolve_projects --tenant <tenant> --project-name "https://github.com/endorlabs/endorlabs-sdk"
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.fetch_scan_results --tenant <tenant> --project-name "https://github.com/endorlabs/endorlabs-sdk" --limit 30
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.select_anomalous_scans --input-summary <summary-json> --root-tenant <tenant> --project-uuid <project-uuid>
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.fetch_scan_logs --tenant <tenant> --namespace <project-namespace> --project-uuid <project-uuid> --input-pairs <pairs-json>
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.diff_scans --tenant <tenant> --namespace <project-namespace> --input-pairs <pairs-json>
```

After diff: use primary/secondary scan UUIDs from the pairs artifact with [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) (`context.scan_uuid` filter) for finding-level drill-down.

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
