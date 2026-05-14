"""Tests for BaseResourceOperations.list / list_iter with field masks."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field

from endorlabs.core.types import ListParameters
from endorlabs.operations import BaseResourceOperations


class _Widget(BaseModel):
    uuid: str = Field(..., description="id")
    meta: dict[str, object] = Field(default_factory=dict)


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client.get_all = MagicMock(
        return_value=[{"uuid": "w1", "meta": {"name": "one"}}],
    )
    return client


def test_list_with_nonempty_mask_returns_dict_rows(mock_client: MagicMock) -> None:
    ops = BaseResourceOperations(mock_client, "widgets", _Widget)
    out = ops.list(
        "tenant.ns",
        ListParameters(mask="uuid"),
        max_pages=1,
    )
    assert out == [{"uuid": "w1", "meta": {"name": "one"}}]
    assert isinstance(out[0], dict)
    mock_client.get_all.assert_called_once()


def test_list_without_mask_returns_models(mock_client: MagicMock) -> None:
    ops = BaseResourceOperations(mock_client, "widgets", _Widget)
    out = ops.list("tenant.ns", None, max_pages=1)
    assert len(out) == 1
    assert isinstance(out[0], _Widget)
    assert out[0].uuid == "w1"


def test_list_iter_with_mask_yields_dicts(mock_client: MagicMock) -> None:
    ops = BaseResourceOperations(mock_client, "widgets", _Widget)
    rows = list(
        ops.list_iter(
            "tenant.ns",
            ListParameters(mask="uuid"),
            max_pages=1,
        )
    )
    assert rows == [{"uuid": "w1", "meta": {"name": "one"}}]
    assert isinstance(rows[0], dict)
