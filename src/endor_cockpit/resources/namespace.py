"""
Namespace Resource Deep-Dive

> **Comprehensive guide to namespace resources in Endor Labs platform**

This module provides a resource-oriented interface for managing Endor Labs
namespaces. It implements CRUD operations following REST principles and
provides type-safe data models.

## Architecture

### Resource Structure

Namespaces in Endor Labs follow a hierarchical structure with canonical naming:

```
Tenant (endor-solutions-tgowan.cockpit)
├── Namespace (tenant.namespace)
│   ├── Child Namespace (tenant.namespace.child)
│   │   └── Grandchild (tenant.namespace.child.grandchild)
│   └── Sibling Namespace (tenant.namespace.sibling)
└── Other Namespace (tenant.other-namespace)
```

### Core Concepts

- **Hierarchical Structure**: Namespaces can contain child namespaces
- **Canonical Naming**: Uses dot-separated hierarchical names, not UUIDs
- **Tenant Isolation**: Each tenant has isolated namespace hierarchies
- **Parent-Child Relationships**: Child namespaces inherit from parent context

### Lifecycle

```
Tenant → Namespace → Child Namespace → Resources
```

**Lifecycle States**:
- **Created**: Namespace created in parent context
- **Active**: Namespace available for resource operations
- **Deleted**: Namespace and all children removed

## Data Model

### SDK Implementation

**Location**: `src/endor_cockpit/resources/namespace.py:117-173`

```python
# Direct reference - see SDK for full definition
class Namespace(BaseModel):
    uuid: str = Field(..., description="Unique identifier for the namespace")
    meta: NamespaceMeta = Field(
        ..., description="Metadata associated with the namespace"
    )
```

**To explore fields**:
- View `NamespaceMeta` in SDK (lines 53-82)
- View `NamespaceMetaCreate` in SDK (lines 84-95)
- View `NamespaceMetaUpdate` in SDK (lines 97-105)

### Mutable Fields

**Via PATCH operations**:
- `meta.description`: str - Namespace description
- `meta.tags`: List[str] - Namespace tags (if supported)

### Immutable Fields

**Read-only, API-managed**:
- `uuid`: Unique identifier
- `meta.name`: Namespace name (set at creation)
- `meta.created_at`: Creation timestamp
- `meta.updated_at`: Last update timestamp

### Field Validation

**Validators** (see `NamespaceMeta:75-81`):
- `name`: Must be 1-255 characters, cannot be empty or whitespace
- `description`: Optional string for namespace purpose

## Operations

### List Namespaces

**Function**: `namespace.list_namespaces(client, tenant_namespace)`
**Location**: `src/endor_cockpit/resources/namespace.py:197`
**Status**: ✅ IMPLEMENTED

```python
from endor_cockpit.resources import namespace

# List all namespaces in tenant
all_namespaces = namespace.list_namespaces(
    client=client,
    tenant_namespace="endor-solutions-tgowan.cockpit"
)
```

**Returns**: `List[Namespace]` - Empty list on error

### Get Namespace

**Function**: `namespace.get_namespace(client, parent_namespace, namespace_uuid)`
**Location**: `src/endor_cockpit/resources/namespace.py:257`
**Status**: ✅ IMPLEMENTED

```python
# Get specific namespace
namespace = namespace.get_namespace(
    client=client,
    parent_namespace="endor-solutions-tgowan.cockpit",
    namespace_uuid="namespace-uuid-here"
)
```

**Returns**: `Optional[Namespace]` - None on error

### Create Namespace

**Function**: `namespace.create_namespace(client, parent_namespace, payload)`
**Location**: `src/endor_cockpit/resources/namespace.py:224`
**Status**: ✅ IMPLEMENTED

```python
from endor_cockpit.resources.namespace import (
    CreateNamespacePayload,
    NamespaceMetaCreate
)

# Create new namespace
payload = CreateNamespacePayload(
    meta=NamespaceMetaCreate(
        name="example-namespace",
        description="An example namespace"
    )
)

namespace = namespace.create_namespace(
    client=client,
    parent_namespace="endor-solutions-tgowan.cockpit",
    payload=payload
)
```

**Required Fields**: `meta.name`, `meta.description`
**Auto-populated**: `uuid`, `meta.created_at`, `meta.updated_at`

### Update Namespace

**Function**: `namespace.update_namespace(client, parent_namespace,\
 namespace_uuid, payload)`
**Location**: `src/endor_cockpit/resources/namespace.py:317`
**Status**: ✅ IMPLEMENTED

```python
from endor_cockpit.resources.namespace import (
    UpdateNamespacePayload,
    NamespaceMetaUpdate
)

# Update namespace fields
payload = UpdateNamespacePayload(
    meta=NamespaceMetaUpdate(
        description="Updated description"
    )
)

namespace = namespace.update_namespace(
    client=client,
    parent_namespace="endor-solutions-tgowan.cockpit",
    namespace_uuid="namespace-uuid",
    payload=payload
)
```

**Mutable Fields**: See Data Model > Mutable Fields

### Delete Namespace

**Function**: `namespace.delete_namespace(client, parent_namespace, namespace_uuid)`
**Location**: `src/endor_cockpit/resources/namespace.py:288`
**Status**: ✅ IMPLEMENTED

```python
# Delete namespace
success = namespace.delete_namespace(
    client=client,
    parent_namespace="endor-solutions-tgowan.cockpit",
    namespace_uuid="namespace-uuid"
)
```

**Behavior**: Permanently removes namespace and all children
**Cascade**: All child namespaces and resources are deleted

## Relationships

### Namespace-Project

Namespaces contain projects and provide organizational context for security scanning.

### Namespace-Finding

Findings are generated within namespace context and inherit namespace metadata.

### Namespace-Policy

Policies can be applied at namespace level to affect all contained resources.

## Common Issues

### Issue: Namespace Creation with Invalid Parent

**Cause**: Using UUID instead of canonical name for parent namespace
**Solution**: Always use canonical hierarchical names

```python
# ❌ WRONG
parent_namespace = "68f3b2956795a2693a0f5bec"

# ✅ CORRECT
parent_namespace = "endor-solutions-tgowan.cockpit.integration-test"
```

### Issue: Cross-Tenant Operations

**Cause**: Attempting to access namespaces across tenant boundaries
**Solution**: Ensure all operations use same tenant namespace

```python
# ❌ WRONG
namespace = "other-tenant.namespace"

# ✅ CORRECT
namespace = "your-tenant.namespace"
```

## Testing Patterns

### CRUD Testing

**Test File**: `tests/test_namespace.py`

```python
# Reference actual test patterns from test_namespace.py
# See lines X-Y for list/get testing
# See lines A-B for create/update testing
# See lines C-D for hierarchy testing
```

### Integration Testing

**Test File**: `tests/test_namespace.py`

```python
# Reference integration test patterns
# See lines X-Y for parent-child relationship testing
# See lines A-B for error handling testing
```

## Related Resources

- [Project](./project.md) - Projects contained within namespaces
- [Finding](./finding.md) - Findings generated in namespace context
- [Policy](./policy.md) - Policies applied at namespace level

---

*Documentation references SDK implementation. See
`src/endor_cockpit/resources/namespace.py` for complete details.*
"""

