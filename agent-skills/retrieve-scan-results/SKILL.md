---
name: retrieve-scan-results
description: >-
  Query projects, scan results, and findings from the Endor Labs platform
  using the SDK. Use when the user wants to retrieve scan results, list
  findings, look up a project by repository URL, or build reports from
  scan data. Covers namespace traversal for tenant-wide queries.
---

# Retrieving Scan Results and Findings

Workflow for navigating the Project -> ScanResult -> Finding hierarchy in the
Endor Labs SDK.

## Concepts

| Resource | What it is | Key fields |
|----------|-----------|------------|
| **Project** | A monitored repository | `meta.name` = repo URL, `uuid` |
| **ScanResult** | One scan's metadata, stats, policies triggered | `meta.parent_uuid` = Project UUID, `spec.findings` = Finding UUIDs |
| **Finding** | A security finding | `context.scan_uuid`, `spec.project_uuid`, `spec.level` |

**Relationship chain:** Project (by repo URL) -> ScanResult (by parent UUID) -> Finding (by scan or project UUID).

## Workflow

### Step 1: Find the Project

```python
# By repository URL
projects = client.Project.list(
    filter='meta.name=="https://github.com/org/repo.git"',
    traverse=True,
    max_pages=1,
)
project = projects[0] if projects else None

# Or use lookup for a single match
project = client.Project.lookup(name="https://github.com/org/repo.git")
```

Use `traverse=True` when the namespace is unknown or you need to search across all child namespaces.

> **Agent note — duplicate projects:** The same repository URL may exist as **several** `Project` rows (different `tenant_meta.namespace`). `lookup` then raises **`AmbiguousError`**. Prefer `Project.list` with a filter on `meta.name` and `traverse=True`, then choose the row for the intended namespace, or call `get` / workflows with **project UUID** (and optional namespace). Universal summary: [AGENTS.md](../../AGENTS.md) (Agent notes: projects, findings, and workflows).

### Step 2: Get the Most Recent ScanResult

```python
# List scan results for the project, sorted by creation time
scan_results = client.ScanResult.list(
    parent=project,                        # Derives namespace + parent_uuid filter
    sort_by="meta.create_time",
    desc=True,
    max_pages=1,
)
latest_scan = scan_results[0] if scan_results else None
```

The `parent=project` argument automatically scopes the query to the project's namespace and filters by `meta.parent_uuid`.

### Step 3: Get Findings

```python
# All findings for the project
findings = client.Finding.list(
    filter=f'spec.project_uuid=="{project.uuid}"',
    namespace=project.namespace,
    traverse=True,
)

# Or findings from a specific scan
findings = client.Finding.list(
    filter=f'context.scan_uuid=="{latest_scan.uuid}"',
    namespace=latest_scan.namespace,
)

# Critical findings only
findings = client.Finding.list(
    filter='spec.level==FINDING_LEVEL_CRITICAL',
    traverse=True,
)
```

### Step 4: Narrow with field masks

Use `mask` to limit response fields for performance. With a **non-empty** mask,
each row is a **`dict[str, Any]`** (wire JSON), not a `Finding` / `Project`
model—use key access (e.g. `row["spec"]["level"]` after checking keys) or
**omit `mask`** when you need Pydantic models (e.g. to pass a resource object
to `delete` / `update`).

```python
# Only get finding name and severity (rows are dicts)
findings = client.Finding.list(
    filter='spec.level==FINDING_LEVEL_CRITICAL',
    mask="meta.name,spec.level,spec.finding_categories",
    traverse=True,
)
for row in findings[:5]:
    spec = row.get("spec") or {}
    level = spec.get("level") if isinstance(spec, dict) else None
    print(level, row.get("meta", {}))
```

**Note:** `filter` (which rows) and `mask` (which fields) are separate concepts. Do not combine them.

## When to Use Traverse

| Scenario | Use traverse? |
|----------|--------------|
| Querying resources across the entire tenant | Yes |
| Building tenant-wide reports or analytics | Yes |
| Resource namespace is unknown | Yes |
| Only need resources from one specific namespace | No |
| Namespace-scoped operations (update, delete) | No |

## Namespace Scoping After Traverse

When acting on resources returned from `list(traverse=True)` **without** a
non-empty field `mask`, pass the **resource object** (not just a UUID string) to
`get`, `update`, or `delete`. If you used `mask=` on that list, rows are
**dicts**—call `get(uuid, namespace=...)` or list again without `mask` before
using model-only APIs.

```python
# Correct: namespace derived from resource object
client.Project.delete(target)

# Risky: may 404 if target is in a child namespace
client.Project.delete(target.uuid, namespace="tenant-root")
```

For full traversal patterns, performance comparison, and filtering examples, see [TRAVERSAL_PATTERNS.md](TRAVERSAL_PATTERNS.md).

## Per-Branch Finding Deduplication

Findings are generated **per RepositoryVersion** (branch). A project with 2 scanned branches (e.g. `main` and `feature-x`) produces **2x finding objects** for the same code-level issue — one per branch scan.

**Key fields for distinguishing branches:**

| Field | Purpose |
|-------|---------|
| `spec.source_code_version.ref` | Branch name the finding came from (e.g. `refs/heads/main`) |
| `context.scan_uuid` | UUID of the specific scan run |

> **Agent note — `ref` shape:** In practice `spec.source_code_version.ref` may be a **short branch name** (e.g. `main`, `dev-tgowan`) rather than the full `refs/heads/...` string. Filters that assume only `refs/heads/main` can return **zero rows** while findings exist on another ref. Prefer `RepositoryVersion.list` for the project to see scanned refs, or list findings **without** a branch filter first, then narrow. See [AGENTS.md](../../AGENTS.md) (Agent notes).

**Deduplication strategies:**

```python
# Strategy 1: Filter to a single branch
main_findings = client.Finding.list(
    filter=(
        (F("spec.project_uuid") == project.uuid)
        & F("spec.source_code_version.ref").matches("refs/heads/main")
    ),
    namespace=project.namespace,
)

# Strategy 2: Group by explanation text to identify unique issues
from collections import defaultdict
by_explanation = defaultdict(list)
for f in findings:
    key = (
        getattr(f.spec, "explanation", "") or "",
        getattr(f.spec, "remediation", "") or "",
    )
    by_explanation[key].append(f)
# Each group represents one unique code issue (may have N branch variants)

# Strategy 3: Use RepositoryVersion to understand branch coverage
repo_versions = client.RepositoryVersion.list(
    filter=f'spec.project_uuid=="{project.uuid}"',
    namespace=project.namespace,
)
# Each RepositoryVersion = one scanned branch
```

**When reviewing findings programmatically**, always account for branch multiplicity to avoid double-counting severity totals or issue counts.

## Quick Reference

| Operation | Example |
|-----------|---------|
| List all projects | `client.Project.list(traverse=True)` |
| Find project by URL | `client.Project.lookup(name="https://github.com/org/repo.git")` |
| Latest scan for a project | `client.ScanResult.list(parent=project, sort_by="meta.create_time", desc=True, max_pages=1)` |
| Findings for a project | `client.Finding.list(filter=f'spec.project_uuid=="{project.uuid}"', namespace=project.namespace)` |
| Critical findings, all namespaces | `client.Finding.list(filter='spec.level==FINDING_LEVEL_CRITICAL', traverse=True)` |
| Count findings | `client.Finding.list(filter='...', count=True, traverse=True)` |
