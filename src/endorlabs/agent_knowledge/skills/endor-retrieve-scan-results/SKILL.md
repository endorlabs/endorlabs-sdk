---
name: endor-retrieve-scan-results
description: 'Project-scoped SDK workflow: resolve Project → latest ScanResult → Finding
  rows for one repo. Use when the user wants scan results, findings, or reports for
  a specific project. Default to namespace=project.namespace without traverse on findings;
  use traverse only to discover Project when namespace is unknown, or when the user
  explicitly requests tenant-wide reports.'
---

# Retrieving Scan Results and Findings

**Default path:** one **Project** → **`ScanResult.list(parent=project)`** → **`Finding.list(..., namespace=project.namespace)`** — no `traverse=True` on findings after the project is resolved.

For **scan pipeline** regressions (bounded scan window, heuristic pair scoring, ScanLogs, aggregate diffs), use [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) first, then return here with scan UUIDs for finding-level drill-down.

Human-oriented reference: [docs/guides/retrieving-scan-results.md](../../../docs/guides/retrieving-scan-results.md). General **`traverse`** mechanics: [docs/contributing/namespace-traversal.md](../../../docs/contributing/namespace-traversal.md).

## Concepts

| Resource | What it is | Key fields |
|----------|-----------|------------|
| **Project** | A monitored repository | `meta.name` = repo URL, `uuid` |
| **ScanResult** | One scan's metadata, stats, policies triggered | `meta.parent_uuid` = Project UUID, `spec.findings` = Finding UUIDs |
| **Finding** | A security finding | `context.scan_uuid`, `spec.project_uuid`, `spec.level` |

**Relationship chain:** Project (by repo URL) → ScanResult (by parent UUID) → Finding (by scan or project UUID).

## Workflow (project-scoped)

### Step 1: Find the Project

Prefer **namespace + filter** when the user names a child namespace; use **`traverse=True` only when the namespace is unknown** (discovery), with **`max_pages`** to bound cost.

```python
# Discovery: namespace unknown — bounded traverse on Project only
projects = client.Project.list(
    filter='meta.name=="https://github.com/org/repo.git"',
    traverse=True,
    max_pages=1,
)
project = projects[0] if projects else None

# When namespace is known — no traverse
projects = client.Project.list(
    filter='meta.name=="https://github.com/org/repo.git"',
    namespace="<child-or-leaf-namespace>",
    max_pages=1,
)
```

```python
# Single unambiguous row only
project = client.Project.lookup(name="https://github.com/org/repo.git")
```

> **Agent note — duplicate projects:** The same repository URL may exist as **several** `Project` rows (different `tenant_meta.namespace`). `lookup` then raises **`AmbiguousError`**. Prefer `Project.list` with `meta.name` filter and `traverse=True` (bounded), then pick the row for the intended namespace, or use **project UUID** (+ optional namespace). See [AGENTS.md](../../../AGENTS.md#agent-notes).

### Step 2: Get the Most Recent ScanResult

```python
scan_results = client.ScanResult.list(
    parent=project,  # namespace + meta.parent_uuid filter
    sort_by="meta.create_time",
    desc=True,
    max_pages=1,
)
latest_scan = scan_results[0] if scan_results else None
```

### Step 3: Get Findings (no traverse)

After **`project`** is resolved, pass **`namespace=project.namespace`** (or `latest_scan.namespace`). Do **not** add `traverse=True` — it widens scope and cost without fixing empty rows from wrong namespace.

```python
# All findings for the project (preferred)
findings = client.Finding.list(
    filter=f'spec.project_uuid=="{project.uuid}"',
    namespace=project.namespace,
)

# One scan's findings
findings = client.Finding.list(
    filter=f'context.scan_uuid=="{latest_scan.uuid}"',
    namespace=latest_scan.namespace,
)

# Severity filter — still project-scoped
findings = client.Finding.list(
    filter=(
        f'spec.project_uuid=="{project.uuid}" '
        '& spec.level==FINDING_LEVEL_CRITICAL'
    ),
    namespace=project.namespace,
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
| **Discover Project** when namespace unknown | **Yes** — `Project.list(..., traverse=True, max_pages=…)` |
| **User explicitly requests tenant-wide report** | **Yes** — selective `filter`, cap `max_pages` |
| **update / delete on a resource** | **No** — pass the resource object or correct namespace |

After `list(traverse=True)`, pass the **resource object** to `get` / `update` / `delete` (unless the list used `mask=` → dict rows). See [namespace-traversal.md](../../../docs/contributing/namespace-traversal.md#namespace-scoping-after-traverse).

## Per-Branch Finding Deduplication

Findings are generated **per RepositoryVersion** (branch). Two scanned branches → **2× finding objects** for the same code-level issue.

| Field | Purpose |
|-------|---------|
| `spec.source_code_version.ref` | Branch the finding came from |
| `context.scan_uuid` | UUID of the scan run |

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
| Latest scan for a project | `ScanResult.list(parent=project, sort_by="meta.create_time", desc=True, max_pages=1)` |
| Findings for a project | `Finding.list(filter=f'spec.project_uuid=="{project.uuid}"', namespace=project.namespace)` |
| Findings for one scan | `Finding.list(filter=f'context.scan_uuid=="{scan.uuid}"', namespace=scan.namespace)` |
| Discover project by URL | `Project.list(filter='meta.name=="…"', traverse=True, max_pages=1)` |
| Tenant-wide critical (explicit ask) | `Finding.list(filter='spec.level==FINDING_LEVEL_CRITICAL', traverse=True, max_pages=5)` |

## Related skills

| Need | Skill |
| ---- | ----- |
| Scan failed, metrics spiked, logs between runs | [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) |
| Policy / exception matches a finding | [endor-validate-policy](../endor-validate-policy/SKILL.md) |
| Reachability conflicts on a finding | [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md) |
| Fixed vs present, SBOM vs API | [endor-dependency-finding-provenance](../endor-dependency-finding-provenance/SKILL.md) |
| Package paths/versions across manifests | [endor-dependency-provenance](../endor-dependency-provenance/SKILL.md) |
