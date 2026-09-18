"""Namespace, installation, scan profile, and authorization policy setup."""

from __future__ import annotations

from .config_presence import (
    LICENSE_BUCKET_DEFAULT,
    CheckResult,
    ConfigPresenceResult,
    aggregate_by_license,
    license_bucket_for,
    probe_project_presence,
    probe_tenant_presence,
    run_config_presence,
)
from .platform_setup import (
    AuthorizationPolicyResult,
    InstallationResult,
    NamespaceResult,
    ScanProfileResult,
    create_authorization_policy,
    create_child_namespace,
    create_github_installation,
    create_scan_profile_with_defaults,
)

__all__ = [
    "LICENSE_BUCKET_DEFAULT",
    "AuthorizationPolicyResult",
    "CheckResult",
    "ConfigPresenceResult",
    "InstallationResult",
    "NamespaceResult",
    "ScanProfileResult",
    "aggregate_by_license",
    "create_authorization_policy",
    "create_child_namespace",
    "create_github_installation",
    "create_scan_profile_with_defaults",
    "license_bucket_for",
    "probe_project_presence",
    "probe_tenant_presence",
    "run_config_presence",
]
