"""Unit tests for reachability resolver joins."""

from __future__ import annotations

from unittest.mock import Mock

from endorlabs.workflows.reachability.resolve import (
    resolve_from_finding,
    resolve_from_package_version,
)


def test_resolve_from_finding_cross_namespace() -> None:
    finding_uuid = "f-1"
    dep_uuid = "dm-1"
    finding_model = Mock()
    finding_model.model_dump = Mock(
        return_value={
            "uuid": finding_uuid,
            "spec": {"target_uuid": dep_uuid, "extra_key": "CVE-1"},
        }
    )
    dep_model = Mock()
    dep_model.model_dump = Mock(
        return_value={
            "uuid": dep_uuid,
            "spec": {
                "importer_data": {
                    "project_uuid": "p-1",
                    "package_version_uuid": "pv-importer",
                },
                "dependency_data": {
                    "namespace": "oss",
                    "package_version_uuid": "pv-oss",
                    "package_name": "maven://x",
                },
            },
        }
    )
    client = Mock()
    client.Finding.get = Mock(return_value=finding_model)
    client.DependencyMetadata.get = Mock(return_value=dep_model)

    subject, finding, dep = resolve_from_finding(
        client, namespace="acme", finding_uuid=finding_uuid
    )
    assert finding["uuid"] == finding_uuid
    assert dep["uuid"] == dep_uuid
    assert subject.importer_pv_uuid == "pv-importer"
    assert subject.oss_namespace == "oss"
    assert subject.oss_package_version_uuid == "pv-oss"


def test_resolve_from_package_version() -> None:
    pv_model = Mock()
    pv_model.model_dump = Mock(
        return_value={
            "uuid": "pv-1",
            "meta": {"name": "npm://pkg@1.0.0"},
            "spec": {"project_uuid": "proj-1"},
        }
    )
    client = Mock()
    client.PackageVersion.get = Mock(return_value=pv_model)

    subject, pv = resolve_from_package_version(
        client, namespace="acme", package_version_uuid="pv-1"
    )
    assert pv["uuid"] == "pv-1"
    assert subject.importer_pv_uuid == "pv-1"
    assert subject.project_uuid == "proj-1"
