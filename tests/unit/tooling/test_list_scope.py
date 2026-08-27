"""Unit tests for project_scoped_list_kwargs."""

from __future__ import annotations

from types import SimpleNamespace

from tests.integration.list_scope import project_scoped_list_kwargs


def test_adds_traverse_at_tenant_root() -> None:
    client = SimpleNamespace(_default_namespace="example-tenant")
    assert project_scoped_list_kwargs(client) == {"traverse": True}


def test_noop_when_child_namespace() -> None:
    client = SimpleNamespace(_default_namespace="example-tenant.child")
    assert project_scoped_list_kwargs(client) == {}


def test_respects_explicit_traverse_false() -> None:
    client = SimpleNamespace(_default_namespace="example-tenant")
    assert project_scoped_list_kwargs(client, traverse=False) == {"traverse": False}
