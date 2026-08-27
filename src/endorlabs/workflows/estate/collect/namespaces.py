"""Resolve estate namespace names for per-namespace analytics exports.

Thin re-exports of :mod:`endorlabs.utils.namespaces` with estate-oriented names.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from endorlabs.utils.namespaces import (
    discover_namespace_names,
    list_probe_namespaces,
    namespaces_for_no_traverse_counts,
)

if TYPE_CHECKING:
    from endorlabs import Client


def discover_estate_namespace_names(client: Client, estate_root: str) -> list[str]:
    """Discover estate namespaces via ``Namespace.list(..., traverse=True)``.

    Traversal is used only here—for discovery—not for DependencyMetadata counts.
    """
    return discover_namespace_names(client, estate_root)


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
    return namespaces_for_no_traverse_counts(discovered, root_namespace=estate_root)


def list_estate_namespace_names(client: Client, estate_root: str) -> list[str]:
    """Return namespaces to use for per-namespace grouped counts (no traverse)."""
    return list_probe_namespaces(client, estate_root)


__all__ = [
    "discover_estate_namespace_names",
    "list_estate_namespace_names",
    "namespaces_for_grouped_counts",
]
