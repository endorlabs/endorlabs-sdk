# Resource route map (generated)

Contract-driven **CRUD+** edges between first-class facades. Regenerate with `uv run python devtools/generate_route_contract.py`.

Source overlay: `devtools/model_sync_profiles/route_contract_overlay.yaml`.

## Relationship table

| From | To | Public method | Edge id | Wire kind | Tier |
|------|-----|---------------|---------|-----------|------|
| Project | Finding | `Finding.list_by_project` | `project.findings` | `list_by_uuid_field` | B |
| Project | ScanResult | `ScanResult.list_by_project` | `project.scan_results` | `list_by_parent` | B |
| ScanResult | Finding | `Finding.list_by_scan` | `scan.findings` | `list_by_index_field` | B |
| Finding | DependencyMetadata | `Finding.to_dependency_metadata` | `finding.dependency_metadata.get` | `get_by_uuid` | A |
| Finding | DependencyMetadata | `Finding.to_dependency_metadata` | `finding.dependency_metadata.by_package` | `list_by_attribute` | C |
| Finding | SemgrepRule | `Finding.to_semgrep_rule` | `finding.semgrep_rule.by_linter` | `via_intermediate` | C |

## Usage

Route methods return `RouteResult` with `.values` (list routes) or `.value` (GET/stitch). Namespace is taken from the source resource unless `namespace=` is passed.

```python
project = client.Project.lookup(name='my-repo', namespace=ns)
findings = client.Finding.list_by_project(project, max_pages=1)
scans = client.ScanResult.list_by_project(project, max_pages=1)
if scans.values:
    by_scan = client.Finding.list_by_scan(scans.values[0], max_pages=1)
dm = client.Finding.to_dependency_metadata(finding_row)
```

See [facade-helpers.md](../guides/facade-helpers.md) and [contracts.md](../contracts.md#resource-routes-crud).
