"""Shared decoded callgraph payload shaping helpers."""

from __future__ import annotations

from typing import Any

from endorlabs.operations.call_graph import unpack_call_graph_envelope


def decode_payload(
    cg_data: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Decode raw callgraph payload into summary, callables, and edges."""
    return unpack_call_graph_envelope(cg_data)
