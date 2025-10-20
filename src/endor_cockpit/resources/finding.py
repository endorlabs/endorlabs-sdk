"""
Finding resource module for Endor Labs API.

This module provides CRUD operations for Finding resources following the established
patterns from the Project resource implementation.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, field_validator

from ..api_client import APIClient
from ..utils import SchemaDriftDetector

logger = logging.getLogger(__name__)


class FlexibleEnum(str, Enum):
    """Base class for flexible enums that can handle unknown values."""

    @classmethod
    def _missing_(cls, value):
        """Handle unknown enum values gracefully."""
        logger.warning(
            f"Unknown {cls.__name__} value: {value}. Adding as dynamic enum."
        )
        # Create a dynamic enum member for unknown values
        obj = str.__new__(cls, value)
        # Use setattr to avoid type checker issues
        obj._name_ = value
        obj._value_ = value
        return obj


class FindingCategory(FlexibleEnum):
    """Finding category enumeration."""

    UNSPECIFIED = "FINDING_CATEGORY_UNSPECIFIED"
    VULNERABILITY = "FINDING_CATEGORY_VULNERABILITY"
    SUPPLY_CHAIN = "FINDING_CATEGORY_SUPPLY_CHAIN"
    LICENSE_RISK = "FINDING_CATEGORY_LICENSE_RISK"
    SCPM = "FINDING_CATEGORY_SCPM"
    SECURITY = "FINDING_CATEGORY_SECURITY"
    OPERATIONAL = "FINDING_CATEGORY_OPERATIONAL"
    SECRETS = "FINDING_CATEGORY_SECRETS"
    MALWARE = "FINDING_CATEGORY_MALWARE"
    CICD = "FINDING_CATEGORY_CICD"
    TOOLS = "FINDING_CATEGORY_TOOLS"
    GHACTIONS = "FINDING_CATEGORY_GHACTIONS"
    CONTAINER = "FINDING_CATEGORY_CONTAINER"
    SAST = "FINDING_CATEGORY_SAST"
    AI_MODELS = "FINDING_CATEGORY_AI_MODELS"


class FindingLevel(FlexibleEnum):
    """Finding severity level enumeration."""

    UNSPECIFIED = "FINDING_LEVEL_UNSPECIFIED"
    CRITICAL = "FINDING_LEVEL_CRITICAL"
    HIGH = "FINDING_LEVEL_HIGH"
    MEDIUM = "FINDING_LEVEL_MEDIUM"
    LOW = "FINDING_LEVEL_LOW"
    INFO = "FINDING_LEVEL_INFO"


class FindingStatus(FlexibleEnum):
    """Finding status enumeration."""

    UNSPECIFIED = "FINDING_STATUS_UNSPECIFIED"
    OPEN = "FINDING_STATUS_OPEN"
    RESOLVED = "FINDING_STATUS_RESOLVED"
    IGNORED = "FINDING_STATUS_IGNORED"
    FALSE_POSITIVE = "FINDING_STATUS_FALSE_POSITIVE"


class AnalysisMethod(FlexibleEnum):
    """Analysis method enumeration."""

    UNSPECIFIED = "SYSTEM_EVALUATION_METHOD_UNSPECIFIED"
    DEFINITION_VULNERABILITIES = "SYSTEM_EVALUATION_METHOD_DEFINITION_VULNERABILITIES"
    DEFINITION_POLICIES = "SYSTEM_EVALUATION_METHOD_DEFINITION_POLICIES"
    SAST = "SYSTEM_EVALUATION_METHOD_SAST"
    SCA = "SYSTEM_EVALUATION_METHOD_SCA"
    SECRETS = "SYSTEM_EVALUATION_METHOD_SECRETS"
    CONTAINER = "SYSTEM_EVALUATION_METHOD_CONTAINER"
    INFRASTRUCTURE = "SYSTEM_EVALUATION_METHOD_INFRASTRUCTURE"


class Ecosystem(FlexibleEnum):
    """Ecosystem enumeration."""

    UNSPECIFIED = "ECOSYSTEM_UNSPECIFIED"
    NPM = "ECOSYSTEM_NPM"
    PYPI = "ECOSYSTEM_PYPI"
    MAVEN = "ECOSYSTEM_MAVEN"
    NUGET = "ECOSYSTEM_NUGET"
    RUBYGEMS = "ECOSYSTEM_RUBYGEMS"
    GO = "ECOSYSTEM_GO"
    RUST = "ECOSYSTEM_RUST"
    DOCKER = "ECOSYSTEM_DOCKER"
    DEBIAN = "ECOSYSTEM_DEBIAN"
    UBUNTU = "ECOSYSTEM_UBUNTU"
    ALPINE = "ECOSYSTEM_ALPINE"
    REDHAT = "ECOSYSTEM_REDHAT"


class FindingMeta(BaseModel):
    """Finding metadata."""

    create_time: Optional[str] = None
    update_time: Optional[str] = None
    upsert_time: Optional[str] = None
    name: str
    kind: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    parent_uuid: Optional[str] = None
    parent_kind: Optional[str] = None
    tags: Optional[List[str]] = None
    annotations: Optional[Dict[str, str]] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    references: Optional[Union[List[dict], dict]] = None
    index_data: Optional[dict] = None


class FindingMetadata(BaseModel):
    """Finding metadata details."""

    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    category: Optional[FindingCategory] = None


class FindingSpec(BaseModel):
    """Finding specification."""

    project_uuid: str
    last_processed: Optional[datetime] = None
    level: FindingLevel
    dismiss: Optional[bool] = None  # Can be None in API response
    remediation: Optional[str] = None
    finding_metadata: Optional[dict] = None  # Complex nested structure
    summary: Optional[str] = None
    finding_tags: Optional[List[str]] = None
    target_uuid: Optional[str] = None
    extra_key: Optional[str] = None
    method: Optional[AnalysisMethod] = None

    @field_validator("level", mode="before")
    @classmethod
    def validate_level(cls, v):
        """Handle unknown level values gracefully."""
        if isinstance(v, str):
            try:
                return FindingLevel(v)
            except ValueError:
                logger.warning(f"Unknown FindingLevel value: {v}. Using as-is.")
                return v
        return v

    @field_validator("method", mode="before")
    @classmethod
    def validate_method(cls, v):
        """Handle unknown method values gracefully."""
        if isinstance(v, str):
            try:
                return AnalysisMethod(v)
            except ValueError:
                logger.warning(f"Unknown AnalysisMethod value: {v}. Using as-is.")
                return v
        return v

    @field_validator("ecosystem", mode="before")
    @classmethod
    def validate_ecosystem(cls, v):
        """Handle unknown ecosystem values gracefully."""
        if isinstance(v, str):
            try:
                return Ecosystem(v)
            except ValueError:
                logger.warning(f"Unknown Ecosystem value: {v}. Using as-is.")
                return v
        return v

    @field_validator("finding_tags")
    @classmethod
    def validate_finding_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate finding tags are not empty strings."""
        if v:
            return [tag.strip() for tag in v if tag.strip()]
        return v

    @field_validator("remediation")
    @classmethod
    def validate_remediation(cls, v: Optional[str]) -> Optional[str]:
        """Validate remediation is not just whitespace."""
        if v and not v.strip():
            raise ValueError("remediation cannot be empty or whitespace")
        return v.strip() if v else v

    target_dependency_package_name: Optional[str] = None
    target_dependency_name: Optional[str] = None
    target_dependency_version: Optional[str] = None
    explanation: Optional[str] = None
    remediation_action: Optional[str] = None
    source_code_version: Optional[dict] = None
    reachable_paths: Optional[List[str]] = None
    ecosystem: Optional[Ecosystem] = None
    finding_categories: Optional[List[str]] = None
    relationship: Optional[str] = None
    latest_version: Optional[str] = None
    dependency_file_paths: Optional[List[str]] = None
    approximation: Optional[bool] = None
    proposed_version: Optional[str] = None
    exceptions: Optional[List[str]] = None
    actions: Optional[List[str]] = None
    fixing_upgrades: Optional[List[str]] = None
    fixing_patch: Optional[List[str]] = None
    code_owners: Optional[List[str]] = None
    location_urls: Optional[Union[List[str], dict]] = None
    call_graph_analysis_type: Optional[str] = None


