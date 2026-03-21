"""Platform setup workflows: namespaces, installations, scan profiles, auth policies.

Thin orchestration wrappers around single Client facade ``create()`` calls
with sensible defaults, returning typed results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .common import WorkflowResult

if TYPE_CHECKING:
    from endorlabs import Client

from endorlabs.utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class NamespaceResult(WorkflowResult):
    """Result of a child namespace creation."""

    uuid: str = ""
    name: str = ""
    parent: str = ""


@dataclass
class InstallationResult(WorkflowResult):
    """Result of a GitHub installation creation."""

    uuid: str = ""
    name: str = ""


@dataclass
class ScanProfileResult(WorkflowResult):
    """Result of a scan profile creation."""

    uuid: str = ""
    name: str = ""
    is_default: bool = False


@dataclass
class AuthorizationPolicyResult(WorkflowResult):
    """Result of an authorization policy creation."""

    uuid: str = ""
    name: str = ""


# ---------------------------------------------------------------------------
# Create child namespace
# ---------------------------------------------------------------------------


def create_child_namespace(
    client: Client,
    parent: str,
    name: str,
    *,
    description: str = "",
    dry_run: bool = False,
) -> NamespaceResult:
    """Create a child namespace under *parent*.

    Args:
        client: Authenticated ``endorlabs.Client`` instance.
        parent: Parent namespace in canonical form (e.g. ``"tenant"``).
        name: Name for the new child namespace.
        description: Optional description.
        dry_run: When True, validate args but skip creation.

    Returns:
        NamespaceResult with the created namespace details.
    """
    result = NamespaceResult(name=name, parent=parent)

    if dry_run:
        result.message = f"[DRY RUN] Would create namespace '{name}' under '{parent}'."
        return result

    try:
        ns = client.Namespace.create(
            name=name,
            description=description or f"Child namespace: {name}",
            namespace=parent,
        )
        result.uuid = ns.uuid
        result.message = f"Created namespace '{name}' (uuid={ns.uuid})."
        logger.info(result.message)
    except Exception as exc:
        result.status = "error"
        result.message = f"Unable to create namespace: {exc}"
        result.errors.append(str(exc))
        logger.error(result.message)

    return result


# ---------------------------------------------------------------------------
# Create GitHub installation
# ---------------------------------------------------------------------------


def create_github_installation(
    client: Client,
    namespace: str,
    name: str,
    *,
    github_org: str | None = None,
    description: str = "",
    dry_run: bool = False,
    **extra_kwargs: Any,
) -> InstallationResult:
    """Create a GitHub App installation resource.

    Args:
        client: Authenticated ``endorlabs.Client`` instance.
        namespace: Namespace to create the installation in.
        name: Name for the installation.
        github_org: GitHub organization name (if applicable).
        description: Optional description.
        dry_run: When True, validate args but skip creation.
        **extra_kwargs: Extra kwargs forwarded to the facade create.

    Returns:
        InstallationResult with the created installation details.
    """
    result = InstallationResult(name=name)

    if dry_run:
        result.message = (
            f"[DRY RUN] Would create installation '{name}' in '{namespace}'."
        )
        return result

    create_kwargs: dict[str, Any] = {
        "name": name,
        "namespace": namespace,
        "description": description or f"GitHub installation: {name}",
        **extra_kwargs,
    }
    if github_org:
        create_kwargs["github_org"] = github_org

    try:
        inst = client.Installation.create(**create_kwargs)
        result.uuid = inst.uuid
        result.message = f"Created installation '{name}' (uuid={inst.uuid})."
        logger.info(result.message)
    except Exception as exc:
        result.status = "error"
        result.message = f"Unable to create installation: {exc}"
        result.errors.append(str(exc))
        logger.error(result.message)

    return result


# ---------------------------------------------------------------------------
# Create scan profile with defaults
# ---------------------------------------------------------------------------


def create_scan_profile_with_defaults(
    client: Client,
    namespace: str,
    name: str,
    *,
    description: str = "",
    is_default: bool = False,
    propagate: bool = True,
    dry_run: bool = False,
    **spec_kwargs: Any,
) -> ScanProfileResult:
    """Create a scan profile with sensible defaults.

    Args:
        client: Authenticated ``endorlabs.Client`` instance.
        namespace: Namespace to create the profile in.
        name: Name for the scan profile.
        description: Optional description.
        is_default: Set as the namespace's default profile.
        propagate: Propagate to child namespaces.
        dry_run: When True, validate args but skip creation.
        **spec_kwargs: Additional spec fields forwarded to the facade
            (e.g. ``automated_scan_parameters``, ``toolchain_profile``).

    Returns:
        ScanProfileResult with the created profile details.
    """
    result = ScanProfileResult(name=name, is_default=is_default)

    if dry_run:
        result.message = (
            f"[DRY RUN] Would create scan profile '{name}' in '{namespace}'."
        )
        return result

    try:
        profile = client.ScanProfile.create(
            name=name,
            namespace=namespace,
            description=description or f"Scan profile: {name}",
            is_default=is_default,
            propagate=propagate,
            **spec_kwargs,
        )
        result.uuid = profile.uuid
        result.message = f"Created scan profile '{name}' (uuid={profile.uuid})."
        logger.info(result.message)
    except Exception as exc:
        result.status = "error"
        result.message = f"Unable to create scan profile: {exc}"
        result.errors.append(str(exc))
        logger.error(result.message)

    return result


# ---------------------------------------------------------------------------
# Create authorization policy
# ---------------------------------------------------------------------------


def create_authorization_policy(
    client: Client,
    namespace: str,
    name: str,
    *,
    description: str = "",
    dry_run: bool = False,
    **extra_kwargs: Any,
) -> AuthorizationPolicyResult:
    """Create an authorization policy.

    Args:
        client: Authenticated ``endorlabs.Client`` instance.
        namespace: Namespace to create the policy in.
        name: Name for the authorization policy.
        description: Optional description.
        dry_run: When True, validate args but skip creation.
        **extra_kwargs: Extra kwargs forwarded to the facade create.

    Returns:
        AuthorizationPolicyResult with the created policy details.
    """
    result = AuthorizationPolicyResult(name=name)

    if dry_run:
        result.message = (
            f"[DRY RUN] Would create authorization policy '{name}' in '{namespace}'."
        )
        return result

    try:
        policy = client.AuthorizationPolicy.create(
            name=name,
            namespace=namespace,
            description=description or f"Authorization policy: {name}",
            **extra_kwargs,
        )
        result.uuid = policy.uuid
        result.message = f"Created authorization policy '{name}' (uuid={policy.uuid})."
        logger.info(result.message)
    except Exception as exc:
        result.status = "error"
        result.message = f"Unable to create authorization policy: {exc}"
        result.errors.append(str(exc))
        logger.error(result.message)

    return result
