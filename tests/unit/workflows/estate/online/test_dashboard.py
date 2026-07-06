"""Tests for online Query-backed estate dashboard counts."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from endorlabs.workflows.estate.online.dashboard import (
    ONLINE_DASHBOARD_SCHEMA,
    fetch_online_dashboard_counts,
)


def test_fetch_online_dashboard_counts_merges_recipes() -> None:
    client = MagicMock()
    topo = SimpleNamespace(
        tenant="tenant.root",
        archetype="estate_sprawl",
        project_count=2,
        duplicate_name_groups=[],
        projects=[
            SimpleNamespace(uuid="p1", name="a", namespace="tenant.child"),
            SimpleNamespace(uuid="p2", name="b", namespace="tenant.child"),
        ],
    )
    project_query = MagicMock()
    project_query.discover.return_value = topo
    project_query.validate_sample.return_value = SimpleNamespace(
        matched=True, to_dict=dict
    )
    project_query.count_pv.return_value = {"p1": 3, "p2": 5}
    project_query.count_findings_by_category.return_value = {"p1": {"VULNERABILITY": 1}}
    project_query.count_dm.return_value = {"p1": 10, "p2": 2}
    client.Query.Project = project_query

    result = fetch_online_dashboard_counts(
        client,
        "tenant.root",
        validate=True,
        sample_size=2,
    )

    payload = result.to_dict()
    assert payload["schema"] == ONLINE_DASHBOARD_SCHEMA
    assert payload["totals"]["pv"] == 8
    assert payload["totals"]["dm"] == 12
    assert payload["routing"]["primary"] == "query"
