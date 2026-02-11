# Namespace Traversal Pattern

Traverse and list parameters are defined in [conventions.md](../conventions.md); this doc adds patterns and examples.

## Overview

When querying resources across an entire tenant, use the **`traverse`** parameter to automatically query all namespaces in the hierarchy. This is the canonical, efficient approach for tenant-wide operations.

## The Problem

Without traversal, you must:
1. Recursively collect all namespaces
2. Query each namespace individually
3. Aggregate results manually

This is slow, inefficient, and error-prone.

## The Solution: Use `traverse=True`

The `traverse` parameter in `ListParameters` automatically queries all child namespaces recursively in a single API call.

## Canonical Pattern

### Basic Usage

```python
import endorlabs

client = endorlabs.Client(tenant="endor-solutions-tgowan")

# Query all DependencyMetadata across all namespaces
all_deps = client.dependency_metadata.list(traverse=True)
```

### With Filtering

```python
# Query all private dependencies across all namespaces
private_deps = client.dependency_metadata.list(
    traverse=True,
    filter="spec.dependency_data.public==false",
)
```

### Resource-Specific Examples

#### DependencyMetadata (Recommended Pattern)

```python
deps = client.dependency_metadata.list(traverse=True)
```

#### PackageVersion

```python
packages = client.package_version.list(traverse=True)
```

#### Finding

```python
findings = client.finding.list(traverse=True)
```

## When to Use Traverse

### ✅ Use `traverse=True` When:

- Querying resources across the entire tenant
- You need all instances of a resource regardless of namespace
- Building tenant-wide reports or analytics
- The resource is distributed across multiple namespaces
- You want the most efficient single-query approach

### ❌ Don't Use `traverse=True` When:

- You only need resources from a specific namespace
- You're doing namespace-scoped operations
- You need to process results per-namespace
- The query is already fast without traversal

## Performance Comparison

### Without Traverse (Inefficient)

```python
# ❌ SLOW: Multiple API calls
namespaces = client.namespace.list(traverse=True)
all_deps = []
for ns in namespaces:
    deps = client.dependency_metadata.list(namespace=ns.meta.name)
    all_deps.extend(deps)
# Result: N API calls (one per namespace)
```

### With Traverse (Efficient)

```python
# ✅ FAST: Single API call
all_deps = client.dependency_metadata.list(traverse=True)
# Result: 1 API call (handles all namespaces automatically)
```

## Implementation Details

### ListParameters.traverse

```python
class ListParameters(BaseModel):
    traverse: bool | None = Field(
        None,
        description=(
            "Traverse all child namespaces recursively. "
            "When True, automatically queries all namespaces in the hierarchy. "
            "Recommended for tenant-wide queries."
        ),
    )
```

### API Mapping

The SDK maps `traverse=True` to the API parameter `list_parameters.traverse=true`.

## Guidelines

1. **Default to traverse for tenant-wide queries**: If you're querying across namespaces, use `traverse=True`

2. **Combine with filters**: Use filters to narrow results while still traversing:
   ```python
   ListParameters(traverse=True, filter="spec.project_uuid==<uuid>")
   ```

3. **Document traversal intent**: When writing functions that use traverse, document why:
   ```python
   def get_all_dependencies(client):
       """Get all dependencies across all namespaces in tenant.
       
       Uses traverse=True for efficient tenant-wide query.
       """
       return client.dependency_metadata.list(traverse=True)
   ```

4. **Use MAX_PAGES for control**: Don't override page_size unless necessary. Use max_pages parameter to limit results:
   ```python
   # Uses API default page size, limits to 10 pages max
   deps = client.dependency_metadata.list(traverse=True, max_pages=10)
   ```
   
   **Important**: Small page sizes (e.g., page_size=1) cause performance issues. Only override if you have a specific need.

## Common Patterns

### Pattern 1: Tenant-Wide Resource Query

```python
# Get all resources of a type across the tenant
projects = client.project.list(traverse=True)
```

### Pattern 2: Filtered Tenant-Wide Query

```python
def get_private_dependencies(client):
    """Get all private dependencies across tenant."""
    return client.dependency_metadata.list(
        traverse=True,
        filter="spec.dependency_data.public==false",
    )
```

### Pattern 3: Tenant-Wide Count

```python
from endorlabs.types import ListParameters

def count_all_findings(client):
    """Count all findings across tenant."""
    list_params = ListParameters(traverse=True, count=True)
    return client.finding.list(list_params=list_params)
```

## Related Documentation

- [ListParameters API Reference](../../src/endorlabs/types.py)
- [BaseResourceOperations Implementation](../../src/endorlabs/operations/__init__.py)
- DependencyMetadata: `endorlabs.resources.dependency_metadata`; see [reference/resources.md](../reference/resources.md) and module docstrings.