import logging
import os
import sys
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..models.base import BaseMeta, BaseResource, BaseResourceOperations, BaseSpec
from ..types import ListParameters

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


# Pydantic Models for Namespace data with OpenAPI validation
class NamespaceMeta(BaseMeta):
    """
    Metadata for an Endor Labs namespace extending BaseMeta.

    Namespace-specific fields only (universal fields inherited from BaseMeta).
    """

    # Namespace-specific fields (universal fields inherited from BaseMeta)
    pass  # No additional fields needed, all were universal

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that the name is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("name cannot be empty")
        return v


class NamespaceSpec(BaseSpec):
    """Namespace specification extending BaseSpec."""

    # Namespace-specific fields (universal fields inherited from BaseSpec)
    pass  # No additional fields needed for namespace spec


class NamespaceMetaCreate(BaseModel):
    """
    Metadata for creating an Endor Labs namespace.
    """

    name: str = Field(
        ..., min_length=1, max_length=255, description="The name of the namespace"
    )
    description: str = Field(
        ..., min_length=1, description="Description of the namespace's purpose"
    )


class NamespaceMetaUpdate(BaseModel):
    """
    Metadata for updating an Endor Labs namespace.
    """

    description: Optional[str] = Field(
        None, description="Updated description of the namespace's purpose"
    )


