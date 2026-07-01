---
name: endor-retrieve-scan-results
description: 'Project-scoped SDK workflow: resolve Project → latest ScanResult → Finding
  rows for one repo. Use when the user wants scan results, findings, or reports for
  a specific project. Default to namespace=project.namespace without traverse on findings;
  use traverse only to discover Project when namespace is unknown, or when the user
  explicitly requests tenant-wide reports.'
---

# Retrieving Scan Results and Findings

**Default path:** one **Project** → **`ScanResult.list_by_project(project)`** → **`Finding.list_by_project(project)`** / **`Finding.list_for_context(scan)`** — no `traverse=True` on findings after the project is resolved.

For **scan pipeline** regressions (bounded scan window, heuristic pair scoring, scan logs via `ScanResult.get_logs`, aggregate diffs), use [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) first, then return here with scan UUIDs for finding-level drill-down.

Human-oriented reference: [docs/guides/retrieving-scan-results.md](../../../docs/guides/retrieving-scan-results.md). General **`traverse`** mechanics: [docs/contributing/namespace-traversal.md](../../../docs/contributing/namespace-traversal.md).

## Concepts

| Resource | What it is | Key fields |
|----------|-----------|------------|
| **Project** | A monitored repository | `meta.name` = repo URL, `uuid` |
| **ScanResult** | One scan's metadata, stats, policies triggered | `meta.parent_uuid` = Project UUID, `spec.findings` = Finding UUIDs |
| **Finding** | A security finding | `context.type`, `context.id`, `spec.project_uuid`, `spec.level` |

**Relationship chain:** Project (by repo URL) → ScanResult (by parent UUID) → Finding rows in the **same scan plane** (`context.type` + `context.id`) or via `spec.findings` UUID list + `get`.

## Workflow (project-scoped)

### Step 1: Find the Project

Prefer **namespace + filter** when the user names a child namespace; use **`traverse=True` only when the namespace is unknown** (discovery), with **`max_pages`** to bound cost.

```python
import endorlabs
from endorlabs import F

# Discovery — bounded list; caller picks row or disambiguates
projects = client.Project.search_by_name(
    "github.com/org/repo",
    traverse=True,
    max_pages=2,
)

# Optional server-side pre-filter before fuzzy match
projects = client.Project.search_by_name(
    "repo",
    namespace="<child-or-leaf-namespace>",
    filter=F("meta.tags").contains("production"),
    max_pages=2,
)

project = projects[0] if projects else None
```

> **Agent note — duplicate projects:** The same repository URL may exist as **several** `Project` rows (different `tenant_meta.namespace`). `search_by_name` returns **all matches within limits** — pick the row for the intended namespace, narrow `namespace=`, or use **project UUID** with `get()`. See [resource-discovery contract](../../contracts/resource-discovery.md).

### Step 2: Get the Most Recent ScanResult

```python
scan_result = client.ScanResult.list_by_project(project, limit=1)
latest_scan = scan_result[0] if scan_result else None
```

Or pass explicit list kwargs (date window, `max_pages`, `list_params`) without the workflow preset defaults.

### Step 3: Get Findings (no traverse)

Use **generated accessor helpers** — they derive namespace from the source resource. Do **not** add `traverse=True`.

```python
# All findings for the project (preferred)
findings = client.Finding.list_by_project(project, max_pages=5)

# One scan plane's findings (preferred when you have a ScanResult row)
findings = client.Finding.list_for_context(latest_scan, max_pages=5)

# Severity filter — merge with accessor list kwargs
findings = client.Finding.list_by_project(
    project,
    filter='spec.level==FINDING_LEVEL_CRITICAL',
    max_pages=5,
)
```

**Tenant-wide findings** — only when the user **explicitly** asks for all namespaces / estate-wide reports. Add selective **`filter`**, **`max_pages`**, and prefer **`count=True`** for totals before full pagination:

```python
# Explicit user request only — not the default for one repo
critical = client.Finding.list(
    filter="spec.level==FINDING_LEVEL_CRITICAL",
    traverse=True,
    max_pages=5,
)
```

