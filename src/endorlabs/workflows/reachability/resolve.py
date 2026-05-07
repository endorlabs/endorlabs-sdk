"""Resource resolution helpers for reachability context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ReachabilitySubject:
    """Resolved subject identifiers used by the context workflow."""

    tenant: str
    namespace: str
    finding_uuid: str | None
    project_uuid: str | None
    importer_pv_uuid: str | None
    importer_pv_name: str | None
    target_dependency_uuid: str | None
    target_dependency_package_name: str | None
    oss_namespace: str | None
    oss_package_version_uuid: str | None
    oss_package_name: str | None
    extra_key: str | None


def resolve_from_finding(
    api_client: Any,
    *,
    namespace: str,
    finding_uuid: str,
) -> tuple[ReachabilitySubject, dict[str, Any], dict[str, Any] | None]:
    """Resolve cross-plane IDs starting from a finding UUID."""
    finding = api_client.get(
        f"v1/namespaces/{namespace}/findings/{finding_uuid}"
    ).json()
    fs = finding.get("spec") or {}
    target_uuid = fs.get("target_uuid")

    dep_meta: dict[str, Any] | None = None
    if target_uuid:
        dep_meta = api_client.get(
            f"v1/namespaces/{namespace}/dependency-metadata/{target_uuid}"
        ).json()

    dd = ((dep_meta or {}).get("spec") or {}).get("dependency_data") or {}
    importer = ((dep_meta or {}).get("spec") or {}).get("importer_data") or {}
    subject = ReachabilitySubject(
        tenant=namespace,
        namespace=namespace,
        finding_uuid=finding_uuid,
        project_uuid=importer.get("project_uuid") or fs.get("project_uuid"),
        importer_pv_uuid=importer.get("package_version_uuid")
        or (dep_meta or {}).get("meta", {}).get("parent_uuid"),
        importer_pv_name=importer.get("package_version_name"),
        target_dependency_uuid=target_uuid,
        target_dependency_package_name=fs.get("target_dependency_package_name"),
        oss_namespace=dd.get("namespace"),
        oss_package_version_uuid=dd.get("package_version_uuid"),
        oss_package_name=dd.get("package_name"),
        extra_key=fs.get("extra_key"),
    )
    return subject, finding, dep_meta


def resolve_from_package_version(
    api_client: Any,
    *,
    namespace: str,
    package_version_uuid: str,
) -> tuple[ReachabilitySubject, dict[str, Any]]:
    """Resolve subject when caller provides importer package-version UUID."""
    pv = api_client.get(
        f"v1/namespaces/{namespace}/package-versions/{package_version_uuid}"
    ).json()
    spec = pv.get("spec") or {}
    subject = ReachabilitySubject(
        tenant=namespace,
        namespace=namespace,
        finding_uuid=None,
        project_uuid=spec.get("project_uuid"),
        importer_pv_uuid=package_version_uuid,
        importer_pv_name=(pv.get("meta") or {}).get("name"),
        target_dependency_uuid=None,
        target_dependency_package_name=None,
        oss_namespace=None,
        oss_package_version_uuid=None,
        oss_package_name=None,
        extra_key=None,
    )
    return subject, pv