class UpdateNamespacePayload(BaseModel):
    """
    Payload for updating an Endor Labs namespace.

    MUTABLE FIELDS (can be updated via PATCH):
    - meta.description: Namespace description

    IMMUTABLE FIELDS (read-only, managed by API):
    - uuid: Unique identifier (set at creation)
    - meta.name: Namespace name (set at creation)
    - meta.create_time, meta.created_by: Creation metadata
    - meta.update_time, meta.updated_by: Auto-managed timestamps
    - meta.index_data: Index data (managed by API)
    - meta.kind: Resource kind (managed by API)
    - meta.version: Version (managed by API)

    Example:
        >>> payload = UpdateNamespacePayload(
        ...     meta=NamespaceMetaUpdate(description="Updated namespace description")
        ... )
        >>> namespace = update_namespace(client, parent, uuid, payload)
    """

    meta: NamespaceMetaUpdate = Field(
        ..., description="Updated metadata for the namespace"
    )


class Namespace(BaseResource):
    """
    An Endor Labs namespace entity extending BaseResource.

    Namespace-specific fields (universal fields inherited from BaseResource).
    """

    # Namespace-specific fields (universal fields inherited from BaseResource)
    spec: NamespaceSpec = Field(..., description="Namespace specification")  # type: ignore

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data):
        # Convert spec to NamespaceSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = NamespaceSpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = set()  # No specific fields for namespace spec
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v

    @field_validator("uuid")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Validate that the UUID is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("uuid cannot be empty")
        return v


class CreateNamespacePayload(BaseModel):
    """
    Payload for creating a new namespace.

    Attributes:
        meta: Metadata for the new namespace
    """

    meta: NamespaceMetaCreate = Field(..., description="Metadata for the new namespace")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "meta": {
                    "name": "example-namespace",
                    "description": "An example namespace",
                }
            }
        }
    )


def _get_namespace_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for namespaces."""
    return BaseResourceOperations(client, "namespaces", Namespace)


def list_namespaces(
    client: APIClient,
    tenant_namespace: str,
    list_params: Optional[ListParameters] = None,
) -> List[Namespace]:
    """
    List all namespaces under the specified tenant namespace.

    Args:
        client: The APIClient instance to use for the request
        tenant_namespace: The parent namespace to list namespaces from
        list_params: Optional list parameters for filtering, pagination, etc.

    Returns:
        List[Namespace]: A list of Namespace objects. Empty list if error occurs.

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    ops = _get_namespace_ops(client)
    results = ops.list(tenant_namespace, list_params)
    return [Namespace(**item.model_dump()) for item in results]  # type: ignore


def create_namespace(
    client: APIClient, parent_namespace: str, payload: CreateNamespacePayload
) -> Optional[Namespace]:
    """
    Create a new namespace under the specified parent namespace.

    Args:
        client: The APIClient instance to use for the request
        parent_namespace: The namespace under which to create the new namespace
        payload: The CreateNamespacePayload containing the new namespace details

    Returns:
        Optional[Namespace]: The created Namespace object, or None if creation fails

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    try:
        headers = client.default_headers
        headers.update({"Accept": "application/json"})
        res = client.post(
            f"v1/namespaces/{parent_namespace}/namespaces",
            headers=headers,
            data=payload.model_dump(),
        )
        if res is None:
            logger.error(
                "Failed to create namespace: No response from API "
                "(likely authentication failure)"
            )
            return None
        data = res.json()
        return Namespace(**data)
    except Exception as e:
        logger.error(f"Error creating namespace: {e}", exc_info=True)
        return None


def get_namespace(
    client: APIClient, parent_namespace: str, namespace_uuid: str
) -> Optional[Namespace]:
    """
    Retrieve a specific namespace by UUID.

    Args:
        client: The APIClient instance to use for the request
        parent_namespace: The parent namespace containing the target namespace
        namespace_uuid: The UUID of the namespace to retrieve

    Returns:
        Optional[Namespace]: The requested Namespace object, or None if not found

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    try:
        headers = client.default_headers
        res = client.get(
            f"v1/namespaces/{parent_namespace}/namespaces/{namespace_uuid}",
            headers=headers,
        )
        data = res.json()
        return Namespace(**data)
    except Exception as e:
        logger.error(f"Error retrieving namespace {namespace_uuid}: {e}", exc_info=True)
        return None


