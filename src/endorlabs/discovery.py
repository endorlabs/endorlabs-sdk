"""Programmatic SDK discovery for consumer agents and IDE tooling."""

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

from .agent_knowledge import (
    agent_knowledge_bootstrap_paths,
    agent_knowledge_dir,
    agent_knowledge_index_path,
    agent_knowledge_manifest_path,
)

try:
    from endorlabs._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"


@dataclass(frozen=True)
class SdkDiscovery:
    """Wheel-shipped discovery paths for agents without SDK repo access."""

    version: str
    index: Path
    manifest: Path
    bootstrap_paths: tuple[Path, ...]
    agents_guide: Path
    stub: Path
    contracts_dir: Path
    resource_routes: Path | None
    day0_module: str
    entry_points: tuple[str, ...]


def discover() -> SdkDiscovery:
    """Return paths for day-0 agent onboarding (read before ``Client()``)."""
    bundle = agent_knowledge_dir()
    routes = bundle / "reference" / "resource-routes.md"
    client_surface = import_module("endorlabs.client_surface")
    module_file = client_surface.__file__
    if module_file is None:
        raise RuntimeError("endorlabs.client_surface has no __file__")
    stub_path = Path(module_file).resolve().with_suffix(".pyi")
    try:
        raw_eps = importlib.metadata.entry_points(group="console_scripts")
        eps = tuple(sorted(ep.name for ep in raw_eps))
    except Exception:
        eps = ()
    return SdkDiscovery(
        version=__version__,
        index=agent_knowledge_index_path(),
        manifest=agent_knowledge_manifest_path(),
        bootstrap_paths=tuple(agent_knowledge_bootstrap_paths()),
        agents_guide=bundle / "AGENTS.md",
        stub=stub_path,
        contracts_dir=bundle / "contracts",
        resource_routes=routes if routes.is_file() else None,
        day0_module="endorlabs.examples.day0",
        entry_points=eps,
    )
