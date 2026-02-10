"""Namespace traversal utilities for tenant-wide queries.

.. deprecated::
    ``create_traverse_params`` and ``create_namespace_scoped_params`` are
    thin wrappers around ``ListParameters``. Prefer passing ``traverse=True``
    (or ``False``) and ``filter=`` directly to the facade's ``.list()`` method::

        client.project.list(traverse=True, filter="...")

This module is retained for backwards compatibility.
"""

from __future__ import annotations

import warnings
from typing import Any

from ..types import ListParameters


def create_traverse_params(
    filter_expr: str | None = None,
    page_size: int | None = None,
    **kwargs: Any,
) -> ListParameters:
    """Create ListParameters with traverse enabled for tenant-wide queries.

    .. deprecated::
        Use ``client.<resource>.list(traverse=True, filter=...)`` instead.

    Args:
        filter_expr: Optional filter expression (e.g., "spec.project_uuid==<uuid>")
        page_size: Optional page size for pagination (default: None = use API default)
            Note: Small page sizes can cause performance issues. Only set if needed.
        **kwargs: Additional ListParameters fields

    Returns:
        ListParameters with traverse=True

    """
    warnings.warn(
        "create_traverse_params() is deprecated. "
        "Use client.<resource>.list(traverse=True, filter=...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Don't set page_size unless explicitly provided (let API use default)
    params_dict: dict[str, Any] = {
        "traverse": True,
        "filter": filter_expr,
        **kwargs,
    }
    if page_size is not None:
        params_dict["page_size"] = page_size

    return ListParameters(**params_dict)


def create_namespace_scoped_params(
    filter_expr: str | None = None,
    page_size: int | None = None,
    **kwargs: Any,
) -> ListParameters:
    """Create ListParameters for namespace-scoped queries (no traversal).

    .. deprecated::
        Use ``client.<resource>.list(filter=...)`` instead (traverse
        defaults to ``False``).

    Args:
        filter_expr: Optional filter expression
        page_size: Optional page size for pagination (default: None = use API default)
            Note: Small page sizes can cause performance issues. Only set if needed.
        **kwargs: Additional ListParameters fields

    Returns:
        ListParameters with traverse=False (default)

    """
    warnings.warn(
        "create_namespace_scoped_params() is deprecated. "
        "Use client.<resource>.list(filter=...) instead "
        "(traverse defaults to False).",
        DeprecationWarning,
        stacklevel=2,
    )
    # Don't set page_size unless explicitly provided (let API use default)
    params_dict: dict[str, Any] = {
        "traverse": False,
        "filter": filter_expr,
        **kwargs,
    }
    if page_size is not None:
        params_dict["page_size"] = page_size

    return ListParameters(**params_dict)
