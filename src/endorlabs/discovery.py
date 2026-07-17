"""Programmatic SDK discovery for consumer agents and IDE tooling."""

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import override

from .agent_knowledge import (
    agent_knowledge_bootstrap_paths,
    agent_knowledge_dir,
    agent_knowledge_index_path,
    agent_knowledge_manifest_path,
)

try:
    __version__ = importlib.metadata.version("endorlabs")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0.dev0"

_ENDOR_CONSOLE_SCRIPT_PREFIX = "endor-"


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
    agent_bootstrap_module: str
    entry_points: tuple[str, ...]

    @override
    def __str__(self) -> str:
        """Human-readable discovery map (use instead of the dataclass repr)."""
        return _format_discovery(self)


def _endor_console_script_names() -> tuple[str, ...]:
    """Return endorlabs workflow CLI names from this environment."""
    try:
        raw_eps = importlib.metadata.entry_points(group="console_scripts")
        return tuple(
            sorted(
                ep.name
                for ep in raw_eps
                if ep.name.startswith(_ENDOR_CONSOLE_SCRIPT_PREFIX)
            )
        )
    except Exception:
        return ()


def _bootstrap_path_label(path: Path, bundle: Path) -> str:
    try:
        return path.relative_to(bundle).as_posix()
    except ValueError:
        return path.as_posix()


def _format_discovery(d: SdkDiscovery) -> str:
    bundle = d.index.parent
    lines = [f"endorlabs {d.version}"]
    lines.append(f"index: {d.index.as_posix()}")
    lines.append(f"agents_guide: {d.agents_guide.as_posix()}")
    lines.append(f"stub: {d.stub.as_posix()}")
    if d.resource_routes is not None:
        lines.append(f"resource_routes: {d.resource_routes.as_posix()}")
    lines.append("bootstrap_paths:")
    lines.extend(
        f"  - {_bootstrap_path_label(path, bundle)}" for path in d.bootstrap_paths
    )
    if d.entry_points:
        shown = d.entry_points[:12]
        suffix = ""
        if len(d.entry_points) > 12:
            suffix = f", ... (+{len(d.entry_points) - 12} more)"
        lines.append(f"entry_points: {', '.join(shown)}{suffix}")
    lines.append(f"run: python -m {d.agent_bootstrap_module} [--dry-run]")
    return "\n".join(lines)


def discover() -> SdkDiscovery:
    """Return paths for agent bootstrap (read before ``Client()``)."""
    bundle = agent_knowledge_dir()
    routes = bundle / "reference" / "resource-routes.md"
    client_surface = import_module("endorlabs.client_surface")
    module_file = client_surface.__file__
    if module_file is None:
        raise RuntimeError("endorlabs.client_surface has no __file__")
    stub_path = Path(module_file).resolve().with_suffix(".pyi")
    return SdkDiscovery(
        version=__version__,
        index=agent_knowledge_index_path(),
        manifest=agent_knowledge_manifest_path(),
        bootstrap_paths=tuple(agent_knowledge_bootstrap_paths()),
        agents_guide=bundle / "AGENTS.md",
        stub=stub_path,
        contracts_dir=bundle / "contracts",
        resource_routes=routes if routes.is_file() else None,
        agent_bootstrap_module="endorlabs.examples.agent_bootstrap",
        entry_points=_endor_console_script_names(),
    )
