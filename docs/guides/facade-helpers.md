# Facade list helpers

Normative catalog for SDK facade helpers. Wire logic lives in `operations/`; workflows orchestrate only.

## Layer placement

| Layer | Owns |
|-------|------|
| `facade.py` | Public helpers on resource facades + `CallGraphData` custom facade |
| `operations/` | Pagination, group wire parsing |
| `resources/call_graph_data.py` | CallGraphData fetch/decode wire helpers |
| `api_client.py` | `get_all` — single low-level pagination loop |
| `workflows/` | Orchestration — **must not** duplicate list/count/group pagination |
| `tools/` | Composition (`list_sharding`, hydration orchestration) |

## Facade naming rules

1. **`client.<Kind>`** matches the endorctl resource kind (PascalCase).
2. **CRUD** (`list`, `get`, `lookup`) return **`<Kind>` models** (or masked `dict` rows).
3. **Auxiliary helpers** on the **wire resource facade** when the API entity is clear:
   - `client.CallGraphData.decode(package_version)` → `CallGraphDecoded`
   - `client.CallGraphData.fetch(package_version)` → raw envelope `dict`
4. **Parent-scoped sugar** on the facade the caller already holds when that is more ergonomic:
   - `client.ScanResult.get_logs(scan_result)` → `list[ScanLogRequestLogMessage]` (wire: ScanLogRequest POST)
   - `client.Finding.list_for_scan(scan_result)` → `list[Finding]`
   - `client.ScanResult.list_for_project(project, …)` → `list[ScanResult]`
   - `client.Project.resolve(name_or_uuid)` → `Project`
5. **Custom facades** only when the kind is not yet on `registry_contract` but needs a client attr — today: **`CallGraphData`** only. Do **not** add parallel attrs like `ScanLogs`.

## Pagination

- `list(max_pages=None)` fetches **all pages** via `get_all()`.
- Bounded helpers (`latest`, `lookup` default) set `max_pages=1` (or explicit cap).
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
| `Finding.list_for_scan(scan_result, …)` | `ScanResult` | `list[Finding]` |
| `ScanResult.list_for_project(project, …)` | `Project` or UUID | `list[ScanResult]` |
| `ScanResult.latest_created(parent=project, …)` | `Project` parent | `ScanResult \| None` |

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
- [contracts.md](../contracts.md)
- [list-query-performance.md](../contributing/list-query-performance.md)
