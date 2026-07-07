"""Tests for workflows.query_collect helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock


def test_collect_project_findings_via_query_estate() -> None:
    client = MagicMock()
    client.Query.Project.collect_estate_findings.return_value = [{"uuid": "f1"}]
    from endorlabs.workflows.query_collect import collect_project_findings_via_query

    rows = collect_project_findings_via_query(
        client,
        [SimpleNamespace(uuid="p1")],
        mask="uuid",
    )
    assert rows == [{"uuid": "f1"}]
    client.Query.Project.collect_estate_findings.assert_called_once()