class Context(BaseModel):
    """Context information for findings."""

    id: Optional[str] = None
    type: Optional[str] = None
    scan_uuid: Optional[str] = None
    scan_type: Optional[str] = None
    scan_time: Optional[datetime] = None
    will_be_deleted_at: Optional[str] = None
    tags: Optional[List[str]] = None


class TenantMeta(BaseModel):
    """Tenant metadata."""

    namespace: str


class Finding(BaseModel):
    """
    An Endor Labs finding entity based on API specification.

    Attributes:
        uuid: Unique identifier for the finding
        tenant_meta: Tenant metadata including namespace
        meta: Finding metadata
        spec: Finding specification including severity and details
        context: Context information for the finding
    """

    uuid: str
    tenant_meta: TenantMeta
    meta: FindingMeta
    spec: FindingSpec
    context: Context

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            # Define expected fields for each model
            model_fields = {
                "meta": {
                    "create_time",
                    "update_time",
                    "upsert_time",
                    "name",
                    "kind",
                    "version",
                    "description",
                    "parent_uuid",
                    "parent_kind",
                    "tags",
                    "annotations",
                    "created_by",
                    "updated_by",
                    "references",
                    "index_data",
                },
                "spec": {
                    "project_uuid",
                    "last_processed",
                    "level",
                    "dismiss",
                    "remediation",
                    "finding_metadata",
                    "summary",
                    "finding_tags",
                    "target_uuid",
                    "extra_key",
                    "method",
                    "target_dependency_package_name",
                    "target_dependency_name",
                    "target_dependency_version",
                    "explanation",
                    "remediation_action",
                    "source_code_version",
                    "reachable_paths",
                    "ecosystem",
                    "finding_categories",
                    "relationship",
                    "latest_version",
                    "dependency_file_paths",
                    "approximation",
                    "proposed_version",
                    "exceptions",
                    "actions",
                    "fixing_upgrades",
                    "fixing_patch",
                    "code_owners",
                    "location_urls",
                    "call_graph_analysis_type",
                },
                "context": {
                    "id",
                    "type",
                    "scan_uuid",
                    "scan_type",
                    "scan_time",
                    "will_be_deleted_at",
                    "tags",
                },
                "tenant_meta": {"namespace"},
            }

            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields[info.field_name], f"Finding.{info.field_name}"
                )

        return v


