"""Tests for client.Query facade and Project sub-facade."""

from __future__ import annotations

from unittest.mock import MagicMock

from endorlabs.facade.specialized import QueryFacade


def test_query_facade_has_project_subfacade() -> None:
    api = MagicMock()
    facade = QueryFacade(api, "tenant")
    assert hasattr(facade, "Project")
    assert hasattr(facade.Project, "count_pv")
    assert hasattr(facade.Project, "collect")
    assert hasattr(facade.Project, "discover")


def test_query_execute_delegates_to_executor() -> None:
    import json
    from pathlib import Path

    from endorlabs.query.parse import parse_project_reference_counts
    from endorlabs.query.recipes import pv_count_spec
    from endorlabs.query.scope import QueryScope

    fixture = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "fixtures"
            / "query"
            / "pv_count_response.json"
        ).read_text(encoding="utf-8")
    )
    api = MagicMock()
    facade = QueryFacade(api, "tenant")
    api.Query = facade
    facade.create = MagicMock(return_value=fixture)
    counts = facade.execute(
        pv_count_spec(),
        [QueryScope(namespace="tenant.child", keys=("p1",))],
        parse=lambda result: parse_project_reference_counts(result, "PackageVersion"),
    )
    assert counts == {"proj-a": 42, "proj-b": 7}


def test_query_at_namespace_merges_pages() -> None:
    from endorlabs.query.spec import QuerySpec

    api = MagicMock()
    facade = QueryFacade(api, "tenant")
    api.Query = facade
    facade.create = MagicMock(
        side_effect=[
            {"list": {"objects": [{"uuid": "a"}]}},
            {"list": {"objects": []}},
        ]
    )
    spec = QuerySpec.root("Finding").leaf_scope()
    rows = facade.at_namespace(
        spec,
        "tenant",
        parse=lambda page: page.get("list", {}).get("objects", []),
        merge=lambda pages: [row for page in pages for row in page],
        max_pages=2,
    )
    assert rows == [{"uuid": "a"}]
