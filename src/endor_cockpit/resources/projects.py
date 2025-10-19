"""
This module provides a resource-oriented interface for managing Endor Labs
projects. It implements CRUD operations following REST principles and
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


class SchemaDriftDetector:
    """Detects and logs API schema drift for unknown fields."""
    
    @staticmethod
    def log_unknown_fields(model_name: str, unknown_fields: dict, context: str = ""):
        """Log unknown fields as warnings for schema drift detection."""
        if unknown_fields:
            field_list = ", ".join(unknown_fields.keys())
            logger.warning(
                f"API Schema Drift Detected in {model_name}: "
                f"Unknown fields found: {field_list}. "
                f"Context: {context}. "
                f"This may indicate API evolution or missing model fields."
            )
            # Log detailed field information for debugging
            for field, value in unknown_fields.items():
                logger.debug(f"Unknown field '{field}': {type(value).__name__} = {repr(value)[:100]}")
    
    @staticmethod
    def extract_unknown_fields(data: dict, model_fields: set, model_name: str) -> dict:
        """Extract unknown fields from data and log them."""
        unknown_fields = {k: v for k, v in data.items() if k not in model_fields}
        if unknown_fields:
            SchemaDriftDetector.log_unknown_fields(model_name, unknown_fields)
        return unknown_fields


# Pydantic Models for Project data based on actual API response
class IndexData(BaseModel):
    """Index data for a project."""
    data: List[str]
    tenant: str

class ProjectMeta(BaseModel):
    """
    Metadata for an Endor Labs project based on actual API response.

    Attributes:
        create_time: When the project was created
        created_by: Who created the project
        index_data: Index data for the project
        kind: The kind of resource (Project)
        name: The name of the project
        update_time: When the project was last updated
        updated_by: Who last updated the project
        version: The version of the project
        description: Optional description (can be None)
    """
    create_time: str
    created_by: str
    index_data: IndexData
    kind: str
    name: str
    update_time: str
    updated_by: str
    version: str
    description: Optional[str] = None
    upsert_time: Optional[str] = None
    tags: Optional[List[str]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that the name is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("name cannot be empty")
        return v


class ProjectMetaCreate(BaseModel):
    """
    Metadata for creating an Endor Labs project.
    """

    name: str = Field(
        ..., min_length=1, max_length=255, description="The name of the project"
    )
    description: str = Field(
        ..., min_length=1, description="Description of the project's purpose"
    )
    repository_url: str = Field("", description="Repository URL for the project")
    language: str = Field("", description="Primary programming language")
    framework: str = Field("", description="Framework used in the project")


class ProjectMetaUpdate(BaseModel):
    """
    Metadata for updating an Endor Labs project.
    """

    description: Optional[str] = Field(
        None, description="Updated description of the project's purpose"
    )
    repository_url: Optional[str] = Field(
        None, description="Updated repository URL for the project"
    )
    language: Optional[str] = Field(
        None, description="Updated primary programming language"
    )
    framework: Optional[str] = Field(
        None, description="Updated framework used in the project"
    )
    tags: Optional[List[str]] = Field(
        None, description="Updated tags for the project"
    )


class UpdateProjectPayload(BaseModel):
    """
    Payload for updating an Endor Labs project.
    """

    meta: ProjectMetaUpdate = Field(
        ..., description="Updated metadata for the project"
    )


class GitInfo(BaseModel):
    """Git information for a project."""
    full_name: str
    git_clone_url: str
    http_clone_url: str
    organization: str
    path: str
    web_url: str

class ProjectSpec(BaseModel):
    """Project specification."""
    git: GitInfo
    internal_reference_key: str
    platform_source: str

class ProcessingStatus(BaseModel):
    """Processing status for a project."""
    disable_automated_scan: bool
    scan_state: str
    scan_time: str

class TenantMeta(BaseModel):
    """Tenant metadata."""
    namespace: str

class Project(BaseModel):
    """
    An Endor Labs project entity based on actual API response.

    Attributes:
        meta: Project metadata
        processing_status: Processing status information
        spec: Project specification including git info
        tenant_meta: Tenant metadata including namespace
        uuid: Unique identifier for the project
    """
    meta: ProjectMeta
    processing_status: ProcessingStatus
    spec: ProjectSpec
    tenant_meta: TenantMeta
    uuid: str
    
    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            # Define expected fields for each model
            model_fields = {
                'meta': {
                    'create_time', 'created_by', 'index_data', 'kind', 'name', 'update_time',
                    'updated_by', 'version', 'description', 'parent_uuid', 'parent_kind',
                    'tags', 'annotations', 'references', 'upsert_time'
                },
                'processing_status': {
                    'scan_state', 'scan_time', 'scan_error', 'scan_progress', 'scan_duration',
                    'last_scan_time', 'next_scan_time', 'scan_frequency', 'scan_enabled',
                    'analytic_time', 'queue_time', 'disable_automated_scan', 'metadata'
                },
                'spec': {
                    'git_info', 'language', 'framework', 'repository_url', 'branch', 'commit_hash',
                    'scan_config', 'policy_config', 'notification_config', 'integration_config',
                    'platform_source', 'internal_reference_key', 'git', 'ingestion_token',
                    'toolchain_profile_uuid', 'scan_profile_uuid'
                },
                'tenant_meta': {
                    'namespace', 'tenant_id', 'tenant_name'
                }
            }
            
            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, 
                    model_fields[info.field_name], 
                    f"Project.{info.field_name}"
                )
        
        return v

    @field_validator("uuid")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Validate that the UUID is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("uuid cannot be empty")
        return v


class CreateProjectPayload(BaseModel):
    """
    Payload for creating a new project.

    Attributes:
        meta: Metadata for the new project
        namespace_uuid: UUID of the parent namespace
    """

    meta: ProjectMetaCreate = Field(..., description="Metadata for the new project")
    namespace_uuid: str = Field(
        ..., description="UUID of the parent namespace"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "meta": {
                    "name": "example-project",
                    "description": "An example project",
                    "repository_url": "https://github.com/owner/repo",
                    "language": "Python",
                    "framework": "FastAPI"
                },
                "namespace_uuid": "namespace-uuid-here"
            }
        }
    )


def list_projects(client: APIClient, tenant_meta_namespace: str) -> List[Project]:
    """
    List all projects in the specified namespace.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name (e.g., 'endor-solutions-tgowan.cockpit')

    Returns:
        List[Project]: A list of Project objects. Empty list if error occurs.

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    try:
        headers = client.default_headers
        res = client.get(
            f"v1/namespaces/{tenant_meta_namespace}/projects", headers=headers
        )
        data = res.json()
        # Handle the actual API response structure: list.objects
        projects_data = data.get("list", {}).get("objects", [])
        return [Project(**item) for item in projects_data]
    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        return []


