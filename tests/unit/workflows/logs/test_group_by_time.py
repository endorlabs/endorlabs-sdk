"""Unit tests for generic log group-by-time helpers."""

from __future__ import annotations

from endorlabs.operations.list_response import GroupBucket
from endorlabs.workflows.logs.group_by_time import (
    buckets_to_counts,
    group_bucket_count,
    group_bucket_time_key,
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
