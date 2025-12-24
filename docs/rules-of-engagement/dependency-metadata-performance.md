# DependencyMetadata Query Performance Analysis

## Issue Summary

DependencyMetadata queries with `traverse=True` are experiencing timeout issues when querying across large tenants.

## Findings from endorctl Debug Output

### Endpoint Verification ✅

The endpoint is **correct**:
```
GET /v1/namespaces/endor-solutions-tgowan/dependency-metadata
?list_parameters.page_size=1
&list_parameters.traverse=true
```

### Timeout Behavior

From endorctl verbose logs:
- **Deadline**: 150 seconds (2.5 minutes)
- **Actual time**: ~2m30s before timeout
- **HTTP Status**: 500/504 (Gateway Timeout)
- **Error**: `context deadline exceeded`

### Retry/Backoff Configuration

**Current SDK Settings**:
- `max_retries`: 15
- `backoff_factor`: 0.5
- `status_forcelist`: (429, 500, 502, 503, 504)

**Backoff Calculation**:
```
delay = backoff_factor * (2 ^ retry_count)
```

**Backoff Schedule**:
- Retry 1: 0.5 * 2^0 = **0.5 seconds**
- Retry 2: 0.5 * 2^1 = **1.0 seconds**
- Retry 3: 0.5 * 2^2 = **2.0 seconds**
- Retry 4: 0.5 * 2^3 = **4.0 seconds**
- Retry 5: 0.5 * 2^4 = **8.0 seconds**
- Retry 6: 0.5 * 2^5 = **16.0 seconds**
- etc.

### Observed Behavior

1. Request sent to API
2. ~20 seconds pass
3. Server returns 504 Gateway Timeout
4. urllib3 retries with backoff (0.5s, 1s, 2s, etc.)
5. Each retry also takes ~20 seconds
6. After ~2.5 minutes total, deadline exceeded

## Root Cause

The DependencyMetadata query with `traverse=True` is **too expensive** for the API server to process within the timeout window. This is likely because:

1. **Large dataset**: Traversing all namespaces aggregates a large amount of data
2. **Complex query**: Cross-namespace queries require significant processing
3. **Server-side timeout**: The API server has its own timeout limits

## Solutions

### Option 1: Increase Timeout (SDK)

Add timeout parameter to API client requests:

```python
# In api_client.py
response = self.session.request(
    method="GET",
    url=normalized_url,
    params=params,
    timeout=300,  # 5 minutes instead of default
    **request_kwargs,
)
```

### Option 2: Query Without Traverse (Namespace-Scoped)

Query each namespace individually instead of using traverse:

```python
# Query specific namespace only
list_params = ListParameters(traverse=False)
deps = dependency_metadata.list_dependency_metadata(
    client, "endor-solutions-tgowan.specific-namespace", list_params
)
```

### Option 3: Use Filters to Reduce Dataset

Add filters to reduce the amount of data returned:

```python
# Filter to reduce dataset size
list_params = ListParameters(
    traverse=True,
    filter="spec.dependency_data.direct==true"  # Only direct dependencies
)
```

### Option 4: Use API Default Page Size (Recommended)

**Don't override page_size** - let the API use its default (typically 100):

```python
# Uses API default page size - most efficient
list_params = ListParameters(traverse=True)
deps = dependency_metadata.list_dependency_metadata(
    client, tenant_namespace, list_params
)
```

**Why**: Small page sizes (like page_size=1) cause many requests and timeouts. The API's default page size is optimized for performance.

### Option 5: Use endorctl with Increased Timeout

endorctl has a `--timeout` flag:

```bash
endorctl api list -r DependencyMetadata --traverse --timeout 300s
```

## Recommendations

1. **For large tenants**: Don't use `traverse=True` for DependencyMetadata
2. **For specific queries**: Use filters to narrow the dataset
3. **For SDK**: Consider adding configurable timeout parameter
4. **For production**: Query namespace-by-namespace or use pagination with smaller page sizes

## Related Documentation

- [Namespace Traversal Guide](./namespace-traversal.md)
- [Package Dependency Visibility](../package-dependency-visibility.md)