def get_project(client: APIClient, tenant_meta_namespace: str, project_uuid: str) -> Optional[Project]:
    """
    Retrieve a specific project by UUID.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name (e.g., 'endor-solutions-tgowan.cockpit')
        project_uuid: The UUID of the project to retrieve

    Returns:
        Optional[Project]: The requested Project object, or None if not found

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    try:
        headers = client.default_headers
        res = client.get(
            f"v1/namespaces/{tenant_meta_namespace}/projects/{project_uuid}",
            headers=headers,
        )
        data = res.json()
        return Project(**data)
    except Exception as e:
        logger.error(f"Error retrieving project {project_uuid}: {e}", exc_info=True)
        return None


def create_project(
    client: APIClient, tenant_meta_namespace: str, payload: CreateProjectPayload
) -> Optional[Project]:
    """
    Create a new project in the specified namespace.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name (e.g., 'endor-solutions-tgowan.cockpit')
        payload: The CreateProjectPayload containing the new project details

    Returns:
        Optional[Project]: The created Project object, or None if creation fails

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    try:
        headers = client.default_headers
        headers.update({"Accept": "application/json"})
        res = client.post(
            f"v1/namespaces/{tenant_meta_namespace}/projects",
            headers=headers,
            data=payload.model_dump(),
        )
        data = res.json()
        return Project(**data)
    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        return None


def update_project(
    client: APIClient,
    tenant_meta_namespace: str,
    project_uuid: str,
    payload: UpdateProjectPayload,
) -> Optional[Project]:
    """
    Update an existing project.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name (e.g., 'endor-solutions-tgowan.cockpit')
        project_uuid: The UUID of the project to update
        payload: The UpdateProjectPayload containing the updated project details

    Returns:
        Optional[Project]: The updated Project object, or None if update fails

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    try:
        headers = client.default_headers
        headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )
        
        # The API expects the UUID in the request body, not the URL path
        request_data = {
            "object": {
                "uuid": project_uuid,
                "tenant_meta": {"namespace": tenant_meta_namespace},
                **payload.model_dump()
            }
        }
        
        res = client.patch(
            f"v1/namespaces/{tenant_meta_namespace}/projects",
            headers=headers,
            data=request_data,
        )
        data = res.json()
        return Project(**data)
    except Exception as e:
        logger.error(f"Error updating project {project_uuid}: {e}", exc_info=True)
        return None


def delete_project(
    client: APIClient, tenant_meta_namespace: str, project_uuid: str
) -> bool:
    """
    Delete a project by UUID.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name (e.g., 'endor-solutions-tgowan.cockpit')
        project_uuid: The UUID of the project to delete

    Returns:
        bool: True if deletion was successful, False otherwise

    Raises:
        requests.exceptions.HTTPError: For API-level errors
    """
    try:
        headers = client.default_headers
        res = client.delete(
            f"v1/namespaces/{tenant_meta_namespace}/projects/{project_uuid}",
            headers=headers,
        )
        return res.status_code == 200  # Endor's API returns 200 on successful deletion
    except Exception as e:
        logger.error(f"Error deleting project {project_uuid}: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # Example usage
    client = APIClient()
    tenant_meta_namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")

    # List projects
    print("Listing projects...")
    projects = list_projects(client, tenant_meta_namespace)
    print(f"Found {len(projects)} projects")
    
    for project in projects[:3]:  # Show first 3
        print(f"  - {project.meta.name} (UUID: {project.uuid})")
