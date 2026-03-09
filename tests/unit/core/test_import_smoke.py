"""Import smoke tests for public and optional SDK boundaries."""

from __future__ import annotations

import importlib
import sys

import pytest


def test_public_imports_smoke() -> None:
    """Top-level SDK import should expose core public symbols."""
    import endorlabs
    from endorlabs import Client, F

    assert endorlabs is not None
    assert Client is not None
    assert F is not None


def test_internal_namespace_imports_smoke() -> None:
    """Internal core namespace should be importable."""
    import endorlabs.core as core

    assert core is not None


def test_optional_agent_error_path_when_deps_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Agent entrypoint should provide install guidance when deps are absent."""
    for module_name in list(sys.modules):
        if module_name.startswith("endorlabs.agent.langgraph_agent"):
            del sys.modules[module_name]

    monkeypatch.setitem(sys.modules, "langgraph", None)
    monkeypatch.setitem(sys.modules, "langchain_core", None)
    monkeypatch.setitem(sys.modules, "langchain_openai", None)

    module = importlib.import_module("endorlabs.agent.langgraph_agent")

    with pytest.raises(
        ImportError,
        match=r"Install with: pip install endorlabs-sdk\[agent\]",
    ):
        module.create_endor_graph()