def delete_namespace(
    client: APIClient, parent_namespace: str, namespace_uuid: str
) -> bool:
    """
    Delete a namespace by UUID.

    Args:
        client: The APIClient instance to use for the request
        parent_namespace: The parent namespace containing the target namespace
        namespace_uuid: The UUID of the namespace to delete

    Returns:
        bool: True if deletion was successful, False otherwise

    Raises:
        requests.exceptions.HTTPError: For API-level errors
    """
    try:
        headers = client.default_headers
        res = client.delete(
            f"v1/namespaces/{parent_namespace}/namespaces/{namespace_uuid}",
            headers=headers,
        )
        return res.status_code == 200  # Endor's API returns 200 on successful deletion
    except Exception as e:
        logger.error(f"Error deleting namespace {namespace_uuid}: {e}", exc_info=True)
        return False


def update_namespace(
    client: APIClient,
    parent_namespace: str,
    namespace_uuid: str,
    payload: UpdateNamespacePayload,
) -> Optional[Namespace]:
    """
    Update an existing namespace.

    This function supports updating namespace metadata fields that are marked as
    mutable. Only the fields specified in the payload will be updated.

    MUTABLE FIELDS:
    - meta.description: Namespace description

    IMMUTABLE FIELDS (cannot be updated):
    - uuid: Unique identifier (set at creation)
    - meta.name: Namespace name (set at creation)
    - meta.create_time, meta.created_by: Creation metadata
    - meta.update_time, meta.updated_by: Auto-managed timestamps
    - meta.index_data: Index data (managed by API)
    - meta.kind: Resource kind (managed by API)
    - meta.version: Version (managed by API)

    Args:
        client: The APIClient instance to use for the request
        parent_namespace: The parent namespace containing the target namespace
        namespace_uuid: The UUID of the namespace to update
        payload: The UpdateNamespacePayload containing the updated namespace details

    Returns:
        Optional[Namespace]: The updated Namespace object, or None if update fails

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema

    Example:
        >>> payload = UpdateNamespacePayload(
        ...     meta=NamespaceMetaUpdate(description="Updated description")
        ... )
        >>> updated_namespace = update_namespace(client, parent, uuid, payload)
    """
    try:
        headers = client.default_headers
        headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

        logger.info(f"Updating namespace {namespace_uuid}")

        res = client.patch(
            f"v1/namespaces/{parent_namespace}/namespaces/{namespace_uuid}",
            headers=headers,
            data=payload.model_dump(),
        )
        data = res.json()
        return Namespace(**data)
    except Exception as e:
        logger.error(f"Error updating namespace {namespace_uuid}: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    # Note: To run this example, you need to be in the root of the project
    # and run as a module: python -m src.endor_sdk.resources.namespaces
    client = APIClient(max_retries=15, backoff_factor=1)

    # Get OpenAPI spec and store it in the tmp directory
    spec_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "tmp",
        "openapiv2.swagger.json",
    )
    try:
        client.get_openapi_spec(url=None, path=spec_path)
        logger.info(f"Successfully retrieved and stored OpenAPI spec at {spec_path}")
    except Exception as e:
        logger.error(f"Failed to retrieve OpenAPI spec: {e}")
        sys.exit(1)

    tenant_namespace = "endor-solutions-tgowan"

    # Create mock namespaces using Pydantic models
    mock_namespaces_to_create = [
        CreateNamespacePayload(
            meta=NamespaceMetaCreate(
                name=f"mock-namespace-{i}",
                description=f"Description for mock-namespace-{i}",
            )
        )
        for i in range(3)
    ]

    for payload in mock_namespaces_to_create:
        print(f"Creating namespace: {payload.meta.name}")
        created_ns = create_namespace(client, tenant_namespace, payload)
        if created_ns:
            print(f"  -> Created with UUID: {created_ns.uuid}")

    # List and delete the created namespaces
    print("\nListing all namespaces to find and delete mocks...")
    all_namespaces = list_namespaces(client, tenant_namespace)
    mock_names = {p.meta.name for p in mock_namespaces_to_create}

    for ns in all_namespaces:
        if ns.meta.name in mock_names:
            print(f"Deleting namespace: {ns.meta.name} (UUID: {ns.uuid})")
            success = delete_namespace(client, tenant_namespace, ns.uuid)
            if success:
                print("  -> Deleted successfully.")
            else:
                print("  -> Deletion failed.")
