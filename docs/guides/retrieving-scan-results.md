# Retrieving ScanResult and Findings

Agent skill (on-demand): [endor-retrieve-scan-results](../../agent-knowledge/skills/endor-retrieve-scan-results/SKILL.md). General **`traverse`** patterns: [namespace-traversal.md](../contributing/namespace-traversal.md). List performance: [list-query-performance.md](../contributing/list-query-performance.md).

## Concepts

- **ScanResult**: Scan metadata, environment, runtime stats, policies triggered; `spec.findings` holds Finding UUIDs.
- **Finding**: Security findings; linked by `context.scan_uuid` and `spec.project_uuid`.
- **Relationship**: Project (`meta.name` = repo URL) → ScanResult (`meta.parent_uuid` = Project UUID) → Finding rows (via `spec.findings` UUIDs or `Finding.list` filters).

## Default workflow (one project)

1. **Resolve Project** — filter on `meta.name` (repo URL). If namespace is known, pass **`namespace=`**; if unknown, **`Project.list(..., traverse=True, max_pages=1)`** for discovery only.
2. **Latest ScanResult** — `ScanResult.list(parent=project, sort_by="meta.create_time", desc=True, max_pages=1)`.
3. **Findings** — `Finding.list(filter=f'spec.project_uuid=="{project.uuid}"', namespace=project.namespace)` or filter by `context.scan_uuid`. **Do not** use `traverse=True` here — wrong namespace causes empty rows, not errors ([contracts.md](../contracts.md) — project-scoped lists).

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
