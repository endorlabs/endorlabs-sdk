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
from endorlabs.resources import dependency_metadata
from endorlabs.types import ListParameters

# Query all DependencyMetadata across all namespaces
# Uses API default page size (typically 100) - no page_size override
list_params = ListParameters(traverse=True)
all_deps = dependency_metadata.list_dependency_metadata(
    client, tenant_namespace, list_params
)
```

### With Filtering

```python
from endorlabs.resources import dependency_metadata
from endorlabs.types import ListParameters

# Query all private dependencies across all namespaces
list_params = ListParameters(
    traverse=True,
    filter="spec.dependency_data.public==false"
)
private_deps = dependency_metadata.list_dependency_metadata(
    client, tenant_namespace, list_params
)
```

### Resource-Specific Examples

#### DependencyMetadata (Recommended Pattern)

```python
from endorlabs.resources import dependency_metadata
from endorlabs.types import ListParameters

# Get all dependencies across tenant
list_params = ListParameters(traverse=True)
deps = dependency_metadata.list_dependency_metadata(
    client, "endor-solutions-tgowan", list_params
)
```

#### PackageVersion

```python
from endorlabs.resources import package_version
from endorlabs.types import ListParameters

# Get all package versions across tenant
list_params = ListParameters(traverse=True)
packages = package_version.list_package_versions(
    client, "endor-solutions-tgowan", list_params
)
```

#### Finding

```python
from endorlabs.resources import finding
from endorlabs.types import ListParameters

# Get all findings across tenant
list_params = ListParameters(traverse=True)
findings = finding.list_findings(
    client, "endor-solutions-tgowan", list_params
)
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
namespaces = collect_all_namespaces(client, tenant_namespace)
all_deps = []
for ns in namespaces:
    deps = dependency_metadata.list_dependency_metadata(client, ns)
    all_deps.extend(deps)
# Result: N API calls (one per namespace)
```

### With Traverse (Efficient)

```python
# ✅ FAST: Single API call
list_params = ListParameters(traverse=True)
all_deps = dependency_metadata.list_dependency_metadata(
    client, tenant_namespace, list_params
)
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

### Migration from include_child_namespaces

The `include_child_namespaces` parameter has been removed. Use `traverse` instead.

## Best Practices

1. **Default to traverse for tenant-wide queries**: If you're querying across namespaces, use `traverse=True`

2. **Combine with filters**: Use filters to narrow results while still traversing:
   ```python
   ListParameters(traverse=True, filter="spec.project_uuid==<uuid>")
   ```

3. **Document traversal intent**: When writing functions that use traverse, document why:
   ```python
   def get_all_dependencies(client, tenant_namespace):
       """Get all dependencies across all namespaces in tenant.
       
       Uses traverse=True for efficient tenant-wide query.
       """
       list_params = ListParameters(traverse=True)
       return dependency_metadata.list_dependency_metadata(
           client, tenant_namespace, list_params
       )
   ```

4. **Use MAX_PAGES for control**: Don't override page_size unless necessary. Use max_pages parameter to limit results:
   ```python
   # Uses API default page size, limits to 10 pages max
   list_params = ListParameters(traverse=True)
   deps = dependency_metadata.list_dependency_metadata(
       client, tenant_namespace, list_params, max_pages=10
   )
   ```
   
   **Important**: Small page sizes (e.g., page_size=1) cause performance issues. Only override if you have a specific need.

## Common Patterns

### Pattern 1: Tenant-Wide Resource Query

```python
def get_all_resources(client, tenant_namespace, resource_type):
    """Get all resources of a type across tenant."""
    list_params = ListParameters(traverse=True)
    # Use appropriate resource module
    return resource_module.list_resources(client, tenant_namespace, list_params)
```

### Pattern 2: Filtered Tenant-Wide Query

```python
def get_private_dependencies(client, tenant_namespace):
    """Get all private dependencies across tenant."""
    list_params = ListParameters(
        traverse=True,
        filter="spec.dependency_data.public==false"
    )
    return dependency_metadata.list_dependency_metadata(
        client, tenant_namespace, list_params
    )
```

### Pattern 3: Tenant-Wide Count

```python
def count_all_findings(client, tenant_namespace):
    """Count all findings across tenant."""
    list_params = ListParameters(traverse=True, count=True)
    # Implementation depends on resource module
    return finding.list_findings(client, tenant_namespace, list_params)
```

## Related Documentation

- [ListParameters API Reference](../../src/endorlabs/types.py)
- [BaseResourceOperations Implementation](../../src/endorlabs/models/base.py)
- DependencyMetadata: `endorlabs.resources.dependency_metadata`; see [reference/resources.md](../reference/resources.md) and module docstrings.

