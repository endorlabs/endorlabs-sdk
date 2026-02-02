"""Tests for endorlabs.utils.namespace (resolve_namespace_for_resource)."""

from endorlabs.utils.namespace import resolve_namespace_for_resource


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
