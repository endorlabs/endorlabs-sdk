"""Unit tests for generic log group-by-time helpers."""

from __future__ import annotations

from endorlabs.core.exceptions import NetworkError, ServerError
from endorlabs.core.types import ListParameters
from endorlabs.operations.list_response import GroupBucket
from endorlabs.workflows.logs.group_by_time import (
    buckets_to_counts,
    group_bucket_count,
    group_bucket_time_key,
    group_by_time_counts,
    is_timeout_like,
    parse_bucket_key,
)


def test_group_bucket_count_prefers_aggregation_count() -> None:
    bucket = GroupBucket(
        key='"2026-01-04T00:00:00Z"',
        parsed={"meta.create_time": "2026-01-04T00:00:00Z"},
        data={"aggregation_count": {"count": 7}},
        count=0,
    )
    assert group_bucket_count(bucket) == 7


def test_buckets_to_counts() -> None:
    bucket = GroupBucket(
        key='"2026-01-04T00:00:00Z"',
        parsed={"meta.create_time": "2026-01-04T00:00:00Z"},
        data={"aggregation_count": {"count": 4}},
        count=0,
    )
    assert buckets_to_counts([bucket]) == {"2026-01-04T00:00:00Z": 4}


def test_parse_bucket_key_strips_quotes() -> None:
    assert parse_bucket_key('"2026-01-04T00:00:00Z"') == "2026-01-04T00:00:00Z"


def test_group_bucket_time_key_from_parsed() -> None:
    bucket = GroupBucket(
        key="ignored",
        parsed={"meta.create_time": "2026-01-04T00:00:00Z"},
        data={},
        count=1,
    )
    assert group_bucket_time_key(bucket) == "2026-01-04T00:00:00Z"


def test_group_by_time_counts_wires_list_groups() -> None:
    bucket = GroupBucket(
        key='"2026-01-04T00:00:00Z"',
        parsed={"meta.create_time": "2026-01-04T00:00:00Z"},
        data={"aggregation_count": {"count": 5}},
        count=0,
    )
    captured: dict[str, object] = {}

    def list_groups(**kwargs: object) -> list[GroupBucket]:
        captured.update(kwargs)
        list_params = kwargs.get("list_params")
        assert isinstance(list_params, ListParameters)
        assert list_params.group_by_time is True
        assert list_params.group_by_time_interval == "day"
        return [bucket]

    counts = group_by_time_counts(
        list_groups,
        namespace="tenant",
        filter="spec.operation==OPERATION_CREATE",
        traverse=False,
        interval="day",
    )
    assert counts == {"2026-01-04T00:00:00Z": 5}
    assert captured["namespace"] == "tenant"
    assert captured["traverse"] is False


def test_is_timeout_like_detects_gateway_and_network_errors() -> None:
    assert is_timeout_like(ServerError("gateway timeout", status_code=504)) is True
    assert is_timeout_like(NetworkError("read timeout exceeded")) is True
    assert is_timeout_like(RuntimeError("deadline exceeded")) is True
    assert is_timeout_like(ValueError("not found")) is False