### Step 4: Narrow with field masks

Use `mask` to limit response fields. With a **non-empty** mask, each row is a **`dict[str, Any]`** (wire JSON), not a model — use key access or **omit `mask`** when you need Pydantic models for `delete` / `update`.

```python
findings = client.Finding.list(
    filter=f'spec.project_uuid=="{project.uuid}"',
    namespace=project.namespace,
    mask="meta.name,spec.level,spec.finding_categories",
)
```

**Note:** `filter` (which rows) and `mask` (which fields) are separate concepts.

## When to use traverse

| Scenario | Traverse? |
|----------|-----------|
| **Findings / ScanResults for a resolved project** | **No** — use `namespace=project.namespace` or `parent=project` |
| **Discover Project** when namespace unknown | **Yes** — `Project.search_by_name(query, traverse=True, max_pages=…)` |
| **User explicitly requests tenant-wide report** | **Yes** — selective `filter`, cap `max_pages` |
| **update / delete on a resource** | **No** — pass the resource object or correct namespace |

After `list(traverse=True)`, pass the **resource object** to `get` / `update` / `delete` (unless the list used `mask=` → dict rows). See [namespace-traversal.md](../../../docs/contributing/namespace-traversal.md#namespace-scoping-after-traverse).

## Per-Branch Finding Deduplication

Findings are generated **per RepositoryVersion** (branch). Two scanned branches → **2× finding objects** for the same code-level issue.

| Field | Purpose |
|-------|---------|
| `spec.source_code_version.ref` | Branch the finding came from |
| `context.type` / `context.id` | Scan plane (MAIN, CI_RUN, REF, …) |

> **Agent note — `ref` shape:** `spec.source_code_version.ref` may be a **short branch name** (`main`) rather than `refs/heads/main`. Branch filters that assume full ref strings can return **zero rows**. List findings **without** a branch filter first, or use `RepositoryVersion.list` for scanned refs. See [AGENTS.md](../../../AGENTS.md#agent-notes).

```python
main_findings = client.Finding.list(
    filter=(
        (F("spec.project_uuid") == project.uuid)
        & F("spec.source_code_version.ref").matches("main")
    ),
    namespace=project.namespace,
)

repo_versions = client.RepositoryVersion.list(
    filter=f'spec.project_uuid=="{project.uuid}"',
    namespace=project.namespace,
)
```

When counting severity or unique issues, dedupe by explanation/remediation or filter to one branch — do not sum raw row counts across branches blindly.

## Quick reference

| Operation | Example |
|-----------|---------|
| Latest scan for a project | `ScanResult.list_by_project(project, limit=1)[0]` |
| Findings for a project | `Finding.list_by_project(project, max_pages=…)` |
| Findings for one scan plane | `Finding.list_for_context(scan, max_pages=…)` |
| Discover project by URL | `Project.search_by_name("github.com/org/repo", traverse=True, max_pages=2)` |
| Tenant-wide critical (explicit ask) | `Finding.list(filter='spec.level==FINDING_LEVEL_CRITICAL', traverse=True, max_pages=5)` |

## Related skills

| Need | Skill |
| ---- | ----- |
| CLI vs Cloud (agentless SCM) project classification | [endor-cli-vs-cloud-projects](../endor-cli-vs-cloud-projects/SKILL.md) |
| Scan failed, metrics spiked, logs between runs | [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) |
| Policy / exception matches a finding | [endor-validate-policy](../endor-validate-policy/SKILL.md) |
| Reachability conflicts on a finding | [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md) |
| Tenant-wide PRF approximation + PV resolution errors | [endor-potentially-reachable-analysis](../endor-potentially-reachable-analysis/SKILL.md) |
| New vs resolved FindingLog trend charts | [endor-chart-new-vs-resolved-findings](../endor-chart-new-vs-resolved-findings/SKILL.md) |
| Fixed vs present, SBOM vs API | [endor-dependency-finding-provenance](../endor-dependency-finding-provenance/SKILL.md) |
| Package paths/versions across manifests | [endor-dependency-provenance](../endor-dependency-provenance/SKILL.md) |
