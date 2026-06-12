"""Tests for list/group wire response parsing."""

from __future__ import annotations

from endorlabs.operations.list_response import (
    GroupBucket,
    count_from_wire,
    extract_list_objects,
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
