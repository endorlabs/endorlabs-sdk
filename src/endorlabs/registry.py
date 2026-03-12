"""Resource registry for the Client facade.

Single source of truth for which resources are exposed on endorlabs.Client.
- RESOURCE_REGISTRY: declarative metadata entries; Client builds
  ResourceFacade from each entry using BaseResourceOperations.
- CUSTOM_FACADE_REGISTRY: Resources with non-CRUD APIs (e.g. scan_logs); Client
  attaches the facade instance returned by each entry's factory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Callable

    from .api_client import APIClient

from .resources.api_key import APIKey
from .resources.api_key import build_create_payload as api_key_build_create
from .resources.audit_log import AuditLog
from .resources.audit_log import build_create_payload as audit_log_build_create
from .resources.authentication_log import AuthenticationLog
from .resources.authorization_policy import (
    AuthorizationPolicy,
)
from .resources.authorization_policy import (
    build_create_payload as authorization_policy_build_create,
)
from .resources.code_owners import (
    CodeOwners,
)
from .resources.code_owners import (
    build_create_payload as code_owners_build_create,
)
from .resources.dependency_metadata import (
    DependencyMetadata,
)
from .resources.dependency_metadata import (
    build_create_payload as dependency_metadata_build_create,
)
from .resources.endor_license import EndorLicense
from .resources.finding import Finding
from .resources.finding import build_create_payload as finding_build_create
from .resources.finding_log import (
    FindingLog,
)
from .resources.finding_log import (
    build_create_payload as finding_log_build_create,
)
from .resources.installation import (
    Installation,
)
from .resources.installation import (
    build_create_payload as installation_build_create,
)
from .resources.invitation import (
    Invitation,
)
from .resources.invitation import (
    build_create_payload as invitation_build_create,
)
from .resources.linter_result import (
    LinterResult,
)
from .resources.linter_result import (
    build_create_payload as linter_result_build_create,
)
from .resources.malware import Malware
from .resources.metric import Metric
from .resources.metric import build_create_payload as metric_build_create
from .resources.namespace import (
    Namespace,
)
from .resources.namespace import (
    build_create_payload as namespace_build_create,
)
from .resources.notification_target import (
    NotificationTarget,
)
from .resources.notification_target import (
    build_create_payload as notification_target_build_create,
)
from .resources.package_license import (
    PackageLicense,
)
from .resources.package_license import (
    build_create_payload as package_license_build_create,
)
from .resources.package_version import (
    PackageVersion,
)
from .resources.package_version import (
    build_create_payload as package_version_build_create,
)
from .resources.policy import Policy
from .resources.policy import build_create_payload as policy_build_create
from .resources.policy_template import PolicyTemplate
from .resources.project import Project
from .resources.project import build_create_payload as project_build_create
from .resources.query_malware import QueryMalware
from .resources.query_malware import build_create_payload as query_malware_build_create
from .resources.query_vulnerability import QueryVulnerability
from .resources.query_vulnerability import (
    build_create_payload as query_vulnerability_build_create,
)
from .resources.repository import (
    Repository,
)
from .resources.repository import (
    build_create_payload as repository_build_create,
)
from .resources.repository_version import (
    RepositoryVersion,
)
from .resources.repository_version import (
    build_create_payload as repository_version_build_create,
)
from .resources.scan_log_request import (
    ScanLogRequest,
)
from .resources.scan_profile import (
    ScanProfile,
)
from .resources.scan_profile import (
    build_create_payload as scan_profile_build_create,
)
from .resources.scan_result import (
    ScanResult,
)
from .resources.scan_result import (
    build_create_payload as scan_result_build_create,
)
from .resources.scan_workflow import ScanWorkflow
from .resources.scan_workflow_result import ScanWorkflowResult
from .resources.semgrep_rule import (
    SemgrepRule,
)
from .resources.semgrep_rule import (
    build_create_payload as semgrep_rule_build_create,
)
from .resources.version_upgrade import VersionUpgrade
from .resources.vulnerability import Vulnerability


@dataclass
class ResourceEntry:
    """One resource exposed on Client; used to build facade in __init__.

    Declarative metadata — no function references. The facade creates
    ``BaseResourceOperations`` from ``resource_name`` + ``model_class`` at
    runtime.

    scope: "system" = system-owned, get only when namespace is oss;
    "oss" = namespace fixed to oss; None = tenant (default).
    """

    attr_name: str
    resource_name: str  # API path (e.g. "projects", "scan-results")
    model_class: type
    supported_ops: frozenset[str] = frozenset(
        {"list", "get", "create", "update", "delete"}
    )
    build_create_payload_fn: Callable[..., Any] | None = None
    filter_kwarg_map: dict[str, str] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]
    parent_kind: str | None = None
    scope: Literal["system"] | Literal["oss"] | None = None


@dataclass
class CustomFacadeEntry:
    """Custom facade on Client; factory(client, default_namespace) -> facade."""

    attr_name: str
    factory: Callable[["APIClient", str | None], Any]  # noqa: UP037


def _scan_logs_facade(client: APIClient, default_namespace: str | None) -> Any:
    """Build ScanLogsFacade for client.scan_logs (request-based API)."""
    from .facade import ScanLogsFacade

    return ScanLogsFacade(client, default_namespace)


_NAME_FILTER: dict[str, str] = {"name": "meta.name"}

RESOURCE_REGISTRY: list[ResourceEntry] = [
    # -- Tenant-scoped (full CRUD) ----------------------------------------
    ResourceEntry(
        attr_name="namespace",
        resource_name="namespaces",
        model_class=Namespace,
        build_create_payload_fn=namespace_build_create,
        filter_kwarg_map=_NAME_FILTER,
    ),
    ResourceEntry(
        attr_name="project",
        resource_name="projects",
        model_class=Project,
        build_create_payload_fn=project_build_create,
        filter_kwarg_map=_NAME_FILTER,
    ),
    ResourceEntry(
        attr_name="finding",
        resource_name="findings",
        model_class=Finding,
        build_create_payload_fn=finding_build_create,
        filter_kwarg_map=_NAME_FILTER,
    ),
    ResourceEntry(
        attr_name="repository",
        resource_name="repositories",
        model_class=Repository,
        build_create_payload_fn=repository_build_create,
        filter_kwarg_map={
            "name": "meta.name",
            "vcs_url": "spec.vcs_url",
            "git_url": "spec.vcs_url",
        },
    ),
    ResourceEntry(
        attr_name="repository_version",
        resource_name="repository-versions",
        model_class=RepositoryVersion,
        build_create_payload_fn=repository_version_build_create,
        filter_kwarg_map=_NAME_FILTER,
        parent_kind="project",
    ),
    ResourceEntry(
        attr_name="policy",
        resource_name="policies",
        model_class=Policy,
        build_create_payload_fn=policy_build_create,
        filter_kwarg_map={
            "name": "meta.name",
            "policy_type": "spec.policy_type",
        },
    ),
    ResourceEntry(
        attr_name="authorization_policy",
        resource_name="authorization-policies",
        model_class=AuthorizationPolicy,
        build_create_payload_fn=authorization_policy_build_create,
        filter_kwarg_map=_NAME_FILTER,
    ),
    ResourceEntry(
        attr_name="package_version",
        resource_name="package-versions",
        model_class=PackageVersion,
        build_create_payload_fn=package_version_build_create,
        filter_kwarg_map=_NAME_FILTER,
    ),
    ResourceEntry(
        attr_name="installation",
        resource_name="installations",
        model_class=Installation,
        build_create_payload_fn=installation_build_create,
        filter_kwarg_map=_NAME_FILTER,
    ),
    ResourceEntry(
        attr_name="scan_profile",
        resource_name="scan-profiles",
        model_class=ScanProfile,
        build_create_payload_fn=scan_profile_build_create,
        filter_kwarg_map=_NAME_FILTER,
    ),
    ResourceEntry(
        attr_name="scan_result",
        resource_name="scan-results",
        model_class=ScanResult,
        build_create_payload_fn=scan_result_build_create,
        filter_kwarg_map=_NAME_FILTER,
        parent_kind="project",
    ),
    ResourceEntry(
        attr_name="scan_log_request",
        resource_name="scan-log-requests",
        model_class=ScanLogRequest,
        supported_ops=frozenset({"create"}),
    ),
    ResourceEntry(
        attr_name="linter_result",
        resource_name="linter-results",
        model_class=LinterResult,
        supported_ops=frozenset({"list", "get", "create", "delete"}),
        build_create_payload_fn=linter_result_build_create,
    ),
    ResourceEntry(
        attr_name="metric",
        resource_name="metrics",
        model_class=Metric,
        build_create_payload_fn=metric_build_create,
        filter_kwarg_map=_NAME_FILTER,
    ),
    ResourceEntry(
        attr_name="semgrep_rule",
        resource_name="semgrep-rules",
        model_class=SemgrepRule,
        build_create_payload_fn=semgrep_rule_build_create,
        filter_kwarg_map=_NAME_FILTER,
    ),
    ResourceEntry(
        attr_name="api_key",
        resource_name="api-keys",
        model_class=APIKey,
        supported_ops=frozenset({"list", "get", "create", "delete"}),
        build_create_payload_fn=api_key_build_create,
    ),
    ResourceEntry(
        attr_name="audit_log",
        resource_name="audit-logs",
        model_class=AuditLog,
        supported_ops=frozenset({"list", "get", "create", "delete"}),
        build_create_payload_fn=audit_log_build_create,
    ),
    ResourceEntry(
        attr_name="finding_log",
        resource_name="finding-logs",
        model_class=FindingLog,
        supported_ops=frozenset({"list", "get", "create", "delete"}),
        build_create_payload_fn=finding_log_build_create,
    ),
    ResourceEntry(
        attr_name="notification_target",
        resource_name="notification-targets",
        model_class=NotificationTarget,
        build_create_payload_fn=notification_target_build_create,
        filter_kwarg_map=_NAME_FILTER,
    ),
    ResourceEntry(
        attr_name="scan_workflow",
        resource_name="scan-workflows",
        model_class=ScanWorkflow,
        supported_ops=frozenset({"list", "get", "delete"}),
    ),
    ResourceEntry(
        attr_name="scan_workflow_result",
        resource_name="scan-workflow-results",
        model_class=ScanWorkflowResult,
        supported_ops=frozenset({"list", "get", "delete"}),
    ),
    ResourceEntry(
        attr_name="version_upgrade",
        resource_name="version-upgrades",
        model_class=VersionUpgrade,
        supported_ops=frozenset({"list", "get", "delete"}),
    ),
    ResourceEntry(
        attr_name="invitation",
        resource_name="invitations",
        model_class=Invitation,
        build_create_payload_fn=invitation_build_create,
        filter_kwarg_map=_NAME_FILTER,
    ),
    ResourceEntry(
        attr_name="code_owners",
        resource_name="codeowners",
        model_class=CodeOwners,
        build_create_payload_fn=code_owners_build_create,
        filter_kwarg_map=_NAME_FILTER,
    ),
    # -- OSS-scoped (namespace fixed to "oss") ----------------------------
    ResourceEntry(
        attr_name="package_license",
        resource_name="package-licenses",
        model_class=PackageLicense,
        build_create_payload_fn=package_license_build_create,
        scope="oss",
    ),
    ResourceEntry(
        attr_name="dependency_metadata",
        resource_name="dependency-metadata",
        model_class=DependencyMetadata,
        build_create_payload_fn=dependency_metadata_build_create,
        scope="oss",
    ),
    ResourceEntry(
        attr_name="vulnerability",
        resource_name="vulnerabilities",
        model_class=Vulnerability,
        build_create_payload_fn=None,
        supported_ops=frozenset({"list", "get"}),
        filter_kwarg_map=_NAME_FILTER,
        scope="oss",
    ),
    ResourceEntry(
        attr_name="malware",
        resource_name="malware",
        model_class=Malware,
        build_create_payload_fn=None,
        supported_ops=frozenset({"list", "get"}),
        filter_kwarg_map=_NAME_FILTER,
        scope="oss",
    ),
    ResourceEntry(
        attr_name="query_vulnerability",
        resource_name="queries/vulnerabilities",
        model_class=QueryVulnerability,
        build_create_payload_fn=query_vulnerability_build_create,
        supported_ops=frozenset({"create"}),
        scope="oss",
    ),
    ResourceEntry(
        attr_name="query_malware",
        resource_name="queries/malware",
        model_class=QueryMalware,
        build_create_payload_fn=query_malware_build_create,
        supported_ops=frozenset({"create"}),
        scope="oss",
    ),
    # -- System-scoped (get only for oss namespace) -----------------------
    ResourceEntry(
        attr_name="authentication_log",
        resource_name="authentication-logs",
        model_class=AuthenticationLog,
        supported_ops=frozenset({"list", "get"}),
        scope="system",
    ),
    ResourceEntry(
        attr_name="endor_license",
        resource_name="endor-licenses",
        model_class=EndorLicense,
        supported_ops=frozenset({"list", "get"}),
        scope="system",
    ),
    ResourceEntry(
        attr_name="policy_template",
        resource_name="policy-templates",
        model_class=PolicyTemplate,
        supported_ops=frozenset({"list", "get"}),
        scope="system",
    ),
]

CUSTOM_FACADE_REGISTRY: list[CustomFacadeEntry] = [
    CustomFacadeEntry("scan_logs", _scan_logs_facade),
]
