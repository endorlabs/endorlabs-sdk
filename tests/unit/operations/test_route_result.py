"""RouteResult collection protocol for relationship accessors."""

from __future__ import annotations

from dataclasses import dataclass

from endorlabs.operations.routes import RouteResult


@dataclass
class _Row:
    uuid: str


def test_route_result_iterates_values() -> None:
    rows = [_Row("a"), _Row("b")]
    result = RouteResult(edge_used="test.edge", values=rows)
    assert list(result) == rows
    assert len(result) == 2
    assert result


def test_route_result_iterates_single_value() -> None:
    row = _Row("only")
    result = RouteResult(edge_used="test.edge", value=row)
    assert list(result) == [row]
    assert len(result) == 1
    assert result


def test_route_result_empty_is_falsy() -> None:
    result = RouteResult(edge_used="test.edge")
    assert list(result) == []
    assert len(result) == 0
    assert not result
