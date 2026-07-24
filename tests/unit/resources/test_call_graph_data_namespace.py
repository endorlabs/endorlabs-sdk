"""Unit tests for CallGraphData PackageVersion namespace resolution."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from endorlabs.resources.call_graph_data import _pv_uuid_and_namespace


def test_pv_uuid_and_namespace_explicit_namespace() -> None:
    uuid, ns = _pv_uuid_and_namespace("pv-1", namespace="tenant.child")
    assert uuid == "pv-1"
    assert ns == "tenant.child"


def test_pv_uuid_and_namespace_object_tenant_meta() -> None:
    pv = SimpleNamespace(
        uuid="pv-2",
        tenant_meta=SimpleNamespace(namespace="tenant.from_meta"),
    )
    uuid, ns = _pv_uuid_and_namespace(pv, namespace=None)
    assert uuid == "pv-2"
    assert ns == "tenant.from_meta"


def test_pv_uuid_and_namespace_dict_tenant_meta() -> None:
    pv = SimpleNamespace(
        uuid="pv-3",
        tenant_meta={"namespace": "tenant.from_dict"},
    )
    uuid, ns = _pv_uuid_and_namespace(pv, namespace=None)
    assert uuid == "pv-3"
    assert ns == "tenant.from_dict"


def test_pv_uuid_and_namespace_fallback_to_pv_namespace() -> None:
    pv = SimpleNamespace(
        uuid="pv-4",
        tenant_meta=None,
        namespace="tenant.from_attr",
    )
    uuid, ns = _pv_uuid_and_namespace(pv, namespace=None)
    assert uuid == "pv-4"
    assert ns == "tenant.from_attr"


def test_pv_uuid_and_namespace_empty_tenant_meta_uses_attr() -> None:
    pv = SimpleNamespace(
        uuid="pv-5",
        tenant_meta={},
        namespace="tenant.after_empty_meta",
    )
    uuid, ns = _pv_uuid_and_namespace(pv, namespace=None)
    assert uuid == "pv-5"
    assert ns == "tenant.after_empty_meta"


def test_pv_uuid_and_namespace_missing_raises() -> None:
    with pytest.raises(ValueError, match="namespace required"):
        _pv_uuid_and_namespace("pv-bare", namespace=None)
    with pytest.raises(ValueError, match="namespace required"):
        _pv_uuid_and_namespace(
            SimpleNamespace(uuid="pv-6", tenant_meta=None, namespace=None),
            namespace=None,
        )
