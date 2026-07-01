"""Tests for group_by_time wire serialization."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from endorlabs.core.types import ListParameters
from endorlabs.operations import BaseResourceOperations
from endorlabs.operations.group_by_time_wire import (
    GROUP_BY_TIME_INTERVAL_ALIASES,
    add_group_by_time_wire_params,
    normalize_group_by_time_interval,
)


@pytest.mark.parametrize(
    ("alias", "wire"),
    sorted(GROUP_BY_TIME_INTERVAL_ALIASES.items()),
)
def test_normalize_group_by_time_interval_aliases(alias: str, wire: str) -> None:
    assert normalize_group_by_time_interval(alias) == wire
    assert normalize_group_by_time_interval(alias.upper()) == wire


def test_normalize_group_by_time_interval_passes_enum() -> None:
    assert (
        normalize_group_by_time_interval("GROUP_BY_TIME_INTERVAL_DAY")
        == "GROUP_BY_TIME_INTERVAL_DAY"
    )


def test_normalize_group_by_time_interval_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unsupported group_by_time_interval"):
        normalize_group_by_time_interval("fortnight")


def test_add_group_by_time_wire_params_field_value_prepend() -> None:
    params: dict[str, str] = {}
    list_params = ListParameters(
        group_by_time_field_value="meta.create_time",
        group_aggregation_paths=["spec.level"],
        group_by_time_interval="day",
        group_by_time_mode="count",
    )
    add_group_by_time_wire_params(params, list_params)
    assert params["list_parameters.group_by_time.aggregation_paths"] == (
        "meta.create_time,spec.level"
    )
    assert params["list_parameters.group_by_time.interval"] == (
        "GROUP_BY_TIME_INTERVAL_DAY"
    )
    assert params["list_parameters.group_by_time.mode"] == "count"


def test_field_grouping_without_time_uses_legacy_group_paths() -> None:
    client = Mock()
    ops = BaseResourceOperations(client, "test-resources", Mock)
    params = ops._build_params(
        ListParameters(group_aggregation_paths=["meta.name"], group_by_time=False)
    )
    assert params["list_parameters.group.aggregation_paths"] == "meta.name"
    assert params["list_parameters.group_by_time"] == "false"
