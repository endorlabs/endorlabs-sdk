"""Resolve estate namespace names for per-namespace analytics exports."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endorlabs import Client


def _normalize_namespace_name(name: str) -> str:
    return name.strip()


def _dedupe_namespace_names(names: list[str]) -> list[str]:
    """Preserve order while dropping empty/duplicate names."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in names:
        normalized = _normalize_namespace_name(raw)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def _namespace_wire_name(ns_obj: object) -> str | None:
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


def discover_estate_namespace_names(client: Client, estate_root: str) -> list[str]:
    """Discover estate namespaces via ``Namespace.list(..., traverse=True)``.

    Traversal is used only here—for discovery—not for DependencyMetadata counts.
    """
    root = _normalize_namespace_name(estate_root)
    discovered: list[str] = [root] if root else []
    for ns_obj in client.Namespace.list(namespace=estate_root, traverse=True):
        wire_name = _namespace_wire_name(ns_obj)
        if wire_name:
            discovered.append(wire_name)
    return _dedupe_namespace_names(discovered)


def namespaces_for_grouped_counts(
    discovered: list[str],
    *,
    estate_root: str,
) -> list[str]:
    """Namespaces to query with ``traverse=False`` grouped DependencyMetadata lists.

    When traverse discovery found descendant namespaces under ``estate_root``,
    the root is omitted from counting so root-scoped and child-scoped queries
    are not summed together (avoids double-counting estate-wide aggregates).
    """
    root = _normalize_namespace_name(estate_root)
    names = _dedupe_namespace_names(discovered)
    if not root or not names:
        return names
    child_prefix = f"{root}."
    has_descendant = any(
        name != root and name.startswith(child_prefix) for name in names
    )
    if not has_descendant:
        return names
    return [name for name in names if name != root]


def list_estate_namespace_names(client: Client, estate_root: str) -> list[str]:
    """Return namespaces to use for per-namespace grouped counts (no traverse)."""
    discovered = discover_estate_namespace_names(client, estate_root)
    return namespaces_for_grouped_counts(discovered, estate_root=estate_root)
