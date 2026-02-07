"""Resource registry for the Client facade.

Single source of truth for which resources are exposed on endorlabs.Client.
- RESOURCE_REGISTRY: CRUD resources (list/get/create/update/delete); Client builds
  ResourceFacade from each entry.
- CUSTOM_FACADE_REGISTRY: Resources with non-CRUD APIs (e.g. scan_logs); Client
  attaches the facade instance returned by each entry's factory.
"""

from __future__ import annotations

import types
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

    @classmethod
    def from_module(
        cls,
        attr_name: str,
        module: types.ModuleType,
        model_class: type,
        resource_name: str,
        *,
        list_name: str = "",
        op_name: str = "",
        scope: Literal["system", "oss"] | None = None,
        parent_kind: str | None = None,
    ) -> ResourceEntry:
        """Build a ResourceEntry by convention from a resource module.

        Discovers ``list_<list_name>``, ``get_<op_name>``,
        ``create_<op_name>``, ``update_<op_name>``, ``delete_<op_name>``,
        ``list_<list_name>_iter``, and ``build_create_payload`` by name.

        Args:
            attr_name: Attribute name on ``Client`` (e.g. ``"project"``).
            module: The resource module to inspect.
            model_class: Pydantic model class for the resource.
            resource_name: API resource path (e.g. ``"projects"``).
            list_name: Override for the plural in ``list_<X>`` / ``list_<X>_iter``.
                Defaults to ``resource_name`` with hyphens replaced by underscores.
            op_name: Override for the singular in ``get_<X>`` / ``create_<X>`` etc.
                Defaults to ``attr_name``.
            scope: Resource scope (``"system"``, ``"oss"``, or ``None``).
            parent_kind: Parent resource kind for ``list(parent=)``.
        """
        if not list_name:
            list_name = resource_name.replace("-", "_")
        if not op_name:
            op_name = attr_name

        return cls(
            attr_name=attr_name,
            model_class=model_class,
            list_fn=getattr(module, f"list_{list_name}"),
            get_fn=getattr(module, f"get_{op_name}", None),
            create_fn=getattr(module, f"create_{op_name}", None),
            update_fn=getattr(module, f"update_{op_name}", None),
            delete_fn=getattr(module, f"delete_{op_name}", None),
            list_iter_fn=getattr(module, f"list_{list_name}_iter", None),
            resource_name=resource_name,
            parent_kind=parent_kind,
            scope=scope,
            build_create_payload_fn=getattr(module, "build_create_payload", None),
        )


@dataclass
class CustomFacadeEntry:
    """Custom facade on Client; factory(client, default_namespace) -> facade."""

    attr_name: str
    factory: Callable[["APIClient", str | None], Any]  # noqa: UP037


def _scan_logs_facade(client: APIClient, default_namespace: str | None) -> Any:
    """Build ScanLogsFacade for client.scan_logs (request-based API)."""
    from .facade import ScanLogsFacade

    return ScanLogsFacade(client, default_namespace)


_fm = ResourceEntry.from_module

RESOURCE_REGISTRY: list[ResourceEntry] = [
    # -- Tenant-scoped (full CRUD) ----------------------------------------
    _fm("namespace", namespace_module, Namespace, "namespaces"),
    _fm("project", project_module, Project, "projects"),
    _fm("finding", finding_module, Finding, "findings"),
    _fm("repository", repository_module, Repository, "repositories"),
    _fm(
        "repository_version",
        repository_version_module,
        RepositoryVersion,
        "repository-versions",
        parent_kind="project",
    ),
    _fm("policy", policy_module, Policy, "policies"),
    _fm(
        "authorization_policy",
        authorization_policy_module,
        AuthorizationPolicy,
        "authorization-policies",
    ),
    _fm(
        "package_version",
        package_version_module,
        PackageVersion,
        "package-versions",
    ),
    _fm("installation", installation_module, Installation, "installations"),
    _fm("scan_profile", scan_profile_module, ScanProfile, "scan-profiles"),
    _fm(
        "scan_result",
        scan_result_module,
        ScanResult,
        "scan-results",
        parent_kind="project",
    ),
    _fm(
        "linter_result",
        linter_result_module,
        LinterResult,
        "linter-results",
    ),
    _fm("metric", metric_module, Metric, "metrics"),
    _fm("semgrep_rule", semgrep_rule_module, SemgrepRule, "semgrep-rules"),
    _fm("api_key", api_key_module, APIKey, "api-keys"),
    _fm("audit_log", audit_log_module, AuditLog, "audit-logs"),
    _fm("finding_log", finding_log_module, FindingLog, "finding-logs"),
    _fm(
        "notification_target",
        notification_target_module,
        NotificationTarget,
        "notification-targets",
    ),
    _fm(
        "scan_workflow",
        scan_workflow_module,
        ScanWorkflow,
        "scan-workflows",
    ),
    _fm(
        "scan_workflow_result",
        scan_workflow_result_module,
        ScanWorkflowResult,
        "scan-workflow-results",
    ),
    _fm(
        "version_upgrade",
        version_upgrade_module,
        VersionUpgrade,
        "version-upgrades",
    ),
    _fm("invitation", invitation_module, Invitation, "invitations"),
    # -- Special naming (plural op_name) ----------------------------------
    _fm(
        "code_owners",
        code_owners_module,
        CodeOwners,
        "codeowners",
        list_name="code_owners",
        op_name="code_owners",
    ),
    # -- OSS-scoped (namespace fixed to "oss") ----------------------------
    _fm(
        "package_license",
        package_license_module,
        PackageLicense,
        "package-licenses",
        scope="oss",
    ),
    _fm(
        "dependency_metadata",
        dependency_metadata_module,
        DependencyMetadata,
        "dependency-metadata",
        scope="oss",
    ),
    # -- System-scoped (get only for oss namespace) -----------------------
    _fm(
        "authentication_log",
        authentication_log_module,
        AuthenticationLog,
        "authentication-logs",
        scope="system",
    ),
    _fm(
        "endor_license",
        endor_license_module,
        EndorLicense,
        "endor-licenses",
        scope="system",
    ),
    _fm(
        "policy_template",
        policy_template_module,
        PolicyTemplate,
        "policy-templates",
        scope="system",
    ),
]

CUSTOM_FACADE_REGISTRY: list[CustomFacadeEntry] = [
    CustomFacadeEntry("scan_logs", _scan_logs_facade),
]
