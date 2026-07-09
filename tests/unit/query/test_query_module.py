"""Tests for endorlabs.query module."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from endorlabs.filters import project_uuid_in_filter, to_query_filter
from endorlabs.query import (
    QueryExecutor,
    QuerySpec,
    Reference,
    dm_count_spec,
    estate_findings_list_spec,
    extract_query_objects,
    group_projects_by_namespace,
    next_page_token,
    parse_group_bucket_counts,
    parse_project_multi_reference_counts,
    parse_project_reference_counts,
    parse_project_reference_list_totals,
    parse_query_root_count,
    pv_count_spec,
    query_create_pages,
    reference_next_page_cursor,
    reference_next_page_token,
    reference_total,
    scopes_from_projects,
    wire_spec_with_reference_page_token,
)
from endorlabs.query.project_facade import ProjectQueryFacade

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
    assert wire["list_parameters"]["traverse"] is False
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
    assert (
        ref["query_spec"]["list_parameters"]["filter"]
        == "context.type==CONTEXT_TYPE_MAIN"
    )


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


def test_dm_count_spec_wire_shape() -> None:
    spec = dm_count_spec()
    wire = spec.to_wire()
    assert wire["kind"] == "Project"
    refs = wire["references"]
    assert len(refs) == 1
    assert refs[0]["query_spec"]["kind"] == "DependencyMetadata"


def test_count_pv_posts_to_leaf_namespace() -> None:
    client = _FakeClient()
    projects = [
        SimpleNamespace(uuid="p1", namespace="tenant.leaf"),
    ]
    project_query = ProjectQueryFacade(client, client.Query)
    counts = project_query.count_pv(projects)
    assert counts == {"proj-a": 42, "proj-b": 7}
    assert client.Query.calls[0][0] == "tenant.leaf"


def test_query_executor_merges_multiple_namespaces() -> None:
    client = _FakeClient()
    projects = [
        SimpleNamespace(uuid="p1", namespace="tenant.ns-a"),
        SimpleNamespace(uuid="p2", namespace="tenant.ns-b"),
    ]
    executor = QueryExecutor(client, name_prefix="test")
    merged = executor.execute(
        pv_count_spec(),
        scopes=scopes_from_projects(projects),
        parse_page=lambda r: parse_project_reference_counts(r, "PackageVersion"),
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
    project_query = ProjectQueryFacade(client, client.Query)
    counts = project_query.count_findings_by_category(projects)
    assert counts == {
        "proj-a": {
            "VULNERABILITY": 10,
            "SECRETS": 2,
            "MALWARE": 0,
        }
    }


def test_to_query_filter_strips_quoted_enums() -> None:
    assert (
        to_query_filter('context.type=="CONTEXT_TYPE_MAIN"')
        == "context.type==CONTEXT_TYPE_MAIN"
    )


def test_parse_group_bucket_counts_from_fixture() -> None:
    payload = _load_fixture("group_response.json")
    counts = parse_group_bucket_counts(payload)
    assert counts["2026-07-01T00:00:00Z"] == 12
    assert counts["2026-07-02T00:00:00Z"] == 5


def test_reference_total_prefers_count_ref() -> None:
    payload = _load_fixture("finding_list_ref_response.json")
    objs = extract_query_objects(payload)
    assert reference_total(objs[0], "Finding") == 796
    assert parse_project_reference_list_totals(payload, "Finding") == {"proj-a": 796}


def test_next_page_token_from_fixture() -> None:
    payload = _load_fixture("paginated_root_response.json")
    assert next_page_token(payload) == 100


def test_parse_query_root_count_from_fixture() -> None:
    payload = _load_fixture("finding_root_count_response.json")
    assert parse_query_root_count(payload) == 917


def test_query_create_pages_stops_at_last_token() -> None:
    calls: list[dict[str, Any]] = []

    class _PagingClient:
        def __init__(self) -> None:
            super().__init__()
            self.Query = self

        def create(self, *, payload: Any, namespace: str) -> dict[str, Any]:
            _ = namespace
            spec = payload.spec["query_spec"]
            calls.append(spec)
            token = (spec.get("list_parameters") or {}).get("page_token")
            if token is None:
                return _load_fixture("paginated_root_response.json")
            return _load_fixture("pv_count_response.json")

    pages = query_create_pages(
        _PagingClient(),
        namespace="tenant.leaf",
        name="test-pages",
        query_spec={"kind": "Project", "list_parameters": {}},
    )
    assert len(pages) == 2
    assert calls[1]["list_parameters"]["page_token"] == 100


def test_reference_next_page_token_from_fixture() -> None:
    payload = _load_fixture("finding_list_ref_page1.json")
    objs = extract_query_objects(payload)
    assert reference_next_page_token(objs[0], "Finding") == 100


def test_wire_spec_with_reference_page_token() -> None:
    wire = estate_findings_list_spec().for_scope_batch(("proj-a",))
    updated = wire_spec_with_reference_page_token(wire, "Finding", 100)
    ref = updated["references"][0]["query_spec"]["list_parameters"]
    assert ref["page_token"] == 100


def test_reference_next_page_cursor_prefers_token_over_page_id() -> None:
    obj = {
        "meta": {
            "references": {
                "Finding": {
                    "list": {
                        "response": {
                            "next_page_token": 100,
                            "next_page_id": "page-id-1",
                        }
                    }
                }
            }
        }
    }
    from endorlabs.operations.pagination import PageCursor

    cursor = reference_next_page_cursor(obj, "Finding")
    assert cursor == PageCursor(page_token=100)


def test_reference_next_page_cursor_falls_back_to_page_id() -> None:
    obj = {
        "meta": {
            "references": {
                "Finding": {
                    "list": {
                        "response": {
                            "next_page_id": "page-id-1",
                        }
                    }
                }
            }
        }
    }
    from endorlabs.operations.pagination import PageCursor

    cursor = reference_next_page_cursor(obj, "Finding")
    assert cursor == PageCursor(page_id="page-id-1")


def test_collect_reference_rows_paginates_nested_list() -> None:
    calls: list[dict[str, Any]] = []

    class _CollectClient:
        def __init__(self) -> None:
            super().__init__()
            self.Query = self

        def create(self, *, payload: Any, namespace: str) -> dict[str, Any]:
            _ = namespace
            spec = payload.spec["query_spec"]
            calls.append(spec)
            refs = spec.get("references") or []
            ref_lp = refs[0]["query_spec"]["list_parameters"] if refs else {}
            token = ref_lp.get("page_token")
            if token is None:
                return _load_fixture("finding_list_ref_page1.json")
            if token == 100:
                return _load_fixture("finding_list_ref_page2.json")
            raise AssertionError(f"unexpected page_token {token!r}")

    spec = estate_findings_list_spec()
    scope = scopes_from_projects(
        [SimpleNamespace(uuid="proj-a", namespace="tenant.leaf")]
    )[0]
    merged = QueryExecutor(_CollectClient()).collect_reference_rows(
        spec,
        scopes=[scope],
        ref_keys=("Finding",),
    )
    rows = merged["proj-a"]
    assert [row["uuid"] for row in rows] == ["f-001", "f-002", "f-101", "f-102"]
    assert len(calls) == 2
    assert (
        calls[1]["references"][0]["query_spec"]["list_parameters"]["page_token"] == 100
    )