class CreateFindingPayload(BaseModel):
    """Payload for creating a new finding."""

    meta: FindingMeta
    spec: FindingSpec
    context: Context


class UpdateFindingPayload(BaseModel):
    """
    Payload for updating an Endor Labs finding.

    MUTABLE FIELDS (can be updated via PATCH):
    - meta.tags: General resource tags
    - spec.finding_tags: Finding-specific tags
    - spec.dismiss: Dismissal status
    - spec.remediation: Remediation guidance
    - context.tags: Contextual tags

    IMMUTABLE FIELDS (read-only, managed by API):
    - uuid: Unique identifier
    - meta.name: Finding name
    - spec.level: Severity level (set by scan)
    - spec.category: Finding category (set by scan)
    - spec.project_uuid: Associated project (set at creation)
    - spec.finding_metadata: Scan-discovered metadata
    - tenant_meta.namespace: Namespace assignment

    Example:
        >>> payload = UpdateFindingPayload(
        ...     spec=FindingSpec(
        ...         dismiss=True,
        ...         finding_tags=["reviewed", "false-positive"]
        ...     )
        ... )
        >>> finding = update_finding(
        ...     client, namespace, uuid, payload, "spec.dismiss,spec.finding_tags"
        ... )
    """

    meta: FindingMeta
    spec: FindingSpec
    context: Context


def list_findings(
    client: APIClient, tenant_meta_namespace: str, **kwargs
) -> List[Finding]:
    """
    List findings in a namespace.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name (e.g., 'tenant.namespace')
        **kwargs: Additional query parameters

    Returns:
        List of Finding objects
    """
    try:
        headers = client.default_headers
        res = client.get(
            f"v1/namespaces/{tenant_meta_namespace}/findings",
            headers=headers,
            params=kwargs,
        )
        data = res.json()
        # Handle the actual API response structure: list.objects
        findings_data = data.get("list", {}).get("objects", [])
        return [Finding(**finding) for finding in findings_data]
    except Exception as e:
        print(f"Error listing findings: {e}")
        return []


def get_finding(
    client: APIClient, tenant_meta_namespace: str, finding_uuid: str
) -> Optional[Finding]:
    """
    Get a specific finding by UUID.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        finding_uuid: UUID of the finding to retrieve

    Returns:
        Finding object if found, None otherwise
    """
    try:
        headers = client.default_headers
        res = client.get(
            f"v1/namespaces/{tenant_meta_namespace}/findings/{finding_uuid}",
            headers=headers,
        )
        data = res.json()
        return Finding(**data)
    except Exception as e:
        logger.error(f"Error getting finding {finding_uuid}: {e}", exc_info=True)
        return None


