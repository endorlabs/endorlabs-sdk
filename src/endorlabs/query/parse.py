"""Parse Query.create response shapes into count maps and list aggregates."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

from endorlabs.operations.list_response import (
    GroupBucket,
    buckets_to_counts,
    count_from_wire,
    iter_group_buckets_from_pages,
)
from endorlabs.operations.pagination import PageCursor

from .normalize import normalize_reference_rows


def _as_dict(value: Any) -> dict[str, Any]:
    return cast("dict[str, Any]", value) if isinstance(value, dict) else {}


def wire_dict(obj: Any) -> dict[str, Any]:
    """Coerce a Query response or nested object to a plain dict."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return cast("dict[str, Any]", obj)
    if hasattr(obj, "model_dump"):
        return cast("dict[str, Any]", obj.model_dump(mode="json", warnings=False))
    return {}


def extract_query_response(result: Any) -> dict[str, Any]:
    """Return ``spec.query_response`` from a Query.create result."""
    root = wire_dict(result)
    spec = _as_dict(root.get("spec"))
    return wire_dict(spec.get("query_response"))


def extract_group_response(result: Any) -> dict[str, Any]:
    """Return ``group_response`` when present on ``spec.query_response``."""
    return wire_dict(extract_query_response(result).get("group_response"))


def extract_query_response_objects(query_response: Any) -> list[dict[str, Any]]:
    """Extract root-kind objects from ``spec.query_response``."""
    data = wire_dict(query_response)
    if not data:
        return []

    lst = data.get("list")
    if isinstance(lst, dict):
        lst_dict = cast("dict[str, Any]", lst)
        objects = lst_dict.get("objects")
        if isinstance(objects, list):
            typed_objects = cast("list[Any]", objects)
            return [wire_dict(item) for item in typed_objects if item is not None]

    for key in ("value", "data"):
        nested = data.get(key)
        if isinstance(nested, dict):
            inner = extract_query_response_objects(nested)
            if inner:
                return inner

    return []


def extract_query_objects(result: Any) -> list[dict[str, Any]]:
    """Return root-kind objects from a Query.create result."""
    return extract_query_response_objects(extract_query_response(result))


def next_page_token(result: Any) -> int | None:
    """Return root ``list.response.next_page_token`` from a Query response."""
    qr = extract_query_response(result)
    lst = wire_dict(qr.get("list"))
    resp = wire_dict(lst.get("response"))
    raw = resp.get("next_page_token")
    if raw is None:
        return None
    return int(raw)


def parse_query_root_count(result: Any) -> int:
    """Return integer count from a root count-only ``Query.create`` response."""
    qr = extract_query_response(result)
    if not qr:
        return 0
    if "count_response" in qr or qr.get("count") is not None:
        return count_from_wire(qr)
    objects = extract_query_response_objects(qr)
    if objects:
        return count_from_wire(objects[0])
    lst = wire_dict(qr.get("list"))
    resp = wire_dict(lst.get("response"))
    total = resp.get("total")
    if total is not None:
        return int(total)
    return 0


def iter_group_buckets(result: Any) -> Iterator[GroupBucket]:
    """Yield grouped buckets from one Query.create page."""
    grp = extract_group_response(result)
    if not grp:
        return
    yield from iter_group_buckets_from_pages(iter([{"group_response": grp}]))


def parse_group_bucket_counts(
    result: Any,
    *,
    time_path: str = "meta.create_time",
) -> dict[str, int]:
    """Map grouped time bucket keys to counts (``group`` / ``group_by_time``)."""
    buckets = list(iter_group_buckets(result))
    return buckets_to_counts(buckets, time_path=time_path)


def reference_block(project_obj: dict[str, Any], ref_key: str) -> dict[str, Any]:
    """Read ``meta.references[ref_key]`` from a Query project row."""
    meta = _as_dict(project_obj.get("meta"))
    refs = _as_dict(meta.get("references"))
    return wire_dict(refs.get(ref_key))


def reference_count(project_obj: dict[str, Any], ref_key: str) -> int:
    """Read count from ``meta.references[ref_key]``."""
    block_dict = reference_block(project_obj, ref_key)
    if not block_dict:
        return 0
    if "count_response" in block_dict:
        return count_from_wire(block_dict)
    if "count" in block_dict:
        return int(block_dict["count"])
    lst = block_dict.get("list")
    if isinstance(lst, dict):
        lst_dict = cast("dict[str, Any]", lst)
        resp = lst_dict.get("response")
        if isinstance(resp, dict):
            resp_dict = cast("dict[str, Any]", resp)
            total = resp_dict.get("total")
            if total is not None:
                return int(total)
    return 0


def reference_list_total(project_obj: dict[str, Any], ref_key: str) -> int | None:
    """Read ``list.response.total`` from a nested reference list."""
    block_dict = reference_block(project_obj, ref_key)
    lst = wire_dict(block_dict.get("list"))
    resp = wire_dict(lst.get("response"))
    total = resp.get("total")
    if total is not None:
        return int(total)
    return None


def reference_list_objects(
    project_obj: dict[str, Any], ref_key: str
) -> list[dict[str, Any]]:
    """Return objects from a nested reference list (one page)."""
    block_dict = reference_block(project_obj, ref_key)
    lst = wire_dict(block_dict.get("list"))
    objects = lst.get("objects")
    if not isinstance(objects, list):
        return []
    typed_objects = cast("list[Any]", objects)
    return [wire_dict(item) for item in typed_objects if item is not None]


