---
name: endor-troubleshooting-scans
description: |
  Use when doing scan pipeline RCA: resolve a project (including app scan-history
  URLs), compare scan pairs (heuristic or user-supplied), search embedded spec.logs
  for errors, diff aggregate metrics, and probe PackageVersion resolution_errors.
  Not for individual Finding rows or policy validation—hand off to sibling skills
  when deeper analysis is needed.
endorlabs:
  catalog:
    workflow_id: troubleshooting-scans
    module: endorlabs.workflows.troubleshooting_scans
    default_output: .endorlabs-context/workspace/runs/troubleshooting-scans/
    agent_visible: true
    composition: artifact_chain
    library_entrypoints:
      - endorlabs.Client.ScanResult.list_by_project
      - endorlabs.Client.Project.search_by_name
      - endorlabs.Client.Finding.list_for_context
      - endorlabs.workflows.troubleshooting_scans.common.scanlog_entries_have_content
---

# Troubleshooting Scans

Chain CLI steps on JSON artifacts; extend with library imports per [workflow-composition](../../rules/endor-workflow-composition.md). Each step is optional — use the orchestrator for convenience or run modules individually and stop when you have enough signal.

## Scope

**In scope (this skill):**

- Resolve project candidates (name, UUID, **app scan-history URL**).
- Fetch a **bounded** scan-result window and normalized summary metrics.
- **Heuristically** rank adjacent scan pairs **or** build an **explicit user-supplied pair**.
- Search **embedded** `spec.logs` for error signatures (`search_scan_errors`).
- Pull scan logs for selected pair UUIDs (embedded fallback when ScanLog API rows are hollow).
- Diff scan-level aggregate metrics into JSON + markdown artifacts.
- **Library probe:** `PackageVersion.list_by_project(project)` → `spec.resolution_errors` when dependency metrics collapse.

**Out of scope (use another skill):**

- Whether the project is **CLI vs Cloud** (agentless SCM) → [endor-workflow-reports](../endor-workflow-reports/SKILL.md) — especially when `RunBySystem` differs between scans
- Listing or triaging individual **Finding** resources → [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md)
- Policy / exception matching → [endor-validate-policy](../endor-validate-policy/SKILL.md)
- Reachability signal conflicts on a finding → [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md)
- Tenant-wide PRF approximation / PV resolution error report → [endor-workflow-reports](../endor-workflow-reports/SKILL.md)
- New vs resolved FindingLog trend charts → [endor-workflow-reports](../endor-workflow-reports/SKILL.md)
- Fixed vs present at branch/commit, SBOM reconciliation → [endor-sca-findings](../endor-sca-findings/SKILL.md)
- Package introduction paths across manifests/versions → [endor-dependency-provenance](../endor-dependency-provenance/SKILL.md)

Finding counts here come from **`ScanResult.spec.stats` aggregates only** — not `Finding.list`.

## Entry paths (pick one)

| User gives you | Start with | Skip |
| -------------- | ---------- | ---- |
| App **scan-history** or **project** URL | `search_projects --endor-app-url` or `--scan-result-url` | — |
| **Two specific scans** to compare | `build_scan_pair` → `diff_scans` → `search_scan_errors` | `select_anomalous_scans` |
| “Something regressed recently” (no UUIDs) | `run_troubleshooting_workflow` or heuristic chain below | explicit pair |
| Single scan failed (`PARTIAL_SUCCESS`, etc.) | `search_projects` + `search_scan_errors` on that scan's window | pair diff until baseline known |

Thread UUIDs and namespace from each artifact into the next step; do not re-list projects when JSON already has them.

## When to use this skill vs others

| Symptom / goal | Start here | Then |
| ---------------- | ---------- | ---- |
| Scan failed, metrics spiked, or logs look wrong between runs | **This skill** | — |
| Need CVE/finding rows, filters, branch dedup | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) | This skill if scan *pipeline* regressed |
| Diff flagged `findings_*` counts; need which findings changed | This skill (pair UUIDs from diff) | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) via `Finding.list_for_context(scan)` |
| `dependency_count_total` collapsed / resolution errors | This skill (embedded logs + PV probe) | [endor-sca-findings](../endor-sca-findings/SKILL.md) at branch/sha |
| Tenant-wide PV resolution error patterns | [endor-workflow-reports](../endor-workflow-reports/SKILL.md) | This skill for one scan pair |
| Automated vs manual scan config differs (`RunBySystem`) | [endor-workflow-reports](../endor-workflow-reports/SKILL.md) | This skill for metrics/logs |
| Exception policy matches a finding? | [endor-validate-policy](../endor-validate-policy/SKILL.md) | — |
| Reachable dep vs unreachable function | [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md) | — |
| New vs resolved vuln trend (FindingLog) | [endor-workflow-reports](../endor-workflow-reports/SKILL.md) | — |
| Same package, multiple versions/paths | [endor-dependency-provenance](../endor-dependency-provenance/SKILL.md) | — |

