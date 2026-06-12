"""Tests for route contract schema validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from endorlabs.operations.route_contract import (
    RouteContract,
    RouteEdge,
    load_golden_contract,
)

FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "routes" / "golden_edges.json"
)


def test_golden_fixture_loads() -> None:
    contract = RouteContract.load_json(FIXTURE)
    assert len(contract.edges) >= 5
    ids = {edge.id for edge in contract.edges}
    assert "project.findings" in ids
    assert "scan.findings" in ids


def test_edge_by_id() -> None:
    contract = load_golden_contract()
    edge = contract.edge_by_id("project.findings")
    assert edge is not None
    assert edge.to_kind == "Finding"
    assert edge.public_method == "Finding.list_by_project"


def test_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="Duplicate"):
        RouteContract.from_dict(
            {
                "edges": [
                    {
                        "id": "a",
                        "from_kind": "P",
                        "to_kind": "F",
                        "edge": "get_by_uuid",
                    },
                    {
                        "id": "a",
                        "from_kind": "P",
                        "to_kind": "F",
                        "edge": "get_by_uuid",
                    },
                ]
            }
        )


def test_rejects_unknown_edge_kind() -> None:
    with pytest.raises(ValueError, match="Invalid or missing edge kind"):
        RouteEdge.from_dict(
            {"id": "x", "from_kind": "P", "to_kind": "F", "edge": "unknown_kind"}
        )


def test_scan_findings_is_list_only() -> None:
    edge = load_golden_contract().edge_by_id("scan.findings")
    assert edge is not None
    assert edge.list_only is True
    assert edge.filter_field == "context.scan_uuid"
