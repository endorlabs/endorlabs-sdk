# Facade list helpers

Normative catalog for SDK facade helpers. Wire logic lives in `operations/`; workflows orchestrate only.

## Layer placement

| Layer | Owns |
|-------|------|
| `facade/` | Public helpers on resource facades + `CallGraphData` custom facade |
| `operations/routes.py` | Contract-driven CRUD+ executors (`RouteExecutor`, `RouteResult`) |
| `operations/` | Pagination, group wire parsing |
| `resources/call_graph_data.py` | CallGraphData fetch/decode wire helpers |
| `api_client.py` | `get_all` — single low-level pagination loop |
| `workflows/` | Orchestration — **must not** duplicate list/count/group pagination or route filters |
| `tools/` | Composition (`list_sharding`, hydration orchestration) |

## Facade naming rules

1. **`client.<Kind>`** matches the endorctl resource kind (PascalCase).
2. **CRUD** (`list`, `get`, `lookup`) return **`<Kind>` models** (or masked `dict` rows).
3. **Contract routes (CRUD+)** return **`RouteResult`** with `.values` / `.value`, `.edge_used`, `.warnings`.
4. **Auxiliary helpers** on the **wire resource facade** when the API entity is clear:
   - `client.CallGraphData.decode(package_version)` → `CallGraphDecoded`
   - `client.CallGraphData.fetch(package_version)` → raw envelope `dict`
5. **Parent-scoped routes** on the **child or source facade** (see [resource-routes.md](../generated-reference/resource-routes.md)):
   - `client.Finding.list_by_project(project, …)` → `RouteResult[list[Finding]]`
   - `client.Finding.list_by_scan(scan, …)` → `RouteResult[list[Finding]]`
   - `client.ScanResult.list_by_project(project, …)` → `RouteResult[list[ScanResult]]`
   - `client.Finding.to_dependency_metadata(finding, …)` → `RouteResult[DependencyMetadata]`
   - `client.Finding.to_semgrep_rule(finding, …)` → `RouteResult[SemgrepRule]` (SAST only)
6. **Discovery sugar:** `client.Project.resolve(name_or_uuid)` → `Project`
7. **Custom facades** only when the kind is not yet on `registry_contract` — today: **`CallGraphData`** only.

## Resource route map (codegen)

Generated from `devtools/model_sync_profiles/route_contract_overlay.yaml`:

- Python: `src/endorlabs/generated/route_contract.py` (`ROUTE_CONTRACT`, `ROUTE_RELATIONSHIP_MAP`)
- Docs: [generated-reference/resource-routes.md](../generated-reference/resource-routes.md)

Regenerate: `uv run python devtools/generate_route_contract.py`

## Pagination

- `list(max_pages=None)` fetches **all pages** via `get_all()`.
- Route methods forward `max_pages`, `filter`, and other list kwargs to the underlying wire op.
- Do **not** set `page_size` unless the user asks.

## Universal helpers (`ListableFacade`)

| Method | Purpose |
|--------|---------|
| `count(**list_kwargs) -> int` | Server-side count (replaces broken `list(count=True)`) |
| `list_groups(*, paths, **kwargs)` | Yield `GroupBucket` rows from `group_response` |
| `latest(sort_by=..., **kwargs) -> T \| None` | Newest row; always `max_pages=1` |
| `latest_created(**kwargs)` | Sugar for `sort_by="meta.create_time"` |
| `latest_updated(**kwargs)` | Sugar for `sort_by="meta.update_time"` |
| `parent(resource) -> ParentModel` | Registry `parent_kind` → parent GET (today: `"project"`) |

`list(count=True)` emits `DeprecationWarning` and delegates to `count()`.

## Resource helpers

| Method | Input | Returns |
|--------|-------|---------|
| `CallGraphData.decode(package_version)` | `PackageVersion` or UUID + `namespace=` | `CallGraphDecoded` |
| `CallGraphData.fetch(package_version)` | same | raw CallGraphData envelope |
| `ScanResult.get_logs(scan_result, …)` | `ScanResult` or UUID + `namespace=` | `ScanLogRequestLogMessage[]` |
| `Project.resolve(name_or_uuid, …)` | name or UUID | `Project` |
| `Finding.list_by_project(project, …)` | `Project` | `RouteResult` → findings |
| `Finding.list_by_scan(scan, …)` | `ScanResult` | `RouteResult` → findings |
| `ScanResult.list_by_project(project, …)` | `Project` or UUID | `RouteResult` → scan results |
| `Finding.to_dependency_metadata(finding, …)` | `Finding` | `RouteResult` → dependency row |
| `Finding.to_semgrep_rule(finding, …)` | `Finding` (SAST) | `RouteResult` → semgrep rule |
| `ScanResult.latest_created(parent=project, …)` | `Project` parent | `ScanResult \| None` |

### Example: project-scoped retrieval with routes

```python
import endorlabs

client = endorlabs.Client(tenant="tenant.child")
project = client.Project.lookup(name="https://github.com/org/repo", namespace="tenant.child")

findings = client.Finding.list_by_project(project, max_pages=1)
print(findings.edge_used, len(findings.values or []))

scans = client.ScanResult.list_by_project(project, max_pages=1)
if scans.values:
    scan_findings = client.Finding.list_by_scan(scans.values[0], max_pages=1)
    print(scan_findings.warnings)  # list-only index fields

for finding in findings.values or []:
    if finding.spec and finding.spec.target_uuid:
        dm = client.Finding.to_dependency_metadata(finding)
        if dm.value:
            print(dm.edge_used, dm.value.uuid)
```

### `CallGraphData`

Supported decode/fetch sources: **`PackageVersion`** (`meta.parent_uuid == package_version.uuid`).

```python
decoded = client.CallGraphData.decode(package_version)
raw = client.CallGraphData.fetch(package_version)
```

Requires optional `zstandard` for zstd/protobuf payloads when decoding.

### `ScanResult.get_logs`

Uses ScanLogRequest POST under the hood. For embedded lines only, GET the scan-result resource (`spec.logs`).

## See also

- [consumer-ux-list-update.md](consumer-ux-list-update.md)
- [contracts.md](../contracts.md#resource-routes-crud)
- [resource-routes.md](../generated-reference/resource-routes.md)
- [list-query-performance.md](../contributing/list-query-performance.md)
