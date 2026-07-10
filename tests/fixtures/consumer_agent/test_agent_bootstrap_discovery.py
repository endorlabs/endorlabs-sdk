"""Agent-style discovery checks (Read stub, no Pyright inheritance)."""

from __future__ import annotations

import endorlabs


def _facade_section(stub_text: str, class_name: str) -> str:
    start = stub_text.index(f"class {class_name}")
    end = stub_text.find("\nclass _", start + 1)
    if end == -1:
        end = stub_text.find("\nclass Client:", start + 1)
    return stub_text[start:end]


def test_bootstrap_includes_resource_discovery_contract() -> None:
    paths = endorlabs.agent_knowledge_bootstrap_paths()
    assert any(path.name == "resource-discovery.md" for path in paths)


def test_stub_flat_search_by_name_on_project_facade() -> None:
    d = endorlabs.discover()
    section = _facade_section(d.stub.read_text(encoding="utf-8"), "_ProjectFacade")
    assert "def search_by_name(" in section


def test_discover_agents_guide_points_to_index() -> None:
    d = endorlabs.discover()
    assert d.agents_guide.is_file()
    text = d.agents_guide.read_text(encoding="utf-8")
    assert "INDEX.md" in text
    assert d.index.name in text


def test_resource_routes_shipped_when_present() -> None:
    d = endorlabs.discover()
    if d.resource_routes is not None:
        assert d.resource_routes.is_file()
        assert "list_by_project" in d.resource_routes.read_text(encoding="utf-8")
