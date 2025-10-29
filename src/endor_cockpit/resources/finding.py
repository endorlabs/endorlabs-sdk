"""
Finding resource module for Endor Labs API.

This module provides CRUD operations for Finding resources following the established
patterns from the Project resource implementation.
"""

import logging
from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient
from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseResourceOperations,
    BaseSpec,
    FlexibleEnum,
)
from ..types import ListParameters

logger = logging.getLogger(__name__)


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


class CallGraphAnalysisType(FlexibleEnum):
    """Call graph analysis type enumeration."""

    UNSPECIFIED = "CALL_GRAPH_ANALYSIS_TYPE_UNSPECIFIED"
    FULL = "CALL_GRAPH_ANALYSIS_TYPE_FULL"


class Ecosystem(FlexibleEnum):
    """Package ecosystem enumeration."""

    UNSPECIFIED = "ECOSYSTEM_UNSPECIFIED"
    NPM = "ECOSYSTEM_NPM"
    PYPI = "ECOSYSTEM_PYPI"
    MAVEN = "ECOSYSTEM_MAVEN"
    NUGET = "ECOSYSTEM_NUGET"
    RUBYGEMS = "ECOSYSTEM_RUBYGEMS"
    GO = "ECOSYSTEM_GO"
    RUST = "ECOSYSTEM_RUST"
    CARGO = "ECOSYSTEM_CARGO"
    COMPOSER = "ECOSYSTEM_COMPOSER"
    HEX = "ECOSYSTEM_HEX"
    COCOAPODS = "ECOSYSTEM_COCOAPODS"
    SWIFT = "ECOSYSTEM_SWIFT"
    CONAN = "ECOSYSTEM_CONAN"
    CRAN = "ECOSYSTEM_CRAN"
    PUB = "ECOSYSTEM_PUB"
    PACKAGIST = "ECOSYSTEM_PACKAGIST"
    DEBIAN = "ECOSYSTEM_DEBIAN"
    UBUNTU = "ECOSYSTEM_UBUNTU"
    ALPINE = "ECOSYSTEM_ALPINE"
    RHEL = "ECOSYSTEM_RHEL"
    AMAZON = "ECOSYSTEM_AMAZON"
    SUSE = "ECOSYSTEM_SUSE"
    ARCH = "ECOSYSTEM_ARCH"
    GENTOO = "ECOSYSTEM_GENTOO"
    FEDORA = "ECOSYSTEM_FEDORA"
    PHARONIX = "ECOSYSTEM_PHARONIX"
    DOCKER = "ECOSYSTEM_DOCKER"
    GITHUB = "ECOSYSTEM_GITHUB"
    GITLAB = "ECOSYSTEM_GITLAB"
    BITBUCKET = "ECOSYSTEM_BITBUCKET"
    AZURE_DEVOPS = "ECOSYSTEM_AZURE_DEVOPS"
    JENKINS = "ECOSYSTEM_JENKINS"
    CIRCLECI = "ECOSYSTEM_CIRCLECI"
    TRAVIS_CI = "ECOSYSTEM_TRAVIS_CI"
    GITHUB_ACTIONS = "ECOSYSTEM_GITHUB_ACTIONS"
    GITLAB_CI = "ECOSYSTEM_GITLAB_CI"
    AZURE_PIPELINES = "ECOSYSTEM_AZURE_PIPELINES"
    BAMBOO = "ECOSYSTEM_BAMBOO"
    TEAMCITY = "ECOSYSTEM_TEAMCITY"
    BUILDKITE = "ECOSYSTEM_BUILDKITE"
    CODESHIP = "ECOSYSTEM_CODESHIP"
    DRONE = "ECOSYSTEM_DRONE"
    SEMAPHORE = "ECOSYSTEM_SEMAPHORE"
    APPVEYOR = "ECOSYSTEM_APPVEYOR"
    WERCKER = "ECOSYSTEM_WERCKER"
    SHIPPABLE = "ECOSYSTEM_SHIPPABLE"
    MAGNUM = "ECOSYSTEM_MAGNUM"
    SOLANO = "ECOSYSTEM_SOLANO"
    BUDDY = "ECOSYSTEM_BUDDY"
    CODEFRESH = "ECOSYSTEM_CODEFRESH"
    CODEFRESH_PIPELINES = "ECOSYSTEM_CODEFRESH_PIPELINES"
    CODEFRESH_RUNTIME = "ECOSYSTEM_CODEFRESH_RUNTIME"
    CODEFRESH_RUNTIME_IMAGES = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES"
    CODEFRESH_RUNTIME_IMAGES_UBUNTU = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_UBUNTU"
    CODEFRESH_RUNTIME_IMAGES_ALPINE = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_ALPINE"
    CODEFRESH_RUNTIME_IMAGES_DEBIAN = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_DEBIAN"
    CODEFRESH_RUNTIME_IMAGES_CENTOS = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_CENTOS"
    CODEFRESH_RUNTIME_IMAGES_RHEL = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_RHEL"
    CODEFRESH_RUNTIME_IMAGES_AMAZON = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_AMAZON"
    CODEFRESH_RUNTIME_IMAGES_SUSE = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_SUSE"
    CODEFRESH_RUNTIME_IMAGES_ARCH = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_ARCH"
    CODEFRESH_RUNTIME_IMAGES_GENTOO = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_GENTOO"
    CODEFRESH_RUNTIME_IMAGES_FEDORA = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_FEDORA"
    CODEFRESH_RUNTIME_IMAGES_PHARONIX = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_PHARONIX"
    CODEFRESH_RUNTIME_IMAGES_DOCKER = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_DOCKER"
    CODEFRESH_RUNTIME_IMAGES_GITHUB = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_GITHUB"
    CODEFRESH_RUNTIME_IMAGES_GITLAB = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_GITLAB"
    CODEFRESH_RUNTIME_IMAGES_BITBUCKET = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_BITBUCKET"
    CODEFRESH_RUNTIME_IMAGES_AZURE_DEVOPS = (
        "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_AZURE_DEVOPS"
    )
    CODEFRESH_RUNTIME_IMAGES_JENKINS = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_JENKINS"
    CODEFRESH_RUNTIME_IMAGES_CIRCLECI = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_CIRCLECI"
    CODEFRESH_RUNTIME_IMAGES_TRAVIS_CI = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_TRAVIS_CI"
    CODEFRESH_RUNTIME_IMAGES_GITHUB_ACTIONS = (
        "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_GITHUB_ACTIONS"
    )
    CODEFRESH_RUNTIME_IMAGES_GITLAB_CI = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_GITLAB_CI"
    CODEFRESH_RUNTIME_IMAGES_AZURE_PIPELINES = (
        "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_AZURE_PIPELINES"
    )
    CODEFRESH_RUNTIME_IMAGES_BAMBOO = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_BAMBOO"
    CODEFRESH_RUNTIME_IMAGES_TEAMCITY = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_TEAMCITY"
    CODEFRESH_RUNTIME_IMAGES_BUILDKITE = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_BUILDKITE"
    CODEFRESH_RUNTIME_IMAGES_CODESHIP = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_CODESHIP"
    CODEFRESH_RUNTIME_IMAGES_DRONE = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_DRONE"
    CODEFRESH_RUNTIME_IMAGES_SEMAPHORE = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_SEMAPHORE"
    CODEFRESH_RUNTIME_IMAGES_APPVEYOR = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_APPVEYOR"
    CODEFRESH_RUNTIME_IMAGES_WERCKER = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_WERCKER"
    CODEFRESH_RUNTIME_IMAGES_SHIPPABLE = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_SHIPPABLE"
    CODEFRESH_RUNTIME_IMAGES_MAGNUM = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_MAGNUM"
    CODEFRESH_RUNTIME_IMAGES_SOLANO = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_SOLANO"
    CODEFRESH_RUNTIME_IMAGES_BUDDY = "ECOSYSTEM_CODEFRESH_RUNTIME_IMAGES_BUDDY"


