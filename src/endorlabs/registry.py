"""Resource registry for the Client facade.

Single source of truth for which resources are exposed on endorlabs.Client.
- RESOURCE_REGISTRY: CRUD resources (list/get/create/update/delete); Client builds
  ResourceFacade from each entry.
- CUSTOM_FACADE_REGISTRY: Resources with non-CRUD APIs (e.g. scan_logs); Client
  attaches the facade instance returned by each entry's factory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from .api_client import APIClient

from .resources import (
    api_key as api_key_module,
)
from .resources import (
    audit_log as audit_log_module,
)
from .resources import (
    authentication_log as authentication_log_module,
)
from .resources import (
    authorization_policy as authorization_policy_module,
)
from .resources import (
    code_owners as code_owners_module,
)
from .resources import (
    dependency_metadata as dependency_metadata_module,
)
from .resources import (
    endor_license as endor_license_module,
)
from .resources import (
    finding as finding_module,
)
from .resources import (
    finding_log as finding_log_module,
)
from .resources import (
    installation as installation_module,
)
from .resources import (
    invitation as invitation_module,
)
from .resources import (
    linter_result as linter_result_module,
)
from .resources import (
    metric as metric_module,
)
from .resources import (
    namespace as namespace_module,
)
from .resources import (
    notification_target as notification_target_module,
)
from .resources import (
    package_license as package_license_module,
)
from .resources import (
    package_version as package_version_module,
)
from .resources import (
    policy as policy_module,
)
from .resources import (
    policy_template as policy_template_module,
)
from .resources import (
    project as project_module,
)
from .resources import (
    repository as repository_module,
)
from .resources import (
    repository_version as repository_version_module,
)
from .resources import (
    scan_profile as scan_profile_module,
)
from .resources import (
    scan_result as scan_result_module,
)
from .resources import (
    scan_workflow as scan_workflow_module,
)
from .resources import (
    scan_workflow_result as scan_workflow_result_module,
)
from .resources import (
    semgrep_rule as semgrep_rule_module,
)
from .resources import (
    version_upgrade as version_upgrade_module,
)
from .resources.api_key import APIKey
from .resources.audit_log import AuditLog
from .resources.authentication_log import AuthenticationLog
from .resources.authorization_policy import AuthorizationPolicy
from .resources.code_owners import CodeOwners
from .resources.dependency_metadata import DependencyMetadata
from .resources.endor_license import EndorLicense
from .resources.finding import Finding
from .resources.finding_log import FindingLog
from .resources.installation import Installation
from .resources.invitation import Invitation
from .resources.linter_result import LinterResult
from .resources.metric import Metric
from .resources.namespace import Namespace
from .resources.notification_target import NotificationTarget
from .resources.package_license import PackageLicense
from .resources.package_version import PackageVersion
from .resources.policy import Policy
from .resources.policy_template import PolicyTemplate
from .resources.project import Project
from .resources.repository import Repository
from .resources.repository_version import RepositoryVersion
from .resources.scan_profile import ScanProfile
from .resources.scan_result import ScanResult
from .resources.scan_workflow import ScanWorkflow
from .resources.scan_workflow_result import ScanWorkflowResult
from .resources.semgrep_rule import SemgrepRule
from .resources.version_upgrade import VersionUpgrade


@dataclass
class ResourceEntry:
    """One resource exposed on Client; used to build facade in __init__.

    scope: "system" = system-owned, get only when namespace is oss;
    "oss" = namespace fixed to oss; None = tenant (default).
    build_create_payload_fn: when set, facade.create(**kwargs) builds payload.
    """

    attr_name: str
    model_class: type
    list_fn: Callable[..., Any]
    get_fn: Callable[..., Any] | None
    create_fn: Callable[..., Any] | None
    update_fn: Callable[..., Any] | None
    delete_fn: Callable[..., bool] | None
    list_iter_fn: Callable[..., Iterator[Any]] | None = None
    resource_name: str = ""  # API path for capability lookup (e.g. "scan-results")
    parent_kind: str | None = None  # parent_kind for list(parent=) (e.g. project)
    scope: Literal["system"] | Literal["oss"] | None = None  # system | oss | tenant
    build_create_payload_fn: Callable[..., Any] | None = None  # kwargs -> payload


@dataclass
class CustomFacadeEntry:
    """Custom facade on Client; factory(client, default_namespace) -> facade."""

    attr_name: str
    factory: Callable[["APIClient", str | None], Any]  # noqa: UP037


def _scan_logs_facade(client: APIClient, default_namespace: str | None) -> Any:
    """Build ScanLogsFacade for client.scan_logs (request-based API)."""
    from .facade import ScanLogsFacade

    return ScanLogsFacade(client, default_namespace)


RESOURCE_REGISTRY: list[ResourceEntry] = [
    ResourceEntry(
        "namespace",
        Namespace,
        namespace_module.list_namespaces,
        namespace_module.get_namespace,
        namespace_module.create_namespace,
        namespace_module.update_namespace,
        namespace_module.delete_namespace,
        namespace_module.list_namespaces_iter,
        "namespaces",
        build_create_payload_fn=namespace_module.build_create_payload,
    ),
    ResourceEntry(
        "project",
        Project,
        project_module.list_projects,
        project_module.get_project,
        project_module.create_project,
        project_module.update_project,
        project_module.delete_project,
        project_module.list_projects_iter,
        "projects",
        build_create_payload_fn=project_module.build_create_payload,
    ),
    ResourceEntry(
        "finding",
        Finding,
        finding_module.list_findings,
        finding_module.get_finding,
        finding_module.create_finding,
        finding_module.update_finding,
        finding_module.delete_finding,
        finding_module.list_findings_iter,
        "findings",
        build_create_payload_fn=finding_module.build_create_payload,
    ),
    ResourceEntry(
        "repository",
        Repository,
        repository_module.list_repositories,
        repository_module.get_repository,
        repository_module.create_repository,
        repository_module.update_repository,
        repository_module.delete_repository,
        repository_module.list_repositories_iter,
        "repositories",
        build_create_payload_fn=repository_module.build_create_payload,
    ),
    ResourceEntry(
        "repository_version",
        RepositoryVersion,
        repository_version_module.list_repository_versions,
        repository_version_module.get_repository_version,
        repository_version_module.create_repository_version,
        repository_version_module.update_repository_version,
        repository_version_module.delete_repository_version,
        repository_version_module.list_repository_versions_iter,
        "repository-versions",
        parent_kind="project",
        build_create_payload_fn=repository_version_module.build_create_payload,
    ),
    ResourceEntry(
        "policy",
        Policy,
        policy_module.list_policies,
        policy_module.get_policy,
        policy_module.create_policy,
        policy_module.update_policy,
        policy_module.delete_policy,
        policy_module.list_policies_iter,
        "policies",
        build_create_payload_fn=policy_module.build_create_payload,
    ),
    ResourceEntry(
        "authorization_policy",
        AuthorizationPolicy,
        authorization_policy_module.list_authorization_policies,
        authorization_policy_module.get_authorization_policy,
        authorization_policy_module.create_authorization_policy,
        authorization_policy_module.update_authorization_policy,
        authorization_policy_module.delete_authorization_policy,
        authorization_policy_module.list_authorization_policies_iter,
        "authorization-policies",
        build_create_payload_fn=authorization_policy_module.build_create_payload,
    ),
    ResourceEntry(
        "package_version",
        PackageVersion,
        package_version_module.list_package_versions,
        package_version_module.get_package_version,
        package_version_module.create_package_version,
        package_version_module.update_package_version,
        package_version_module.delete_package_version,
        package_version_module.list_package_versions_iter,
        "package-versions",
        build_create_payload_fn=package_version_module.build_create_payload,
    ),
    ResourceEntry(
        "package_license",
        PackageLicense,
        package_license_module.list_package_licenses,
        package_license_module.get_package_license,
        package_license_module.create_package_license,
        package_license_module.update_package_license,
        package_license_module.delete_package_license,
        package_license_module.list_package_licenses_iter,
        "package-licenses",
        scope="oss",
        build_create_payload_fn=package_license_module.build_create_payload,
    ),
    ResourceEntry(
        "dependency_metadata",
        DependencyMetadata,
        dependency_metadata_module.list_dependency_metadata,
        dependency_metadata_module.get_dependency_metadata,
        dependency_metadata_module.create_dependency_metadata,
        None,  # update unimplemented: platform-managed "oss" data, not for SDK updates
        dependency_metadata_module.delete_dependency_metadata,
        dependency_metadata_module.list_dependency_metadata_iter,
        "dependency-metadata",
        scope="oss",
        build_create_payload_fn=dependency_metadata_module.build_create_payload,
    ),
    ResourceEntry(
        "installation",
        Installation,
        installation_module.list_installations,
        installation_module.get_installation,
        installation_module.create_installation,
        installation_module.update_installation,
        installation_module.delete_installation,
        installation_module.list_installations_iter,
        "installations",
        build_create_payload_fn=installation_module.build_create_payload,
    ),
    ResourceEntry(
        "scan_profile",
        ScanProfile,
        scan_profile_module.list_scan_profiles,
        scan_profile_module.get_scan_profile,
        scan_profile_module.create_scan_profile,
        scan_profile_module.update_scan_profile,
        scan_profile_module.delete_scan_profile,
        scan_profile_module.list_scan_profiles_iter,
        "scan-profiles",
        build_create_payload_fn=scan_profile_module.build_create_payload,
    ),
    ResourceEntry(
        "scan_result",
        ScanResult,
        scan_result_module.list_scan_results,
        scan_result_module.get_scan_result,
        scan_result_module.create_scan_result,
        scan_result_module.update_scan_result,
        scan_result_module.delete_scan_result,
        scan_result_module.list_scan_results_iter,
        "scan-results",
        parent_kind="project",
        build_create_payload_fn=scan_result_module.build_create_payload,
    ),
    ResourceEntry(
        "linter_result",
        LinterResult,
        linter_result_module.list_linter_results,
        linter_result_module.get_linter_result,
        linter_result_module.create_linter_result,
        None,  # update unimplemented: linter results are read-only (scan-generated)
        linter_result_module.delete_linter_result,
        linter_result_module.list_linter_results_iter,
        "linter-results",
        build_create_payload_fn=linter_result_module.build_create_payload,
    ),
    ResourceEntry(
        "metric",
        Metric,
        metric_module.list_metrics,
        metric_module.get_metric,
        metric_module.create_metric,
        metric_module.update_metric,
        metric_module.delete_metric,
        metric_module.list_metrics_iter,
        "metrics",
        build_create_payload_fn=metric_module.build_create_payload,
    ),
    ResourceEntry(
        "semgrep_rule",
        SemgrepRule,
        semgrep_rule_module.list_semgrep_rules,
        semgrep_rule_module.get_semgrep_rule,
        semgrep_rule_module.create_semgrep_rule,
        semgrep_rule_module.update_semgrep_rule,
        semgrep_rule_module.delete_semgrep_rule,
        semgrep_rule_module.list_semgrep_rules_iter,
        "semgrep-rules",
        build_create_payload_fn=semgrep_rule_module.build_create_payload,
    ),
    ResourceEntry(
        "api_key",
        APIKey,
        api_key_module.list_api_keys,
        api_key_module.get_api_key,
        api_key_module.create_api_key,
        None,
        api_key_module.delete_api_key,
        api_key_module.list_api_keys_iter,
        "api-keys",
        build_create_payload_fn=api_key_module.build_create_payload,
    ),
    ResourceEntry(
        "audit_log",
        AuditLog,
        audit_log_module.list_audit_logs,
        audit_log_module.get_audit_log,
        audit_log_module.create_audit_log,
        None,
        audit_log_module.delete_audit_log,
        audit_log_module.list_audit_logs_iter,
        "audit-logs",
        build_create_payload_fn=audit_log_module.build_create_payload,
    ),
    ResourceEntry(
        "finding_log",
        FindingLog,
        finding_log_module.list_finding_logs,
        finding_log_module.get_finding_log,
        finding_log_module.create_finding_log,
        None,
        finding_log_module.delete_finding_log,
        finding_log_module.list_finding_logs_iter,
        "finding-logs",
        build_create_payload_fn=finding_log_module.build_create_payload,
    ),
    ResourceEntry(
        "notification_target",
        NotificationTarget,
        notification_target_module.list_notification_targets,
        notification_target_module.get_notification_target,
        notification_target_module.create_notification_target,
        notification_target_module.update_notification_target,
        notification_target_module.delete_notification_target,
        notification_target_module.list_notification_targets_iter,
        "notification-targets",
        build_create_payload_fn=notification_target_module.build_create_payload,
    ),
    ResourceEntry(
        "scan_workflow",
        ScanWorkflow,
        scan_workflow_module.list_scan_workflows,
        scan_workflow_module.get_scan_workflow,
        None,
        None,
        None,
        scan_workflow_module.list_scan_workflows_iter,
        "scan-workflows",
    ),
    ResourceEntry(
        "scan_workflow_result",
        ScanWorkflowResult,
        scan_workflow_result_module.list_scan_workflow_results,
        scan_workflow_result_module.get_scan_workflow_result,
        None,
        None,
        None,
        scan_workflow_result_module.list_scan_workflow_results_iter,
        "scan-workflow-results",
    ),
    ResourceEntry(
        "version_upgrade",
        VersionUpgrade,
        version_upgrade_module.list_version_upgrades,
        version_upgrade_module.get_version_upgrade,
        None,
        None,
        None,
        version_upgrade_module.list_version_upgrades_iter,
        "version-upgrades",
    ),
    ResourceEntry(
        "code_owners",
        CodeOwners,
        code_owners_module.list_code_owners,
        code_owners_module.get_code_owners,
        code_owners_module.create_code_owners,
        code_owners_module.update_code_owners,
        code_owners_module.delete_code_owners,
        code_owners_module.list_code_owners_iter,
        "codeowners",
        build_create_payload_fn=code_owners_module.build_create_payload,
    ),
    ResourceEntry(
        "invitation",
        Invitation,
        invitation_module.list_invitations,
        invitation_module.get_invitation,
        invitation_module.create_invitation,
        invitation_module.update_invitation,
        invitation_module.delete_invitation,
        invitation_module.list_invitations_iter,
        "invitations",
        build_create_payload_fn=invitation_module.build_create_payload,
    ),
    ResourceEntry(
        "authentication_log",
        AuthenticationLog,
        authentication_log_module.list_authentication_logs,
        authentication_log_module.get_authentication_log,
        None,
        None,
        None,
        authentication_log_module.list_authentication_logs_iter,
        "authentication-logs",
        scope="system",
    ),
    ResourceEntry(
        "endor_license",
        EndorLicense,
        endor_license_module.list_endor_licenses,
        endor_license_module.get_endor_license,
        None,
        None,
        None,
        endor_license_module.list_endor_licenses_iter,
        "endor-licenses",
        scope="system",
    ),
    ResourceEntry(
        "policy_template",
        PolicyTemplate,
        policy_template_module.list_policy_templates,
        policy_template_module.get_policy_template,
        None,
        None,
        None,
        policy_template_module.list_policy_templates_iter,
        "policy-templates",
        scope="system",
    ),
]

CUSTOM_FACADE_REGISTRY: list[CustomFacadeEntry] = [
    CustomFacadeEntry("scan_logs", _scan_logs_facade),
]
