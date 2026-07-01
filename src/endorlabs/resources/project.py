"""Project — thin consumer wrapper over generated V1Project."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from endorlabs.generated.models.project_service import (
    V1Meta,
    V1Project,
)
from endorlabs.operations import BaseResourceOperations

from ..utils.logging_config import get_resource_logger
from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import (
    ConsumerResourceWireMixin,
    ProjectProcessingStatus,
    ProjectSpec,
)

ProjectMeta = V1Meta

if TYPE_CHECKING:
    from ..api_client import APIClient

logger = get_resource_logger(__name__)


class Project(V1Project, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for Project (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("Project")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("Project")

    spec: ProjectSpec | None = None  # pyright: ignore[reportIncompatibleVariableOverride]
    processing_status: ProjectProcessingStatus | None = None  # pyright: ignore[reportIncompatibleVariableOverride]


def is_hex_project_id(value: str) -> bool:
    """Return whether *value* is a 24-character lowercase hex project UUID."""
    return len(value) == 24 and all(c in "0123456789abcdef" for c in value.lower())


def _project_git_dict(project: Any) -> dict[str, Any]:
    """Return ``spec.git`` as a plain dict from a Project model or masked row."""
    if isinstance(project, dict):
        git = (project.get("spec") or {}).get("git")
        return dict(git) if isinstance(git, dict) else {}
    spec = getattr(project, "spec", None)
    if spec is None:
        return {}
    git = getattr(spec, "git", None)
    if git is None:
        return {}
    if hasattr(git, "model_dump"):
        dumped = git.model_dump(mode="json", warnings=False)
        return dict(dumped) if isinstance(dumped, dict) else {}
    if isinstance(git, dict):
        return git
    return {}


def is_sbom_project_row(project: Any) -> bool:
    """Return whether the project row represents an SBOM import (``spec.sbom`` set)."""
    if isinstance(project, dict):
        return (project.get("spec") or {}).get("sbom") is not None
    spec = getattr(project, "spec", None)
    if spec is None:
        return False
    return getattr(spec, "sbom", None) is not None


def is_app_project_row(project: Any) -> bool:
    """Return whether the project was registered via an SCM app installation.

    True when ``spec.git.external_installation_id`` is present (app-based / cloud
    registration). For per-scan CLI vs cloud execution, use ScanResult
    ``spec.environment.config.RunBySystem`` instead.
    """
    inst = _project_git_dict(project).get("external_installation_id")
    return bool(inst)


def is_cli_project_row(project: Any) -> bool:
    """Return whether the project was registered for CLI scanning (no SCM app id).

    Exclude SBOM rows before using this for inventory classification.
    """
    return not is_app_project_row(project)


def associate_scan_profile_with_project(
    client: APIClient,
    tenant_meta_namespace: str,
    project_uuid: str,
    scan_profile_uuid: str,
) -> Project:
    """Associate a scan profile with a project."""
    ops = BaseResourceOperations(client, "projects", Project)
    current_project = ops.get(tenant_meta_namespace, project_uuid)

    spec_dict = current_project.spec.model_dump() if current_project.spec else {}
    spec_dict["scan_profile_uuid"] = scan_profile_uuid

    tenant_meta_dict = (
        current_project.tenant_meta.model_dump()
        if current_project.tenant_meta
        else {"namespace": tenant_meta_namespace}
    )
    request_data = {
        "object": {
            "uuid": project_uuid,
            "tenant_meta": tenant_meta_dict,
            "meta": {
                "name": current_project.meta.name,
            },
            "spec": spec_dict,
        },
        "request": {"update_mask": "spec.scan_profile_uuid"},
    }

    from endorlabs.operations import validate_namespace

    ns = validate_namespace(tenant_meta_namespace)
    try:
        res = client.patch(
            f"v1/namespaces/{ns}/projects",
            json=request_data,
            headers={"Accept": "application/json"},
        )
        _ = res.raise_for_status()
        data = res.json()
        updated_project = Project(**data)
        logger.info(
            "Associated scan profile '%s' with project '%s'",
            scan_profile_uuid,
            project_uuid,
        )
        return updated_project
    except httpx.HTTPStatusError as e:
        raise client.map_http_error_to_exception(
            e, "update", tenant_meta_namespace, resource_uuid=project_uuid
        ) from e
    except Exception as e:
        from ..core.exceptions import ServerError

        raise ServerError(
            message=(f"Unexpected error associating scan profile with project: {e!s}"),
            operation="update",
            namespace=tenant_meta_namespace,
            resource_uuid=project_uuid,
        ) from e


def verify_scan_profile_association(
    client: APIClient,
    tenant_meta_namespace: str,
    project_uuid: str,
    scan_profile_uuid: str,
) -> bool:
    """Verify that a scan profile is associated with a project."""
    from ..core.exceptions import NotFoundError

    try:
        ops = BaseResourceOperations(client, "projects", Project)
        project = ops.get(tenant_meta_namespace, project_uuid)
    except NotFoundError:
        return False

    current_scan_profile_uuid = getattr(project.spec, "scan_profile_uuid", None)
    is_associated = current_scan_profile_uuid == scan_profile_uuid

    if is_associated:
        logger.info(
            "Verified: Scan profile '%s' is associated with project '%s'",
            scan_profile_uuid,
            project_uuid,
        )
    else:
        logger.warning(
            "Scan profile mismatch: Project '%s' has "
            "scan_profile_uuid='%s', expected '%s'",
            project_uuid,
            current_scan_profile_uuid,
            scan_profile_uuid,
        )

    return is_associated


# --- integration / create-update compat (pre-cutover helpers) ---


class ProjectMetaCreate(BaseModel):
    """Metadata for creating an Endor Labs project."""

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
    """Metadata for updating an Endor Labs project."""

    description: str | None = Field(
        None, description="Updated description of the project's purpose"
    )
    repository_url: str | None = Field(
        None, description="Updated repository URL for the project"
    )
    language: str | None = Field(
        None, description="Updated primary programming language"
    )
    framework: str | None = Field(
        None, description="Updated framework used in the project"
    )
    tags: list[str] | None = Field(None, description="Updated tags for the project")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """Validate tags are not empty strings."""
        if v:
            return [tag.strip() for tag in v if tag.strip()]
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Validate description is not just whitespace."""
        if v and not v.strip():
            raise ValueError("description cannot be empty or whitespace")
        return v.strip() if v else v


