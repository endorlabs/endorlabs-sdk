"""Characterization tests for LangGraph SDK tool generation."""

import importlib
import sys
import types
from types import SimpleNamespace

import pytest


class _StubTool:
    """Minimal StructuredTool-compatible object for unit tests."""

    def __init__(self, func: object, name: str, description: str) -> None:
        super().__init__()
        self.func = func
        self.name = name
        self.description = description


class _StubStructuredTool:
    """Stub replacement for langchain_core.tools.StructuredTool."""

    @staticmethod
    def from_function(func: object, name: str, description: str) -> _StubTool:
        return _StubTool(func=func, name=name, description=description)


@pytest.fixture
def tool_module(monkeypatch: pytest.MonkeyPatch):
    """Import tools module with stubbed langchain_core dependency."""
    stub_langchain_core = types.ModuleType("langchain_core")
    stub_langchain_core_tools = types.ModuleType("langchain_core.tools")
    stub_langchain_core_tools.StructuredTool = _StubStructuredTool
    stub_langchain_core.tools = stub_langchain_core_tools

    monkeypatch.setitem(sys.modules, "langchain_core", stub_langchain_core)
    monkeypatch.setitem(sys.modules, "langchain_core.tools", stub_langchain_core_tools)

    module_name = "endorlabs.agent.langgraph_agent.tools"
    if module_name in sys.modules:
        del sys.modules[module_name]
    return importlib.import_module(module_name)


def _build_fake_client(tool_module: object) -> object:
    """Create a fake client exposing every registry attribute."""
    client = SimpleNamespace()
    for entry in tool_module.RESOURCE_REGISTRY:
        setattr(
            client,
            entry.attr_name,
            SimpleNamespace(
                list=lambda **_kwargs: [],
                get=lambda _uuid, **_kwargs: None,
            ),
        )
    return client


class TestLanggraphTools:
    """Characterization tests for tool creation behavior."""

    def test_create_tools_respects_supported_ops(self, tool_module: object) -> None:
        """Tools should only be generated for operations in supported_ops."""
        client = _build_fake_client(tool_module)
        tools = tool_module.create_tools(client)
        tool_names = {t.name for t in tools}

        entry_map = {entry.attr_name: entry for entry in tool_module.RESOURCE_REGISTRY}
        for attr_name, entry in entry_map.items():
            list_name = f"list_{attr_name}"
            get_name = f"get_{attr_name}"
            if attr_name == "finding":
                # finding has a custom list tool name
                continue
            assert (list_name in tool_names) == ("list" in entry.supported_ops)
            assert (get_name in tool_names) == ("get" in entry.supported_ops)

    def test_findings_tools_include_custom_list(self, tool_module: object) -> None:
        """findings include custom list tool and get tool."""
        client = _build_fake_client(tool_module)
        tools = tool_module.create_tools(client)
        tool_names = {t.name for t in tools}
        assert "list_findings" in tool_names
        assert "get_finding" in tool_names

    def test_list_findings_defaults_to_traverse_without_namespace(
        self, tool_module: object
    ) -> None:
        """When namespace is omitted, findings list should traverse by default."""
        calls: list[dict[str, object]] = []

        def _finding_list(**kwargs):
            calls.append(kwargs)
            return []

        client = _build_fake_client(tool_module)
        client.finding = SimpleNamespace(
            list=_finding_list,
            get=lambda _uuid, **_kwargs: None,
        )
        tools = tool_module.create_tools(client)
        list_findings = next(t for t in tools if t.name == "list_findings")

        list_findings.func()

        assert calls
        assert calls[0].get("traverse") is True

    def test_list_findings_respects_explicit_non_traverse_with_namespace(
        self, tool_module: object
    ) -> None:
        """Explicit traverse=False with namespace should stay local scope."""
        calls: list[dict[str, object]] = []

        def _finding_list(**kwargs):
            calls.append(kwargs)
            return []

        client = _build_fake_client(tool_module)
        client.finding = SimpleNamespace(
            list=_finding_list,
            get=lambda _uuid, **_kwargs: None,
        )
        tools = tool_module.create_tools(client)
        list_findings = next(t for t in tools if t.name == "list_findings")

        list_findings.func(namespace="tenant.team", traverse=False)

        assert calls
        assert "traverse" not in calls[0]
