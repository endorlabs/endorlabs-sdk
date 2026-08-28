"""Portable namespace discovery for per-namespace (no-traverse) probes and counts."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endorlabs.client_surface import Client


def normalize_namespace_name(name: str) -> str:
    """Strip whitespace from a namespace path."""
    return name.strip()


def dedupe_namespace_names(names: list[str]) -> list[str]:
    """Preserve order while dropping empty/duplicate names."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in names:
        normalized = normalize_namespace_name(raw)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def namespace_wire_name(ns_obj: object) -> str | None:
    """Resolve canonical namespace string from a Namespace list row."""
    spec = getattr(ns_obj, "spec", None)
    full_name = getattr(spec, "full_name", None) if spec else None
    if full_name:
        return str(full_name)

    tenant_meta = getattr(ns_obj, "tenant_meta", None)
    parent_ns = (
        getattr(tenant_meta, "namespace", None) if tenant_meta is not None else None
    )
    meta = getattr(ns_obj, "meta", None)
    child_name = getattr(meta, "name", None) if meta is not None else None
    if parent_ns and child_name:
        return f"{parent_ns}.{child_name}"
    if parent_ns:
        return str(parent_ns)
    return None


def discover_namespace_names(client: Client, root_namespace: str) -> list[str]:
    """Discover namespaces via ``Namespace.list(..., traverse=True)``.

    Traversal is used only for discovery—not for subsequent resource counts.
    """
    root = normalize_namespace_name(root_namespace)
    discovered: list[str] = [root] if root else []
    for ns_obj in client.Namespace.list(namespace=root_namespace, traverse=True):
        wire_name = namespace_wire_name(ns_obj)
        if wire_name:
            discovered.append(wire_name)
    return dedupe_namespace_names(discovered)


def namespaces_for_no_traverse_counts(
    discovered: list[str],
    *,
    root_namespace: str,
) -> list[str]:
    """Namespaces to query with ``traverse=False`` per-namespace counts.

    When traverse discovery found descendant namespaces under ``root_namespace``,
    the root is omitted so root-scoped and child-scoped queries are not summed
    together (avoids double-counting hierarchy-wide aggregates).
    """
    root = normalize_namespace_name(root_namespace)
    names = dedupe_namespace_names(discovered)
    if not root or not names:
        return names
    child_prefix = f"{root}."
    has_descendant = any(
        name != root and name.startswith(child_prefix) for name in names
    )
    if not has_descendant:
        return names
    return [name for name in names if name != root]


def list_probe_namespaces(client: Client, root_namespace: str) -> list[str]:
    """Return namespaces for per-namespace probes/counts (no traverse)."""
    discovered = discover_namespace_names(client, root_namespace)
    return namespaces_for_no_traverse_counts(discovered, root_namespace=root_namespace)


__all__ = [
    "dedupe_namespace_names",
    "discover_namespace_names",
    "list_probe_namespaces",
    "namespace_wire_name",
    "namespaces_for_no_traverse_counts",
    "normalize_namespace_name",
]
