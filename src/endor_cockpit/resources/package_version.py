"""
PackageVersion resource module for Endor Labs API.

This module provides CRUD operations for PackageVersion resources following the established
patterns from the base class implementation.
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


class PackageVersionMeta(BaseMeta):
    """PackageVersion metadata extending BaseMeta."""
    # PackageVersion-specific fields only (universal fields inherited from BaseMeta)
    pass


class PackageVersionSpec(BaseSpec):
    """PackageVersion specification extending BaseSpec."""
    # PackageVersion-specific spec fields based on Resource Guide example
    call_graph_available: bool = Field(..., description="Whether call graph analysis is available")
    ecosystem: str = Field(..., description="Package ecosystem (NPM, PyPI, Maven, etc.)")
    language: str = Field(..., description="Programming language")
    package_name: str = Field(..., description="Package name")
    project_uuid: str = Field(..., description="UUID of the project this package belongs to")
    relative_path: str = Field(..., description="Relative path to the package")
    release_timestamp: str = Field(..., description="Package release timestamp")
    resolution_errors: Optional[dict] = Field(None, description="Resolution errors")
    resolved_dependencies: Optional[dict] = Field(None, description="Resolved dependencies")
    source_code_reference: Optional[dict] = Field(None, description="Source code reference")
    unresolved_dependencies: Optional[List[dict]] = Field(None, description="Unresolved dependencies")


class PackageVersion(BaseResource):
    """PackageVersion resource model extending BaseResource."""
    # PackageVersion-specific fields (universal fields inherited from BaseResource)
    spec: PackageVersionSpec = Field(..., description="PackageVersion specification")  # type: ignore
    # Conditional attributes from Resource Guide example
    context: Optional[dict] = Field(None, description="Contextual information", alias="context")
    processing_status: Optional[dict] = Field(None, description="Processing status information", alias="processing_status")

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data):
        # Convert spec to PackageVersionSpec if it's a dict
        if 'spec' in data and isinstance(data['spec'], dict):
            data['spec'] = PackageVersionSpec(**data['spec'])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "call_graph_available", "ecosystem", "language", "package_name",
                "project_uuid", "relative_path", "release_timestamp", "resolution_errors",
                "resolved_dependencies", "source_code_reference", "unresolved_dependencies"
            }
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v


class UpdatePackageVersionPayload(BaseModel):
    """Payload for updating PackageVersion resources."""
    meta: Optional[dict] = None
    spec: Optional[PackageVersionSpec] = None
    update_mask: Optional[List[str]] = None


def _get_package_version_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for PackageVersion."""
    return BaseResourceOperations(client, "package-versions", PackageVersion)


def list_package_versions(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
    **kwargs
) -> List[PackageVersion]:
    """List package versions with advanced filtering and pagination."""
    ops = _get_package_version_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)  # type: ignore


def get_package_version(
    client: APIClient,
    tenant_meta_namespace: str,
    package_version_uuid: str
) -> Optional[PackageVersion]:
    """Get specific package version by UUID."""
    ops = _get_package_version_ops(client)
    return ops.get(tenant_meta_namespace, package_version_uuid)  # type: ignore


def update_package_version(
    client: APIClient,
    tenant_meta_namespace: str,
    package_version_uuid: str,
    payload: UpdatePackageVersionPayload,
    update_mask: List[str]
) -> Optional[PackageVersion]:
    """Update package version using base class operations."""
    ops = _get_package_version_ops(client)
    return ops.update(tenant_meta_namespace, package_version_uuid, payload, update_mask)  # type: ignore
