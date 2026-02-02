"""Namespace traversal utilities for tenant-wide queries.

This module provides canonical patterns and helpers for efficiently
querying resources across all namespaces using the traverse parameter.
"""

from typing import Any

from ..types import ListParameters


def create_traverse_params(
    filter_expr: str | None = None,
    page_size: int | None = None,
    **kwargs: Any,
) -> ListParameters:
    """Create ListParameters with traverse enabled for tenant-wide queries.

    This is the canonical way to query resources across all namespaces
    in a single efficient API call.

    Args:
        filter_expr: Optional filter expression (e.g., "spec.project_uuid==<uuid>")
        page_size: Optional page size for pagination (default: None = use API default)
            Note: Small page sizes can cause performance issues. Only set if needed.
        **kwargs: Additional ListParameters fields

    Returns:
        ListParameters with traverse=True

    Example:
        ```python
        from endorlabs.utils.traversal import create_traverse_params
        from endorlabs.resources import dependency_metadata

        # Query all dependencies across tenant (uses API default page size)
        params = create_traverse_params()
        deps = dependency_metadata.list_dependency_metadata(
            client, tenant_namespace, params
        )

        # Query private dependencies only
        params = create_traverse_params(
            filter_expr="spec.dependency_data.public==false"
        )
        private_deps = dependency_metadata.list_dependency_metadata(
            client, tenant_namespace, params
        )
        ```

    """
    # Don't set page_size unless explicitly provided (let API use default)
    params_dict = {
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

    Use this when you only need resources from a specific namespace,
    not across the entire tenant hierarchy.

    Args:
        filter_expr: Optional filter expression
        page_size: Optional page size for pagination (default: None = use API default)
            Note: Small page sizes can cause performance issues. Only set if needed.
        **kwargs: Additional ListParameters fields

    Returns:
        ListParameters with traverse=False (default)

    Example:
        ```python
        from endorlabs.utils.traversal import create_namespace_scoped_params
        from endorlabs.resources import package_version

        # Query packages in specific namespace only (uses API default page size)
        params = create_namespace_scoped_params()
        packages = package_version.list_package_versions(
            client, "tenant.namespace", params
        )
        ```

    """
    # Don't set page_size unless explicitly provided (let API use default)
    params_dict = {
        "traverse": False,
        "filter": filter_expr,
        **kwargs,
    }
    if page_size is not None:
        params_dict["page_size"] = page_size

    return ListParameters(**params_dict)
