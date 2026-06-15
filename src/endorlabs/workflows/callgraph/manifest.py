"""Manifest helpers for call-graph export artifacts."""

from __future__ import annotations

from typing import Any


def resolve_callgraph_export_artifact(
    artifacts: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return call-graph export block from bundle ``artifacts``."""
    if not artifacts:
        return None
    return artifacts.get("callgraph_export")
