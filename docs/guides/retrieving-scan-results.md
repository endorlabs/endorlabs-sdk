# Retrieving ScanResult and Findings

Agent skill (on-demand): [endor-retrieve-scan-results](../../agent-knowledge/skills/endor-retrieve-scan-results/SKILL.md). General **`traverse`** patterns: [namespace-traversal.md](../contributing/namespace-traversal.md). List performance: [list-query-performance.md](../contributing/list-query-performance.md).

## Concepts

- **ScanResult**: Scan metadata, environment, runtime stats, policies triggered; `spec.findings` holds Finding UUIDs.
- **Finding**: Security findings; linked by `context.type` / `context.id` (scan plane) and `spec.project_uuid`.
- **Relationship**: Project (`meta.name` = repo URL) → ScanResult (`meta.parent_uuid` = Project UUID) → Finding rows (via `list_for_context(scan)`, `list_by_project`, or `spec.findings` UUIDs + `get`).

## Default workflow (one project)

1. **Resolve Project** — `client.Project.search_by_name(query, …)` or `Project.get(uuid)` when UUID is known.
2. **Scan results** — `client.ScanResult.list_by_project(project, max_pages=1, sort_by="meta.create_time", desc=True)` or `ScanResult.list(parent=project, sort_by="meta.create_time", desc=True, max_pages=1)`.
3. **Findings** — `client.Finding.list_by_project(project, max_pages=…)` or `Finding.list_for_context(scan, max_pages=…)`. **Do not** use `traverse=True` here — wrong namespace causes empty rows, not errors ([contracts.md](../contracts.md) — project-scoped lists).

Generated list accessors return **`list[T]`** like `.list()`. Stitch accessors (`to_dependency_metadata`) return **`RouteResult`**. See [facade-helpers.md](facade-helpers.md) and [resource-routes.md](../generated-reference/resource-routes.md).

```python
projects = client.Project.search_by_name(repo_url, namespace=ns, max_pages=2)
project = projects[0] if projects else None
findings = client.Finding.list_by_project(project, max_pages=1)
scans = client.ScanResult.list_by_project(
    project, max_pages=1, sort_by="meta.create_time", desc=True
)
if scans:
    scan_findings = client.Finding.list_for_context(scans[0], max_pages=1)
```

Use **field-mask** (`mask=` / `--field-mask`) for smaller responses; with a **non-empty** mask, `list()` returns **dict** rows, not full resource models.

## When to use traverse

| Goal | Traverse? |
|------|-----------|
| Findings or scans for a **resolved project** | **No** — `namespace=project.namespace` or `parent=project` |
| **Discover** Project when namespace unknown | **Yes** — bounded `Project.search_by_name(query, traverse=True, max_pages=…)` (or exact `Project.list(filter='meta.name=="…"', traverse=True, max_pages=1)` when URL is known) |
| **Tenant-wide** finding/report (user explicitly asked) | **Yes** — selective `filter`, cap `max_pages`; see [namespace-traversal.md](../contributing/namespace-traversal.md) |

Do not run unbounded tenant-wide `Finding.list(traverse=True)` during routine single-repo triage.

## Branch multiplicity

Findings are per **RepositoryVersion** (branch). The same issue may appear once per scanned branch. `spec.source_code_version.ref` may be a short name (`main`) or a full ref — verify with `RepositoryVersion.list` or list findings without a branch filter before narrowing.

## Resources

- SDK: `client.Project`, `client.ScanResult`, `client.Finding`
- [contracts.md](../contracts.md) — traverse, mask, project-scoped namespace
- [reference/resources.md](../reference/resources.md)

Runnable patterns: `tests/`; product docs via Docs MCP when configured.
