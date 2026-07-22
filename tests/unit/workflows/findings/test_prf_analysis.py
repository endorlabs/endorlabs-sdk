"""Unit tests for PRF finding aggregation helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from endorlabs.tools.list_sharding import ProjectShard
from endorlabs.workflows.findings.prf_analysis import (
    aggregate_prf_metrics,
    fetch_parent_package_versions,
    findings_by_parent,
    list_findings_sharded,
    list_findings_tenant,
    parent_uuids_by_eco,
    parent_uuids_by_namespace,
)


def test_aggregate_prf_metrics_counts_ecosystem_approximation_and_prd() -> None:
    findings = [
        {
            "meta": {"parent_uuid": "pv-1"},
            "spec": {
                "ecosystem": "ECOSYSTEM_NPM",
                "approximation": True,
                "finding_tags": ["FINDING_TAGS_POTENTIALLY_REACHABLE_DEPENDENCY"],
            },
        },
        {
            "meta": {"parent_uuid": "pv-2"},
            "spec": {
                "ecosystem": "ECOSYSTEM_NPM",
                "approximation": False,
                "finding_tags": [],
            },
        },
        {
            "meta": {"parent_uuid": "pv-3"},
            "spec": {
                "ecosystem": "ECOSYSTEM_PYPI",
                "approximation": "true",
                "finding_tags": [],
            },
        },
    ]

    prf, approx, not_approx, prd = aggregate_prf_metrics(findings)

    assert prf == {"NPM": 2, "PYPI": 1}
    assert approx == {"NPM": 1, "PYPI": 1}
    assert not_approx == {"NPM": 1}
    assert prd == {"NPM": 1}


def test_parent_uuids_by_eco_groups_parents() -> None:
    findings = [
        {
            "meta": {"parent_uuid": "pv-1"},
            "spec": {"ecosystem": "ECOSYSTEM_MAVEN"},
        },
        {
            "meta": {"parent_uuid": "pv-2"},
            "spec": {"ecosystem": "ECOSYSTEM_MAVEN"},
        },
    ]

    grouped = parent_uuids_by_eco(findings)

    assert grouped["MAVEN"] == {"pv-1", "pv-2"}


def test_parent_uuids_by_namespace_groups_and_tracks_orphans() -> None:
    findings = [
        {
            "meta": {"parent_uuid": "pv-1"},
            "tenant_meta": {"namespace": "tenant.child"},
        },
        {
            "meta": {"parent_uuid": "pv-2"},
            "tenant_meta": {},
        },
    ]

    by_ns, orphans = parent_uuids_by_namespace(findings, {"pv-1", "pv-2"})

    assert by_ns == {"tenant.child": {"pv-1"}}
    assert orphans == {"pv-2"}


def test_findings_by_parent_counts() -> None:
    findings = [
        {"meta": {"parent_uuid": "pv-1"}},
        {"meta": {"parent_uuid": "pv-1"}},
        {"meta": {}},
    ]
    counts = findings_by_parent(findings)
    assert counts["pv-1"] == 2


def test_list_findings_sharded_scopes_by_project_uuid() -> None:
    client = MagicMock()
    client.Finding.list_by_project.return_value = [
        {"meta": {"parent_uuid": "pv-1"}, "spec": {"ecosystem": "ECOSYSTEM_NPM"}}
    ]
    shards = [
        ProjectShard(project_uuid="proj-1", namespace="tenant.child", label="child")
    ]

    rows = list_findings_sharded(
        client,
        shards,
        "context.type==CONTEXT_TYPE_MAIN",
        mask="meta.parent_uuid",
    )

    assert len(rows) == 1
    client.Finding.list_by_project.assert_called_once()
    args, kwargs = client.Finding.list_by_project.call_args
    project = args[0]
    assert project.uuid == "proj-1"
    assert project.namespace == "tenant.child"
    assert kwargs["filter"] == "context.type==CONTEXT_TYPE_MAIN"
    assert kwargs["mask"] == "meta.parent_uuid"


def test_list_findings_sharded_passes_max_pages_none_explicitly() -> None:
    """Regression: omitting max_pages (vs. passing None) reintroduces silent
    truncation — the route executor backing Finding.list_by_project defaults
    to max_pages=1 when the keyword is absent entirely from the call.
    """
    client = MagicMock()
    client.Finding.list_by_project.return_value = []
    shards = [
        ProjectShard(project_uuid="proj-1", namespace="tenant.child", label="child")
    ]

    list_findings_sharded(
        client,
        shards,
        "context.type==CONTEXT_TYPE_MAIN",
        mask="meta.parent_uuid",
    )

    _, kwargs = client.Finding.list_by_project.call_args
    assert "max_pages" in kwargs
    assert kwargs["max_pages"] is None


def test_list_findings_tenant_uses_traverse_when_namespace_shared() -> None:
    client = MagicMock()
    client.Finding.list_iter.return_value = [
        {"meta": {"parent_uuid": "pv-1"}, "spec": {"ecosystem": "ECOSYSTEM_NPM"}}
    ]
    client.Query.Project.discover.return_value = SimpleNamespace(
        project_shards=lambda: [
            ProjectShard(project_uuid="p-1", namespace="tenant.child", label="a"),
            ProjectShard(project_uuid="p-2", namespace="tenant.child", label="b"),
        ]
    )

    rows = list_findings_tenant(
        client,
        "tenant",
        "context.type==CONTEXT_TYPE_MAIN",
        mask="meta.parent_uuid",
    )

    assert len(rows) == 1
    client.Finding.list_iter.assert_called_once()
    kwargs = client.Finding.list_iter.call_args.kwargs
    assert kwargs["namespace"] == "tenant.child"
    assert kwargs["traverse"] is True
    assert "spec.project_uuid" not in kwargs["filter"]


def test_list_findings_tenant_defaults_to_sharded() -> None:
    client = MagicMock()
    client.Finding.list_by_project.return_value = []
    client.Query.Project.discover.return_value = SimpleNamespace(
        project_shards=lambda: [
            ProjectShard(project_uuid="p-1", namespace="tenant.child-a", label="a"),
            ProjectShard(project_uuid="p-2", namespace="tenant.child-b", label="b"),
        ]
    )

    rows = list_findings_tenant(
        client,
        "tenant",
        "context.type==CONTEXT_TYPE_MAIN",
        mask="meta.parent_uuid",
    )

    assert rows == []
    assert client.Finding.list_by_project.call_count == 2
    first_project = client.Finding.list_by_project.call_args_list[0].args[0]
    assert first_project.uuid == "p-1"
    assert first_project.namespace == "tenant.child-a"


def test_fetch_parent_package_versions_groups_by_namespace() -> None:
    client = MagicMock()
    client.PackageVersion.list_iter.return_value = [
        {"uuid": "pv-1", "spec": {"resolution_errors": {}}}
    ]
    findings = [
        {
            "meta": {"parent_uuid": "pv-1"},
            "tenant_meta": {"namespace": "tenant.child"},
        }
    ]

    pvs = fetch_parent_package_versions(
        client,
        "tenant",
        findings,
        {"pv-1"},
        pv_filter="context.type==CONTEXT_TYPE_MAIN",
    )

    assert pvs["pv-1"]["uuid"] == "pv-1"
    kwargs = client.PackageVersion.list_iter.call_args.kwargs
    assert kwargs["namespace"] == "tenant.child"
    assert kwargs["traverse"] is False
