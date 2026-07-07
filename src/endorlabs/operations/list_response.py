"""Parse list/group wire JSON from API responses."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, cast

from endorlabs.workflows.wire_access import as_dict, nested_dict


@dataclass(frozen=True)
class GroupBucket:
    """One grouped aggregation bucket from ``group_response`` pagination."""

    key: str
    parsed: dict[str, str]
    data: dict[str, Any]
    count: int


def parse_group_key(group_key: str) -> dict[str, str]:
    """Parse a group index key into ``{field_path: value}``."""
    try:
        payload = json.loads(group_key)
    except json.JSONDecodeError:
        return {"_raw": group_key}
    if not isinstance(payload, list):
        return {"_raw": group_key}
    parsed: dict[str, str] = {}
    for raw_entry in cast("list[Any]", payload):
        if not isinstance(raw_entry, dict):
            continue
        entry = cast("dict[str, Any]", raw_entry)
        if "key" in entry and "value" in entry:
            parsed[str(entry["key"])] = str(entry["value"])
    return parsed


def count_from_wire(block: Any) -> int:
    """Extract integer count from ``count_response``-shaped wire JSON."""
    block_dict = as_dict(block)
    raw = block_dict.get("count")
    if raw is None:
        count_response = nested_dict(block_dict, "count_response")
        raw = count_response.get("count")
    if raw is None:
        return 0
    return int(raw)


def extract_list_objects(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract objects list from standard Endor API list response JSON."""
    if "list" not in data:
        return []
    list_data = data["list"]
    if isinstance(list_data, dict):
        list_block = cast("dict[str, Any]", list_data)
        objects_raw = list_block.get("objects")
        if isinstance(objects_raw, list):
            return [
                cast("dict[str, Any]", obj)
                for obj in cast("list[Any]", objects_raw)
                if isinstance(obj, dict)
            ]
    return []


def next_page_id_from_response(data: dict[str, Any]) -> str | None:
    """Return ``next_page_id`` from a list or group response page."""
    response_meta = nested_dict(nested_dict(data, "list"), "response")
    raw_next = response_meta.get("next_page_id")
    if raw_next:
        return str(raw_next)
    return None


def iter_group_buckets_from_page(
    page: dict[str, Any],
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(group_key, group_data)`` from one grouped list page."""
    group_response = nested_dict(page, "group_response")
    groups_raw = group_response.get("groups")
    if not isinstance(groups_raw, dict):
        return
    groups = cast("dict[str, Any]", groups_raw)
    for key, value in groups.items():
        if isinstance(value, dict):
            yield str(key), cast("dict[str, Any]", value)


def iter_group_buckets_from_pages(
    pages: Iterator[dict[str, Any]],
) -> Iterator[GroupBucket]:
    """Yield :class:`GroupBucket` rows from grouped list pages."""
    for page in pages:
        for key, value in iter_group_buckets_from_page(page):
            yield GroupBucket(
                key=key,
                parsed=parse_group_key(key),
                data=value,
                count=count_from_wire(value),
            )


def parse_bucket_key(raw: str) -> str:
    """Normalize a grouped time bucket key from wire JSON."""
    cleaned = raw.strip().strip('"').strip("'")
    return cleaned.strip('"').strip("'")


def group_bucket_count(bucket: GroupBucket) -> int:
    """Extract integer count from a ``GroupBucket`` wire row."""
    agg = nested_dict(bucket.data, "aggregation_count")
    count_raw = agg.get("count")
    if count_raw is not None:
        return int(count_raw)
    return bucket.count


def group_bucket_time_key(
    bucket: GroupBucket, *, time_path: str = "meta.create_time"
) -> str:
    """Return normalized time-path key for a grouped bucket."""
    if time_path in bucket.parsed:
        return parse_bucket_key(bucket.parsed[time_path])
    return parse_bucket_key(bucket.key)


def buckets_to_counts(
    buckets: list[GroupBucket], *, time_path: str = "meta.create_time"
) -> dict[str, int]:
    """Merge ``GroupBucket`` rows into ``{bucket_start_iso: count}``."""
    out: dict[str, int] = {}
    for bucket in buckets:
        key = group_bucket_time_key(bucket, time_path=time_path)
        out[key] = out.get(key, 0) + group_bucket_count(bucket)
    return out
