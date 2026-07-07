"""Resource resolution helpers for reachability context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from endorlabs.workflows.wire_access import as_dict, nested_dict, nested_str

if TYPE_CHECKING:
    from endorlabs import Client


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
    client: Client,
    *,
    namespace: str,
    finding_uuid: str,
) -> tuple[ReachabilitySubject, dict[str, Any], dict[str, Any] | None]:
    """Resolve cross-plane IDs starting from a finding UUID."""
    finding_dict = cast(
        "dict[str, Any]",
        client.Finding.get(finding_uuid, namespace=namespace).model_dump(mode="json"),
    )
    fs = nested_dict(finding_dict, "spec")
    target_uuid = fs.get("target_uuid")

    dep_meta: dict[str, Any] | None = None
    if target_uuid:
        dep_meta = client.DependencyMetadata.get(
            target_uuid, namespace=namespace
        ).model_dump(mode="json")

    dep_spec = nested_dict(as_dict(dep_meta), "spec")
    dd = nested_dict(dep_spec, "dependency_data")
    importer = nested_dict(dep_spec, "importer_data")
    dep_meta_meta = nested_dict(as_dict(dep_meta), "meta")
    subject = ReachabilitySubject(
        tenant=namespace,
        namespace=namespace,
        finding_uuid=finding_uuid,
        project_uuid=importer.get("project_uuid") or fs.get("project_uuid"),
        importer_pv_uuid=importer.get("package_version_uuid")
        or dep_meta_meta.get("parent_uuid"),
        importer_pv_name=importer.get("package_version_name"),
        target_dependency_uuid=target_uuid,
        target_dependency_package_name=fs.get("target_dependency_package_name"),
        oss_namespace=dd.get("namespace"),
        oss_package_version_uuid=dd.get("package_version_uuid"),
        oss_package_name=dd.get("package_name"),
        extra_key=fs.get("extra_key"),
    )
    return subject, finding_dict, dep_meta


def resolve_from_package_version(
    client: Client,
    *,
    namespace: str,
    package_version_uuid: str,
) -> tuple[ReachabilitySubject, dict[str, Any]]:
    """Resolve subject when caller provides importer package-version UUID."""
    pv = cast(
        "dict[str, Any]",
        client.PackageVersion.get(package_version_uuid, namespace=namespace).model_dump(
            mode="json"
        ),
    )
    spec = nested_dict(pv, "spec")
    subject = ReachabilitySubject(
        tenant=namespace,
        namespace=namespace,
        finding_uuid=None,
        project_uuid=spec.get("project_uuid"),
        importer_pv_uuid=package_version_uuid,
        importer_pv_name=nested_str(pv, "meta", "name") or None,
        target_dependency_uuid=None,
        target_dependency_package_name=None,
        oss_namespace=None,
        oss_package_version_uuid=None,
        oss_package_name=None,
        extra_key=None,
    )
    return subject, pv
