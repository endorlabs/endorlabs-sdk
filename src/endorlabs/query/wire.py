"""Serialize list_parameters group knobs for Query POST JSON."""

from __future__ import annotations

from typing import Any


def group_query_wire(*aggregation_paths: str) -> dict[str, Any]:
    """Build nested ``list_parameters.group`` for Query POST."""
    paths = [path.strip() for path in aggregation_paths if path.strip()]
    return {"aggregation_paths": ",".join(paths)}
