"""Tests for facade search helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from endorlabs.facade.search import search_substring_on_fields


def test_search_substring_on_fields_matches_name() -> None:
    facade = Mock()
    facade._ns = Mock(return_value="tenant")
    facade.list = Mock(
        return_value=[
            SimpleNamespace(uuid="1", meta=SimpleNamespace(name="github.com/org/a")),
            SimpleNamespace(uuid="2", meta=SimpleNamespace(name="other")),
        ]
    )
    out = search_substring_on_fields(
        facade,
        query="org/a",
        field_paths=("meta.name",),
        namespace="tenant",
    )
    assert len(out) == 1
    assert out[0].uuid == "1"


def test_search_forwards_mask_to_list() -> None:
    facade = Mock()
    facade._ns = Mock(return_value="tenant")
    facade.list = Mock(return_value=[])
    search_substring_on_fields(
        facade,
        query="x",
        field_paths=("meta.name",),
        mask="uuid,meta.name",
        max_pages=1,
    )
    facade.list.assert_called_once()
    assert facade.list.call_args.kwargs.get("mask") == "uuid,meta.name"


def test_search_policy_by_claims_matches_name() -> None:
    from endorlabs.facade.search import search_policy_by_claims

    facade = Mock()
    facade._ns = Mock(return_value="tenant")
    policy = SimpleNamespace(
        meta=SimpleNamespace(name="sso-group-policy"),
        spec=SimpleNamespace(clause=[], target_namespaces=[]),
    )
    facade.list = Mock(return_value=[policy])
    out = search_policy_by_claims(facade, query="sso-group", max_pages=2)
    assert out == [policy]


def test_search_rejects_count_true() -> None:
    facade = Mock()
    with pytest.raises(ValueError, match="count=True"):
        search_substring_on_fields(
            facade,
            query="x",
            field_paths=("meta.name",),
            count=True,
        )
