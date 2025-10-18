"""
This module provides a resource-oriented interface for managing Endor Labs
namespaces. It implements CRUD operations following REST principles and
provides type-safe data models.
"""

import logging
import os
import sys
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))

# Pydantic Models for Namespace data with OpenAPI validation
class NamespaceMeta(BaseModel):
    """
    Metadata for an Endor Labs namespace.

    Attributes:
        name: The name of the namespace (1-255 characters)
        description: A description of the namespace's purpose (can be empty)
        created_at: Timestamp when the namespace was created
        updated_at: Timestamp when the namespace was last updated
    """
    name: str = Field(
        ..., min_length=1, max_length=255, description="The name of the namespace"
    )
    description: str = Field("", description="Description of the namespace's purpose")
    created_at: Optional[datetime] = Field(
        None, description="Timestamp when the namespace was created"
    )
    updated_at: Optional[datetime] = Field(
        None, description="Timestamp when the namespace was last updated"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that the name is not empty or just whitespace."""
        if not v.strip():
            raise ValueError('name cannot be empty')
        return v

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
    """
    meta: NamespaceMetaUpdate = Field(
        ..., description="Updated metadata for the namespace"
    )

class Namespace(BaseModel):
    """
    An Endor Labs namespace entity.

    Attributes:
        uuid: Unique identifier for the namespace
        meta: Metadata associated with the namespace
    """
    uuid: str = Field(..., description="Unique identifier for the namespace")
    meta: NamespaceMeta = Field(
        ..., description="Metadata associated with the namespace"
    )

    @field_validator('uuid')
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Validate that the UUID is not empty or just whitespace."""
        if not v.strip():
            raise ValueError('uuid cannot be empty')
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
                    "description": "An example namespace"
                }
            }
        }
    )


def list_namespaces(client: APIClient, tenant_namespace: str) -> List[Namespace]:
    """
    List all namespaces under the specified tenant namespace.

    Args:
        client: The APIClient instance to use for the request
        tenant_namespace: The parent namespace to list namespaces from

    Returns:
        List[Namespace]: A list of Namespace objects. Empty list if error occurs.

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    try:
        headers = client.default_headers
        res = client.get(
            f'v1/namespaces/{tenant_namespace}/namespaces', headers=headers
        )
        data = res.json().get('list', {}).get("objects", [])
        return [Namespace(**item) for item in data]
    except Exception as e:
        logger.error(f"Error listing namespaces: {e}", exc_info=True)
        return []

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
        headers.update({'Accept': 'application/json'})
        res = client.post(
            f'v1/namespaces/{parent_namespace}/namespaces',
            headers=headers,
            data=payload.model_dump()
        )
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
            f'v1/namespaces/{parent_namespace}/namespaces/{namespace_uuid}',
            headers=headers
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
            f'v1/namespaces/{parent_namespace}/namespaces/{namespace_uuid}',
            headers=headers
        )
        return res.status_code == 200  # Endor's API returns 200 on successful deletion
    except Exception as e:
        logger.error(f"Error deleting namespace {namespace_uuid}: {e}", exc_info=True)
        return False

def update_namespace(
    client: APIClient,
    parent_namespace: str,
    namespace_uuid: str,
    payload: UpdateNamespacePayload
) -> Optional[Namespace]:
    """
    Update an existing namespace.

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
    """
    try:
        headers = client.default_headers
        headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        res = client.patch(
            f'v1/namespaces/{parent_namespace}/namespaces/{namespace_uuid}',
            headers=headers,
            data=payload.model_dump()
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
        'tmp',
        'openapiv2.swagger.json'
    )
    try:
        client.get_openapi_spec(url=None, path=spec_path)
        logger.info(f"Successfully retrieved and stored OpenAPI spec at {spec_path}")
    except Exception as e:
        logger.error(f"Failed to retrieve OpenAPI spec: {e}")
        sys.exit(1)

    tenant_namespace = 'endor-solutions-tgowan'

    # Create mock namespaces using Pydantic models
    mock_namespaces_to_create = [
        CreateNamespacePayload(
            meta=NamespaceMetaCreate(
                name=f"mock-namespace-{i}",
                description=f"Description for mock-namespace-{i}"
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
