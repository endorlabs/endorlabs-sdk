"""
This module provides a resource-oriented interface for managing Endor Labs
repositories. It implements CRUD operations following REST principles and
provides type-safe data models.
"""

import logging
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..utils import SchemaDriftDetector

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


# Pydantic Models for Repository data based on actual API response
class TenantMeta(BaseModel):
    """Tenant metadata for repository resources."""
    namespace: str = Field(..., description="Canonical namespace name")


class RepositoryMeta(BaseModel):
    """Repository metadata."""
    name: str = Field(..., description="Repository name (same as Project)")
    description: Optional[str] = Field(None, description="Repository description")
    create_time: Optional[str] = Field(None, description="Creation timestamp")
    created_by: Optional[str] = Field(None, description="Creator identifier")
    update_time: Optional[str] = Field(None, description="Last update timestamp")
    updated_by: Optional[str] = Field(None, description="Last updater identifier")
    tags: Optional[List[str]] = Field(None, description="Repository tags")

    # Schema drift fields
    parent_uuid: Optional[str] = Field(None, description="Parent resource UUID")
    parent_kind: Optional[str] = Field(None, description="Parent resource kind")
    upsert_time: Optional[str] = Field(None, description="Upsert timestamp")
    references: Optional[dict] = Field(None, description="Resource references")

    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            model_fields = {
                'create_time', 'update_time', 'name', 'description', 'created_by',
                'updated_by', 'tags', 'parent_uuid', 'parent_kind', 'upsert_time',
                'references'
            }

            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields, f"RepositoryMeta.{info.field_name}"
                )
        return v


class RepositorySpec(BaseModel):
    """Repository specification."""
    project_uuid: str = Field(..., description="Associated project UUID")
    source_code_info: Optional[dict] = Field(
        None, description="Source code information"
    )

    # Schema drift fields
    notification: Optional[dict] = Field(None, description="Notification configuration")

    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            model_fields = {
                'project_uuid', 'source_code_info', 'notification'
            }

            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields, f"RepositorySpec.{info.field_name}"
                )
        return v


class Repository(BaseModel):
    """Repository resource model."""
    model_config = ConfigDict(extra='ignore')

    uuid: str = Field(..., description="Unique identifier for the repository")
    meta: RepositoryMeta = Field(..., description="Repository metadata")
    spec: RepositorySpec = Field(..., description="Repository specification")
    tenant_meta: TenantMeta = Field(..., description="Tenant metadata")

    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            model_fields = {
                'uuid', 'meta', 'spec', 'tenant_meta'
            }

            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields, f"Repository.{info.field_name}"
                )
        return v


# Payload models for CRUD operations
class CreateRepositoryPayload(BaseModel):
    """Payload for creating a repository."""
    meta: RepositoryMeta = Field(..., description="Repository metadata")
    spec: RepositorySpec = Field(..., description="Repository specification")


class UpdateRepositoryPayload(BaseModel):
    """Payload for updating a repository."""
    meta: Optional[RepositoryMeta] = Field(None, description="Repository metadata")
    spec: Optional[RepositorySpec] = Field(None, description="Repository specification")


# CRUD Operations
def list_repositories(
    client: APIClient, tenant_meta_namespace: str
) -> List[Repository]:
    """List all repositories in the specified namespace."""
    try:
        headers = client.default_headers
        res = client.get(
            f"v1/namespaces/{tenant_meta_namespace}/repositories",
            headers=headers,
        )
        data = res.json()
        repositories_data = data.get("list", {}).get("objects", [])
        return [Repository(**repo) for repo in repositories_data]
    except Exception as e:
        logger.error(f"Error listing repositories: {e}", exc_info=True)
        return []


def get_repository(
    client: APIClient, tenant_meta_namespace: str, repository_uuid: str
) -> Optional[Repository]:
    """Get a specific repository by UUID."""
    try:
        headers = client.default_headers
        res = client.get(
            f"v1/namespaces/{tenant_meta_namespace}/repositories/{repository_uuid}",
            headers=headers,
        )
        data = res.json()
        return Repository(**data)
    except Exception as e:
        logger.error(f"Error getting repository {repository_uuid}: {e}", exc_info=True)
        return None


def create_repository(
    client: APIClient, tenant_meta_namespace: str, payload: CreateRepositoryPayload
) -> Optional[Repository]:
    """Create a new repository."""
    try:
        headers = client.default_headers
        headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

        request_data = {
            "object": {
                "tenant_meta": {"namespace": tenant_meta_namespace},
                **payload.model_dump()
            }
        }

        res = client.post(f"v1/namespaces/{tenant_meta_namespace}/repositories",
                         headers=headers, data=request_data)
        data = res.json()
        return Repository(**data)
    except Exception as e:
        logger.error(f"Error creating repository: {e}", exc_info=True)
        return None


def update_repository(
    client: APIClient,
    tenant_meta_namespace: str,
    repository_uuid: str,
    payload: UpdateRepositoryPayload,
    update_mask: Optional[str] = None,
) -> Optional[Repository]:
    """Update an existing repository using partial updates."""
    try:
        headers = client.default_headers
        headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

        # Get the current repository to include required fields
        current_repository = get_repository(
            client, tenant_meta_namespace, repository_uuid
        )
        if not current_repository:
            logger.error(f"Repository {repository_uuid} not found")
            return None

        # Build request data with correct structure
        request_data = {
            "object": {
                "uuid": repository_uuid,
                "tenant_meta": current_repository.tenant_meta.model_dump(),
                "meta": {
                    "name": current_repository.meta.name,  # Required field
                    **(
                        payload.meta.model_dump(exclude_none=True)
                        if payload.meta else {}
                    ),
                },
                "spec": {
                    **current_repository.spec.model_dump(),  # Include all
                    # existing spec fields
                    **(
                        payload.spec.model_dump(exclude_none=True)
                        if payload.spec else {}
                    ),
                },
            }
        }

        if update_mask:
            request_data["request"] = {"update_mask": update_mask}

        logger.info(f"Updating repository {repository_uuid} with mask: {update_mask}")

        res = client.patch(f"v1/namespaces/{tenant_meta_namespace}/repositories",
                          headers=headers, data=request_data)

        if res.status_code == 200:
            data = res.json()
            return Repository(**data)
        else:
            logger.error(
                f"Failed to update repository {repository_uuid}: "
                f"{res.status_code} - {res.text}"
            )
            return None
    except Exception as e:
        logger.error(f"Error updating repository {repository_uuid}: {e}", exc_info=True)
        return None


def delete_repository(
    client: APIClient, tenant_meta_namespace: str, repository_uuid: str
) -> bool:
    """Delete a repository."""
    try:
        headers = client.default_headers
        res = client.delete(
            f"v1/namespaces/{tenant_meta_namespace}/repositories/{repository_uuid}",
            headers=headers,
        )
        return res.status_code == 200
    except Exception as e:
        logger.error(f"Error deleting repository {repository_uuid}: {e}", exc_info=True)
        return False