def reference_list_response_meta(
    project_obj: dict[str, Any], ref_key: str
) -> dict[str, Any]:
    """Read ``list.response`` from a nested reference list block."""
    block_dict = reference_block(project_obj, ref_key)
    lst = wire_dict(block_dict.get("list"))
    return wire_dict(lst.get("response"))


def reference_next_page_token(project_obj: dict[str, Any], ref_key: str) -> int | None:
    """Return nested ``list.response.next_page_token`` for a reference key."""
    raw = reference_list_response_meta(project_obj, ref_key).get("next_page_token")
    if raw is None:
        return None
    return int(raw)


def reference_next_page_cursor(
    project_obj: dict[str, Any], ref_key: str
) -> PageCursor | None:
    """Return the next reference list cursor (``page_token`` over ``page_id``)."""
    meta = reference_list_response_meta(project_obj, ref_key)
    token = meta.get("next_page_token")
    if token is not None:
        return PageCursor(page_token=int(token))
    page_id = meta.get("next_page_id")
    if page_id is not None:
        return PageCursor(page_id=str(page_id))
    return None


def wire_spec_with_reference_page_token(
    wire: dict[str, Any],
    ref_key: str,
    page_token: int | str | None,
) -> dict[str, Any]:
    """Return a copy of wire with ``page_token`` set on the matching reference."""
    from endorlabs.operations.pagination import PageCursor

    cursor = PageCursor(page_token=page_token) if page_token is not None else None
    return wire_spec_with_reference_page_cursor(wire, ref_key, cursor)


def wire_spec_with_reference_page_cursor(
    wire: dict[str, Any],
    ref_key: str,
    cursor: PageCursor | None,
) -> dict[str, Any]:
    """Return a copy of wire with reference list pagination cursor fields set."""
    import copy
    from typing import cast

    spec = copy.deepcopy(wire)
    refs = cast("list[dict[str, Any]]", spec.get("references") or [])
    for ref in refs:
        child = wire_dict(ref.get("query_spec"))
        kind = child.get("kind")
        return_as = child.get("return_as")
        if ref_key not in (kind, return_as):
            continue
        lp = dict(child.get("list_parameters") or {})
        lp.pop("page_token", None)
        lp.pop("page_id", None)
        if cursor is not None:
            if cursor.page_id is not None:
                lp["page_id"] = cursor.page_id
            elif cursor.page_token is not None:
                lp["page_token"] = cursor.page_token
        child["list_parameters"] = lp
        ref["query_spec"] = child
        break
    return spec


def reference_total(project_obj: dict[str, Any], ref_key: str) -> int:
    """Best-effort total for a reference: count ref, then list total, else page size."""
    block_dict = reference_block(project_obj, ref_key)
    has_count = (
        block_dict.get("count_response") is not None
        or block_dict.get("count") is not None
    )
    if has_count:
        return reference_count(project_obj, ref_key)
    total = reference_list_total(project_obj, ref_key)
    if total is not None:
        return total
    return len(reference_list_objects(project_obj, ref_key))


def project_uuid_from_object(obj: dict[str, Any]) -> str:
    """Read project UUID from a Query response object row."""
    raw = obj.get("uuid")
    return str(raw) if raw else ""


def parse_project_reference_counts(result: Any, ref_key: str) -> dict[str, int]:
    """Map project UUID to count for one reference key (kind or ``return_as``)."""
    objects = extract_query_objects(result)
    out: dict[str, int] = {}
    for obj in objects:
        pid = project_uuid_from_object(obj)
        if not pid:
            continue
        out[pid] = reference_count(obj, ref_key)
    return out


def parse_project_multi_reference_counts(
    result: Any,
    ref_keys: list[str],
) -> dict[str, dict[str, int]]:
    """Map project UUID to ``{ref_key: count}``."""
    objects = extract_query_objects(result)
    out: dict[str, dict[str, int]] = {}
    for obj in objects:
        pid = project_uuid_from_object(obj)
        if not pid:
            continue
        out[pid] = {key: reference_count(obj, key) for key in ref_keys}
    return out


def parse_project_reference_list_totals(
    result: Any,
    ref_key: str,
) -> dict[str, int]:
    """Map project UUID to nested list total (prefer count ref when set)."""
    objects = extract_query_objects(result)
    out: dict[str, int] = {}
    for obj in objects:
        pid = project_uuid_from_object(obj)
        if not pid:
            continue
        out[pid] = reference_total(obj, ref_key)
    return out


def parse_normalized_query_objects(result: Any) -> list[dict[str, Any]]:
    """Return root objects with single-row reference lists hoisted (ewok parity)."""
    return normalize_reference_rows(extract_query_objects(result))


__all__ = [
    "extract_group_response",
    "extract_query_objects",
    "extract_query_response",
    "extract_query_response_objects",
    "iter_group_buckets",
    "next_page_token",
    "parse_group_bucket_counts",
    "parse_normalized_query_objects",
    "parse_project_multi_reference_counts",
    "parse_project_reference_counts",
    "parse_project_reference_list_totals",
    "parse_query_root_count",
    "project_uuid_from_object",
    "reference_block",
    "reference_count",
    "reference_list_objects",
    "reference_list_total",
    "reference_next_page_cursor",
    "reference_next_page_token",
    "reference_total",
    "wire_dict",
    "wire_spec_with_reference_page_cursor",
    "wire_spec_with_reference_page_token",
]
