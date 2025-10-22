"""
Repository resource module for Endor Labs API.

This module provides CRUD operations for Repository resources following the established
patterns from the base class implementation.
"""

import logging
from typing import List, Optional

from pydantic import ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..models.base import BaseMeta, BaseResource, BaseResourceOperations, BaseSpec
from ..types import ListParameters

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


class RepositoryMeta(BaseMeta):
    """Repository metadata extending BaseMeta."""
    # Repository-specific fields only (universal fields inherited from BaseMeta)
    pass


class RepositorySpec(BaseSpec):
    """Repository specification extending BaseSpec."""
    # Repository-specific spec fields based on Resource Guide example
    create_time: str = Field(..., description="Repository creation timestamp")
    default_branch: str = Field(..., description="Default branch name")
    http_clone_url: str = Field(..., description="HTTP clone URL")
    platform_source: str = Field(..., description="Platform source (GITHUB, GITLAB, etc.)")


class Repository(BaseResource):
    """Repository resource model extending BaseResource."""
    # Repository-specific fields (universal fields inherited from BaseResource)
    spec: RepositorySpec = Field(..., description="Repository specification")  # type: ignore
    # Conditional attributes from Resource Guide example
    ingested_object: Optional[dict] = Field(None, description="Ingested object information", alias="ingested_object")

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data):
        # Convert spec to RepositorySpec if it's a dict
        if 'spec' in data and isinstance(data['spec'], dict):
            data['spec'] = RepositorySpec(**data['spec'])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "create_time", "default_branch", "http_clone_url", "platform_source"
            }
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v


def _get_repository_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for Repository."""
    return BaseResourceOperations(client, "repositories", Repository)


def list_repositories(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
    **kwargs
) -> List[Repository]:
    """List repositories with advanced filtering and pagination."""
    ops = _get_repository_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)  # type: ignore


def get_repository(
    client: APIClient,
    tenant_meta_namespace: str,
    repository_uuid: str
) -> Optional[Repository]:
    """Get specific repository by UUID."""
    ops = _get_repository_ops(client)
    return ops.get(tenant_meta_namespace, repository_uuid)  # type: ignore
