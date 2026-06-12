# Retrieving ScanResult and Findings

Agent skill (on-demand): [endor-retrieve-scan-results](../../agent-knowledge/skills/endor-retrieve-scan-results/SKILL.md). General **`traverse`** patterns: [namespace-traversal.md](../contributing/namespace-traversal.md). List performance: [list-query-performance.md](../contributing/list-query-performance.md).

## Concepts

- **ScanResult**: Scan metadata, environment, runtime stats, policies triggered; `spec.findings` holds Finding UUIDs.
- **Finding**: Security findings; linked by `context.scan_uuid` and `spec.project_uuid`.
- **Relationship**: Project (`meta.name` = repo URL) → ScanResult (`meta.parent_uuid` = Project UUID) → Finding rows (via `spec.findings` UUIDs or `Finding.list` filters).

## Default workflow (one project)

1. **Resolve Project** — `client.Project.resolve(name_or_uuid)` or `Project.lookup(name=…, namespace=…)`.
2. **Scan results** — `client.ScanResult.list_by_project(project, max_pages=1)` or `ScanResult.list(parent=project, sort_by="meta.create_time", desc=True, max_pages=1)`.
3. **Findings** — `client.Finding.list_by_project(project, max_pages=…)` or `Finding.list_by_scan(scan, max_pages=…)`. **Do not** use `traverse=True` here — wrong namespace causes empty rows, not errors ([contracts.md](../contracts.md) — project-scoped lists).

Route methods return `RouteResult`; use `.values` for rows. See [facade-helpers.md](facade-helpers.md) and [resource-routes.md](../generated-reference/resource-routes.md).

```python
project = client.Project.lookup(name=repo_url, namespace=ns)
findings = client.Finding.list_by_project(project, max_pages=1)
scans = client.ScanResult.list_by_project(project, max_pages=1)
if scans.values:
    scan_findings = client.Finding.list_by_scan(scans.values[0], max_pages=1)
```

Use **field-mask** (`mask=` / `--field-mask`) for smaller responses; with a **non-empty** mask, `list()` returns **dict** rows, not full resource models.

## When to use traverse

| Goal | Traverse? |
|------|-----------|
| Findings or scans for a **resolved project** | **No** — `namespace=project.namespace` or `parent=project` |
| **Discover** Project when namespace unknown | **Yes** — bounded `Project.list(..., traverse=True, max_pages=…)` |
| **Tenant-wide** finding/report (user explicitly asked) | **Yes** — selective `filter`, cap `max_pages`; see [namespace-traversal.md](../contributing/namespace-traversal.md) |

Do not run unbounded tenant-wide `Finding.list(traverse=True)` during routine single-repo triage.

## Branch multiplicity

Findings are per **RepositoryVersion** (branch). The same issue may appear once per scanned branch. `spec.source_code_version.ref` may be a short name (`main`) or a full ref — verify with `RepositoryVersion.list` or list findings without a branch filter before narrowing.

## Resources

- SDK: `client.Project`, `client.ScanResult`, `client.Finding`
- [contracts.md](../contracts.md) — traverse, mask, project-scoped namespace
- [reference/resources.md](../reference/resources.md)

Runnable patterns: `tests/`; platform docs under `.endorlabs-context/platform/user-docs/` when materialized.
