"""Namespace resolution utilities for resource-scoped operations.

Used to anchor get/update/delete (and list/filter scoped to a resource)
to the resource's owning namespace, avoiding context mismatch (404) when
acting on objects returned from traverse.
"""

from __future__ import annotations

from typing import Any


def resource_namespace(resource: Any) -> str | None:
    """Return canonical namespace from a resource model or wire-shaped dict."""
    ns = getattr(resource, "namespace", None)
    if isinstance(ns, str) and ns.strip():
        return ns
    tenant_meta = getattr(resource, "tenant_meta", None)
    if tenant_meta is not None:
        tm_ns = getattr(tenant_meta, "namespace", None)
        if isinstance(tm_ns, str) and tm_ns.strip():
            return tm_ns
    if isinstance(resource, dict):
        tenant_meta_dict = resource.get("tenant_meta")
        if isinstance(tenant_meta_dict, dict):
            dict_ns = tenant_meta_dict.get("namespace")
            if isinstance(dict_ns, str) and dict_ns.strip():
                return dict_ns
    return None


def resource_in_namespace_tree(resource: Any, namespace: str) -> bool:
    """True when *resource* lives in *namespace* or a descendant path segment."""
    resource_ns = resource_namespace(resource)
    if not resource_ns:
        return True
    if resource_ns == namespace:
        return True
    return resource_ns.startswith(f"{namespace}.")


def resolve_namespace_for_resource(resource: Any, fallback: str | None) -> str | None:
    """Resolve namespace from a resource object (duck typing).

    When the consumer has a resource (e.g. from list with traverse), use
    this to get the namespace for get/update/delete or for list/filter
    scoped to that resource. Avoids coupling utils to model types.

    Args:
        resource: Object that may have tenant_meta.namespace (e.g. BaseResource).
        fallback: Namespace to use when resource has no tenant_meta or namespace.

    Returns:
        resource.tenant_meta.namespace if present and non-empty, else fallback.

    """
    ns = resource_namespace(resource)
    if ns:
        return ns
    return fallback
