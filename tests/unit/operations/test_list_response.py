"""Tests for list/group wire response parsing."""

from __future__ import annotations

from endorlabs.operations.list_response import (
    GroupBucket,
    count_from_wire,
    extract_list_objects,
    group_bucket_count,
    iter_group_buckets_from_page,
    iter_group_buckets_from_pages,
    parse_group_key,
)


def test_parse_group_key_json() -> None:
    key = '[{"key":"spec.package","value":"requests"}]'
    parsed = parse_group_key(key)
    assert parsed["spec.package"] == "requests"


def test_count_from_wire() -> None:
    assert count_from_wire({"count": 3}) == 3
    assert count_from_wire({"count_response": {"count": 5}}) == 5
    assert count_from_wire({"aggregation_count": {"count": 7}}) == 7
    assert count_from_wire({}) == 0


def test_extract_list_objects() -> None:
    data = {"list": {"objects": [{"uuid": "a"}, {"uuid": "b"}]}}
    assert len(extract_list_objects(data)) == 2
    assert extract_list_objects({}) == []


def test_iter_group_buckets_from_page() -> None:
    page = {
        "group_response": {
            "groups": {
                '["k"]': {"count": 2},
            }
        }
    }
    rows = list(iter_group_buckets_from_page(page))
    assert rows == [('["k"]', {"count": 2})]


def test_iter_group_buckets_from_pages_yields_group_bucket() -> None:
    pages = iter(
        [
            {
                "group_response": {
                    "groups": {
                        '["pkg"]': {"count": 1},
                    }
                }
            }
        ]
    )
    bucket = next(iter_group_buckets_from_pages(pages))
    assert isinstance(bucket, GroupBucket)
    assert bucket.count == 1


def test_iter_group_buckets_reads_aggregation_count() -> None:
    """Finding/DM list_groups wire has no top-level count (zeros if missed)."""
    key = (
        '[{"key":"spec.target_dependency_package_name","value":"mvn://org.example:lib"},'
        '{"key":"spec.target_dependency_version","value":"1.0.0"}]'
    )
    pages = iter(
        [
            {
                "group_response": {
                    "groups": {
                        key: {"aggregation_count": {"count": 12}},
                    }
                }
            }
        ]
    )
    bucket = next(iter_group_buckets_from_pages(pages))
    assert bucket.count == 12
    assert group_bucket_count(bucket) == 12
    assert (
        bucket.parsed["spec.target_dependency_package_name"] == "mvn://org.example:lib"
    )
    assert bucket.parsed["spec.target_dependency_version"] == "1.0.0"


def test_group_bucket_count_preserves_explicit_zero() -> None:
    bucket = GroupBucket(
        key="[]",
        parsed={},
        data={"aggregation_count": {"count": 0}},
        count=9,
    )
    assert group_bucket_count(bucket) == 0
