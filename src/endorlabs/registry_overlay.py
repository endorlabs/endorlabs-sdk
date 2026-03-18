"""Minimal policy overlay for generated runtime registry contract."""

from __future__ import annotations

from typing import Any, cast

_ALLOWED_OVERRIDE_KEYS = {"supported_ops", "scope", "parent_kind", "filter_kwarg_map"}

# Keep this intentionally small: only explicit SDK divergences belong here.
RESOURCE_CONTRACT_OVERLAY_BY_ATTR: dict[str, dict[str, Any]] = {}


def merge_generated_contract_with_overlay(
    generated_resources: list[Any],
) -> list[dict[str, Any]]:
    """Merge generated resource contract with explicit per-resource overrides."""
    by_attr: dict[str, dict[str, Any]] = {}
    for item in generated_resources:
        if not isinstance(item, dict):
            continue
        item_dict = cast("dict[str, Any]", item)
        attr_name = item_dict.get("attr_name")
        if isinstance(attr_name, str):
            by_attr[attr_name] = dict(item_dict)
    for attr_name, override in RESOURCE_CONTRACT_OVERLAY_BY_ATTR.items():
        if attr_name not in by_attr:
            continue
        for key, value in override.items():
            if key in _ALLOWED_OVERRIDE_KEYS:
                by_attr[attr_name][key] = value
    return [by_attr[attr_name] for attr_name in sorted(by_attr)]
