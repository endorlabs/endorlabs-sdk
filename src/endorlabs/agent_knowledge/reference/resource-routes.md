# Resource route map (generated)

Generated **relationship accessor** edges between first-class facades. Regenerate with `uv run python devtools/generate_route_contract.py`.

Manual edges: `devtools/model_sync_profiles/route_contract_overlay.yaml`.
Partition edges: `devtools/model_sync_profiles/route_partition_targets.yaml`.

## Relationship table

| From | To | Public method | Edge id | Wire kind | Tier |
|------|-----|---------------|---------|-----------|------|
| Project | Finding | `Finding.list_by_project` | `project.findings` | `list_by_uuid_field` | B |
| Project | ScanResult | `ScanResult.list_by_project` | `project.scan_results` | `list_by_parent` | B |
| Project | PackageVersion | `PackageVersion.list_by_project` | `project.package_versions` | `list_by_uuid_field` | B |
| Finding | DependencyMetadata | `Finding.to_dependency_metadata` | `finding.dependency_metadata.get` | `get_by_uuid` | A |
| Finding | DependencyMetadata | `Finding.to_dependency_metadata` | `finding.dependency_metadata.by_package` | `list_by_attribute` | C |
| ScanResult | Finding | `Finding.list_for_context` | `scan.findings` | `list_by_context_partition` | B |
| ScanResult | PackageVersion | `PackageVersion.list_for_context` | `scan.package_versions` | `list_by_context_partition` | B |
| ScanResult | DependencyMetadata | `DependencyMetadata.list_for_context` | `scan.dependency_metadata` | `list_by_context_partition` | B |
| ScanResult | RepositoryVersion | `RepositoryVersion.list_for_context` | `scan.repository_versions` | `list_by_context_partition` | B |
| ScanResult | FindingLog | `FindingLog.list_for_context` | `scan.finding_logs` | `list_by_context_partition` | B |
| ScanResult | LinterResult | `LinterResult.list_for_context` | `scan.linter_results` | `list_by_context_partition` | B |
| ScanResult | Metric | `Metric.list_for_context` | `scan.metrics` | `list_by_context_partition` | B |
| ScanResult | PackageLicense | `PackageLicense.list_for_context` | `scan.package_licenses` | `list_by_context_partition` | B |
| ScanResult | ScanWorkflowResult | `ScanWorkflowResult.list_for_context` | `scan.scan_workflow_results` | `list_by_context_partition` | B |
| ScanResult | VersionUpgrade | `VersionUpgrade.list_for_context` | `scan.version_upgrades` | `list_by_context_partition` | B |

## Usage

Generated list accessors (`list_by_project`, `list_for_context`, …) return `list[T]` like `.list()`. Stitch accessors (`to_dependency_metadata`, …) return `RouteResult` — use `.value` / `.single` and inspect `.edge_used` / `.warnings`. Namespace is taken from the source resource unless `namespace=` is passed.

```python
projects = client.Project.search_by_name('my-repo', namespace=ns, max_pages=2)
project = projects[0] if projects else None
findings = client.Finding.list_by_project(project, max_pages=1)
scans = client.ScanResult.list_by_project(
    project, max_pages=1, sort_by='meta.create_time', desc=True)
if scans:
    by_context = client.Finding.list_for_context(scans[0], max_pages=1)
dm = client.Finding.to_dependency_metadata(finding_row)
```

See [facade-helpers.md](../guides/facade-helpers.md) and [contracts.md](../contracts.md#generated-accessor-helpers).
