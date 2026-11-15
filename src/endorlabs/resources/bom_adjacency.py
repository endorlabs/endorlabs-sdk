"""BOM dependency_graph adjacency validation (SDK-005).

Upstream OpenAPI still declares object-only adjacency; the SDK wire-tolerance
union accepts strings or objects. Cap string coordinate length so unbounded
payloads cannot pass validation silently.
"""

from __future__ import annotations

from typing import Any

BOM_ADJACENCY_STRING_MAX_LEN = 4096


def validate_bom_adjacency_entry(entry: Any) -> None:
    """Raise ``ValueError`` when an adjacency entry is not object/string-shaped.

    Strings longer than ``BOM_ADJACENCY_STRING_MAX_LEN`` are rejected.
    """
    if isinstance(entry, dict):
        return
    if isinstance(entry, str):
        if len(entry) > BOM_ADJACENCY_STRING_MAX_LEN:
            raise ValueError(
                "BOM adjacency string exceeds "
                f"{BOM_ADJACENCY_STRING_MAX_LEN} characters"
            )
        return
    raise TypeError(
        f"BOM adjacency entry must be object or string, got {type(entry).__name__}"
    )


def validate_bom_dependency_graph(
    graph: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Validate every adjacency list entry; return *graph* unchanged on success."""
    if graph is None:
        return None
    for entries in graph.values():
        if not isinstance(entries, list):
            raise TypeError("BOM adjacency values must be lists")
        for entry in entries:
            validate_bom_adjacency_entry(entry)
    return graph
