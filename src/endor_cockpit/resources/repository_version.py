"""
This module provides a resource-oriented interface for managing Endor Labs
repository versions. It implements CRUD operations following REST principles and
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


# Pydantic Models for RepositoryVersion data based on actual API response
class TenantMeta(BaseModel):
    """Tenant metadata for repository version resources."""
    namespace: str = Field(..., description="Canonical namespace name")


class RepositoryVersionMeta(BaseModel):
    """Repository version metadata."""
    name: str = Field(..., description="Repository version name (branch/tag)")
    description: Optional[str] = Field(
        None, description="Repository version description"
    )
    create_time: Optional[str] = Field(None, description="Creation timestamp")
    created_by: Optional[str] = Field(None, description="Creator identifier")
    update_time: Optional[str] = Field(None, description="Last update timestamp")
    updated_by: Optional[str] = Field(None, description="Last updater identifier")
    tags: Optional[List[str]] = Field(None, description="Repository version tags")

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
                    v, model_fields, f"RepositoryVersionMeta.{info.field_name}"
                )
        return v


class RepositoryVersionSpec(BaseModel):
    """Repository version specification."""
    repository_uuid: str = Field(..., description="Parent repository UUID")
    commit_sha: Optional[str] = Field(None, description="Git commit SHA")
    branch: Optional[str] = Field(None, description="Git branch name")
    tag: Optional[str] = Field(None, description="Git tag name")
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
                'repository_uuid', 'commit_sha', 'branch', 'tag', 'source_code_info',
                'notification'
            }

            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields, f"RepositoryVersionSpec.{info.field_name}"
                )
        return v


class RepositoryVersion(BaseModel):
    """Repository version resource model."""
    model_config = ConfigDict(extra='ignore')

    uuid: str = Field(..., description="Unique identifier for the repository version")
    meta: RepositoryVersionMeta = Field(..., description="Repository version metadata")
    spec: RepositoryVersionSpec = Field(
        ..., description="Repository version specification"
    )
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
                    v, model_fields, f"RepositoryVersion.{info.field_name}"
                )
        return v


# Payload models for CRUD operations
class CreateRepositoryVersionPayload(BaseModel):
    """Payload for creating a repository version."""
    meta: RepositoryVersionMeta = Field(..., description="Repository version metadata")
    spec: RepositoryVersionSpec = Field(
        ..., description="Repository version specification"
    )


class UpdateRepositoryVersionPayload(BaseModel):
    """Payload for updating a repository version."""
    meta: Optional[RepositoryVersionMeta] = Field(
        None, description="Repository version metadata"
    )
    spec: Optional[RepositoryVersionSpec] = Field(
        None, description="Repository version specification"
    )


# CRUD Operations
def list_repository_versions(
    client: APIClient, tenant_meta_namespace: str, repository_uuid: str
) -> List[RepositoryVersion]:
    """List all repository versions for a specific repository."""
    try:
        headers = client.default_headers
        res = client.get(
            f"v1/namespaces/{tenant_meta_namespace}/repositories/{repository_uuid}/versions",
            headers=headers,
        )
        data = res.json()
        versions_data = data.get("list", {}).get("objects", [])
        return [RepositoryVersion(**version) for version in versions_data]
    except Exception as e:
        logger.error(f"Error listing repository versions: {e}", exc_info=True)
        return []


def get_repository_version(
    client: APIClient, tenant_meta_namespace: str, repository_uuid: str,
    version_uuid: str
) -> Optional[RepositoryVersion]:
    """Get a specific repository version by UUID."""
    try:
        headers = client.default_headers
        res = client.get(
            f"v1/namespaces/{tenant_meta_namespace}/repositories/{repository_uuid}/versions/{version_uuid}",
            headers=headers,
        )
        data = res.json()
        return RepositoryVersion(**data)
    except Exception as e:
        logger.error(
            f"Error getting repository version {version_uuid}: {e}",
            exc_info=True,
        )
        return None


def create_repository_version(
    client: APIClient, tenant_meta_namespace: str, repository_uuid: str,
    payload: CreateRepositoryVersionPayload
) -> Optional[RepositoryVersion]:
    """Create a new repository version."""
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

        res = client.post(
            f"v1/namespaces/{tenant_meta_namespace}/repositories/{repository_uuid}/versions",
            headers=headers, data=request_data,
        )
        data = res.json()
        return RepositoryVersion(**data)
    except Exception as e:
        logger.error(f"Error creating repository version: {e}", exc_info=True)
        return None


def update_repository_version(
    client: APIClient,
    tenant_meta_namespace: str,
    repository_uuid: str,
    version_uuid: str,
    payload: UpdateRepositoryVersionPayload,
    update_mask: Optional[str] = None,
) -> Optional[RepositoryVersion]:
    """Update an existing repository version using partial updates."""
    try:
        headers = client.default_headers
        headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

        # Get the current repository version to include required fields
        current_version = get_repository_version(
            client, tenant_meta_namespace, repository_uuid, version_uuid
        )
        if not current_version:
            logger.error(f"Repository version {version_uuid} not found")
            return None

        # Build request data with correct structure
        request_data = {
            "object": {
                "uuid": version_uuid,
                "tenant_meta": current_version.tenant_meta.model_dump(),
                "meta": {
                    "name": current_version.meta.name,  # Required field
                    **(
                        payload.meta.model_dump(exclude_none=True)
                        if payload.meta else {}
                    ),
                },
                "spec": {
                    **current_version.spec.model_dump(),  # Include all
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

        logger.info(
            f"Updating repository version {version_uuid} with mask: {update_mask}"
        )

        res = client.patch(
            f"v1/namespaces/{tenant_meta_namespace}/repositories/{repository_uuid}/versions",
            headers=headers, data=request_data,
        )

        if res.status_code == 200:
            data = res.json()
            return RepositoryVersion(**data)
        else:
            logger.error(
                f"Failed to update repository version {version_uuid}: "
                f"{res.status_code} - {res.text}"
            )
            return None
    except Exception as e:
        logger.error(
            f"Error updating repository version {version_uuid}: {e}",
            exc_info=True,
        )
        return None


def delete_repository_version(
    client: APIClient, tenant_meta_namespace: str, repository_uuid: str,
    version_uuid: str
) -> bool:
    """Delete a repository version."""
    try:
        headers = client.default_headers
        res = client.delete(
            f"v1/namespaces/{tenant_meta_namespace}/repositories/{repository_uuid}/versions/{version_uuid}",
            headers=headers,
        )
        return res.status_code == 200
    except Exception as e:
        logger.error(
            f"Error deleting repository version {version_uuid}: {e}",
            exc_info=True,
        )
        return False
