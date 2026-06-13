"""Registry contract field lists for consumer resource cutover."""

from __future__ import annotations

from typing import Any

from endorlabs.generated.registry_contract import RUNTIME_REGISTRY_CONTRACT


def _resources() -> list[dict[str, Any]]:
    return list(RUNTIME_REGISTRY_CONTRACT.get("resources", []))


def registry_row_for_attr(attr_name: str) -> dict[str, Any] | None:
    """Return the registry contract row for a facade attr name (PascalCase)."""
    for row in _resources():
        if row.get("attr_name") == attr_name:
            return row
    return None


def mutable_fields_for(attr_name: str) -> list[str]:
    """Return mutable field paths from registry contract."""
    row = registry_row_for_attr(attr_name)
    if row is None:
        return ["meta.description", "meta.tags"]
    fields = row.get("mutable_fields")
    if isinstance(fields, list):
        return [str(f) for f in fields]
    return ["meta.description", "meta.tags"]


def immutable_fields_for(attr_name: str) -> list[str]:
    """Return immutable field paths from registry contract."""
    row = registry_row_for_attr(attr_name)
    if row is None:
        return []
    fields = row.get("immutable_fields")
    if isinstance(fields, list):
        return [str(f) for f in fields]
    return []
