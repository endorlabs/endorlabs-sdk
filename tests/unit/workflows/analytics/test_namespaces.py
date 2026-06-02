"""Unit tests for analytics namespace resolution."""

from __future__ import annotations

from unittest.mock import MagicMock

from endorlabs.workflows.analytics.namespaces import (
    discover_estate_namespace_names,
    list_estate_namespace_names,
    namespaces_for_grouped_counts,
)


def test_discover_estate_namespace_names_uses_traverse() -> None:
    client = MagicMock()
    root = MagicMock()
    root.spec.full_name = "tenant"
    child = MagicMock()
    child.spec.full_name = "tenant.child"
    client.Namespace.list.return_value = [root, child]

    names = discover_estate_namespace_names(client, "tenant")

    assert names == ["tenant", "tenant.child"]
    client.Namespace.list.assert_called_once_with(namespace="tenant", traverse=True)


def test_namespaces_for_grouped_counts_omits_root_when_descendants_exist() -> None:
    discovered = ["tenant", "tenant.team-a", "tenant.team-b"]
    counting = namespaces_for_grouped_counts(discovered, estate_root="tenant")
    assert counting == ["tenant.team-a", "tenant.team-b"]


def test_namespaces_for_grouped_counts_keeps_root_when_no_descendants() -> None:
    discovered = ["tenant"]
    counting = namespaces_for_grouped_counts(discovered, estate_root="tenant")
    assert counting == ["tenant"]


def test_list_estate_namespace_names_dedupes_and_excludes_root_for_counts() -> None:
    client = MagicMock()
    root = MagicMock()
    root.spec.full_name = "tenant"
    child = MagicMock()
    child.spec.full_name = "tenant.child"
    client.Namespace.list.return_value = [root, child]

    names = list_estate_namespace_names(client, "tenant")

    assert names == ["tenant.child"]