class CvssVersion(FlexibleEnum):
    """CVSS version enumeration."""

    UNSPECIFIED = "CVSS_VERSION_UNSPECIFIED"
    V3 = "CVSS_VERSION_V3"
    V4 = "CVSS_VERSION_V4"


class CvssSeverityLevel(FlexibleEnum):
    """CVSS severity level enumeration."""

    UNSPECIFIED = "CVSS_SEVERITY_LEVEL_UNSPECIFIED"
    NONE = "CVSS_SEVERITY_LEVEL_NONE"
    LOW = "CVSS_SEVERITY_LEVEL_LOW"
    MEDIUM = "CVSS_SEVERITY_LEVEL_MEDIUM"
    HIGH = "CVSS_SEVERITY_LEVEL_HIGH"
    CRITICAL = "CVSS_SEVERITY_LEVEL_CRITICAL"


class FindingTags(FlexibleEnum):
    """Finding tags enumeration."""

    UNSPECIFIED = "FINDING_TAGS_UNSPECIFIED"
    NORMAL = "FINDING_TAGS_NORMAL"
    POLICY = "FINDING_TAGS_POLICY"
    EXCEPTION = "FINDING_TAGS_EXCEPTION"
    TEST = "FINDING_TAGS_TEST"


class RangeType(FlexibleEnum):
    """Range type enumeration."""

    UNSPECIFIED = "RANGE_TYPE_UNSPECIFIED"
    ECOSYSTEM = "RANGE_TYPE_ECOSYSTEM"
    GIT = "RANGE_TYPE_GIT"
    SEMVER = "RANGE_TYPE_SEMVER"
    UNKNOWN = "RANGE_TYPE_UNKNOWN"