class UpdateProjectPayload(BaseModel):
    """Payload for updating an Endor Labs project.

    MUTABLE FIELDS (can be updated via PATCH):
    - meta.name: Project name (NOT readOnly in API spec)
    - meta.description: Project description (NOT readOnly in API spec)
    - meta.tags: List of tags for categorization (NOT readOnly in API spec)
    - meta.parent_uuid, meta.parent_kind: Parent object references
      (NOT readOnly in API spec)
    - meta.annotations: Resource annotations (NOT readOnly in API spec)
    - spec.platform_source: Platform source (NOT readOnly in API spec)
    - spec.git.http_clone_url: HTTP clone URL (NOT readOnly in API spec)
    - spec.git.external_installation_id: External installation ID
      (NOT readOnly in API spec)
    - spec.git.invalid_installation: Invalid installation flag
      (NOT readOnly in API spec)
    - spec.toolchain_profile_uuid: Toolchain profile UUID (NOT readOnly in API spec)
    - spec.scan_profile_uuid: Scan profile UUID (NOT readOnly in API spec)
    - processing_status.scan_state: Scan state
      (e.g., SCAN_STATE_IDLE, SCAN_STATE_INGESTING) (NOT readOnly in API spec)
    - processing_status.disable_automated_scan: Disable automated scanning flag
      (NOT readOnly in API spec)
    - processing_status.scan_time: Last scan time
      (NOT readOnly in API spec, but typically system-managed)
    - processing_status.analytic_time: Last analytics time
      (NOT readOnly in API spec, but typically system-managed)
    - processing_status.queue_time: Last queue time
      (NOT readOnly in API spec, but typically system-managed)

    IMMUTABLE FIELDS (read-only, managed by API):
    - uuid: Unique identifier (readOnly: true in API spec)
    - meta.create_time, meta.update_time, meta.upsert_time: Timestamps
      (readOnly: true in API spec)
    - meta.kind, meta.version: Resource metadata (readOnly: true in API spec)
    - meta.created_by, meta.updated_by: Audit fields (readOnly: true in API spec)
    - meta.references, meta.index_data: System-managed fields
      (readOnly: true in API spec)
    - spec.internal_reference_key: Internal reference key (readOnly: true in API spec)
    - spec.ingestion_token: Ingestion token (readOnly: true in API spec)
    - spec.git.git_clone_url, spec.git.organization, spec.git.path,
      spec.git.full_name, spec.git.web_url: Git metadata
      (readOnly: true in API spec)
    - tenant_meta.namespace: Namespace assignment

    Example:
        >>> payload = UpdateProjectPayload(
        ...     meta=ProjectMetaUpdate(
        ...         description="Backend API service",
        ...         tags=["production", "backend"]
        ...     )
        ... )
        >>> project = update_project(
        ...     client, namespace, uuid, payload, "meta.description,meta.tags"
        ... )

    """

    meta: ProjectMetaUpdate = Field(..., description="Updated metadata for the project")


class GitInfo(BaseModel):
    """Git information for a project."""

    full_name: str | None = None
    git_clone_url: str | None = None
    http_clone_url: str | None = None
    organization: str | None = None
    path: str | None = None
    web_url: str | None = None
    external_installation_id: str | None = Field(
        None,
        description=(
            "Endor Labs GitHub app installation ID of this project. "
            "Optional and only available if the project is created "
            "through an installation."
        ),
    )
    invalid_installation: bool | None = Field(
        None,
        description="Indicates that Endor Labs installation no longer exists "
        "for this project and was potentially deleted. Endor Labs can no longer "
        "refresh or rescan this project.",
    )


class CreateProjectPayload(BaseModel):
    """Payload for creating a new project.

    Attributes:
        meta: Metadata for the new project
        namespace_uuid: UUID of the parent namespace

    """

    meta: ProjectMetaCreate = Field(..., description="Metadata for the new project")
    namespace_uuid: str = Field(..., description="UUID of the parent namespace")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "meta": {
                    "name": "example-project",
                    "description": "An example project",
                    "repository_url": "https://github.com/owner/repo",
                    "language": "Python",
                    "framework": "FastAPI",
                },
                "namespace_uuid": "namespace-uuid-here",
            }
        }
    )


def build_create_payload(**kwargs: Any) -> CreateProjectPayload:
    """Build CreateProjectPayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateProjectPayload, kwargs, attr_name="Project"
    )