## Artifact chains

### Heuristic regression (default)

1. `search_projects` or `resolve_projects` → project UUID + namespace
2. `fetch_scan_results` → scan window summary
3. `select_anomalous_scans` → ranked pair (`regression_detected` = score > 0)
4. `search_scan_errors` → embedded `spec.logs` regex hits
5. `diff_scans` → aggregate metric diff
6. `fetch_scan_logs` or `pull_scan_logs` → only if embedded search insufficient
7. `summarize_scan_triage` → optional markdown from pull artifacts

### Explicit pair (user named two scans)

1. `search_projects --endor-app-url <either-scan-url>` → project UUID + namespace
2. `build_scan_pair --primary-scan-result-url … --secondary-scan-result-url …`
3. `search_scan_errors` (per scan or bounded window)
4. `diff_scans --input-pairs <pairs-json>`
5. **If dep metrics collapsed:** library PV `resolution_errors` probe (below)
6. `fetch_scan_logs` / `pull_scan_logs` / `summarize_scan_triage` as needed

### Dependency-resolution branch

After `diff_scans`, when `scan_success` drops and/or `dependency_count_total` collapses:

1. `search_scan_errors` with patterns like `dependency-resolution|Unable to resolve|sbt|maven|gradle|invalid`
2. Library probe on `Project.get(uuid)`:

```python
project = client.Project.get(project_uuid, namespace=project_ns)
scan = client.ScanResult.get(scan_uuid, namespace=project_ns)
for line in (scan.model_dump(mode="json").get("spec") or {}).get("logs") or []:
  ...  # embedded JSON error lines

for pv in client.PackageVersion.list_by_project(project, namespace=project_ns, max_pages=5):
    errs = (pv.model_dump(mode="json").get("spec") or {}).get("resolution_errors")
    if errs:
        ...  # STATUS_ERROR_BUILD / unresolved.description
```

3. **Hand off:** single-project branch/sha → [endor-sca-findings](../endor-sca-findings/SKILL.md); tenant-wide → [endor-workflow-reports](../endor-workflow-reports/SKILL.md)

## Optional stops (artifact chain)

| Stop after | When |
| ---------- | ---- |
| `search_projects` | Resolved namespace + project from app URL only |
| `resolve_projects` | You only needed project UUID + namespace |
| `fetch_scan_results` | Scan window/summary without pair scoring |
| `build_scan_pair` | User supplied both scan UUIDs; skip heuristic pairing |
| `search_scan_errors` | Embedded errors explain `PARTIAL_SUCCESS` or dep collapse |
| `select_anomalous_scans` | Candidate pair UUIDs; skip logs until user confirms |
| `diff_scans` | Aggregate diff enough; no full log pull |
| `fetch_scan_logs` | Log artifact sufficient; skip markdown summarize |
| `run_troubleshooting_workflow --regression-only` | Fast check; skips logs/diff when heuristic score is zero |

### Decision signals

| Signal in artifact | Next step |
| -------------------- | --------- |
| `status: STATUS_PARTIAL_SUCCESS` | `search_scan_errors` before ScanLog API pull |
| `scan_success` ↓ and `dependency_count_total` ↓ | PV `resolution_errors` library probe |
| `fetch_scan_logs` `entry_count > 0` but no `error` in text | Re-check embedded `spec.logs`; API rows may be hollow |
| `regression_detected: false` but user named two scans | Use explicit-pair path; user intent overrides heuristic |
| `RunBySystem: true` vs `false` in scan config | [endor-workflow-reports](../endor-workflow-reports/SKILL.md) for config narrative |

Artifacts live under `.endorlabs-context/workspace/runs/troubleshooting-scans/`.
See [workspace-layout](../../rules/endor-workspace-layout.md). Filename
contract:

`{rootTenant}__{objectKind}__{objectUuid}__{purpose}[__timestamp].ext`

## Prerequisites

- Valid authentication in environment variables (`ENDOR_TOKEN` or API creds).
- Read access to project, scan results, and scan logs in target namespace.

## Modules (`endorlabs.workflows.troubleshooting_scans`)

Installed package modules (run with `uv run python -m endorlabs.workflows.troubleshooting_scans.<name>`).

- `search_projects.py`
  - **Preferred entry** from Endor app URLs (`--endor-app-url`, `--scan-result-url`, `--scan-result-uuid`).
  - Traverse-aware `ScanResult.get` when namespace in URL may differ from `--tenant`.
  - Output object kind: `project_search`.

- `resolve_projects.py`
  - Resolves target project candidates by name/UUID (no app URL parsing).
  - Output object kind: `project`.

- `build_scan_pair.py`
  - Builds `scan_result_pairs` JSON for **user-supplied** primary/secondary scan UUIDs or scan-history URLs.
  - Output object kind: `scan_result_pairs` (`pair_mode: user_supplied`).

