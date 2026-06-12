"""Parse list/group wire JSON from API responses."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any


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
    for entry in payload:
        if isinstance(entry, dict) and "key" in entry and "value" in entry:
            parsed[str(entry["key"])] = str(entry["value"])
    return parsed


def count_from_wire(block: Any) -> int:
    """Extract integer count from ``count_response``-shaped wire JSON."""
    if not isinstance(block, dict):
        return 0
    raw = block.get("count")
    if raw is None:
        count_response = block.get("count_response")
        if isinstance(count_response, dict):
            raw = count_response.get("count")
    if raw is None:
        return 0
    return int(raw)


def extract_list_objects(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract objects list from standard Endor API list response JSON."""
    if "list" not in data:
        return []
    list_data = data["list"]
    if isinstance(list_data, dict) and "objects" in list_data:
        objects = list_data["objects"]
        if isinstance(objects, list):
            return [obj for obj in objects if isinstance(obj, dict)]
    return []


def next_page_id_from_response(data: dict[str, Any]) -> str | None:
    """Return ``next_page_id`` from a list or group response page."""
    list_block = data.get("list")
    if isinstance(list_block, dict):
        response_meta = list_block.get("response")
        if isinstance(response_meta, dict):
            raw_next = response_meta.get("next_page_id")
            if raw_next:
                return str(raw_next)
    return None


def iter_group_buckets_from_page(
    page: dict[str, Any],
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(group_key, group_data)`` from one grouped list page."""
    group_response = page.get("group_response")
    if not isinstance(group_response, dict):
        return
    groups = group_response.get("groups")
    if not isinstance(groups, dict):
        return
    for key, value in groups.items():
        if isinstance(value, dict):
            yield str(key), value


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
