"""Shared list filters for main-context (default branch) scan objects."""

from __future__ import annotations

MAIN_CONTEXT_TYPE = "CONTEXT_TYPE_MAIN"

# Endor list filter: default-branch / main context rows only.
MAIN_CONTEXT_LIST_FILTER = f'context.type=="{MAIN_CONTEXT_TYPE}"'


def main_context_filter(extra: str | None = None) -> str:
    """Combine main-context filter with an optional additional expression."""
    if not extra or not extra.strip():
        return MAIN_CONTEXT_LIST_FILTER
    return f"({MAIN_CONTEXT_LIST_FILTER}) and ({extra.strip()})"
