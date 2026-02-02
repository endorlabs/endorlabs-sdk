"""Resource registry for the Client facade.

Single source of truth for which resources are exposed on endorlabs.Client.
- RESOURCE_REGISTRY: CRUD resources (list/get/create/update/delete); Client builds
  ResourceFacade from each entry.
- CUSTOM_FACADE_REGISTRY: Resources with non-CRUD APIs (e.g. scan_logs); Client
  attaches the facade instance returned by each entry's factory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

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
    authorization_policy as authorization_policy_module,
)
from .resources import (
    dependency_metadata as dependency_metadata_module,
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
    linter_result as linter_result_module,
)
from .resources import (
    metric as metric_module,
)
from .resources import (
    namespace as namespace_module,
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
    semgrep_rule as semgrep_rule_module,
)
from .resources.api_key import APIKey
from .resources.audit_log import AuditLog
from .resources.authorization_policy import AuthorizationPolicy
from .resources.dependency_metadata import DependencyMetadata
from .resources.finding import Finding
from .resources.finding_log import FindingLog
from .resources.installation import Installation
from .resources.linter_result import LinterResult
from .resources.metric import Metric
from .resources.namespace import Namespace
from .resources.package_license import PackageLicense
from .resources.package_version import PackageVersion
from .resources.policy import Policy
from .resources.project import Project
from .resources.repository import Repository
from .resources.repository_version import RepositoryVersion
from .resources.scan_profile import ScanProfile
from .resources.scan_result import ScanResult
from .resources.semgrep_rule import SemgrepRule


@dataclass
class ResourceEntry:
    """One resource exposed on Client; used to build ResourceFacade in __init__."""

    attr_name: str
    model_class: type
    list_fn: Callable[..., Any]
    get_fn: Callable[..., Any]
    create_fn: Callable[..., Any]
    update_fn: Callable[..., Any] | None
    delete_fn: Callable[..., bool] | None
    list_iter_fn: Callable[..., Iterator[Any]] | None = None
    resource_name: str = ""  # API path for capability lookup (e.g. "scan-results")
    parent_kind: str | None = None  # parent_kind for list(parent=) (e.g. project)


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
    ),
]

CUSTOM_FACADE_REGISTRY: list[CustomFacadeEntry] = [
    CustomFacadeEntry("scan_logs", _scan_logs_facade),
]