def create_finding(
    client: APIClient, tenant_meta_namespace: str, payload: CreateFindingPayload
) -> Optional[Finding]:
    """
    Create a new finding.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        payload: Finding creation payload

    Returns:
        Created Finding object if successful, None otherwise
    """
    endpoint = f"/v1/namespaces/{tenant_meta_namespace}/findings"

    try:
        response = client.post(endpoint, data=payload.model_dump())
        if response:
            return Finding(**response)
        return None
    except Exception as e:
        print(f"Error creating finding: {e}")
        return None


def update_finding(
    client: APIClient,
    tenant_meta_namespace: str,
    finding_uuid: str,
    payload: UpdateFindingPayload,
    update_mask: Optional[str] = None,
) -> Optional[Finding]:
    """
    Update an existing finding using partial updates.

    This function supports updating only specific fields using the update_mask
    parameter, which enables efficient partial updates without overwriting
    unchanged fields.

    MUTABLE FIELDS:
    - meta.tags: General resource tags
    - spec.finding_tags: Finding-specific tags
    - spec.dismiss: Dismissal status
    - spec.remediation: Remediation guidance
    - context.tags: Contextual tags

    IMMUTABLE FIELDS (cannot be updated):
    - uuid, meta.name: Set at creation
    - spec.level, spec.category: Set by scan
    - spec.project_uuid: Associated project (set at creation)
    - spec.finding_metadata: Scan-discovered metadata
    - tenant_meta.namespace: Namespace assignment

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        finding_uuid: UUID of the finding to update
        payload: Finding update payload
        update_mask: Optional comma-separated list of fields to update
            (e.g., "spec.dismiss,spec.finding_tags"). If provided, only these
            fields will be updated. If omitted, all non-None fields in
            payload will be updated.

    Returns:
        Updated Finding object if successful, None otherwise

    Raises:
        requests.exceptions.HTTPError: For API-level errors (403, 404, etc.)
        pydantic.ValidationError: If response data doesn't match expected schema

    Example:
        >>> # Dismiss a finding
        >>> payload = UpdateFindingPayload(
        ...     spec=FindingSpec(dismiss=True)
        ... )
        >>> finding = update_finding(client, namespace, uuid, payload, "spec.dismiss")

        >>> # Add finding tags
        >>> payload = UpdateFindingPayload(
        ...     spec=FindingSpec(finding_tags=["reviewed", "false-positive"])
        ... )
        >>> finding = update_finding(
        ...     client, namespace, uuid, payload, "spec.finding_tags"
        ... )

    Note:
        Tags persist correctly when using update_mask. Without update_mask,
        the API may not persist tag changes reliably.
    """
    try:
        headers = client.default_headers
        headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

        # Get the current finding to include required fields
        current_finding = get_finding(client, tenant_meta_namespace, finding_uuid)
        if not current_finding:
            logger.error(f"Finding {finding_uuid} not found")
            return None

        # Build request data with correct structure
        request_data = {
            "object": {
                "uuid": finding_uuid,
                "tenant_meta": current_finding.tenant_meta.model_dump(),
                "meta": {
                    "name": current_finding.meta.name,  # Required field
                    **(
                        payload.meta.model_dump(exclude_none=True)
                        if payload.meta
                        else {}
                    ),
                },
                "spec": {
                    **current_finding.spec.model_dump(),  # Include all
                    # existing spec fields
                    **(
                        payload.spec.model_dump(exclude_none=True)
                        if payload.spec
                        else {}
                    ),
                },
                "context": (
                    current_finding.context.model_dump()
                    if current_finding.context
                    else {}
                ),
            }
        }

        # Add update_mask if provided for partial updates
        if update_mask:
            request_data["request"] = {"update_mask": update_mask}

        logger.info(f"Updating finding {finding_uuid} with mask: {update_mask}")

        res = client.patch(
            f"v1/namespaces/{tenant_meta_namespace}/findings",
            headers=headers,
            data=request_data,
        )

        if res.status_code == 200:
            data = res.json()
            return Finding(**data)
        else:
            logger.error(
                f"Failed to update finding {finding_uuid}: "
                f"{res.status_code} - {res.text}"
            )
            return None
    except Exception as e:
        logger.error(f"Error updating finding {finding_uuid}: {e}", exc_info=True)
        return None


def delete_finding(
    client: APIClient, tenant_meta_namespace: str, finding_uuid: str
) -> bool:
    """
    Delete a finding.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        finding_uuid: UUID of the finding to delete

    Returns:
        True if successful, False otherwise
    """
    endpoint = f"/v1/namespaces/{tenant_meta_namespace}/findings/{finding_uuid}"

    try:
        response = client.delete(endpoint)
        return response is not None
    except Exception as e:
        print(f"Error deleting finding {finding_uuid}: {e}")
        return False
