"""Unit tests for reachability resolver joins."""

from __future__ import annotations

from dataclasses import dataclass

from endorlabs.workflows.reachability.resolve import (
    resolve_from_finding,
    resolve_from_package_version,
)


@dataclass
class _Resp:
    _payload: dict

    def json(self):
        return self._payload


@dataclass
class _Api:
    payloads: dict

    def get(self, path, **_kwargs):
        return _Resp(self.payloads[path])


def test_resolve_from_finding_cross_namespace() -> None:
    finding_uuid = "f-1"
    dep_uuid = "dm-1"
    api = _Api(
        {
            f"v1/namespaces/acme/findings/{finding_uuid}": {
                "uuid": finding_uuid,
                "spec": {"target_uuid": dep_uuid, "extra_key": "CVE-1"},
            },
            f"v1/namespaces/acme/dependency-metadata/{dep_uuid}": {
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
            },
        }
    )
    subject, finding, dep = resolve_from_finding(
        api, namespace="acme", finding_uuid=finding_uuid
    )
    assert finding["uuid"] == finding_uuid
    assert dep["uuid"] == dep_uuid
    assert subject.importer_pv_uuid == "pv-importer"
    assert subject.oss_namespace == "oss"
    assert subject.oss_package_version_uuid == "pv-oss"


def test_resolve_from_package_version() -> None:
    api = _Api(
        {
            "v1/namespaces/acme/package-versions/pv-1": {
                "uuid": "pv-1",
                "meta": {"name": "npm://pkg@1.0.0"},
                "spec": {"project_uuid": "proj-1"},
            }
        }
    )
    subject, pv = resolve_from_package_version(
        api, namespace="acme", package_version_uuid="pv-1"
    )
    assert pv["uuid"] == "pv-1"
    assert subject.importer_pv_uuid == "pv-1"
    assert subject.project_uuid == "proj-1"
