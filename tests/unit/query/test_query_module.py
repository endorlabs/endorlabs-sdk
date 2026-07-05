"""Tests for endorlabs.query module."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from endorlabs.query import (
    QueryExecutor,
    QuerySpec,
    Reference,
    count_findings_by_category,
    count_pv_by_project,
    group_projects_by_namespace,
    parse_project_multi_reference_counts,
    parse_project_reference_counts,
    project_uuid_in_filter,
    pv_count_spec,
)

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "query"


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def test_project_uuid_in_filter() -> None:
    filt = project_uuid_in_filter(["a", "b"])
    assert filt == 'uuid in ["a", "b"]'


def test_group_projects_by_namespace() -> None:
    projects = [
        SimpleNamespace(uuid="p1", namespace="tenant.child-a"),
        SimpleNamespace(uuid="p2", namespace="tenant.child-a"),
        SimpleNamespace(uuid="p3", namespace="tenant.child-b"),
    ]
    grouped = group_projects_by_namespace(projects)
    assert grouped == {
        "tenant.child-a": ["p1", "p2"],
        "tenant.child-b": ["p3"],
    }


def test_parse_project_reference_counts_from_fixture() -> None:
    payload = _load_fixture("pv_count_response.json")
    counts = parse_project_reference_counts(payload, "PackageVersion")
    assert counts == {"proj-a": 42, "proj-b": 7}


def test_parse_project_multi_reference_counts_from_fixture() -> None:
    payload = _load_fixture("finding_count_response.json")
    ref_keys = [
        "VulnerabilityFindingsCount",
        "SecretsFindingsCount",
        "MalwareFindingsCount",
    ]
    counts = parse_project_multi_reference_counts(payload, ref_keys)
    assert counts == {
        "proj-a": {
            "VulnerabilityFindingsCount": 10,
            "SecretsFindingsCount": 2,
            "MalwareFindingsCount": 0,
        }
    }


def test_pv_count_spec_wire_shape() -> None:
    wire = pv_count_spec().for_namespace_batch(["proj-1"])
    assert wire["kind"] == "Project"
    assert wire["list_parameters"]["filter"] == 'uuid in ["proj-1"]'
    assert wire["references"][0]["query_spec"]["kind"] == "PackageVersion"
    assert wire["references"][0]["query_spec"]["list_parameters"]["count"] is True


def test_query_spec_reference_builder() -> None:
    spec = (
        QuerySpec.root("Project")
        .mask("uuid")
        .reference(
            Reference("Finding", return_as="VulnCount")
            .connect("uuid", "spec.project_uuid")
            .count(filter="context.type==CONTEXT_TYPE_MAIN")
        )
    )
    wire = spec.to_wire()
    ref = wire["references"][0]
    assert ref["query_spec"]["return_as"] == "VulnCount"


class _FakeQueryFacade:
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def create(self, *, payload: Any, namespace: str) -> dict[str, Any]:
        _ = payload
        self.calls.append((namespace, payload.meta["name"], {}))
        return _load_fixture("pv_count_response.json")


class _FakeClient:
    def __init__(self) -> None:
        super().__init__()
        self._default_namespace = "tenant.root"
        self.Query = _FakeQueryFacade()


def test_count_pv_by_project_posts_to_leaf_namespace() -> None:
    client = _FakeClient()
    projects = [
        SimpleNamespace(uuid="p1", namespace="tenant.leaf"),
    ]
    counts = count_pv_by_project(client, projects)
    assert counts == {"proj-a": 42, "proj-b": 7}
    assert client.Query.calls[0][0] == "tenant.leaf"


def test_query_executor_merges_multiple_namespaces() -> None:
    client = _FakeClient()
    projects = [
        SimpleNamespace(uuid="p1", namespace="tenant.ns-a"),
        SimpleNamespace(uuid="p2", namespace="tenant.ns-b"),
    ]
    executor = QueryExecutor(client, name_prefix="test")
    merged = executor.run(
        pv_count_spec(),
        projects=projects,
        parse_result=lambda r: parse_project_reference_counts(r, "PackageVersion"),
    )
    assert merged == {"proj-a": 42, "proj-b": 7}
    assert len(client.Query.calls) == 2
    namespaces = {call[0] for call in client.Query.calls}
    assert namespaces == {"tenant.ns-a", "tenant.ns-b"}


def test_count_findings_by_category_relabels_refs() -> None:
    client = _FakeClient()

    def _fake_create(*, payload: Any, namespace: str) -> dict[str, Any]:
        _ = payload
        client.Query.calls.append((namespace, "finding", {}))
        return _load_fixture("finding_count_response.json")

    client.Query.create = _fake_create
    projects = [SimpleNamespace(uuid="p1", namespace="tenant.leaf")]
    counts = count_findings_by_category(client, projects)
    assert counts == {
        "proj-a": {
            "VULNERABILITY": 10,
            "SECRETS": 2,
            "MALWARE": 0,
        }
    }
