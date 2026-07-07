"""Typed accessors for API wire dict rows in workflow modules."""

from __future__ import annotations

from typing import Any, cast


def as_dict(value: Any) -> dict[str, Any]:
    """Return *value* when it is a dict; otherwise an empty dict."""
    if isinstance(value, dict):
        return cast("dict[str, Any]", value)
    return {}


def dict_str(d: dict[str, Any], key: str, default: str = "") -> str:
    """Read a string field from a wire dict."""
    raw = d.get(key, default)
    if raw is None:
        return default
    return str(raw)


def nested_dict(d: dict[str, Any], *keys: str) -> dict[str, Any]:
    """Walk nested dict keys; return empty dict when a segment is missing."""
    cur: dict[str, Any] = d
    for key in keys:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            return {}
        cur = cast("dict[str, Any]", nxt)
    return cur


def nested_str(d: dict[str, Any], *keys: str, default: str = "") -> str:
    """Read a string from nested dict keys."""
    if not keys:
        return default
    cur: Any = d
    for key in keys[:-1]:
        if not isinstance(cur, dict):
            return default
        cur_dict = cast("dict[str, Any]", cur)
        cur = cur_dict.get(key)
    last = keys[-1]
    if not isinstance(cur, dict):
        return default
    cur_dict = cast("dict[str, Any]", cur)
    raw = cur_dict.get(last, default)
    if raw is None:
        return default
    return str(raw)


def _wire_from_model_dump(obj: Any) -> dict[str, Any] | None:
    r"""Return a wire dict when *obj* exposes a real ``model_dump(mode=\"json\")``."""
    model_dump = getattr(obj, "model_dump", None)
    if not callable(model_dump):
        return None
    try:
        dumped = model_dump(mode="json")
    except TypeError:
        return None
    if isinstance(dumped, dict):
        return cast("dict[str, Any]", dumped)
    return None


def _is_unittest_mock(value: Any) -> bool:
    return type(value).__name__ in {
        "Mock",
        "MagicMock",
        "NonCallableMock",
        "NonCallableMagicMock",
    }


def _is_mock_internal(key: str) -> bool:
    return key.startswith(("_mock", "_spec")) or key == "method_calls"


def _scalar_or_wire(value: Any, *, _depth: int = 0) -> Any:
    """Convert nested wire values, including unittest.mock attribute trees."""
    if _depth > 10:
        return None
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return cast("dict[str, Any]", value)
    if isinstance(value, list):
        return [
            _scalar_or_wire(item, _depth=_depth + 1)
            for item in cast("list[Any]", value)
        ]
    if isinstance(value, tuple):
        return [
            _scalar_or_wire(item, _depth=_depth + 1)
            for item in cast("tuple[Any, ...]", value)
        ]
    dumped = _wire_from_model_dump(value)
    attrs = _resource_attrs_to_dict(value, _depth=_depth + 1)
    if dumped is not None and attrs and _is_unittest_mock(value):
        return {**attrs, **dumped}
    if dumped is not None:
        return dumped
    return attrs or None


def _resource_attrs_to_dict(obj: Any, *, _depth: int = 0) -> dict[str, Any]:
    """Build a wire dict from attribute-bearing objects (e.g. unit-test mocks)."""
    if _depth > 10:
        return {}
    if isinstance(obj, dict):
        return cast("dict[str, Any]", obj)

    result: dict[str, Any] = {}
    obj_vars = cast("dict[str, Any]", vars(obj))
    for key, val in obj_vars.items():
        if _is_mock_internal(key):
            continue
        converted = _scalar_or_wire(val, _depth=_depth + 1)
        if converted is not None:
            result[key] = converted

    children = getattr(obj, "_mock_children", None)
    if isinstance(children, dict):
        children_dict = cast("dict[str, Any]", children)
        for key, child in children_dict.items():
            if key in result:
                continue
            converted = _scalar_or_wire(child, _depth=_depth + 1)
            if converted is not None:
                result[key] = converted
    return result


def model_to_dict(item: Any) -> dict[str, Any]:
    """Convert SDK model objects to JSON dict; passthrough dicts."""
    dumped = _wire_from_model_dump(item)
    if dumped is not None:
        return dumped
    if isinstance(item, dict):
        return cast("dict[str, Any]", item)
    return _resource_attrs_to_dict(item)
