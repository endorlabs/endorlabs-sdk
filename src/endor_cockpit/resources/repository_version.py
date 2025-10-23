"""
RepositoryVersion resource module for Endor Labs API.

This module provides CRUD operations for RepositoryVersion resources following the
established patterns from the base class implementation.
"""

import logging
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..models.base import BaseMeta, BaseResource, BaseResourceOperations, BaseSpec
from ..types import ListParameters

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


class RepositoryVersionMeta(BaseMeta):
    """RepositoryVersion metadata extending BaseMeta."""

    # RepositoryVersion-specific fields only (universal fields inherited from BaseMeta)
    pass


class VersionInfo(BaseModel):
    """Version information for RepositoryVersion."""

    ref: str = Field(..., description="Version reference (branch, tag, or commit)")
    sha: str = Field(..., description="Commit SHA hash")


class RepositoryVersionSpec(BaseSpec):
    """RepositoryVersion specification extending BaseSpec."""

    # RepositoryVersion-specific spec fields based on actual API structure
    version: VersionInfo = Field(
        ..., description="Version information with ref and sha"
    )


class RepositoryVersion(BaseResource):
    """RepositoryVersion resource model extending BaseResource."""

    # RepositoryVersion-specific fields (universal fields inherited from BaseResource)
    spec: RepositoryVersionSpec = Field(
        ..., description="RepositoryVersion specification"
    )  # type: ignore
    # Conditional attributes from Resource Guide example
    context: Optional[dict] = Field(
        None, description="Contextual information", alias="context"
    )
    scan_object: Optional[dict] = Field(
        None, description="Scan object information", alias="scan_object"
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data):
        # Convert spec to RepositoryVersionSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = RepositoryVersionSpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {"version"}
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v


def _get_repository_version_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for RepositoryVersion."""
    return BaseResourceOperations(client, "repository-versions", RepositoryVersion)


def list_repository_versions(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
    **kwargs,
) -> List[RepositoryVersion]:
    """List repository versions with advanced filtering and pagination."""
    ops = _get_repository_version_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)  # type: ignore


def get_repository_version(
    client: APIClient, tenant_meta_namespace: str, repository_version_uuid: str
) -> Optional[RepositoryVersion]:
    """Get specific repository version by UUID."""
    ops = _get_repository_version_ops(client)
    return ops.get(tenant_meta_namespace, repository_version_uuid)  # type: ignore
