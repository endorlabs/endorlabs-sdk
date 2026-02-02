"""Namespace resolution utilities for resource-scoped operations.

Used to anchor get/update/delete (and list/filter scoped to a resource)
to the resource's owning namespace, avoiding context mismatch (404) when
acting on objects returned from traverse.
"""

from __future__ import annotations

from typing import Any


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
    tenant_meta = getattr(resource, "tenant_meta", None)
    if tenant_meta is None:
        return fallback
    ns = getattr(tenant_meta, "namespace", None)
    if ns and isinstance(ns, str) and ns.strip():
        return ns
    return fallback
