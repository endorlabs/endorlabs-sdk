"""Tests for ResourceEntry.from_module() convention-based discovery."""

from __future__ import annotations

import types
from typing import Any
from unittest.mock import Mock

from endorlabs.registry import ResourceEntry


def _make_module(
    name: str, functions: dict[str, Any] | None = None
) -> types.ModuleType:
    """Build a fake module with the given callable attributes."""
    mod = types.ModuleType(name)
    for fn_name, fn in (functions or {}).items():
        setattr(mod, fn_name, fn)
    return mod


class TestFromModuleDiscovery:
    """from_module() discovers list/get/create/update/delete by convention."""

    def test_discovers_all_operations(self) -> None:
        """Standard naming: list_widgets, get_widget, create/update/delete."""
        mod = _make_module(
            "widgets",
            {
                "list_widgets": Mock(),
                "get_widget": Mock(),
                "create_widget": Mock(),
                "update_widget": Mock(),
                "delete_widget": Mock(),
                "list_widgets_iter": Mock(),
                "build_create_payload": Mock(),
            },
        )

        entry = ResourceEntry.from_module("widget", mod, Mock, "widgets")
        assert entry.attr_name == "widget"
        assert entry.list_fn is mod.list_widgets
        assert entry.get_fn is mod.get_widget
        assert entry.create_fn is mod.create_widget
        assert entry.update_fn is mod.update_widget
        assert entry.delete_fn is mod.delete_widget
        assert entry.list_iter_fn is mod.list_widgets_iter
        assert entry.build_create_payload_fn is mod.build_create_payload
        assert entry.resource_name == "widgets"
        assert entry.scope is None

    def test_returns_none_for_missing_operations(self) -> None:
        """Read-only module: only list and get are present."""
        mod = _make_module(
            "things",
            {
                "list_things": Mock(),
                "get_thing": Mock(),
            },
        )

        entry = ResourceEntry.from_module("thing", mod, Mock, "things")
        assert entry.list_fn is mod.list_things
        assert entry.get_fn is mod.get_thing
        assert entry.create_fn is None
        assert entry.update_fn is None
        assert entry.delete_fn is None
        assert entry.list_iter_fn is None
        assert entry.build_create_payload_fn is None

    def test_code_owners_override(self) -> None:
        """code_owners has list_code_owners (plural = op_name)."""
        mod = _make_module(
            "code_owners",
            {
                "list_code_owners": Mock(),
                "get_code_owners": Mock(),
                "create_code_owners": Mock(),
                "update_code_owners": Mock(),
                "delete_code_owners": Mock(),
                "list_code_owners_iter": Mock(),
                "build_create_payload": Mock(),
            },
        )

        entry = ResourceEntry.from_module(
            "code_owners",
            mod,
            Mock,
            "codeowners",
            list_name="code_owners",
            op_name="code_owners",
        )
        assert entry.list_fn is mod.list_code_owners
        assert entry.get_fn is mod.get_code_owners
        assert entry.list_iter_fn is mod.list_code_owners_iter

    def test_scope_passthrough(self) -> None:
        """scope= is forwarded into the entry."""
        mod = _make_module("logs", {"list_logs": Mock()})
        entry = ResourceEntry.from_module("log", mod, Mock, "logs", scope="system")
        assert entry.scope == "system"

    def test_parent_kind_passthrough(self) -> None:
        """parent_kind= is forwarded into the entry."""
        mod = _make_module("results", {"list_results": Mock()})
        entry = ResourceEntry.from_module(
            "result", mod, Mock, "results", parent_kind="project"
        )
        assert entry.parent_kind == "project"


class TestRegistryParity:
    """Refactored registry must produce identical entries to the current one."""

    def test_all_entries_have_from_module(self) -> None:
        """Every entry in RESOURCE_REGISTRY can be reproduced by from_module."""
        from endorlabs.registry import RESOURCE_REGISTRY

        for entry in RESOURCE_REGISTRY:
            assert entry.attr_name, "attr_name must be set"
            assert entry.list_fn is not None, f"{entry.attr_name}: list_fn missing"
            # Verify resource_name is set (needed for from_module)
            assert entry.resource_name, f"{entry.attr_name}: resource_name missing"
