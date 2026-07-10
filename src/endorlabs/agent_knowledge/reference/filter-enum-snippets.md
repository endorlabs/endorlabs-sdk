# Filter enum snippets (generated)

Illustrative wire enum strings for **`filter=`** on list and accessor calls.
Regenerate with `uv run python devtools/codegen/generate_filter_enum_reference.py`.
Values are sourced from generated model-sync enums — not hand-maintained.

## ScanResult status (`spec.status`)

From `endorlabs.generated.models.scan_result_service.ScanResultSpecStatus`:

| Value | Typical meaning |
|-------|-----------------|
| `STATUS_UNSPECIFIED` | Unset / unknown |
| `STATUS_SUCCESS` | Scan completed successfully |
| `STATUS_PARTIAL_SUCCESS` | Completed with partial results |
| `STATUS_FAILURE` | Scan failed |
| `STATUS_RUNNING` | Scan in progress |

Example:

```python
scans = client.ScanResult.list_by_project(
    project,
    filter='spec.status=="STATUS_SUCCESS"',
    max_pages=5,
)
```

`ScanResult.list_by_project(..., status_filter="STATUS_SUCCESS")` applies the
same value client-side after the route list.

## Finding level (`spec.level`)

From `endorlabs.generated.models.finding_service.SpecFindingLevel`:

| Value |
|-------|
| `FINDING_LEVEL_UNSPECIFIED` |
| `FINDING_LEVEL_CRITICAL` |
| `FINDING_LEVEL_HIGH` |
| `FINDING_LEVEL_MEDIUM` |
| `FINDING_LEVEL_LOW` |

Example:

```python
findings = client.Finding.list_by_project(
    project,
    filter='spec.level=="FINDING_LEVEL_CRITICAL"',
    max_pages=5,
)
```

Or with `F()`:

```python
from endorlabs import F

findings = client.Finding.list_by_project(
    project,
    filter=F("spec.level") == "FINDING_LEVEL_CRITICAL",
    max_pages=5,
)
```

## Related docs

- [contracts/list-parameters.md](../contracts/list-parameters.md) — pagination, `mask`, `limit` alias
- [contracts/resource-discovery.md](../contracts/resource-discovery.md) — return types and discovery flow
- [resource-routes.md](resource-routes.md) — relationship accessor inventory
