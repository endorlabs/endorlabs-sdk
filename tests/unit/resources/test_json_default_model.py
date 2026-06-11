"""Tests for JsonDefaultModel mixin and model_dump defaults.

Verifies that the JsonDefaultModel base class correctly defaults
mode='json' for all model hierarchies, and that BaseResource
preserves its warnings=False default.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from endorlabs.resources.base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
    Context,
    JsonDefaultModel,
    TenantMeta,
)


class TestJsonDefaultModelDirectly:
    """JsonDefaultModel itself defaults to mode='json'."""

    def test_model_dump_defaults_to_json_mode(self) -> None:
        """model_dump() without args should use mode='json'."""

        class Simple(JsonDefaultModel):
            value: str = "hello"

        obj = Simple()
        result = obj.model_dump()
        assert isinstance(result, dict)
        assert result["value"] == "hello"

    def test_model_dump_mode_python_still_works(self) -> None:
        """Explicit mode='python' must be honoured."""

        class Simple(JsonDefaultModel):
            value: str = "hello"

        obj = Simple()
        result = obj.model_dump(mode="python")
        assert result["value"] == "hello"


class TestSubclassesInheritJsonDefault:
    """TenantMeta, Context, BaseMeta, BaseSpec all inherit mode='json'."""

    def test_tenant_meta_json_mode(self) -> None:
        tm = TenantMeta(namespace="test")
        d = tm.model_dump()
        assert d["namespace"] == "test"

    def test_context_json_mode(self) -> None:
        ctx = Context(type="scan")
        d = ctx.model_dump()
        assert d["type"] == "scan"
        assert d["id"] == "default"

    def test_base_meta_json_mode(self) -> None:
        bm = BaseMeta(name="res", kind="Project")
        d = bm.model_dump()
        assert d["name"] == "res"

    def test_base_spec_json_mode(self) -> None:
        bs = BaseSpec()
        d = bs.model_dump()
        assert isinstance(d, dict)


class TestBaseResourceWarningsDefault:
    """BaseResource overrides warnings=False (suppress nested-model warnings)."""

    def test_base_resource_warnings_false_by_default(self) -> None:
        """BaseResource.model_dump() should not raise warnings for nested models."""

        class Minimal(BaseResource):
            uuid: str = Field(..., description="id")

        obj = Minimal(
            uuid="abc",
            meta=BaseMeta(name="x"),
            tenant_meta=TenantMeta(namespace="ns"),
        )
        # Should not raise / emit warnings
        d = obj.model_dump()
        assert d["uuid"] == "abc"

    def test_base_resource_mode_python_explicit(self) -> None:
        """mode='python' still works on BaseResource."""

        class Minimal(BaseResource):
            uuid: str = Field(..., description="id")

        obj = Minimal(
            uuid="abc",
            meta=BaseMeta(name="x"),
            tenant_meta=TenantMeta(namespace="ns"),
        )
        d: dict[str, Any] = obj.model_dump(mode="python")
        assert d["uuid"] == "abc"
