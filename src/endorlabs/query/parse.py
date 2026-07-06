"""Parse Query.create response shapes into count maps."""

from __future__ import annotations

from typing import Any, cast

from endorlabs.operations.list_response import count_from_wire


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


def reference_count(project_obj: dict[str, Any], ref_key: str) -> int:
    """Read count from ``meta.references[ref_key]``."""
    meta = _as_dict(project_obj.get("meta"))
    refs = _as_dict(meta.get("references"))
    block = refs.get(ref_key)
    if not isinstance(block, dict):
        return 0
    block_dict = cast("dict[str, Any]", block)
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


def project_uuid_from_object(obj: dict[str, Any]) -> str:
    """Read project UUID from a Query response object row."""
    raw = obj.get("uuid")
    return str(raw) if raw else ""


def parse_project_reference_counts(result: Any, ref_key: str) -> dict[str, int]:
    """Map project UUID to count for one reference key (kind or ``return_as``)."""
    root = wire_dict(result)
    spec = _as_dict(root.get("spec"))
    objects = extract_query_response_objects(spec.get("query_response"))
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
    root = wire_dict(result)
    spec = _as_dict(root.get("spec"))
    objects = extract_query_response_objects(spec.get("query_response"))
    out: dict[str, dict[str, int]] = {}
    for obj in objects:
        pid = project_uuid_from_object(obj)
        if not pid:
            continue
        out[pid] = {key: reference_count(obj, key) for key in ref_keys}
    return out
