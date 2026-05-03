"""Namespace, installation, scan profile, and authorization policy setup."""

from __future__ import annotations

from .setup import (
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
    "AuthorizationPolicyResult",
    "InstallationResult",
    "NamespaceResult",
    "ScanProfileResult",
    "create_authorization_policy",
    "create_child_namespace",
    "create_github_installation",
    "create_scan_profile_with_defaults",
]
