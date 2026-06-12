"""Tests for endorlabs.utils.namespace helpers."""

from __future__ import annotations

from endorlabs.resources.base import BaseMeta, BaseResource, TenantMeta
from endorlabs.utils.namespace import (
    resolve_namespace_for_resource,
    resource_in_namespace_tree,
    resource_namespace,
)


class _Resource(BaseResource):
    pass


def test_resolve_namespace_returns_tenant_meta_namespace_when_present() -> None:
    """When resource has tenant_meta.namespace, return it."""
    ns = "tenant.engineering.team"
    resource = type("R", (), {"tenant_meta": type("TM", (), {"namespace": ns})()})()
    assert resolve_namespace_for_resource(resource, "fallback") == ns


def test_resolve_namespace_returns_fallback_when_tenant_meta_missing() -> None:
    """When resource has no tenant_meta, return fallback."""
    resource = type("R", (), {})()
    assert resolve_namespace_for_resource(resource, "fallback-ns") == "fallback-ns"


def test_resolve_namespace_returns_fallback_when_tenant_meta_none() -> None:
    """When resource.tenant_meta is None, return fallback."""
    resource = type("R", (), {"tenant_meta": None})()
    assert resolve_namespace_for_resource(resource, "fallback-ns") == "fallback-ns"


def test_resolve_namespace_returns_fallback_when_namespace_empty() -> None:
    """When tenant_meta.namespace is empty or whitespace, return fallback."""
    resource = type("R", (), {"tenant_meta": type("TM", (), {"namespace": ""})()})()
    assert resolve_namespace_for_resource(resource, "fallback-ns") == "fallback-ns"

    resource2 = type("R", (), {"tenant_meta": type("TM", (), {"namespace": "   "})()})()
    assert resolve_namespace_for_resource(resource2, "fallback-ns") == "fallback-ns"


def test_resolve_namespace_returns_fallback_when_fallback_none_and_no_ns() -> None:
    """When fallback is None and resource has no namespace, return None."""
    resource = type("R", (), {})()
    assert resolve_namespace_for_resource(resource, None) is None


def test_resource_namespace_from_model() -> None:
    resource = _Resource(
        uuid="r-1",
        meta=BaseMeta(),
        tenant_meta=TenantMeta(namespace="tenant.child"),
    )
    assert resource_namespace(resource) == "tenant.child"


def test_resource_namespace_from_wire_dict() -> None:
    wire = {"uuid": "r-1", "tenant_meta": {"namespace": "tenant.child"}}
    assert resource_namespace(wire) == "tenant.child"


def test_resource_in_namespace_tree() -> None:
    resource = _Resource(
        uuid="r-1",
        meta=BaseMeta(),
        tenant_meta=TenantMeta(namespace="tenant.root.team"),
    )
    assert resource_in_namespace_tree(resource, "tenant.root")
    assert resource_in_namespace_tree(resource, "tenant.root.team")
    assert not resource_in_namespace_tree(resource, "tenant.other")


def test_resolve_namespace_for_resource_prefers_resource_namespace() -> None:
    resource = _Resource(
        uuid="r-1",
        meta=BaseMeta(),
        tenant_meta=TenantMeta(namespace="tenant.child"),
    )
    assert resolve_namespace_for_resource(resource, "tenant.root") == "tenant.child"