- `fetch_scan_results.py`
  - Pulls raw scan results and normalized summary rows.
  - Use `--scan-window` (alias of `--limit`) to bound retrieved scan count.
  - Optional **`--status-filter`** (e.g. `STATUS_FAILURE`, `STATUS_PARTIAL_SUCCESS`) filters client-side after listing.
  - Output object kind: `scan_results`.

- `pull_scan_results.py`
  - Heavier scan-result pull for `summarize_scan_triage` input artifacts.

- `select_anomalous_scans.py`
  - **Heuristic** scoring on adjacent pairs. `regression_detected` = selected pair **score > 0**.
  - **`--pair-mode`:** `best-anomaly` (default), `latest`, `adjacent`.
  - Output object kind: `scan_result_pairs`.

- `search_scan_errors.py`
  - Regex search over **embedded** `spec.logs` in a bounded scan window — **run before** `fetch_scan_logs` when status is partial/failed.
  - Output object kind: `scan_error_hits`.

- `diff_scans.py`
  - Compares normalized scan metrics (status, deps, findings totals, ref/sha). Does **not** diff Finding rows or `resolution_errors`.
  - Output object kind: `scan_diff`.

- `fetch_scan_logs.py`
  - ScanLog API via `ScanResult.get_logs`; falls back to embedded `spec.logs` when API returns no rows **or hollow messages** (timestamp/level only).
  - Output object kinds: `scan_log`, `scan_logs`.

- `pull_scan_logs.py`
  - Paginated full log pull for deep RCA / `summarize_scan_triage`.

- `summarize_scan_triage.py`
  - Markdown triage summary from `pull_scan_results` + `pull_scan_logs` artifacts.

- `run_troubleshooting_workflow.py`
  - End-to-end orchestrator (heuristic path).
  - **`--regression-only`:** `--scan-window 2`, latest pair, skip logs/diff when heuristic score is zero.
  - **`--emit-diff`:** with `--regression-only`, still write diff when regression detected.

## Fast path examples

From app scan-history URL (explicit pair):

```bash
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.search_projects \
  --tenant <tenant> \
  --endor-app-url "https://app.endorlabs.com/t/<namespace>/scan-history/<scan-uuid>"

uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.build_scan_pair \
  --tenant <tenant> \
  --project-uuid <project-uuid> \
  --primary-scan-result-url "<bad-scan-url>" \
  --secondary-scan-result-url "<good-scan-url>" \
  --timestamped

uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.search_scan_errors \
  --tenant <tenant> \
  --project-uuid <project-uuid> \
  --error-pattern "Unable to resolve|dependency-resolution|sbt|STATUS_" \
  --limit 10

uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.diff_scans \
  --tenant <tenant> \
  --namespace <project-namespace> \
  --input-pairs <pairs-json> \
  --timestamped
```

Heuristic regression from project name:

```bash
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.run_troubleshooting_workflow \
  --tenant <tenant> \
  --project-name "https://github.com/org/repo" \
  --scan-window 2 \
  --regression-only \
  --emit-diff
```

Tenant-wide error signature search:

```bash
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.search_scan_errors \
  --tenant <tenant> \
  --all-projects \
  --error-pattern "maven-profiler|dependency-resolution-error|STATUS_FAILURE" \
  --limit 20
```

## Hand off to finding-level drill-down

After diff, use scan UUIDs from the pairs artifact with [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md):

```python
scan = client.ScanResult.get(scan_uuid, namespace=project_ns)
findings = client.Finding.list_for_context(scan, max_pages=5)
```

Do **not** filter on `context.scan_uuid` — see [resource-discovery contract](../../contracts/resource-discovery.md).

## Interpretation hints

- `scan_success` drop + `dependency_count_total` collapse → dependency-resolution pipeline failure; check embedded logs and PV `resolution_errors`.
- Compare `endorctl_version`, scan status, `RunBySystem`, and dependency metrics first.
- Use `search_scan_errors.py` with ecosystem-specific patterns before pulling full ScanLog streams.
- Empty `package defined in ''` in embedded logs → root build unit (e.g. root `build.sbt` / `pom.xml`).

## Related skills

| Need | Skill |
| ---- | ----- |
| Finding rows for a scan plane | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) |
| CLI vs Cloud scan config | [endor-workflow-reports](../endor-workflow-reports/SKILL.md) |
| Branch/sha fixed vs present | [endor-sca-findings](../endor-sca-findings/SKILL.md) |
| Tenant-wide PV resolution errors | [endor-workflow-reports](../endor-workflow-reports/SKILL.md) |

## Recommended defaults

- Fast regression check: `--scan-window 2 --regression-only`
- Full RCA: `--scan-window 30` (or `50` for noisier repos)
- Emit diff in regression-only mode when needed: add `--emit-diff`