class FindingRemediation(FlexibleEnum):
    """Finding remediation action enumeration."""

    UNSPECIFIED = "FINDING_REMEDIATION_UNSPECIFIED"
    UPGRADE = "FINDING_REMEDIATION_UPGRADE"
    DOWNGRADE = "FINDING_REMEDIATION_DOWNGRADE"
    REPLACE = "FINDING_REMEDIATION_REPLACE"
    REMOVE = "FINDING_REMEDIATION_REMOVE"
    VENDOR = "FINDING_REMEDIATION_VENDOR"
    IMPROVE = "FINDING_REMEDIATION_IMPROVE"
    REIMPLEMENT = "FINDING_REMEDIATION_REIMPLEMENT"
    REVIEW = "FINDING_REMEDIATION_REVIEW"
    NOTIFICATION = "FINDING_REMEDIATION_NOTIFICATION"
    PIN = "FINDING_REMEDIATION_PIN"


class FindingMeta(BaseMeta):
    """Finding metadata extending BaseMeta."""

    # Finding-specific fields (universal fields inherited from BaseMeta)
    pass  # No additional fields needed, all were universal


class FindingMetadata(BaseModel):
    """Finding metadata details."""

    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    category: Optional[FindingCategory] = None


class FindingSpec(BaseSpec):
    """Finding specification extending BaseSpec.

    Field Mutability Guide:
    ======================

    IMMUTABLE FIELDS (cannot be updated after creation):
    - project_uuid: Project assignment (set at creation)
    - level: Severity level (determined by analysis)
    - method: Analysis method used (determined by analysis)
    - target_uuid: Target resource (set at creation)
    - finding_metadata: Analysis results (system-generated)
    - last_processed: System-managed timestamp
    - target_dependency_package_name: Dependency package name (analysis-determined)
    - target_dependency_name: Dependency name (analysis-determined)
    - target_dependency_version: Dependency version (analysis-determined)
    - explanation: Analysis explanation (analysis-determined)
    - remediation_action: Recommended action (analysis-determined)
    - source_code_version: Source code version (analysis-determined)
    - reachable_paths: Function paths (analysis-determined)
    - ecosystem: Ecosystem where found (analysis-determined)
    - finding_categories: Finding categories (analysis-determined)
    - relationship: Relationship information (analysis-determined)
    - latest_version: Latest version (analysis-determined)
    - dependency_file_paths: Dependency file paths (analysis-determined)
    - approximation: Approximation flag (analysis-determined)
    - proposed_version: Proposed version (analysis-determined)
    - exceptions: Exception information (analysis-determined)
    - actions: Action information (analysis-determined)
    - fixing_upgrades: Fixing upgrade info (analysis-determined)
    - fixing_patch: Fixing patch info (analysis-determined)
    - code_owners: Code owners (analysis-determined)
    - location_urls: Location URLs (analysis-determined)
    - call_graph_analysis_type: Call graph analysis type (analysis-determined)

    MUTABLE FIELDS (can be updated via API):
    - dismiss: User can dismiss/undismiss findings
    - remediation: User can add remediation guidance
    - summary: User can update finding summary
    - finding_tags: User can add/remove tags
    - extra_key: User-defined extra information
    """

    project_uuid: Optional[str] = Field(
        None,
        description="UUID of the project this finding belongs to",  # IMMUTABLE
    )
    last_processed: Optional[datetime] = Field(
        None,
        description="Last processed timestamp",  # IMMUTABLE: System-managed
    )
    level: Optional[FindingLevel] = Field(
        None, description="Severity level of the finding"
    )  # IMMUTABLE: Analysis-determined
    dismiss: Optional[bool] = Field(
        None,
        description="Whether the finding is dismissed",  # MUTABLE: User can update
    )
    remediation: Optional[str] = Field(
        None, description="Remediation guidance"
    )  # MUTABLE: User can update
    finding_metadata: Optional[dict] = Field(
        None,
        description="Complex nested structure",  # IMMUTABLE: System-generated
    )
    summary: Optional[str] = Field(
        None, description="Finding summary"
    )  # MUTABLE: User can update
    finding_tags: Optional[List[str]] = Field(
        None,
        description="Tags associated with the finding",  # MUTABLE: User can update
    )
    target_uuid: Optional[str] = Field(
        None, description="Target resource UUID"
    )  # IMMUTABLE: Set at creation
    extra_key: Optional[str] = Field(
        None, description="Extra key information"
    )  # MUTABLE: User can update
    method: Optional[AnalysisMethod] = Field(
        None, description="Analysis method used"
    )  # IMMUTABLE: Analysis-determined

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

    @field_validator("remediation_action", mode="before")
    @classmethod
    def validate_remediation_action(cls, v):
        """Handle unknown remediation action values gracefully."""
        if isinstance(v, str):
            try:
                return FindingRemediation(v)
            except ValueError:
                logger.warning(f"Unknown FindingRemediation value: {v}. Using as-is.")
                return v
        return v

    @field_validator("finding_categories", mode="before")
    @classmethod
    def validate_finding_categories(cls, v):
        """Handle finding categories validation."""
        if isinstance(v, list):
            validated_categories = []
            for category in v:
                if isinstance(category, str):
                    try:
                        validated_categories.append(FindingCategory(category))
                    except ValueError:
                        logger.warning(
                            f"Unknown FindingCategory value: {category}. Using as-is."
                        )
                        validated_categories.append(category)
                else:
                    validated_categories.append(category)
            return validated_categories
        return v

    @field_validator("call_graph_analysis_type", mode="before")
    @classmethod
    def validate_call_graph_analysis_type(cls, v):
        """Handle unknown call graph analysis type values gracefully."""
        if isinstance(v, str):
            try:
                return CallGraphAnalysisType(v)
            except ValueError:
                logger.warning(
                    f"Unknown CallGraphAnalysisType value: {v}. Using as-is."
                )
                return v
        return v

    target_dependency_package_name: Optional[str] = Field(
        None,
        description="Fully qualified name of the dependency, e.g. eco://package@version",
    )  # IMMUTABLE: Analysis-determined
    target_dependency_name: Optional[str] = Field(
        None,
        description="Dependency package name, if applicable. This is just the name.",
    )  # IMMUTABLE: Analysis-determined
    target_dependency_version: Optional[str] = Field(
        None,
        description="Dependency version, if applicable. This is just the version.",
    )  # IMMUTABLE: Analysis-determined
    explanation: Optional[str] = Field(
        None, description="Information about why this finding is considered noteworthy"
    )  # IMMUTABLE: Analysis-determined
    remediation_action: Optional[FindingRemediation] = Field(
        None, description="Recommended action to resolve the finding"
    )  # IMMUTABLE: Analysis-determined
    source_code_version: Optional[dict] = Field(
        None,
        description="Ref of the source code repository for root package version",
    )  # IMMUTABLE: Analysis-determined
    reachable_paths: Optional[List[dict]] = Field(
        None,
        description="Function paths to vulnerable method. Only for vulnerabilities.",
    )  # IMMUTABLE: Analysis-determined
    ecosystem: Optional[Ecosystem] = Field(
        None, description="Ecosystem where the finding was detected"
    )  # IMMUTABLE: Analysis-determined
    finding_categories: Optional[List[FindingCategory]] = Field(
        None,
        description="List of categories that capture the use case the finding fits in.",
    )  # IMMUTABLE: Analysis-determined
    relationship: Optional[str] = Field(
        None, description="Relationship information"
    )  # IMMUTABLE: Analysis-determined
    latest_version: Optional[str] = Field(
        None, description="Latest version of the dependency"
    )  # IMMUTABLE: Analysis-determined
    dependency_file_paths: Optional[List[str]] = Field(
        None, description="Paths to dependency files"
    )  # IMMUTABLE: Analysis-determined
    approximation: Optional[bool] = Field(
        None, description="Whether this is an approximation"
    )  # IMMUTABLE: Analysis-determined
    proposed_version: Optional[str] = Field(
        None, description="Proposed version for remediation"
    )  # IMMUTABLE: Analysis-determined
    exceptions: Optional[Union[List[str], dict]] = Field(
        None, description="Exception information"
    )  # IMMUTABLE: Analysis-determined
    actions: Optional[Union[List[str], dict]] = Field(
        None, description="Action information"
    )  # IMMUTABLE: Analysis-determined
    fixing_upgrades: Optional[List[str]] = Field(
        None, description="Fixing upgrade information"
    )  # IMMUTABLE: Analysis-determined
    fixing_patch: Optional[List[str]] = Field(
        None, description="Fixing patch information"
    )  # IMMUTABLE: Analysis-determined
    code_owners: Optional[List[str]] = Field(
        None, description="Code owners information"
    )  # IMMUTABLE: Analysis-determined
    location_urls: Optional[Union[List[str], dict]] = Field(
        None, description="Location URLs"
    )  # IMMUTABLE: Analysis-determined
    call_graph_analysis_type: Optional[CallGraphAnalysisType] = Field(
        None, description="Call graph analysis type"
    )  # IMMUTABLE: Analysis-determined


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


