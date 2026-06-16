"""Tests for endorlabs.discover() day-0 discovery API."""

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
    assert d.day0_module == "endorlabs.examples.day0"


def test_discover_bootstrap_includes_resource_discovery_contract() -> None:
    d = endorlabs.discover()
    bootstrap = agent_knowledge_bootstrap_paths()
    assert tuple(bootstrap) == d.bootstrap_paths
    assert any("resource-discovery" in path.name for path in d.bootstrap_paths)


def test_discover_dry_run_day0() -> None:
    from endorlabs.examples.day0 import main

    assert main(["--dry-run"]) == 0
