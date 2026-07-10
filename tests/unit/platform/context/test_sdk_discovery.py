"""Tests for endorlabs.discover() agent bootstrap discovery API."""

from __future__ import annotations

import endorlabs
from endorlabs.agent_knowledge import agent_knowledge_bootstrap_paths


def test_discover_paths_exist() -> None:
    d = endorlabs.discover()
    assert d.version == endorlabs.__version__
    assert d.index.is_file()
    assert d.manifest.is_file()
    assert d.stub.is_file()
    assert d.stub.name == "client_surface.pyi"
    assert d.contracts_dir.is_dir()
    assert d.agents_guide.is_file()
    assert d.agent_bootstrap_module == "endorlabs.examples.agent_bootstrap"


def test_discover_bootstrap_includes_resource_discovery_contract() -> None:
    d = endorlabs.discover()
    bootstrap = agent_knowledge_bootstrap_paths()
    assert tuple(bootstrap) == d.bootstrap_paths
    assert any("resource-discovery" in path.name for path in d.bootstrap_paths)


def test_discover_dry_run_agent_bootstrap() -> None:
    from endorlabs.examples.agent_bootstrap import main

    assert main(["--dry-run"]) == 0


def test_discover_str_is_human_readable() -> None:
    d = endorlabs.discover()
    text = str(d)
    assert f"endorlabs {d.version}" in text
    assert d.index.as_posix() in text
    assert d.agents_guide.as_posix() in text
    assert d.stub.as_posix() in text
    assert "bootstrap_paths:" in text
    for path in d.bootstrap_paths:
        assert path.as_posix() in text or path.name in text
    assert "SdkDiscovery(" not in text


def test_discover_entry_points_are_endor_only() -> None:
    d = endorlabs.discover()
    assert all(name.startswith("endor-") for name in d.entry_points)
    assert "pip" not in d.entry_points
    assert "httpx" not in d.entry_points
