"""
This module provides a resource-oriented interface for managing Endor Labs
package versions. It implements CRUD operations following REST principles and
provides type-safe data models.
"""

import logging
import os
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..utils import SchemaDriftDetector

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


# Pydantic Models for PackageVersion data based on actual API response
class TenantMeta(BaseModel):
    """Tenant metadata for package version resources."""
    namespace: str = Field(..., description="Canonical namespace name")


class PackageVersionMeta(BaseModel):
    """Package version metadata."""
    name: str = Field(..., description="Package version name")
    description: Optional[str] = Field(None, description="Package version description")
    create_time: Optional[str] = Field(None, description="Creation timestamp")
    created_by: Optional[str] = Field(None, description="Creator identifier")
    update_time: Optional[str] = Field(None, description="Last update timestamp")
    updated_by: Optional[str] = Field(None, description="Last updater identifier")
    tags: Optional[List[str]] = Field(None, description="Package version tags")
    
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
                'updated_by', 'tags', 'parent_uuid', 'parent_kind', 'upsert_time', 'references'
            }
            
            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields, f"PackageVersionMeta.{info.field_name}"
                )
        return v


class PackageVersionSpec(BaseModel):
    """Package version specification."""
    package_name: str = Field(..., description="Package name")
    version: str = Field(..., description="Package version")
    ecosystem: Optional[str] = Field(None, description="Package ecosystem (NPM, PyPI, etc.)")
    repository_version_uuid: Optional[str] = Field(None, description="Associated repository version UUID")
    dependency_info: Optional[dict] = Field(None, description="Dependency information")
    
    # Schema drift fields
    notification: Optional[dict] = Field(None, description="Notification configuration")

    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            model_fields = {
                'package_name', 'version', 'ecosystem', 'repository_version_uuid', 'dependency_info', 'notification'
            }
            
            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields, f"PackageVersionSpec.{info.field_name}"
                )
        return v


class PackageVersion(BaseModel):
    """Package version resource model."""
    model_config = ConfigDict(extra='ignore')
    
    uuid: str = Field(..., description="Unique identifier for the package version")
    meta: PackageVersionMeta = Field(..., description="Package version metadata")
    spec: PackageVersionSpec = Field(..., description="Package version specification")
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
                    v, model_fields, f"PackageVersion.{info.field_name}"
                )
        return v


# Payload models for CRUD operations
class CreatePackageVersionPayload(BaseModel):
    """Payload for creating a package version."""
    meta: PackageVersionMeta = Field(..., description="Package version metadata")
    spec: PackageVersionSpec = Field(..., description="Package version specification")


class UpdatePackageVersionPayload(BaseModel):
    """Payload for updating a package version."""
    meta: Optional[PackageVersionMeta] = Field(None, description="Package version metadata")
    spec: Optional[PackageVersionSpec] = Field(None, description="Package version specification")


# CRUD Operations
def list_package_versions(
    client: APIClient, tenant_meta_namespace: str
) -> List[PackageVersion]:
    """List all package versions in the specified namespace."""
    try:
        headers = client.default_headers
        res = client.get(f"v1/namespaces/{tenant_meta_namespace}/package-versions", headers=headers)
        data = res.json()
        package_versions_data = data.get("list", {}).get("objects", [])
        return [PackageVersion(**pv) for pv in package_versions_data]
    except Exception as e:
        logger.error(f"Error listing package versions: {e}", exc_info=True)
        return []


def get_package_version(
    client: APIClient, tenant_meta_namespace: str, package_version_uuid: str
) -> Optional[PackageVersion]:
    """Get a specific package version by UUID."""
    try:
        headers = client.default_headers
        res = client.get(f"v1/namespaces/{tenant_meta_namespace}/package-versions/{package_version_uuid}", headers=headers)
        data = res.json()
        return PackageVersion(**data)
    except Exception as e:
        logger.error(f"Error getting package version {package_version_uuid}: {e}", exc_info=True)
        return None


def create_package_version(
    client: APIClient, tenant_meta_namespace: str, payload: CreatePackageVersionPayload
) -> Optional[PackageVersion]:
    """Create a new package version."""
    try:
        headers = client.default_headers
        headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        
        request_data = {
            "object": {
                "tenant_meta": {"namespace": tenant_meta_namespace},
                **payload.model_dump()
            }
        }
        
        res = client.post(f"v1/namespaces/{tenant_meta_namespace}/package-versions", 
                         headers=headers, data=request_data)
        data = res.json()
        return PackageVersion(**data)
    except Exception as e:
        logger.error(f"Error creating package version: {e}", exc_info=True)
        return None


def update_package_version(
    client: APIClient,
    tenant_meta_namespace: str,
    package_version_uuid: str,
    payload: UpdatePackageVersionPayload,
    update_mask: Optional[str] = None,
) -> Optional[PackageVersion]:
    """Update an existing package version using partial updates."""
    try:
        headers = client.default_headers
        headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        
        # Get the current package version to include required fields
        current_package_version = get_package_version(client, tenant_meta_namespace, package_version_uuid)
        if not current_package_version:
            logger.error(f"Package version {package_version_uuid} not found")
            return None
        
        # Build request data with correct structure
        request_data = {
            "object": {
                "uuid": package_version_uuid,
                "tenant_meta": current_package_version.tenant_meta.model_dump(),
                "meta": {
                    "name": current_package_version.meta.name,  # Required field
                    **(payload.meta.model_dump(exclude_none=True) if payload.meta else {}),
                },
                "spec": {
                    **current_package_version.spec.model_dump(),  # Include all existing spec fields
                    **(payload.spec.model_dump(exclude_none=True) if payload.spec else {}),
                },
            }
        }
        
        if update_mask:
            request_data["request"] = {"update_mask": update_mask}
        
        logger.info(f"Updating package version {package_version_uuid} with mask: {update_mask}")
        
        res = client.patch(f"v1/namespaces/{tenant_meta_namespace}/package-versions", 
                          headers=headers, data=request_data)
        
        if res.status_code == 200:
            data = res.json()
            return PackageVersion(**data)
        else:
            logger.error(f"Failed to update package version {package_version_uuid}: {res.status_code} - {res.text}")
            return None
    except Exception as e:
        logger.error(f"Error updating package version {package_version_uuid}: {e}", exc_info=True)
        return None


def delete_package_version(
    client: APIClient, tenant_meta_namespace: str, package_version_uuid: str
) -> bool:
    """Delete a package version."""
    try:
        headers = client.default_headers
        res = client.delete(f"v1/namespaces/{tenant_meta_namespace}/package-versions/{package_version_uuid}", headers=headers)
        return res.status_code == 200
    except Exception as e:
        logger.error(f"Error deleting package version {package_version_uuid}: {e}", exc_info=True)
        return False
