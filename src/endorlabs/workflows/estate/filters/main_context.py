"""Shared list filters for main-context (default branch) scan objects."""

from __future__ import annotations

from endorlabs.facade.context_partition import (
    MAIN_CONTEXT_TYPE,
    main_context_filter,
)

# Endor list filter: default-branch / main context rows only.
MAIN_CONTEXT_LIST_FILTER = f'context.type=="{MAIN_CONTEXT_TYPE}"'

__all__ = ["MAIN_CONTEXT_LIST_FILTER", "MAIN_CONTEXT_TYPE", "main_context_filter"]
