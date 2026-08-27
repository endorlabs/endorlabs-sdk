"""Unit tests for portable namespace discovery helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from endorlabs.utils.namespaces import (
    discover_namespace_names,
    list_probe_namespaces,
    namespace_wire_name,
    namespaces_for_no_traverse_counts,
)


def test_namespace_wire_name_prefers_full_name() -> None:
    ns = SimpleNamespace(
        spec=SimpleNamespace(full_name="example-tenant.child"),
        tenant_meta=None,
        meta=None,
    )
    assert namespace_wire_name(ns) == "example-tenant.child"


def test_namespaces_for_no_traverse_counts_drops_root_when_children() -> None:
    discovered = [
        "example-tenant",
        "example-tenant.child",
        "example-tenant.other",
    ]
    assert namespaces_for_no_traverse_counts(
        discovered, root_namespace="example-tenant"
    ) == ["example-tenant.child", "example-tenant.other"]


def test_namespaces_for_no_traverse_counts_keeps_root_alone() -> None:
    assert namespaces_for_no_traverse_counts(
        ["example-tenant"], root_namespace="example-tenant"
    ) == ["example-tenant"]


def test_discover_and_list_probe_namespaces() -> None:
    client = MagicMock()
    child = SimpleNamespace(
        spec=SimpleNamespace(full_name="example-tenant.package-firewall"),
        tenant_meta=None,
        meta=None,
    )
    client.Namespace.list.return_value = [child]
    discovered = discover_namespace_names(client, "example-tenant")
    assert discovered == [
        "example-tenant",
        "example-tenant.package-firewall",
    ]
    assert list_probe_namespaces(client, "example-tenant") == [
        "example-tenant.package-firewall"
    ]
