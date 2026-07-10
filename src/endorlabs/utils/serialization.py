"""JSON serialization helpers for SDK models and wire dicts."""

from __future__ import annotations

from typing import Any


def to_json_dict(item: Any) -> dict[str, Any]:
    """Convert SDK model objects to JSON dict; passthrough dicts."""
    from endorlabs.workflows.wire_access import model_to_dict

    return model_to_dict(item)


# Compat alias used by troubleshooting workflows.
object_to_dict = to_json_dict

__all__ = ["object_to_dict", "to_json_dict"]
