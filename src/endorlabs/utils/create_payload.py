"""Helpers for building create payloads from flat facade kwargs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

RESERVED_CREATE_KWARGS = frozenset({"namespace", "payload"})


def promote_create_kwargs(
    payload_kwargs: dict[str, Any],
    *,
    spec_fields: Sequence[str],
    meta_name_default: str | None = None,
    meta_flat_aliases: Mapping[str, str] | None = None,
    resource_label: str = "resource",
) -> dict[str, Any]:
    """Promote flat kwargs into ``meta`` / ``spec`` for create payload builders.

    If ``spec`` is already provided, flat ``spec_fields`` keys are not merged from
    the top level. Unknown keys after promotion raise ``TypeError``.
    """
    if "payload" in payload_kwargs:
        return dict(payload_kwargs)

    result = dict(payload_kwargs)
    aliases = dict(meta_flat_aliases or {})

    if "spec" not in result:
        spec: dict[str, Any] = {}
        for field in spec_fields:
            if field in result:
                spec[field] = result.pop(field)
        if spec:
            result["spec"] = spec

    if "meta" not in result:
        meta: dict[str, Any] = {}
        for flat_name, meta_path in aliases.items():
            if flat_name not in result:
                continue
            value = result.pop(flat_name)
            if meta_path == "name":
                meta["name"] = value
            else:
                meta[meta_path] = value
        if meta_name_default is not None and "name" not in meta:
            meta["name"] = meta_name_default
        if meta:
            result["meta"] = meta
    elif meta_name_default is not None:
        meta_value = result.get("meta")
        if isinstance(meta_value, dict) and not meta_value.get("name"):
            meta_value = dict(meta_value)
            meta_value.setdefault("name", meta_name_default)
            result["meta"] = meta_value

    allowed = set(spec_fields) | set(aliases) | {"meta", "spec"}
    unknown = sorted(
        key
        for key in result
        if key not in allowed and key not in RESERVED_CREATE_KWARGS
    )
    if unknown:
        raise TypeError(
            f"Invalid create kwargs for {resource_label}: {unknown}. "
            f"Allowed flat keys: {sorted(allowed | set(RESERVED_CREATE_KWARGS))}. "
            "Use payload= or spec= for full control."
        )
    return result


def validate_flat_create_kwargs(
    kwargs: Mapping[str, Any],
    *,
    allowed: Sequence[str],
    reserved: frozenset[str] = RESERVED_CREATE_KWARGS,
    resource_label: str = "resource",
) -> None:
    """Raise ``TypeError`` when kwargs contain keys outside the allowlist."""
    allowed_set = set(allowed) | set(reserved)
    unknown = sorted(key for key in kwargs if key not in allowed_set)
    if unknown:
        raise TypeError(
            f"Invalid create kwargs for {resource_label}: {unknown}. "
            f"Allowed: {sorted(allowed_set)}."
        )


def attr_name_to_constant_prefix(attr_name: str) -> str:
    """Convert PascalCase resource attr to SCREAMING_SNAKE."""
    chars: list[str] = []
    for index, char in enumerate(attr_name):
        if char.isupper() and index > 0:
            chars.append("_")
        chars.append(char.upper())
    return "".join(chars)


def pass_through_create_payload(
    model_cls: type[T],
    kwargs: Mapping[str, Any],
    *,
    attr_name: str,
) -> T:
    """Validate flat kwargs and construct a pass-through create payload model."""
    from ..generated import create_convenience as cc

    prefix = attr_name_to_constant_prefix(attr_name)
    top_level = getattr(cc, f"{prefix}_PAYLOAD_TOP_LEVEL_FIELDS", ())
    meta_fields = getattr(cc, f"{prefix}_META_FIELDS", ())
    spec_fields = getattr(cc, f"{prefix}_SPEC_FIELDS", ())
    validate_pass_through_create(
        kwargs,
        payload_top_level_fields=top_level,
        meta_fields=meta_fields,
        spec_fields=spec_fields,
        resource_label=attr_name,
    )
    return model_cls(**dict(kwargs))


def validate_pass_through_create(
    kwargs: Mapping[str, Any],
    *,
    payload_top_level_fields: Sequence[str],
    meta_fields: Sequence[str] = (),
    spec_fields: Sequence[str] = (),
    resource_label: str = "resource",
) -> None:
    """Validate kwargs for ``CreateXPayload(**kwargs)`` pass-through builders."""
    allowed = (
        set(payload_top_level_fields)
        | set(meta_fields)
        | set(spec_fields)
        | {"meta", "spec"}
    )
    validate_flat_create_kwargs(
        kwargs,
        allowed=sorted(allowed),
        resource_label=resource_label,
    )


def flat_create_kwargs_allowed(entry: Any) -> frozenset[str]:
    """Union of generated convenience keys for a registry ``ResourceEntry``."""
    spec = getattr(entry, "create_convenience_spec_fields", ()) or ()
    meta = getattr(entry, "create_convenience_meta_fields", ()) or ()
    top = getattr(entry, "create_convenience_payload_top_level_fields", ()) or ()
    names: set[str] = set(spec) | set(meta) | set(top)
    if "name" in meta:
        names.add("name")
    return frozenset(names)
