---
name: troubleshooting-scans
description: >-
  Troubleshoot Endor Labs scan runs: persisted ScanResults and ScanLogs, triage
  outcomes and logs, reproduce dependency/toolchain issues against the scan
  environment. Scripts in scripts/troubleshooting_scans/. Not for FP review,
  policy design, or dry-run-only workflows.
---

# Troubleshooting Scans

## Scope and out-of-scope

**In scope:** **Scan execution and results** for Git-backed **Projects**: persisted **ScanResult** history, **ScanLogs**, dependency / call graph / provisioning / clone failures surfaced in those artifacts, and **local reproduction** against what the scan environment used. Policy **counters** and triggered IDs in ScanResult stats or logs are **diagnostic only** (separate scanner failure from policy enforcement).

**Out of scope:** **False-positive review**, finding dismissal / “is this finding valid?” triage, and **primary** work on policy design, admission configuration, or exception workflows (use a dedicated policy / governance process or skill when available).

**Out of scope:** **Container registry** list/scan-plan flows (`endorctl container registry`, scan plans) as the main workflow—different from Git Project scan troubleshooting. This playbook applies once a **ScanResult** exists (UI **Scan history**, pasted UUID, or app URL). See [Container registry scanning](https://docs.endorlabs.com/scan/containers/container-registry-scan) ([local](../../../.endorlabs-context/docs/scan/containers/container-registry-scan.md)).

## When this applies (scan prerequisites)

- A **persisted ScanResult** must exist (or you have a **ScanResult UUID** / resolvable app URL). History and logs come from **recorded scans**—**`endorctl scan --dry-run` does not store results for monitoring** ([`endorctl scan` — `--dry-run`](https://docs.endorlabs.com/developers-api/cli/commands/scan) · [local](../../../.endorlabs-context/docs/developers-api/cli/commands/scan.md)).
- **`endorctl container scan --dry-run`** fails with **`unknown flag: --dry-run`**. Docs also warn against combining **`--dry-run`** with container scanning on `endorctl scan` ([scan command](https://docs.endorlabs.com/developers-api/cli/commands/scan) · [local](../../../.endorlabs-context/docs/developers-api/cli/commands/scan.md)).

## Known gaps (scan surface)

1. **Registry/image-only flows** — `endorctl container registry` / scan plans vs **Project** scripts below; you still need a **ScanResult UUID** from that world ([container registry scanning](https://docs.endorlabs.com/scan/containers/container-registry-scan)).
2. **Dry-run** — No persisted ScanResult for monitoring ([`--dry-run`](https://docs.endorlabs.com/developers-api/cli/commands/scan)).
3. **Binary/artifact scan** — `endorctl scan --package --path` etc.: [scan command](https://docs.endorlabs.com/developers-api/cli/commands/scan); may produce ScanResults—flags not enumerated here.
4. **`exit_code` variants** — No single catalog of every `ENDORCTL_RC_*`; use **`status`**, **`exit_code`**, and **logs** together.

## What this skill does

Repeatable **scan RCA** with bounded work: resolve which **ScanResult** to inspect, pull a time window of **ScanResults**, triage, then **full ScanLogs**—see **Required ordering**. Optional: regex over embedded log lines in **`search_scan_errors.py`** with explicit scope.

To locate **Project / ScanResult** resources in automation, see [retrieve-scan-results](../retrieve-scan-results/SKILL.md); this file focuses on **troubleshooting scripts** and scan-artifact triage.

### Required ordering

1. **Resolve scope** — [`search_projects.py`](../../../scripts/troubleshooting_scans/search_projects.py): project name, project UUID, ScanResult UUID, **`--endor-app-url`**, or **`--scan-result-url`**. **`search_projects.py`** resolves a ScanResult UUID via **traverse** `get` from the **tenant root** so a wrong namespace in a pasted URL still resolves (`duplicate_project_decision` and match caps apply per script).
2. **Pull ScanResults (time-bounded)** — [`pull_scan_results.py`](../../../scripts/troubleshooting_scans/pull_scan_results.py): default **30 days** on **`meta.create_time`** (`ListParameters.from_date` / `to_date`); `--days` or `--from-date` / `--to-date` override.
3. **Triage ScanResult JSON** — Use **`scan_results_summary`** in the artifact (`environment`, stats, `exit_code`, provisioning, refs). **`spec.logs`** on the ScanResult is a **short preview** only. UI: **Scan history** ([docs](https://docs.endorlabs.com/inventory-insights/scan-history) · [local](../../../.endorlabs-context/docs/inventory-insights/scan-history.md)).
4. **Pull full ScanLogs (required for standard RCA)** — [`pull_scan_logs.py`](../../../scripts/troubleshooting_scans/pull_scan_logs.py): paginated **ScanLogs** for the ScanResult UUID; writes JSON under the filename contract (`--output-dir`, default **`.tmp`**).
5. **Optional** — [`search_scan_errors.py`](../../../scripts/troubleshooting_scans/search_scan_errors.py): regex over **embedded** `spec.logs` lines with explicit scope (`--project-uuid`, `--project-name`, `--from-search-artifact`, or `--all-projects` + caps).

Legacy pairwise scripts in the same folder (`resolve_projects.py`, `fetch_scan_results.py`, …) exist for diffs; prefer the sequence above for new investigations.

### Endor app URLs (routing for scripts)

**`--tenant`** must match the **root tenant namespace** for the scan you are investigating; the app URL path does **not** replace **`--tenant`** (scripts parse the URL only for project UUID vs scan-history routing).

| Pattern | Example path | Effect of `--endor-app-url` |
|--------|----------------|----------------------------|
| **Scan history** | `/t/{namespace}/scan-history/{scan_result_uuid}` | Same as **`--scan-result-url`** — then **`pull_scan_logs`** for that UUID. |
| **Project** (findings, versions, …) | `/t/{namespace}/projects/{project_uuid}/...` | Sets **project UUID** and **namespace** for **`pull_scan_results.py`**; query string ignored. |

Otherwise pass **`--project-uuid`** / **`--scan-result-uuid`** from the UI.

### Operator boundaries

- Broad “all failures in the tenant” questions: **narrow** to project, time window, or ScanResult UUID before pulling full logs.
- Prefer **these scripts + JSON artifacts** over ad hoc **`endorctl`** unless a flag is missing from the script.
- Tie scan failures to **source**: Project repo URL + ScanResult **`spec.versions`** / **refs** (commit).

### Official scan documentation (pointers only)

| Topic | Endor docs |
|-------|------------|
| Scan capabilities | [Scan with Endor Labs](https://docs.endorlabs.com/scan) · [local](../../../.endorlabs-context/docs/scan.md) |
| `endorctl scan`, **`--dry-run`** | [scan command](https://docs.endorlabs.com/developers-api/cli/commands/scan) · [local](../../../.endorlabs-context/docs/developers-api/cli/commands/scan.md) |
| Local `endorctl` first scan | [Scan using endorctl](https://docs.endorlabs.com/setup-deployment/cli/scan-using-endorctl) · [local](../../../.endorlabs-context/docs/setup-deployment/cli/scan-using-endorctl.md) |
| **Scan history** UI | [Scan history](https://docs.endorlabs.com/inventory-insights/scan-history) · [local](../../../.endorlabs-context/docs/inventory-insights/scan-history.md) |
| Container registry scanning | [Container registry scanning](https://docs.endorlabs.com/scan/containers/container-registry-scan) · [local](../../../.endorlabs-context/docs/scan/containers/container-registry-scan.md) |
| Doc index | [llms.txt](https://docs.endorlabs.com/llms.txt) |

## Artifacts

Default output directory: **`.tmp/`** (override with **`--output-dir`**). Filenames follow:

`{rootTenant}__{objectKind}__{objectUuid}__{purpose}[__timestamp].ext`

Scripts emit **JSON**; stderr may warn (e.g. **`--all-projects`** caps).

## Exit condition (done criteria)

This skill is complete only when you produce **both**:

1. **Artifacts** (paths): at minimum, project/scope artifact + windowed ScanResults artifact + full ScanLogs artifact used for the assessment.
2. **Summary assessment** with two explicit parts:
   - **What is wrong** — concrete failure statement(s) with supporting log evidence (quote `message` / `json_payload` snippets or error codes from pulled artifacts).
   - **What can be fixed and how** — actionable remediation steps tied to the error class, citing **Endor docs** first; include external docs only when environment/tool behavior requires it and settings allow external references.

If either artifacts or the two-part summary is missing, troubleshooting is **not done**.

## Local reproduction (next step after triage)

After you know **what failed in the scan** (from **`scan_results_summary`** + **`pull_scan_logs`**), **reproduce in an environment comparable to the scan**:

- Compare **scan-time environment** in the artifact (**`environment.endorctl_version`**, OS/arch, memory, **`environment.config_summary`** / toolchain) with a **local or CI** run using the **same commit** as **`spec.versions` / `refs`**.
- **Dependency / manifest issues** (e.g. invalid **`requirements.txt`** pins, resolution errors in logs): validate **Python (or runtime) version** and **install paths** the **scan worker** uses against what the repo declares; align **scan profile / toolchain / scan flags** so they match a **healthy build** of that commit (what you would run to compile or install deps successfully).
- **Goal:** prove whether the failure is **reproducible outside Endor** with the same constraints, or specific to **scan configuration** vs **upstream project** state.

## ScanResult triage glossary

From **`pull_scan_results`** / **`scan_results_summary`** (see [`scan_result_extended_summary`](../../../scripts/troubleshooting_scans/common.py)). UI: [Scan history](https://docs.endorlabs.com/inventory-insights/scan-history).

| Area | Fields | What to check |
|------|--------|----------------|
| Outcome | `status`, `exit_code` | Partial vs failed; interpret with logs (no exhaustive public list of every `ENDORCTL_RC_*`). |
| Host / runner | `environment.num_cpus`, `environment.memory_bytes`, `environment.os`, `environment.arch` | Drift vs prior scans (smaller runner, wrong pool). |
| Tooling | `environment.endorctl_version`, `environment.tools[]` | **endorctl** / tool version drift between scans. |
| Scan config (shape only) | `environment.config_summary` | High-level **`spec.environment.config`** (languages, flags—no secrets). |
| Duration | `start_time`, `end_time`, `duration_seconds` | Timeouts vs baseline. |
| Stats | `stats` | `call_graph_*`, `scan_success` / `scan_failures`, deps, findings counts, policy counters. |
| Code / ref | `ref`, `sha` | Commit under scan. |
| Languages | `languages_detected` | vs ScanProfile / repo. |
| Provisioning | `provisioning_result_summary` | Toolchain provisioning before analysis. |
| Embedded logs | `log_line_count` | Preview only; use **`pull_scan_logs`** for the full stream. |

## Failure assessment playbook

Use this section when you need full narrative detail beyond the core skill workflow.

### Scenario

- Scan status is `STATUS_PARTIAL_SUCCESS`.
- `scan_failures` is non-zero while policy and finding data may still exist.
- Embedded `spec.logs` show dependency-resolution errors.

### Evidence pattern

From `pull_scan_results` and `pull_scan_logs` artifacts:

1. `scan_results_summary` shows failure signals (for example, dependency failures).
2. `pull_scan_logs` includes concrete error payloads such as:
   - dependency resolution failures (`STATUS_ERROR_DEPENDENCY`)
   - package/index lookup errors (for example, missing package/version)
   - downstream call-graph impact after dependency install failure

### Assessment template

#### What is wrong (cite logs)

- Name the failing class (for example, dependency-resolution failure).
- Quote at least one matching log payload (`message` or `json_payload`) and one summary field.

#### What can be fixed and how (cite docs)

- Recommend concrete remediation mapped to the error class:
  - fix invalid manifests/requirements
  - align runtime/toolchain versions to what scan expects
  - verify registry/index/auth configuration
- Cite Endor docs first:
  - [scan command](https://docs.endorlabs.com/developers-api/cli/commands/scan)
  - [scan history](https://docs.endorlabs.com/inventory-insights/scan-history)
  - [container registry scanning](https://docs.endorlabs.com/scan/containers/container-registry-scan) (if relevant)
- Add external docs only when environment/tool behavior needs it and settings allow.

### Reproduction checklist

1. Reproduce on the same commit (`spec.versions` / refs).
2. Match scan-time environment as closely as possible (runtime/tool versions, OS/arch, scan-relevant config shape).
3. Validate the failing install/build step locally.
4. Re-run scan and confirm artifact deltas:
   - reduced `scan_failures`
   - expected changes in logs for the same component

## Error classes: what to search next

**Heuristic** signals—confirm against repo + full logs. Background: [Scanning strategies](https://docs.endorlabs.com/scan/sca/scanning-strategies) · [local](../../../.endorlabs-context/docs/scan/sca/scanning-strategies.md), [SAST](https://docs.endorlabs.com/scan/sast/run-a-sast-scan) · [local](../../../.endorlabs-context/docs/scan/sast/run-a-sast-scan.md), [Secrets](https://docs.endorlabs.com/scan/secrets/scan-secrets) · [local](../../../.endorlabs-context/docs/scan/secrets/scan-secrets.md).

Mine **`pull_scan_logs`** **`messages[].json_payload`** and the **scanned commit**. Prefer **`resolution_error`** / **`status`** over generic errors.

### Dependency resolution / install (`STATUS_ERROR_DEPENDENCY`, `dependency-scanning-error`, `scan_failures`)

| Ecosystem | Typical signals (logs / metadata) | Search / inspect |
|-----------|-----------------------------------|------------------|
| **PyPI / pip** | Lines in **`requirements*.txt` / `pyproject`** treated as **installable** names; **`python>=…`** is not a PyPI package; private index / yanked / conflicts. | Files + logs: `pypi json api`, `package not found`, `ResolveModuleVersion`, `unable to install`. |
| **npm / yarn / pnpm** | Registry 404, lockfile skew, peer/optional failures. | `package.json`, lockfiles, `.npmrc`; `E404`, `401`, `integrity`. |
| **Go modules** | Proxy/replace/sum/`GOPRIVATE`. | `go.mod`, `go.sum`; log errors. |
| **Maven / Gradle** | Repo URL, credentials, parent POM. | `pom.xml`, `settings.xml`, Gradle files. |
| **NuGet / .NET** | Feed auth, CPM. | `*.csproj`, `nuget.config`. |

### Call graph / reachability (`call-graph-error`, `call_graph_errors` > 0)

| Typical signals (logs / metadata) | Search / inspect |
|-----------------------------------|------------------|
| No IR / missing build inputs. | Pair with dependency failures; `call_graph_attempted` vs `call_graph_available`. |
| Language / feature gap. | `CallgraphLanguages`, log `unsupported`, `parse`. |

### Provisioning / toolchain (`provisioning_result`, `TOOL_CHAINS_*`)

| Typical signals (logs / metadata) | Search / inspect |
|-----------------------------------|------------------|
| Image/tool fetch, OS/arch mismatch. | `provisioning_result_summary`, `docker`, `pull`, `exec format`. |

### Policy / admission (`policy_admission`, triggered policies)

| Typical signals (logs / metadata) | Search / inspect |
|-----------------------------------|------------------|
| Enforcement hit vs scanner defect. **Policy authoring out of scope.** | Policy UUIDs in logs vs UI. |

### Clone / SCM (during scan)

| Typical signals (logs / metadata) | Search / inspect |
|-----------------------------------|------------------|
| App installation, token, archived repo, missing branch. | `spec.git`, clone errors in logs. |

### Timeouts and resource limits

| Typical signals (logs / metadata) | Search / inspect |
|-----------------------------------|------------------|
| Deadline, OOM, starvation. | `duration_seconds`, `environment.memory_bytes`, `timeout`, `OOM`. |

### SAST / custom rules

| Typical signals (logs / metadata) | Search / inspect |
|-----------------------------------|------------------|
| Rule YAML, fetch, timeout. | `semgrep`, `rule`, `yaml` in logs. |

### Secrets scanning

| Typical signals (logs / metadata) | Search / inspect |
|-----------------------------------|------------------|
| Scanner error vs finding counts. | Separate **log failures** from **stats** findings. |

## Scan-focused assumptions (scripts + artifacts)

1. **`pull_scan_results`** filters by **`meta.create_time`** inside the chosen window; “latest” in the JSON is the **newest row** unless you compare runs explicitly.
2. **`--endor-app-url`** routing: only supported **`app.endorlabs.com`** path shapes; query string ignored for routing.
3. **`spec.logs`** on ScanResult ⊂ **full `pull_scan_logs`** output for line-level RCA.
4. **`STATUS_PARTIAL_SUCCESS`** can mix **scanner errors**, **policy triggers**, and **findings**—use stats + log class separately.

## Fast path examples

Use credentials that can read the tenant’s ScanResults/ScanLogs (e.g. `uv run --env-file .env` per repo convention). Replace **`YOUR_ROOT`**, UUIDs, and paths.

```bash
uv run --env-file .env python scripts/troubleshooting_scans/search_projects.py \
  --tenant YOUR_ROOT \
  --endor-app-url "https://app.endorlabs.com/t/ns.child/scan-history/SCAN_RESULT_UUID" \
  --output-dir .tmp --timestamped
```

```bash
uv run --env-file .env python scripts/troubleshooting_scans/search_projects.py \
  --tenant YOUR_ROOT \
  --endor-app-url "https://app.endorlabs.com/t/ns.child/projects/PROJECT_UUID/versions/default/findings" \
  --output-dir .tmp --timestamped
```

```bash
uv run --env-file .env python scripts/troubleshooting_scans/search_projects.py \
  --tenant YOUR_ROOT \
  --scan-result-url "https://app.endorlabs.com/t/ns.child/scan-history/SCAN_RESULT_UUID" \
  --output-dir .tmp --timestamped
```

```bash
uv run --env-file .env python scripts/troubleshooting_scans/pull_scan_results.py \
  --tenant YOUR_ROOT \
  --project-uuid PROJECT_UUID \
  --namespace project.namespace.if.needed \
  --days 30 \
  --output-dir .tmp --timestamped
```

```bash
uv run --env-file .env python scripts/troubleshooting_scans/pull_scan_logs.py \
  --tenant YOUR_ROOT \
  --scan-result-uuid SCAN_RESULT_UUID \
  --output-dir .tmp --timestamped
```

```bash
uv run --env-file .env python scripts/troubleshooting_scans/search_scan_errors.py \
  --tenant YOUR_ROOT \
  --from-search-artifact path/to/project_search__....json \
  --error-pattern "dependency-scanning-error|call-graph-error" \
  --output-dir .tmp
```

## Interpretation hints

- **`scan_success` → 0** with **`dependency_count_total` collapsed** often points to dependency resolution.
- Triage **`endorctl_version`** and dependency stats, then **`pull_scan_logs`** for detail.
- **`search_scan_errors.py`** after scope is fixed.
