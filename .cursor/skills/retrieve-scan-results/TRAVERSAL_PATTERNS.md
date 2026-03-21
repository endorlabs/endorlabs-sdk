# Namespace Traversal Patterns

Traverse and list parameters for tenant-wide queries in the Endor Labs SDK.

---

## Overview

When querying resources across an entire tenant, use the `traverse` parameter
to automatically query all namespaces in the hierarchy. This is the canonical,
efficient approach for tenant-wide operations.

## The Problem

Without traversal, you must:
1. Recursively collect all namespaces
2. Query each namespace individually
3. Aggregate results manually

This is slow, inefficient, and error-prone.

## The Solution: Use `traverse=True`

The `traverse` parameter in `ListParameters` automatically queries all child
namespaces recursively in a single API call.

## Canonical Pattern

### Basic Usage

```python
# Client surface (recommended)
all_deps = client.DependencyMetadata.list(traverse=True)

# Module-level (advanced)
from endorlabs.resources import dependency_metadata
from endorlabs.core.types import ListParameters

list_params = ListParameters(traverse=True)
all_deps = dependency_metadata.list_dependency_metadata(
    client, tenant_namespace, list_params
)
```

### With Filtering

```python
# All private dependencies across all namespaces
private_deps = client.DependencyMetadata.list(
    traverse=True,
    filter="spec.dependency_data.public==false",
)
```

### Resource-Specific Examples

#### Projects

```python
projects = client.Project.list(traverse=True, max_pages=2)
```

#### Findings

```python
# All critical findings across tenant
critical = client.Finding.list(
    filter="spec.level==FINDING_LEVEL_CRITICAL",
    traverse=True,
)
```

#### Scan Results

```python
# All scan results for a specific project
scans = client.ScanResult.list(
    parent=project,
    sort_by="meta.create_time",
    desc=True,
)
```

## When to Use Traverse

### Use `traverse=True` when:

- Querying resources across the entire tenant
- You need all instances of a resource regardless of namespace
- Building tenant-wide reports or analytics
- The resource is distributed across multiple namespaces
- You want the most efficient single-query approach

### Don't use `traverse=True` when:

- You only need resources from a specific namespace
- You're doing namespace-scoped operations
- You need to process results per-namespace
- The query is already fast without traversal

## Performance Comparison

### Without Traverse (Inefficient)

```python
# Multiple API calls
namespaces = collect_all_namespaces(client, tenant_namespace)
all_deps = []
for ns in namespaces:
    deps = dependency_metadata.list_dependency_metadata(client, ns)
    all_deps.extend(deps)
# Result: N API calls (one per namespace)
```

### With Traverse (Efficient)

```python
# Single API call
all_deps = client.DependencyMetadata.list(traverse=True)
# Result: 1 API call (handles all namespaces automatically)
```

## Pagination Control

Use `max_pages` to limit results (not `page_size`):

```python
# Uses API default page size, limits to 10 pages max
deps = client.DependencyMetadata.list(traverse=True, max_pages=10)
```

**Important**: Small page sizes (e.g., `page_size=1`) cause performance issues.
Only override `page_size` if you have a specific need.

## Common Patterns

### Tenant-Wide Count

```python
findings = client.Finding.list(traverse=True, count=True)
```

### Filtered Tenant-Wide Query

```python
private_deps = client.DependencyMetadata.list(
    traverse=True,
    filter="spec.dependency_data.public==false",
)
```

### Sorted with Field Mask

```python
recent_scans = client.ScanResult.list(
    traverse=True,
    sort_by="meta.create_time",
    desc=True,
    mask="meta.name,meta.create_time,spec.status",
    max_pages=1,
)
```

## Namespace Scoping After Traverse

When you act on objects returned from `list(traverse=True)`, pass the
**resource object** to `get`, `update`, or `delete`. The SDK uses
`resource.tenant_meta.namespace` to set the correct path:

```python
# Correct: namespace derived from resource
client.Project.delete(target)

# Wrong: may 404 if target lives in a child namespace
client.Project.delete(target.uuid, namespace="tenant-root")
```

Helper: `endorlabs.utils.resolve_namespace_for_resource(resource, fallback)`
returns `resource.tenant_meta.namespace` when present, else `fallback`.

## API Mapping

The SDK maps `traverse=True` to the API parameter `list_parameters.traverse=true`.

## References

- `src/endorlabs/core/types.py` -- `ListParameters` definition
- `docs/contracts.md` -- List parameters, traverse, namespace scoping