class Finding(BaseResource):
    """
    An Endor Labs finding entity extending BaseResource.

    Finding-specific fields (universal fields inherited from BaseResource).
    """

    # Finding-specific fields (universal fields inherited from BaseResource)
    spec: FindingSpec = Field(..., description="Finding specification")  # type: ignore
    finding_context: Context = Field(
        ..., description="Context information for the finding", alias="context"
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data):
        # Convert spec to FindingSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = FindingSpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
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
            }
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
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

    meta: Optional[FindingMeta] = Field(None, description="Updated finding metadata")
    spec: Optional[FindingSpec] = Field(
        None, description="Updated finding specification"
    )
    context: Optional[Context] = Field(None, description="Updated finding context")


def _get_finding_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for findings."""
    return BaseResourceOperations(client, "findings", Finding)


def list_findings(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
) -> List[Finding]:
    """
    List findings in a namespace.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name (e.g., 'tenant.namespace')
        list_params: Optional list parameters for filtering, pagination, etc.

    Returns:
        List of Finding objects
    """
    ops = _get_finding_ops(client)
    results = ops.list(tenant_meta_namespace, list_params)
    return [Finding(**item.model_dump()) for item in results]  # type: ignore


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
    ops = _get_finding_ops(client)
    result = ops.get(tenant_meta_namespace, finding_uuid)
    if result:
        return Finding(**result.model_dump())  # type: ignore
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
